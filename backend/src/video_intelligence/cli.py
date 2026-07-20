from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from video_intelligence.config import PipelineConfig, ProcessingProfile
from video_intelligence.export import export_result
from video_intelligence.fusion import analyze_evidence
from video_intelligence.models import EvidenceItem, Platform, Source


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="video-intelligence")
    commands = parser.add_subparsers(dest="command", required=True)
    analyze = commands.add_parser("analyze-evidence")
    analyze.add_argument("--input", type=Path, required=True)
    analyze.add_argument(
        "--profile", choices=[item.value for item in ProcessingProfile], default="balanced"
    )
    analyze.add_argument("--output-dir", type=Path, required=True)
    return parser


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value: dict[str, Any] = json.load(handle)
    return value


def main() -> int:
    args = _parser().parse_args()
    try:
        payload = _load(args.input)
        evidence = [EvidenceItem.model_validate(item) for item in payload["evidence_items"]]
        result = analyze_evidence(
            evidence,
            source=Source.model_validate(
                payload.get("source", {"uri": str(args.input), "authorized": True})
            ),
            platform=Platform(payload.get("platform", "synthetic")),
            title=payload.get("title", args.input.stem),
            config=PipelineConfig(profile=ProcessingProfile(args.profile)),
        )
        json_path, markdown_path = export_result(result, args.output_dir)
    except (OSError, KeyError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        print(f"Analysis failed: {exc}")
        return 2
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
