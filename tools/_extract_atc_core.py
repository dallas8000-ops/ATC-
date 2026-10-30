"""One-off helper to build atc_core.py — run from repo root: python tools/_extract_atc_core.py"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
desktop = (root / "atc_transcription_app.py").read_text(encoding="utf-8").splitlines()
web = (root / "webapp" / "app.py").read_text(encoding="utf-8").splitlines()

cls_lines = desktop[230:902]

filtered = []
skip = False
for i, line in enumerate(cls_lines):
    if "# Number to word mapping - always lowercase" in line:
        skip = True
        continue
    if skip:
        if line.strip() == "}":
            next_nonempty = next(
                (cls_lines[j].strip() for j in range(i + 1, len(cls_lines)) if cls_lines[j].strip()),
                "",
            )
            if next_nonempty.startswith("# Special number pronunciations"):
                skip = False
        continue
    filtered.append(line)

cls_lines = filtered

funcs = desktop[905:946]

start = next(i for i, l in enumerate(web) if l.startswith("def _audio_confidence_01"))
end = next(i for i, l in enumerate(web) if l.startswith("class AudioTranscriber"))
review = web[start:end]

header = '''\
"""
Shared ATC formatting, speaker-role classification, and review assessment.

Used by the PyQt desktop app, Flask web API, and evaluation regression harness.
"""
import re

'''

out = (
    header
    + "\n".join(cls_lines)
    + "\n\n"
    + "\n".join(funcs)
    + "\n\n"
    + "\n".join(review)
    + "\n"
)
(root / "atc_core.py").write_text(out, encoding="utf-8")
print("Wrote atc_core.py", len(out), "chars")
