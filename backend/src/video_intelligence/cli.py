from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from video_intelligence.config import PipelineConfig, ProcessingProfile
from video_intelligence.errors import VideoIntelligenceError
from video_intelligence.export import export_result
from video_intelligence.fusion import analyze_evidence
from video_intelligence.media import MediaValidationConfig, probe_media
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
    inspect = commands.add_parser("inspect-media")
    inspect.add_argument("--input", type=Path, required=True)
    inspect.add_argument("--output", type=Path, required=True)
    inspect.add_argument("--require-audio", action="store_true")
    inspect.add_argument("--confirm-authorized", action="store_true")
    inspect.add_argument("--overwrite", action="store_true")
    return parser


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value: dict[str, Any] = json.load(handle)
    return value


def _analyze_evidence(args: argparse.Namespace) -> int:
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
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")
    return 0


def _inspect_media(args: argparse.Namespace) -> int:
    if not args.confirm_authorized:
        print("Media inspection requires --confirm-authorized.")
        return 2
    if args.output.suffix.casefold() != ".json":
        print("Media inspection output must use a .json extension.")
        return 2
    if args.output.exists() and not args.overwrite:
        print("Media inspection output already exists; use --overwrite to replace it.")
        return 2
    report = probe_media(
        args.input,
        config=MediaValidationConfig(require_audio=args.require_audio),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.output}")
    return 0 if report.valid else 3


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "analyze-evidence":
            return _analyze_evidence(args)
        return _inspect_media(args)
    except VideoIntelligenceError as exc:
        print(json.dumps(exc.detail.model_dump(mode="json"), indent=2))
        return 2
    except (OSError, KeyError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        print(f"Command failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
