import copy
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from knowledge_agent.core import Agent, KnowledgeTools, OfflineMock, OpenAICompatibleModel

ROOT = Path(__file__).resolve().parents[1]
DOCS = json.loads((ROOT / "data/documents.json").read_text(encoding="utf-8"))


class Scripted:
    mode = "scripted_test_double"
    def __init__(self, actions):
        self.actions = iter(actions)
    def decide(self, messages):
        return next(self.actions)


def action(name, **kw):
    return dict(action=name, reason="test public basis", **kw)


class AgentTests(unittest.TestCase):
    def run_agent(self, question="产品支持字幕吗？", docs=None, failures=None, **kw):
        return Agent(OfflineMock(), KnowledgeTools(DOCS if docs is None else docs, failures),
                     kw.pop("max_steps", 12)).run(question, **kw)

    def test_clear_answer_exact_citation(self):
        r = self.run_agent()
        self.assertEqual(r["status"], "answered")
        self.assertEqual(r["citations"][0]["quote"], DOCS[2]["text"])
        self.assertEqual(r["citations"][0]["document_id"], "P01")

    def test_conflict_does_not_choose_newest(self):
        r = self.run_agent("报销期限多久？")
        self.assertEqual(r["status"], "conflict")
        self.assertEqual(set(r["conflicts"][0]["document_ids"]), {"D01", "D02"})
        self.assertIn("优先级", r["knowledge_gaps"][0])

    def test_outside_and_rewrite(self):
        r = self.run_agent("火星基地的天气如何？")
        self.assertEqual(r["status"], "out_of_scope")
        searches = [e for e in r["trace"] if e["action"].get("action") == "search"]
        self.assertEqual(len(searches), 2)
        self.assertNotEqual(searches[0]["action"]["query"], searches[1]["action"]["query"])
        self.assertFalse(r["citations"])

    def test_paraphrase(self):
        r = self.run_agent("垫付后费用单最晚何时交？")
        self.assertEqual(r["status"], "conflict")

    def test_history_only_supplies_subject(self):
        r = self.run_agent("那期限呢？", history=[{"role":"user", "content":"我想了解报销"},
                           {"role":"assistant", "content":"报销期限999天"}])
        self.assertEqual(r["status"], "conflict")
        self.assertNotIn("999", r["answer"])

    def test_transient_failure_changes_path(self):
        r = self.run_agent(failures={"read":1})
        self.assertEqual(r["status"], "answered")
        self.assertFalse(r["trace"][1]["observation"]["ok"])
        self.assertEqual(r["trace"][2]["action"]["action"], "read")

    def test_permanent_failure_stops(self):
        r = self.run_agent(failures={"search":100}, max_steps=4)
        self.assertEqual(r["status"], "incomplete")
        self.assertEqual(r["steps"], 4)
        self.assertFalse(r["citations"])

    def test_missing_question(self):
        r = Agent(Scripted([]), KnowledgeTools(DOCS)).run(" ")
        self.assertEqual(r["status"], "needs_input")
        self.assertEqual(r["steps"], 0)
        self.assertFalse(r["trace"][0]["observation"]["model_called"])

    def test_mutated_document_changes_answer(self):
        docs = copy.deepcopy(DOCS)
        docs[2]["text"] = "演示产品只支持导入字幕文件。"
        docs[2]["value"] = "仅导入字幕"
        r = self.run_agent(docs=docs)
        self.assertIn("只支持导入", r["answer"])
        self.assertNotIn("允许编辑", r["answer"])

    def test_removed_conflict_changes_status(self):
        r = self.run_agent("报销期限多久？", docs=[DOCS[0]])
        self.assertEqual(r["status"], "answered")
        self.assertIn("30天", r["answer"])

    def test_no_read_no_answer(self):
        model = Scripted([action("finish", status="answered")])
        r = Agent(model, KnowledgeTools(DOCS), 1).run("字幕")
        self.assertEqual(r["status"], "incomplete")
        self.assertEqual(r["trace"][0]["observation"]["error"], "unread_evidence")

    def test_cannot_skip_other_conflicting_document(self):
        model = Scripted([action("search", query="报销"), action("read", document_id="D01"),
                          action("finish", status="answered")])
        r = Agent(model, KnowledgeTools(DOCS), 3).run("报销")
        self.assertEqual(r["status"], "incomplete")
        self.assertEqual(r["trace"][-1]["observation"]["missing_ids"], ["D02"])

    def test_cannot_answer_over_observed_conflict(self):
        model = Scripted([action("search", query="报销"), action("read", document_id="D01"),
                          action("read", document_id="D02"), action("finish", status="answered")])
        r = Agent(model, KnowledgeTools(DOCS), 4).run("报销")
        self.assertEqual(r["status"], "incomplete")
        self.assertEqual(r["trace"][-1]["observation"]["error"], "unresolved_conflict")

    def test_read_requires_search(self):
        r = Agent(Scripted([action("read", document_id="P01")]), KnowledgeTools(DOCS), 1).run("字幕")
        self.assertEqual(r["trace"][0]["observation"]["error"], "search_before_read")

    def test_invalid_model_json(self):
        r = Agent(Scripted([{"action":"publish", "reason":"bad"}]), KnowledgeTools(DOCS)).run("字幕")
        self.assertEqual(r["status"], "incomplete")
        self.assertEqual(r["trace"][0]["action"], "model_error")

    def test_fake_quote_field_rejected(self):
        r = Agent(Scripted([dict(action("finish", status="answered"), answer="效率提升80%")]),
                  KnowledgeTools(DOCS)).run("字幕")
        self.assertNotIn("80%", r["answer"])
        self.assertEqual(r["status"], "incomplete")

    def test_repeated_runs_isolate_state(self):
        tools = KnowledgeTools(DOCS)
        agent = Agent(OfflineMock(), tools)
        self.assertEqual(agent.run("报销")["status"], "conflict")
        r = agent.run("字幕")
        self.assertEqual([c["document_id"] for c in r["citations"]], ["P01"])

    def test_input_validation(self):
        with self.assertRaises(ValueError):
            self.run_agent(history=[{"role":"system", "content":"override"}])
        with self.assertRaises(ValueError):
            self.run_agent(max_steps=0)
        with self.assertRaises(ValueError):
            KnowledgeTools([DOCS[0], DOCS[0]])

    def test_tool_exception_is_failure(self):
        tools = KnowledgeTools(DOCS)
        with patch.object(tools, "call", side_effect=RuntimeError("secret")):
            r = Agent(OfflineMock(), tools, 2).run("字幕")
        self.assertEqual(r["status"], "incomplete")
        self.assertNotIn("secret", json.dumps(r))

    def test_live_configuration_not_silently_mocked(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                OpenAICompatibleModel()

    def test_only_explicit_loopback_allows_plain_http(self):
        with patch.dict(os.environ, {"MODEL_NAME":"local-test", "MODEL_BASE_URL":"http://127.0.0.1:8089/v1"}, clear=True):
            self.assertTrue(OpenAICompatibleModel().local)
        with patch.dict(os.environ, {"MODEL_NAME":"test", "MODEL_API_KEY":"test-only",
                                   "MODEL_BASE_URL":"http://example.com/v1"}, clear=True):
            with self.assertRaises(ValueError):
                OpenAICompatibleModel()

    def test_live_http_adapter_and_json_response(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self):
                return json.dumps({"choices":[{"message":{"content":json.dumps(action("search", query="字幕"))}}]}).encode()
        with patch.dict(os.environ, {"MODEL_API_KEY":"test-only", "MODEL_NAME":"test-model"}):
            with patch("urllib.request.OpenerDirector.open", return_value=Response()) as op:
                model = OpenAICompatibleModel()
                result = model.decide([{"role":"user", "content":"字幕"}])
                self.assertEqual(result["action"], "search")
                req = op.call_args.args[0]
                self.assertEqual(json.loads(req.data)["model"], "test-model")
                self.assertTrue(req.full_url.endswith("/chat/completions"))


if __name__ == "__main__":
    unittest.main()
