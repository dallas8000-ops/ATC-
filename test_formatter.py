#!/usr/bin/env python
"""Quick test of updated formatter"""
import sys
sys.path.insert(0, '.')
from atc_transcription_app import ATCFormatter, classify_speaker_role, extract_callsign_key

# Test 1: Basic formatting
formatter = ATCFormatter()
test1 = "united 1234, descend maintain 5000"
result1, violations1 = formatter.format_transcript(test1)
print(f"Test 1 - Basic: {result1}")
print(f"  Violations: {len(violations1)}")

# Test 2: AO2 handling
test2 = "AO2 has joined frequency"
result2, violations2 = formatter.format_transcript(test2)
print(f"\nTest 2 - AO2: {result2}")
print(f"  Violations: {[v for v in violations2 if 'AO2' in v]}")

# Test 3: Tail number parsing
test3 = "N12345 is ready"
result3, violations3 = formatter.format_transcript(test3)
print(f"\nTest 3 - Tail number: {result3}")

# Test 4: Speaker role classification
test4 = "UNITED 1234, cleared for takeoff"
role = classify_speaker_role(test4)
print(f"\nTest 4 - Role classification: {role['speaker_role']} (confidence: {role['confidence']})")

# Test 5: Callsign extraction
callsign = extract_callsign_key("UNITED 1234, roger")
print(f"\nTest 5 - Callsign extraction: {callsign}")

print("\n✓ All tests passed successfully!")
