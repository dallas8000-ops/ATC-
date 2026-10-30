"""Splice atc_core imports into webapp/app.py and atc_transcription_app.py."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]

# --- webapp/app.py: drop inlined core (lines 73-537), insert imports ---
wp = root / "webapp" / "app.py"
wl = wp.read_text(encoding="utf-8").splitlines(True)
inject = (
    "import sys\n"
    "from pathlib import Path\n"
    "_REPO_ROOT = Path(__file__).resolve().parents[1]\n"
    "if str(_REPO_ROOT) not in sys.path:\n"
    "    sys.path.insert(0, str(_REPO_ROOT))\n"
    "from atc_core import (\n"
    "    ATCFormatter,\n"
    "    classify_speaker_role,\n"
    "    extract_callsign_key,\n"
    "    build_review_assessment,\n"
    ")\n\n"
)
# Keep lines 1-72 (indices 0..71), then AudioTranscriber from line 539 (index 538)
wp.write_text("".join(wl[:72]) + inject + "".join(wl[538:]), encoding="utf-8")
print("Updated webapp/app.py")

# --- atc_transcription_app.py: remove ATCFormatter + helpers; import from core ---
ap = root / "atc_transcription_app.py"
al = ap.read_text(encoding="utf-8").splitlines(True)
imp = (
    "\nfrom atc_core import ATCFormatter, classify_speaker_role, extract_callsign_key\n\n"
)
# Lines 1-230 kept; ATCSyntaxHighlighter starts line 951 -> index 950
ap.write_text("".join(al[:230]) + imp + "".join(al[950:]), encoding="utf-8")
print("Updated atc_transcription_app.py")
