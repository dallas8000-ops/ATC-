# ATC Project Review and Upgrade Notes

## Restoration
- Repository restored from GitHub into this workspace on branch `main`.

## Key Gaps Found Against Evaluation Standards
- Callsign capitalization could over-apply to non-callsign text.
- Exclamation-point handling was missing from prohibited punctuation checks.
- `AO2` handling was not compliant with the rule to transcribe as `a oh two`.
- Web UI had duplicated form and element IDs, creating unstable behavior.
- No explicit speaker-role classification support for ATC vs Pilot vs Unknown.
- No sequence endpoint to help keep speaker IDs consistent across multi-utterance clips.

## Upgrades Implemented
- Upgraded web formatter logic to better separate callsign blocks from instruction text.
- Added stronger punctuation and acronym handling in backend checks.
- Added specific `AO2` normalization and violation guidance.
- Added `N123AB` style tail-number expansion to spoken callsign form.
- Added `/api/classify` endpoint for single-utterance role classification.
- Added `/api/classify-sequence` endpoint for role classification with stable `speaker_id` assignment.
- Rebuilt web template to remove duplicated IDs and add a dedicated Speaker Role tab.
- Added Flask/Werkzeug dependencies to `requirements.txt`.

## Why This Exceeds Baseline Better
- The app now supports both transcript formatting and speaker-role adjudication.
- It provides role-confidence/rationale output, reducing ambiguous labeling mistakes.
- Sequence classification with ID reuse directly supports the speaker-id reuse requirement.
- Rule enforcement now catches additional common fail cases seen in evaluation workflows.

## Remaining High-Impact Next Upgrades
- Port the upgraded formatter to the desktop PyQt app so web and desktop behavior are identical.
- Add automated golden-task tests with pass/fail scoring for formatter + speaker-role outputs.
- Add strict phrase dictionary checks against FAA callsign and fix/waypoint references.
- Add a review queue mode for 5-task evaluation simulation before production tasks.
