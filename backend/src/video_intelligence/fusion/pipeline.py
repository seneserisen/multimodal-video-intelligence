from __future__ import annotations

import hashlib
import re
from collections import Counter
from difflib import SequenceMatcher

from video_intelligence.config import PipelineConfig
from video_intelligence.models import (
    AcquisitionAttempt,
    AcquisitionDiagnostic,
    AnalysisResult,
    AttemptOutcome,
    Claim,
    ClaimStatus,
    CoverageReport,
    EvidenceItem,
    Modality,
    Platform,
    Source,
    TimelineSegment,
)


def _normalized(text: str | None) -> str:
    return " ".join(re.findall(r"[\w.]+", (text or "").casefold()))


def _similarity(left: EvidenceItem, right: EvidenceItem) -> float:
    return SequenceMatcher(None, _normalized(left.text), _normalized(right.text)).ratio()


def _overlap(left: EvidenceItem, right: EvidenceItem) -> bool:
    if left.start_ms is None or right.start_ms is None:
        return True
    assert left.end_ms is not None and right.end_ms is not None
    return left.start_ms <= right.end_ms and right.start_ms <= left.end_ms


def _deduplicate_subtitles(
    evidence: list[EvidenceItem], threshold: float
) -> tuple[list[EvidenceItem], list[str]]:
    retained: list[EvidenceItem] = []
    removed: list[str] = []
    speech = [item for item in evidence if item.modality == Modality.SPEECH]
    for item in evidence:
        if item.modality == Modality.SCREEN_TEXT and item.evidence_type == "subtitle":
            duplicate = next(
                (
                    candidate
                    for candidate in speech
                    if _overlap(item, candidate) and _similarity(item, candidate) >= threshold
                ),
                None,
            )
            if duplicate is not None:
                duplicate.attributes.setdefault("deduplicated_evidence_ids", []).append(
                    item.evidence_id
                )
                removed.append(item.evidence_id)
                continue
        retained.append(item)
    return retained, removed


def _numbers(item: EvidenceItem) -> set[str]:
    return set(re.findall(r"\b\d+(?:\.\d+)?\b", item.text or item.description or ""))


def _is_contradiction(speech: EvidenceItem, screen: EvidenceItem) -> bool:
    spoken = _normalized(speech.text)
    shown = _normalized(screen.text)
    polarity_conflict = (
        ("all tests passed" in spoken or "tests passed" in spoken)
        and ("failed" in shown or "error" in shown)
    ) or ("success" in spoken and ("fail" in shown or "error" in shown))
    return polarity_conflict


def _make_claims(evidence: list[EvidenceItem]) -> list[Claim]:
    claims: list[Claim] = []
    paired: set[str] = set()
    speech_items = [item for item in evidence if item.modality == Modality.SPEECH]
    screen_items = [item for item in evidence if item.modality == Modality.SCREEN_TEXT]
    for speech in speech_items:
        for screen in screen_items:
            if not _overlap(speech, screen):
                continue
            if _is_contradiction(speech, screen):
                claims.append(
                    Claim(
                        claim_id=f"claim-contradiction-{len(claims) + 1}",
                        statement=speech.text or speech.description or "Spoken claim",
                        status=ClaimStatus.CONTRADICTED,
                        supporting_evidence_ids=[speech.evidence_id],
                        contradicting_evidence_ids=[screen.evidence_id],
                        confidence=min(speech.confidence, screen.confidence),
                        verification_note="Visible output conflicts with the spoken success claim.",
                    )
                )
                paired.update((speech.evidence_id, screen.evidence_id))
            elif _numbers(speech) & _numbers(screen):
                claims.append(
                    Claim(
                        claim_id=f"claim-confirmed-{len(claims) + 1}",
                        statement=speech.text or speech.description or "Confirmed claim",
                        status=ClaimStatus.CROSS_MODAL_CONFIRMED,
                        supporting_evidence_ids=[speech.evidence_id, screen.evidence_id],
                        confidence=min(speech.confidence, screen.confidence),
                        verification_note="A visible value confirms the spoken value.",
                    )
                )
                paired.update((speech.evidence_id, screen.evidence_id))

    for item in evidence:
        if item.evidence_id in paired:
            continue
        if item.uncertainty:
            status = ClaimStatus.UNCERTAIN
        elif item.modality == Modality.SPEECH:
            status = ClaimStatus.EXPLICITLY_SPOKEN
        elif item.modality == Modality.SCREEN_TEXT:
            status = ClaimStatus.SHOWN_ON_SCREEN
        elif item.modality == Modality.VISUAL_EVENT:
            status = ClaimStatus.DEMONSTRATED
        else:
            status = ClaimStatus.INFERRED
        claims.append(
            Claim(
                claim_id=f"claim-{len(claims) + 1}",
                statement=item.text or item.description or "Evidence finding",
                status=status,
                supporting_evidence_ids=[item.evidence_id],
                confidence=item.confidence,
                verification_note=(
                    "Uncertainty is preserved from the source evidence."
                    if item.uncertainty
                    else "Derived directly from one validated evidence item."
                ),
            )
        )
    return claims


def _segments(
    evidence: list[EvidenceItem], claims: list[Claim], config: PipelineConfig
) -> list[TimelineSegment]:
    timed = sorted(
        (item for item in evidence if item.start_ms is not None),
        key=lambda item: item.start_ms or 0,
    )
    groups: list[list[EvidenceItem]] = []
    for item in timed:
        if not groups:
            groups.append([item])
            continue
        previous_end = groups[-1][-1].end_ms
        assert previous_end is not None and item.start_ms is not None
        if item.start_ms - previous_end <= config.temporal_gap_ms:
            groups[-1].append(item)
        else:
            groups.append([item])
    untimed = [item for item in evidence if item.start_ms is None]
    if untimed:
        groups.append(untimed)

    claim_by_evidence: dict[str, list[Claim]] = {}
    for claim in claims:
        for evidence_id in claim.supporting_evidence_ids + claim.contradicting_evidence_ids:
            claim_by_evidence.setdefault(evidence_id, []).append(claim)

    output: list[TimelineSegment] = []
    for index, group in enumerate(groups, start=1):
        ids = {item.evidence_id for item in group}
        related = {claim.claim_id: claim for item_id in ids for claim in claim_by_evidence[item_id]}
        contradictions = [
            claim.claim_id for claim in related.values() if claim.status == ClaimStatus.CONTRADICTED
        ]
        confidence = sum(item.confidence for item in group) / len(group)
        weights = config.importance_weights
        score = weights.base + max(weights.modality[str(item.modality)] for item in group)
        if contradictions:
            score += weights.contradiction_bonus
        if any(claim.status == ClaimStatus.CROSS_MODAL_CONFIRMED for claim in related.values()):
            score += weights.confirmation_bonus
        if any(item.uncertainty for item in group):
            score -= weights.uncertainty_penalty
        starts = [item.start_ms for item in group if item.start_ms is not None]
        ends = [item.end_ms for item in group if item.end_ms is not None]
        output.append(
            TimelineSegment(
                segment_id=f"segment-{index}",
                start_ms=min(starts) if starts else None,
                end_ms=max(ends) if ends else None,
                topic=(group[0].text or group[0].description or "Evidence")[:80],
                speech_evidence=[i.evidence_id for i in group if i.modality == Modality.SPEECH],
                screen_text_evidence=[
                    i.evidence_id for i in group if i.modality == Modality.SCREEN_TEXT
                ],
                visual_evidence=[
                    i.evidence_id for i in group if i.modality == Modality.VISUAL_EVENT
                ],
                audio_evidence=[i.evidence_id for i in group if i.modality == Modality.AUDIO_EVENT],
                entities=sorted({entity for item in group for entity in item.entities}),
                claims=sorted(related),
                contradictions=contradictions,
                importance_score=max(0.0, min(1.0, score)),
                confidence=confidence,
                warnings=[item.uncertainty for item in group if item.uncertainty],
            )
        )
    return output


def analyze_evidence(
    evidence: list[EvidenceItem],
    *,
    source: Source,
    platform: Platform = Platform.SYNTHETIC,
    title: str = "Synthetic evidence analysis",
    config: PipelineConfig | None = None,
) -> AnalysisResult:
    config = config or PipelineConfig()
    retained, duplicates = _deduplicate_subtitles(evidence, config.subtitle_overlap_threshold)
    claims = _make_claims(retained)
    segments = _segments(retained, claims, config)
    counts = Counter(str(item.modality) for item in retained)
    timed_count = sum(item.start_ms is not None for item in retained)
    uncertain = [item for item in retained if item.uncertainty]
    contradictions = [claim for claim in claims if claim.status == ClaimStatus.CONTRADICTED]
    screen_only = [
        item
        for item in retained
        if item.modality == Modality.SCREEN_TEXT
        and not any(item.evidence_id in claim.supporting_evidence_ids for claim in contradictions)
    ]
    visual = [item for item in retained if item.modality == Modality.VISUAL_EVENT]
    if contradictions:
        takeaway = contradictions[0].statement
    elif retained:
        takeaway = retained[0].text or retained[0].description or "Evidence supplied"
    else:
        takeaway = "No evidence supplied"
    digest = hashlib.sha256("|".join(item.evidence_id for item in retained).encode()).hexdigest()[
        :16
    ]
    duration_values = [item.end_ms for item in retained if item.end_ms is not None]
    return AnalysisResult(
        analysis_id=f"analysis-{digest}",
        source=source,
        platform=platform,
        title=title,
        duration_ms=max(duration_values) if duration_values else None,
        detected_languages=sorted({item.language for item in retained if item.language}),
        processing_profile=config.profile,
        acquisition_diagnostic=AcquisitionDiagnostic(
            platform=platform,
            attempts=[
                AcquisitionAttempt(
                    method="synthetic_evidence_input",
                    outcome=AttemptOutcome.SUCCEEDED,
                    detail="Validated local evidence; no media acquisition attempted.",
                )
            ],
            audio_detected=bool(counts[Modality.SPEECH] or counts[Modality.AUDIO_EVENT]),
            valid_video_frames_detected=bool(
                counts[Modality.SCREEN_TEXT] or counts[Modality.VISUAL_EVENT]
            ),
        ),
        one_sentence_takeaway=takeaway,
        concise_summary=f"Analysed {len(retained)} evidence items in {len(segments)} segments.",
        detailed_summary=(
            f"The deterministic pipeline retained {len(retained)} items, removed "
            f"{len(duplicates)} duplicated subtitles, and found "
            f"{len(contradictions)} contradictions."
        ),
        key_points=[
            {"text": claim.statement, "evidence_ids": claim.supporting_evidence_ids}
            for claim in claims
        ],
        important_screen_only_information=[
            {"text": item.text or item.description, "evidence_ids": [item.evidence_id]}
            for item in screen_only
        ],
        visual_demonstrations=[
            {"text": item.description or item.text, "evidence_ids": [item.evidence_id]}
            for item in visual
        ],
        claims=claims,
        contradictions=[claim.claim_id for claim in contradictions],
        uncertainties=[item.evidence_id for item in uncertain],
        evidence_items=retained,
        timeline_segments=segments,
        coverage_report=CoverageReport(
            evidence_count_by_modality=dict(counts),
            timed_evidence_ratio=timed_count / len(retained) if retained else 0.0,
            uncertain_evidence_count=len(uncertain),
            acquisition_complete=False,
            analysis_complete=True,
            notes=["Milestone 1 begins with synthetic evidence; acquisition was not evaluated."],
        ),
        processing_warnings=(
            [f"Deduplicated subtitle evidence: {', '.join(duplicates)}"] if duplicates else []
        ),
    )
