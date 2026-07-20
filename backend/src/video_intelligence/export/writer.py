from __future__ import annotations

import json
from pathlib import Path

from video_intelligence.models import AnalysisResult


def _markdown(result: AnalysisResult) -> str:
    lines = [
        f"# {result.title}",
        "",
        f"**Takeaway:** {result.one_sentence_takeaway}",
        "",
        result.concise_summary,
        "",
        "## Key points",
        "",
    ]
    for point in result.key_points:
        refs = ", ".join(point["evidence_ids"])
        lines.append(f"- {point['text']} _(evidence: {refs})_")
    if result.contradictions:
        lines.extend(["", "## Contradictions", ""])
        for claim in result.claims:
            if claim.claim_id in result.contradictions:
                refs = ", ".join(claim.contradicting_evidence_ids)
                lines.append(f"- {claim.statement} _(contradicted by: {refs})_")
    if result.uncertainties:
        lines.extend(["", "## Uncertainties", ""])
        lines.extend(f"- Evidence `{item_id}` is uncertain." for item_id in result.uncertainties)
    return "\n".join(lines) + "\n"


def export_result(result: AnalysisResult, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "analysis.json"
    markdown_path = output_dir / "summary.md"
    json_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_markdown(result), encoding="utf-8")
    return json_path, markdown_path
