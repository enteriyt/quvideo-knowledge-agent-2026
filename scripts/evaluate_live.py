"""Execute the same acceptance fixtures against an actual configured model service."""
import json
import argparse
from pathlib import Path
from evaluate import CASES, ROOT
from knowledge_agent.core import Agent, KnowledgeTools, OpenAICompatibleModel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", choices=[c[0] for c in CASES], default=[],
                        help="Rerun selected cases, retaining existing actual outputs for other cases")
    selected = parser.parse_args().case
    model = OpenAICompatibleModel()
    documents = json.loads((ROOT / "data/documents.json").read_text(encoding="utf-8"))
    summary = []
    for name, request, expected in CASES:
        directory = ROOT / "examples" / "live" / name
        if selected and name not in selected:
            result = json.loads((directory / "output.json").read_text(encoding="utf-8"))
        else:
            result = Agent(model, KnowledgeTools(documents, request.get("failures")), 12).run(
                request["question"], request.get("history"))
            directory.mkdir(parents=True, exist_ok=True)
            for filename, value in [("input.json", request), ("output.json", result), ("trace.json", result["trace"])]:
                (directory / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        item = {"case": name, "expected": expected, "actual": result["status"],
                "passed": result["status"] == expected, "steps": result["steps"],
                "elapsed_seconds": result["elapsed_seconds"], "mode": result["mode"]}
        summary.append(item)
        print(json.dumps(item, ensure_ascii=False), flush=True)
    report = {"mode": "live_model", "model": model.model, "local_inference": model.local,
              "passed": sum(c["passed"] for c in summary), "total": len(summary), "cases": summary}
    (ROOT / "examples" / "live" / "evaluation-summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if all(c["passed"] for c in summary) else 1


if __name__ == "__main__":
    raise SystemExit(main())
