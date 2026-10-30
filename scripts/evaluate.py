"""Reproduce offline fixtures and test results; never labels these as live-model traces."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from knowledge_agent.core import Agent, KnowledgeTools, OfflineMock

CASES = [
    ("01-clear", {"question":"产品支持字幕吗？"}, "answered"),
    ("02-conflict", {"question":"报销期限多久？"}, "conflict"),
    ("03-outside", {"question":"火星基地的天气如何？"}, "out_of_scope"),
    ("04-paraphrase", {"question":"垫付后费用单最晚何时交？"}, "conflict"),
    ("05-follow-up", {"question":"那期限呢？", "history":[{"role":"user","content":"我想了解报销流程"}]}, "conflict"),
    ("06-tool-recovery", {"question":"产品支持字幕吗？", "failures":{"read":1}}, "answered"),
    ("07-tool-unavailable", {"question":"产品支持字幕吗？", "failures":{"search":100}}, "incomplete"),
    ("08-missing-question", {"question":""}, "needs_input"),
]


def main():
    docs = json.loads((ROOT / "data/documents.json").read_text(encoding="utf-8"))
    summary = []
    for name, request, expected in CASES:
        directory = ROOT / "examples" / name
        directory.mkdir(parents=True, exist_ok=True)
        result = Agent(OfflineMock(), KnowledgeTools(docs, request.get("failures")), 12).run(
            request["question"], request.get("history"))
        for filename, value in [("input.json", request), ("output.json", result), ("trace.json", result["trace"])]:
            (directory / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summary.append({"case":name, "expected":expected, "actual":result["status"],
                        "passed":result["status"] == expected, "steps":result["steps"], "mode":result["mode"]})
    environment = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    process = subprocess.run([sys.executable, "-X", "utf8", "-m", "unittest", "discover", "-s", "tests", "-v"],
                             cwd=ROOT, env=environment, capture_output=True, text=True, encoding="utf-8")
    (ROOT / "examples" / "test-results.txt").write_text(process.stdout + process.stderr, encoding="utf-8")
    report = {"mode":"offline_mock", "live_model_executed":False, "cases":summary,
              "test_exit_code":process.returncode, "python":sys.version,
              "command":"python scripts/evaluate.py"}
    (ROOT / "examples" / "evaluation-summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if process.returncode == 0 and all(c["passed"] for c in summary) else 1


if __name__ == "__main__":
    raise SystemExit(main())
