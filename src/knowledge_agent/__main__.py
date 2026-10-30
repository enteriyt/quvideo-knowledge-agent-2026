import argparse
import json
from pathlib import Path
from .core import Agent, KnowledgeTools, OfflineMock, OpenAICompatibleModel


def main():
    parser = argparse.ArgumentParser(description="Evidence-grounded knowledge agent; offline mode is a test double")
    parser.add_argument("--input", type=Path, required=True, help="JSON question/history/failures")
    parser.add_argument("--data", type=Path, default=Path("data/documents.json"))
    parser.add_argument("--mode", choices=["mock", "live"], default="mock")
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        request = json.loads(args.input.read_text(encoding="utf-8-sig"))
        documents = json.loads(args.data.read_text(encoding="utf-8-sig"))
        model = OfflineMock() if args.mode == "mock" else OpenAICompatibleModel()
        result = Agent(model, KnowledgeTools(documents, request.get("failures")), args.max_steps).run(
            request.get("question", ""), request.get("history"))
        rendered = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        return 0 if result["status"] != "incomplete" else 2
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "incomplete", "error": type(exc).__name__,
                          "message": "Check input/data schema, paths and model configuration"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
