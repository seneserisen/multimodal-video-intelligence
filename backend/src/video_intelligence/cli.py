from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from video_intelligence.command_center import (
    command_center_start,
    command_center_status,
    command_center_stop,
    run_doctor,
    update_source,
)
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
    doctor = commands.add_parser("doctor")
    doctor.add_argument("--json", action="store_true")
    start = commands.add_parser("start")
    start.add_argument("--port", type=int, default=0)
    start.add_argument("--no-open", action="store_true")
    start.add_argument("--json", action="store_true")
    start.add_argument("--max-upload-mb", type=int, default=512)
    status = commands.add_parser("status")
    status.add_argument("--json", action="store_true")
    stop = commands.add_parser("stop")
    stop.add_argument("--json", action="store_true")
    update = commands.add_parser("update")
    update.add_argument("--apply", action="store_true")
    update.add_argument("--repository", type=Path, default=Path.cwd())
    update.add_argument("--json", action="store_true")
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


def _doctor(args: argparse.Namespace) -> int:
    report = run_doctor()
    if args.json:
        print(json.dumps(report.model_dump(mode="json"), indent=2))
    else:
        for check in report.checks:
            print(f"[{check.status.upper()}] {check.name}: {check.detail}")
            if check.recovery_action:
                print(f"  Recovery: {check.recovery_action}")
    return 0 if report.ready else 3


def _start(args: argparse.Namespace) -> int:
    if args.port < 0 or args.port > 65535:
        print("Port must be 0 or an integer between 1 and 65535.")
        return 2
    if args.max_upload_mb < 1 or args.max_upload_mb > 5120:
        print("Maximum upload size must be between 1 and 5120 MiB.")
        return 2
    result = command_center_start(
        port=args.port,
        open_browser=not args.no_open,
        max_upload_bytes=args.max_upload_mb * 1024**2,
    )
    if args.json:
        print(json.dumps(result.model_dump(mode="json"), indent=2))
    else:
        prefix = "Already running" if result.already_running else "Started"
        print(f"{prefix}: {result.status.host}:{result.status.port}")
        print(f"Dashboard: {result.dashboard_url}")
    return 0


def _status(args: argparse.Namespace) -> int:
    status = command_center_status()
    if args.json:
        print(json.dumps(status.model_dump(mode="json"), indent=2))
    else:
        print(f"{'Running' if status.running else 'Stopped'}: {status.message}")
        if status.running:
            print(f"Process {status.pid} on {status.host}:{status.port}")
    return 0 if status.running else 3


def _stop(args: argparse.Namespace) -> int:
    status = command_center_stop()
    if args.json:
        print(json.dumps(status.model_dump(mode="json"), indent=2))
    else:
        print(status.message)
    return 0


def _update(args: argparse.Namespace) -> int:
    report = update_source(repository=args.repository, apply=args.apply)
    if args.json:
        print(json.dumps(report.model_dump(mode="json"), indent=2))
    else:
        print(report.message)
        print(
            f"Branch {report.branch} tracks {report.upstream}; "
            f"ahead {report.ahead}, behind {report.behind}."
        )
    return 0


def main() -> int:
    args = _parser().parse_args()
    try:
        handlers = {
            "analyze-evidence": _analyze_evidence,
            "inspect-media": _inspect_media,
            "doctor": _doctor,
            "start": _start,
            "status": _status,
            "stop": _stop,
            "update": _update,
        }
        return handlers[args.command](args)
    except VideoIntelligenceError as exc:
        print(json.dumps(exc.detail.model_dump(mode="json"), indent=2))
        return 2
    except (OSError, KeyError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        print(f"Command failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
