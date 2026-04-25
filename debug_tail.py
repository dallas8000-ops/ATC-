from atc_transcription_app import ATCFormatter
import re

formatter = ATCFormatter()
test = "N12345"
print(f"Testing tail number: {test}")

# Test the _is_callsign_start check
print(f"Is 'N12345' a callsign start? {formatter._is_callsign_start('N12345')}")
print(f"Is 'NOVEMBER' a callsign start? {formatter._is_callsign_start('NOVEMBER')}")

# Check if the pattern matches
raw_word = "N12345"
tail_match = re.fullmatch(r'N(\d+)([A-Za-z]{0,3})', raw_word, flags=re.IGNORECASE)
print(f"Tail match result: {tail_match}")
if tail_match:
    print(f"  Group 1 (digits): {tail_match.group(1)}")
    print(f"  Group 2 (suffix): {tail_match.group(2)}")

# Now test the full formatting
result, violations = formatter.format_transcript("N12345 is ready")
print(f"\nFull format result: {result}")
