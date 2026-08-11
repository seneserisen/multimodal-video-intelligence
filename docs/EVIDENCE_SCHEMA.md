# Evidence schema

Times are integer milliseconds from media start. An absent timestamp is represented by both `start_ms` and `end_ms` being null; partial intervals are invalid. Evidence distinguishes observation from inference through modality, type, uncertainty, and claim status. Confidence is in `[0, 1]`.

Evidence IDs are unique. Claims and timeline segments reference only IDs present in the containing analysis. Subtitle duplicates remain available for audit through a `deduplicated_evidence_ids` attribute on the retained speech item, but are not repeated as independent findings.

The checked-in JSON Schemas are the interchange contract. Pydantic models are the executable source of truth and schema versions use `1.0.0`.

Real transcript segments use the `speech` modality and `transcript_segment` evidence type. They include millisecond ranges, source filename, detected language, provider, processing version, and confidence derived from provider log probability when available. A user edit changes only `text`; `attributes.original_text` and `attributes.user_edited` preserve the extraction/edit distinction while provider provenance remains unchanged. Generated summaries and user edits are never reclassified as independently observed source evidence.
