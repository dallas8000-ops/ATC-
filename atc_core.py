"""
Shared ATC formatting, speaker-role classification, and review assessment.

Used by the PyQt desktop app, Flask web API, and evaluation regression harness.
"""
import re

class ATCFormatter:
    """Handles all ATC transcription formatting rules based on training guidelines"""

    # Standard phraseology references:
    # - FAA Order JO 7110.65BB (ATC procedures and phraseology)
    # - FAA AIM Chapter 4 (radio communications)
    # - FAA Pilot/Controller Glossary
    PILOT_PHRASEOLOGY = {
        'roger', 'wilco', 'affirmative', 'negative', 'standby', 'unable',
        'ready', 'request', 'with you', 'leaving', 'passing', 'descending',
        'climbing', 'readback', 'copy', 'say again'
    }
    CONTROLLER_PHRASEOLOGY = {
        'cleared', 'contact', 'descend', 'climb', 'maintain', 'expect', 'hold',
        'proceed', 'turn', 'squawk', 'change', 'frequency', 'radar contact',
        'line up', 'wait', 'cross', 'taxi', 'monitor', 'report', 'advise',
        'approved', 'hold short'
    }
    PROHIBITED_PHRASES = {
        'repeat back', 'over and out', 'ten four', 'copy that', 'breaker', 'come in', 'do you read'
    }

    # NATO Phonetic Alphabet - these are ALWAYS capitalized
    NATO_PHONETIC = {
        'A': 'ALPHA', 'B': 'BRAVO', 'C': 'CHARLIE', 'D': 'DELTA',
        'E': 'ECHO', 'F': 'FOXTROT', 'G': 'GOLF', 'H': 'HOTEL',
        'I': 'INDIA', 'J': 'JULIETT', 'K': 'KILO', 'L': 'LIMA',
        'M': 'MIKE', 'N': 'NOVEMBER', 'O': 'OSCAR', 'P': 'PAPA',
        'Q': 'QUEBEC', 'R': 'ROMEO', 'S': 'SIERRA', 'T': 'TANGO',
        'U': 'UNIFORM', 'V': 'VICTOR', 'W': 'WHISKEY', 'X': 'XRAY',
        'Y': 'YANKEE', 'Z': 'ZULU'
    }

    # Reverse lookup for NATO phonetics
    NATO_PHONETIC_REVERSE = {v: k for k, v in NATO_PHONETIC.items()}
    
    
    # Special number pronunciations
    SPECIAL_NUMBERS = {
        'niner': 'nine',
        'tree': 'three',
        'fife': 'five'
    }
    
    # Words that should NOT be capitalized (from Image 5)
    NON_CALLSIGN_WORDS = {
        'airport', 'tower', 'runway', 'super', 'heavy', 
        'plus', 'three', 'ground', 'approach', 'ramp', 
        'clearance', 'altimeter', 'ntell', 'codel',
        'contact', 'center', 'departure', 'flight', 'level',
        'radar', 'services', 'terminated', 'squawk', 'change',
        'advisory', 'approved', 'taxi', 'via', 'hold', 'short',
        'cleared', 'takeoff', 'descend', 'maintain', 'turn',
        'heading', 'direct', 'expect', 'climb', 'frequency',
        'point', 'wind', 'knots', 'altimeter', 'runway',
        'left', 'right', 'proceed', 'good', 'day', 'thank',
        'you', 'thanks', 'roger', 'that', 'wilco', 'affirmative',
        'negative', 'say', 'again', 'repeat', 'confirm'
    }
    
    NUMBER_DIGITS = {
        '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
        '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'
    }
    NUMBER_WORDS = {
        'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
        'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
        'seventeen', 'eighteen', 'nineteen', 'twenty', 'thirty', 'forty', 'fifty',
        'sixty', 'seventy', 'eighty', 'ninety', 'oh'
    }
    NATO_WORDS = {
        'ALFA', 'BRAVO', 'CHARLIE', 'DELTA', 'ECHO', 'FOXTROT', 'GOLF', 'HOTEL',
        'INDIA', 'JULIETT', 'KILO', 'LIMA', 'MIKE', 'NOVEMBER', 'OSCAR', 'PAPA',
        'QUEBEC', 'ROMEO', 'SIERRA', 'TANGO', 'UNIFORM', 'VICTOR', 'WHISKEY',
        'XRAY', 'YANKEE', 'ZULU'
    }
    CALLSIGN_STARTERS = {
        'UNITED', 'AMERICAN', 'DELTA', 'SOUTHWEST', 'JETBLUE', 'ALASKA', 'SPIRIT',
        'FRONTIER', 'HAWAIIAN', 'ALLEGIANT', 'VOLARIS', 'VIVA', 'MEDEVAC',
        'NOVEMBER', 'ICON', 'CESSNA', 'PIPER', 'CIRRUS', 'SKYHAWK', 'GULFSTREAM',
        'FALCON', 'AIRBUS', 'BOEING', 'UPS', 'FEDEX'
    }
    AVIATION_ACRONYMS = {
        'ILS', 'ATIS', 'VOR', 'VFR', 'IFR', 'GPS', 'RNAV', 'METAR', 'SID', 'STAR', 'ATC', 'NAVAID'
    }
    SUFFIX_WORDS = {'heavy', 'super'}
    INSTRUCTION_WORDS = {
        'taxi', 'hold', 'short', 'cross', 'cleared', 'maintain', 'climb', 'descend', 'turn',
        'contact', 'expect', 'proceed', 'runway', 'heading', 'altimeter', 'frequency', 'report',
        'approved', 'radar', 'services', 'terminated', 'change', 'via', 'ground', 'tower', 'approach'
    }
    FACILITY_SUFFIX_WORDS = {'ground', 'tower', 'approach', 'center', 'departure', 'clearance', 'ramp'}
    LOWERCASE_WORDS = {
        'airport', 'tower', 'runway', 'ground', 'approach', 'ramp', 'clearance', 'altimeter',
        'departure', 'arrival', 'contact', 'center', 'flight', 'level', 'radar', 'services',
        'terminated', 'squawk', 'change', 'advisory', 'approved', 'taxi', 'via', 'hold', 'short',
        'cleared', 'takeoff', 'land', 'descend', 'maintain', 'turn', 'heading', 'direct', 'expect',
        'climb', 'frequency', 'point', 'wind', 'knots', 'left', 'right', 'proceed', 'good', 'day',
        'thanks', 'thank', 'you', 'roger', 'wilco', 'affirmative', 'negative', 'say', 'again',
        'confirm', 'and', 'to', 'for', 'at', 'on', 'of', 'with', 'a', 'an', 'is', 'are', 'plus',
        'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'zero', 'one', 'ten',
        'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen',
        'nineteen', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety'
    }
    FILLER_WORDS = {'uh', 'um', 'oh', 'ah', 'hmm'}

    # Common ASR-to-ATC phrase corrections.
    PHRASEOLOGY_CORRECTIONS = [
        (r'\bcome and maintain\b', 'maintain'),
        (r'\bcome to maintain\b', 'climb and maintain'),
        (r'\bvectors?\s+for\b', 'vector for'),
        (r'\bmaintain follow level\b', 'maintain flight level'),
        (r'\bfollowable\b', 'flight level'),
        (r'\bfollow level\b', 'flight level'),
        (r'\bfollow up altitude\b', 'flight level'),
        (r'\bfollow up\b', 'flight level'),
        (r'\bmaintain level\b', 'maintain flight level'),
        (r'\bvolleyball level\b', 'flight level'),
        (r'\bvolleyball\b', 'flight level'),
        (r'\bclimb maintain\b', 'climb and maintain'),
        (r'\bflight level level\b', 'flight level'),
        (r'\bcamp level\b', 'flight level'),
        (r'\bline up and weight\b', 'line up and wait'),
        (r'\bhold shirt\b', 'hold short'),
        (r'\bfight level\b', 'flight level'),
        (r'\bflight label\b', 'flight level'),
        (r'\bsquak\b', 'squawk'),
        (r'\bsquack\b', 'squawk'),
        (r'\bat camp flight level\b', 'at flight level'),
        (r'\bclimb at flight level\b', 'climb and maintain flight level'),
        (r'\bdescend at flight level\b', 'descend and maintain flight level'),
        (r'\bmaintain altitude\b', 'maintain flight level'),
    ]

    NON_STANDARD_PHRASEOLOGY = {
        r'\bvolleyball\b': 'flight level',
        r'\bfollowable\b': 'flight level',
        r'\bmain thing\b': 'maintain',
        r'\bcome and take\b': 'contact',
        r'\bhold shirt\b': 'hold short',
        r'\bline up and weight\b': 'line up and wait',
    }

    CALLSIGN_SPELLING_CORRECTIONS = [
        (r'\bnovenber\b', 'NOVEMBER'),
        (r'\bnovemer\b', 'NOVEMBER'),
        (r'\bnovembre\b', 'NOVEMBER'),
        (r'\bnovamber\b', 'NOVEMBER'),
        (r'\btangle\b', 'TANGO'),  # Common mishearing of Tango
        (r'\bdiver\b', 'DELTA'),  # Common mishearing of Delta
        (r'\bdevil\b', 'DELTA'),  # Another mishearing variant
        (r'\bunited\b', 'UNITED'),
        (r'\bamerican\b', 'AMERICAN'),
        (r'\bsouthwest\b', 'SOUTHWEST'),
    ]
    
    def __init__(self):
        self.violations = []
    
    def format_transcript(self, text):
        """
        Apply all ATC formatting rules to the text
        Based on training guidelines:
        1. Remove all punctuation except commas
        2. Spell out ALL numbers
        3. Capitalize callsigns, NATO phonetics, facility names, aviation acronyms
        4. Keep everything else lowercase
        5. Include filler words
        6. Handle angled brackets for uncertainty
        7. Enforce standard phraseology and flag prohibited words
        """
        self.violations = []
        
        if not text.strip():
            return text, []
        
        original_text = text
        
        # Step 1: Check for violations BEFORE formatting
        self.check_violations_before(original_text)
        self.check_non_standard_phraseology(original_text)
        
        # Step 2: Normalize special cases (AO2 handling)
        formatted = self.normalize_special_cases(text)

        # Step 2.5: Clean recurring ASR noise patterns from low-quality captures.
        formatted = self.cleanup_asr_noise(formatted)
        
        # Step 3: Remove all punctuation except commas (Rule from Image 3)
        formatted = self.remove_punctuation(formatted)
        
        # Step 4: Convert special number pronunciations
        formatted = self.convert_special_numbers(formatted)
        
        # Step 5: Convert numbers to words (Rule from Images 6-7)
        formatted = self.convert_numbers_to_words(formatted)

        # Step 5.5: Remove commas accidentally inserted inside spelled number sequences.
        formatted = self.normalize_number_sequence_commas(formatted)

        # Step 5.6: Correct common phraseology/terminology errors.
        formatted = self.apply_phraseology_corrections(formatted)
        
        # Step 6: Handle capitalization (Rules from Images 4-5, 11)
        formatted = self.apply_capitalization(formatted)
        
        # Step 6: Validate angled brackets (Rule from Images 9-10)
        formatted = self.validate_brackets(formatted)
        
        # Step 7: Check for phraseology and prohibited words
        self.check_phraseology(formatted)

        # Step 7: Check for violations AFTER formatting
        self.check_violations_after(original_text, formatted)
        
        return formatted, self.violations

    def cleanup_asr_noise(self, text):
        """Normalize common misheard filler phrases from radio/static captures."""
        cleaned = text
        replacements = {
            r'\bcome and maintain\b': 'maintain',
            r'\bcome to maintain\b': 'climb and maintain',
            r'\bvectors?\s+for\b': 'vector for',
            r'\bmaintain follow level\b': 'maintain flight level',
            r'\bfollow level\b': 'flight level',
            r'\bfollowable\b': 'flight level',
            r'\bat camp level\b': 'at flight level',
            r'\bmain thing\b': 'maintain',
            r'\bvolleyball\b': 'flight level',
            r'\bcome and take\b': 'contact',
            r'\bthe channel is done\b': '',
        }
        for pattern, repl in replacements.items():
            cleaned = re.sub(pattern, repl, cleaned, flags=re.IGNORECASE)

        # Collapse duplicate whitespace introduced by removals.
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def normalize_number_sequence_commas(self, text):
        """Remove commas between number words (e.g., 'three, two, zero' -> 'three two zero')."""
        number_terms = (
            'zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|'
            'thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|'
            'thirty|forty|fifty|sixty|seventy|eighty|ninety|oh|point'
        )
        pair_pattern = rf'\b({number_terms})\b\s*,\s*\b({number_terms})\b'
        normalized = text
        while True:
            updated = re.sub(pair_pattern, r'\1 \2', normalized, flags=re.IGNORECASE)
            if updated == normalized:
                break
            normalized = updated
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.strip()

    def apply_phraseology_corrections(self, text):
        """Apply common ATC phraseology and terminology corrections."""
        corrected = text
        for pattern, replacement in self.PHRASEOLOGY_CORRECTIONS:
            updated = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
            if updated != corrected:
                raw_pattern = pattern.replace('\\b', '')
                self.violations.append(
                    f"Phraseology correction applied: '{raw_pattern}' -> '{replacement}'"
                )
            corrected = updated

        # Normalize repeated phrase stutter artifacts.
        corrected = re.sub(
            r'\b(maintain flight level(?:\s+(?:zero|one|two|three|four|five|six|seven|eight|nine))+?)\s+\1\b',
            r'\1',
            corrected,
            flags=re.IGNORECASE,
        )

        corrected = re.sub(r'\s+', ' ', corrected).strip()
        return corrected

    def check_non_standard_phraseology(self, text):
        """Report common non-ATC wording that should be corrected."""
        lowered = (text or '').lower()
        for pattern, suggested in self.NON_STANDARD_PHRASEOLOGY.items():
            if re.search(pattern, lowered):
                raw = pattern.replace('\\b', '')
                self.violations.append(
                    f"Non-standard phraseology detected: '{raw}'. Suggested ATC term: '{suggested}'."
                )

    def normalize_special_cases(self, text):
        """Normalize special cases like AO2 to spoken form and handle tail numbers"""
        # Common ASR misspellings of callsign starters.
        for pattern, replacement in self.CALLSIGN_SPELLING_CORRECTIONS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Evaluation-specific rule: AO2 is spoken as "a oh two" and should not be treated like an acronym.
        text = re.sub(r'\bAO2\b', 'a oh two', text, flags=re.IGNORECASE)
        
        # Handle tail-number style callsigns: N123AB -> NOVEMBER ONE TWO THREE ALFA BRAVO
        def convert_tail_number(match):
            raw = match.group(0)
            tail_match = re.fullmatch(r'N(\d+)([A-Za-z]{0,3})', raw, flags=re.IGNORECASE)
            if tail_match:
                digits = tail_match.group(1)
                suffix = tail_match.group(2).upper()
                result = 'NOVEMBER'
                for d in digits:
                    result += ' ' + self.NUMBER_DIGITS[d].upper()
                for char in suffix:
                    result += ' ' + ('ALFA' if char == 'A' else char)
                return result
            return raw
        
        # Replace N-format tail numbers
        text = re.sub(r'\bN\d+[A-Z]{0,3}\b', convert_tail_number, text, flags=re.IGNORECASE)

        # Enforce callsign number expansion: NOVEMBER 998 -> NOVEMBER NINE NINE EIGHT
        def expand_november_number(match):
            digits = match.group(1)
            return 'NOVEMBER ' + ' '.join(self.NUMBER_DIGITS[d].upper() for d in digits)

        text = re.sub(r'\bNOVEMBER\s+(\d{1,6})\b', expand_november_number, text, flags=re.IGNORECASE)
        return text
    
    def check_phraseology(self, text):
        """
        Check for required and prohibited phraseology for both pilots and controllers.
        Warn if prohibited words are used, or if standard phraseology is missing in typical contexts.
        Uses word boundaries for accurate matching.
        All messages reference FAA AIM and FAA Order JO 7110.65.
        """
        text_lower = text.lower()
        # Prohibited phrases (use word boundaries)
        for phrase in self.PROHIBITED_PHRASES:
            pattern = r'\b' + re.escape(phrase) + r'\b'
            if re.search(pattern, text_lower):
                self.violations.append(
                    f"Prohibited phrase: '{phrase}' is not standard ATC phraseology (FAA JO 7110.65BB / AIM Ch.4 / Pilot-Controller Glossary)")

        # Encourage use of standard phraseology (pilot/controller)
        # Use word boundaries for each phrase
        found_phraseology = False
        known = self.PILOT_PHRASEOLOGY.union(self.CONTROLLER_PHRASEOLOGY)
        for phrase in known:
            pattern = r'\b' + re.escape(phrase) + r'\b'
            if re.search(pattern, text_lower):
                found_phraseology = True
                break
        if not found_phraseology:
            self.violations.append(
                "No standard ATC phraseology detected. Use FAA JO 7110.65BB, AIM Chapter 4, and Pilot/Controller Glossary terms (e.g., 'roger', 'cleared', 'contact').")
    
    def remove_punctuation(self, text):
        """
        Remove all punctuation except commas
        Rule from Image 3: Only commas allowed
        """
        # Remove periods, question marks, quotes, exclamation points
        text = re.sub(r'[.!?"\']', '', text)
        text = text.replace(';', ',').replace(':', ',')
        text = text.replace('-', ' ')
        return text
    
    def convert_special_numbers(self, text):
        """
        Convert special number pronunciations
        NINER → NINE, TREE → THREE (from Image 6-7)
        """
        words = text.split()
        converted = []
        
        for word in words:
            word_lower = word.lower()
            if word_lower in self.SPECIAL_NUMBERS:
                # Replace with correct pronunciation, maintain case context
                if word.isupper():
                    converted.append(self.SPECIAL_NUMBERS[word_lower].upper())
                else:
                    converted.append(self.SPECIAL_NUMBERS[word_lower])
            else:
                converted.append(word)
        
        return ' '.join(converted)
    
    def convert_numbers_to_words(self, text):
        """
        Convert all numbers to written words
        Rule from Images 6-7: ALL numbers spelled out, NO digits, NO hyphens
        Examples:
        - 1234 → one two three four
        - 135.5 → one three five point five
        - 2648 → two six four eight
        - TWENTY-NINE → TWENTY NINE (remove hyphens)
        """
        
        # First, remove hyphens between numbers or number words
        text = re.sub(r'(\d+)-(\d+)', r'\1 \2', text)
        text = re.sub(r'(TWENTY|THIRTY|FORTY|FIFTY|SIXTY|SEVENTY|EIGHTY|NINETY)-(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE)', r'\1 \2', text, flags=re.IGNORECASE)
        
        def replace_number(match):
            number = match.group(0)
            
            # Handle decimals (like 135.5 → one three five point five)
            if '.' in number:
                parts = number.split('.')
                result = ' '.join(self.NUMBER_DIGITS.get(d, d) for d in parts[0])
                result += ' point '
                result += ' '.join(self.NUMBER_DIGITS.get(d, d) for d in parts[1])
                return result
            
            # Convert each digit separately (1234 → one two three four)
            return ' '.join(self.NUMBER_DIGITS.get(digit, digit) for digit in number)
        
        # Replace all numbers (including those with decimals)
        text = re.sub(r'\d+\.?\d*', replace_number, text)
        
        return text
    
    def apply_capitalization(self, text):
        words = text.split()
        formatted_words = []
        i = 0

        while i < len(words):
            word = words[i]
            raw_word = word.rstrip(',')
            has_comma = word.endswith(',')
            word_upper = raw_word.upper()
            word_lower = raw_word.lower()

            if word.startswith('<'):
                bracket_content = []
                while i < len(words):
                    bracket_content.append(words[i])
                    if words[i].endswith('>'):
                        i += 1
                        break
                    i += 1
                formatted_words.append(' '.join(bracket_content))
                continue

            # Numeric-only callsign handling: e.g., "five one nine zero maintain ..."
            if self._is_numeric_callsign_start(words, i):
                j = i
                callsign_parts = []
                while j < len(words):
                    next_word = words[j]
                    next_raw = next_word.rstrip(',')
                    next_lower = next_raw.lower()
                    trailing_comma = next_word.endswith(',')

                    if j > i and next_lower in self.INSTRUCTION_WORDS:
                        break
                    if self._is_spoken_number_token(next_raw) or re.fullmatch(r'[A-Za-z]', next_raw):
                        callsign_parts.append(self._callsign_token(next_raw))
                        j += 1
                        if trailing_comma:
                            callsign_parts[-1] = callsign_parts[-1] + ','
                            break
                        continue
                    break

                if len(callsign_parts) >= 3:
                    formatted_words.extend(callsign_parts)
                    i = j
                    continue

            if self._is_callsign_start(word_upper):
                j = i
                callsign_parts = []
                while j < len(words):
                    next_word = words[j]
                    next_raw = next_word.rstrip(',')
                    next_lower = next_raw.lower()
                    next_upper = next_raw.upper()
                    trailing_comma = next_word.endswith(',')

                    if j > i and next_lower in self.INSTRUCTION_WORDS:
                        break
                    if next_lower in self.SUFFIX_WORDS:
                        callsign_parts.append(next_lower)
                        j += 1
                        break
                    if (
                        j == i
                        or next_raw.isdigit()
                        or self._is_spoken_number_token(next_raw)
                        or next_upper in self.NATO_WORDS
                        or re.fullmatch(r'[A-Za-z]', next_raw)
                    ):
                        callsign_parts.append(self._callsign_token(next_raw))
                        j += 1
                        if trailing_comma:
                            callsign_parts[-1] = callsign_parts[-1] + ','
                            break
                        continue
                    break

                if callsign_parts:
                    formatted_words.extend(callsign_parts)
                    i = j
                    continue

            if word_upper in self.AVIATION_ACRONYMS:
                formatted_word = word_upper
            elif word_upper in self.NATO_WORDS:
                # All NATO phonetic letters should be capitalized
                formatted_word = word_upper
            elif i > 0 and words[i - 1].rstrip(',').lower() == 'direct':
                # Route fixes after "direct" are usually named waypoints.
                formatted_word = word_upper
            elif (i + 1) < len(words) and words[i + 1].rstrip(',').lower() in self.FACILITY_SUFFIX_WORDS:
                # Facility/location name capitalization: "Salinas ground", "Miami center"
                formatted_word = word_lower.capitalize()
            elif word_lower in self.FILLER_WORDS:
                formatted_word = word_lower
            elif word_lower in self.LOWERCASE_WORDS:
                formatted_word = word_lower
            else:
                formatted_word = word_lower

            if has_comma:
                formatted_word += ','
            formatted_words.append(formatted_word)
            i += 1

        return ' '.join(formatted_words)

    @staticmethod
    def _strip_comma(word):
        if word.endswith(','):
            return word[:-1], True
        return word, False

    def _is_callsign_start(self, token_upper):
        return token_upper in self.CALLSIGN_STARTERS

    def _callsign_token(self, token):
        token_upper = token.upper()
        token_lower = token.lower()
        if token.isdigit():
            return ' '.join(self.NUMBER_DIGITS[d].upper() for d in token)
        if token_lower == 'oh':
            return 'OH'
        if token_lower in self.NUMBER_WORDS:
            return token_upper
        if token_upper in self.NATO_WORDS:
            return token_upper
        if re.fullmatch(r'[A-Za-z]', token):
            letter = token_upper
            if letter == 'A':
                return 'ALFA'
            return letter
        return token_upper

    def _is_spoken_number_token(self, token):
        token_lower = token.lower()
        return token.isdigit() or token_lower in self.NUMBER_WORDS

    def _is_numeric_callsign_start(self, words, index):
        # Callsign usually starts a transmission or follows a comma.
        if index < 0 or index >= len(words):
            return False
        if index > 0 and not words[index - 1].endswith(','):
            return False

        probe = []
        j = index
        while j < len(words) and len(probe) < 6:
            token = words[j].rstrip(',')
            if self._is_spoken_number_token(token):
                probe.append(token)
                j += 1
                continue
            break

        # Three+ spoken number tokens at start followed by an instruction word => callsign-like pattern.
        if len(probe) < 3:
            return False
        if j < len(words):
            next_token = words[j].rstrip(',').lower()
            if next_token == 'and' and (j + 1) < len(words):
                next_token = words[j + 1].rstrip(',').lower()
            return next_token in self.INSTRUCTION_WORDS
        return False
    
    def validate_brackets(self, text):
        """
        Validate angled brackets usage from Images 9-10
        Rules:
        - Use angled brackets <> for uncertain words
        - Never leave empty brackets
        - Only use angled brackets (not parentheses, not square brackets)
        """
        # Check for empty brackets
        if '<>' in text or '< >' in text:
            self.violations.append("Empty angled brackets found - always include your best guess inside <>")
        
        # Check for parentheses (should be angled brackets)
        if '(' in text or ')' in text:
            # Replace parentheses with angled brackets
            text = text.replace('(', '<').replace(')', '>')
            self.violations.append("Parentheses found - use angled brackets <> for uncertain words, not ()")
        
        # Check for square brackets
        if '[' in text or ']' in text:
            text = text.replace('[', '<').replace(']', '>')
            self.violations.append("Square brackets found - use angled brackets <> for uncertain words, not []")
        
        return text
    
    def check_violations_before(self, text):
        """Check for violations in the original text before formatting. All messages reference FAA AIM and FAA Order JO 7110.65."""
        # Image 3: Check for prohibited punctuation
        if '.' in text and not re.search(r'\d+\.\d+', text):  # Allow decimals like 135.5
            self.violations.append("⚠ Periods should not be used (Image 3: Punctuation Rules)")
        
        if '?' in text:
            self.violations.append("⚠ Question marks should not be used (Image 3: Punctuation Rules)")
        
        if '!' in text:
            self.violations.append("⚠ Exclamation points should not be used (Image 3: Punctuation Rules)")
        
        if '"' in text or "'" in text or '"' in text or '"' in text:
            self.violations.append("⚠ Quotation marks should not be used (Image 3: Punctuation Rules)")
        
        # Images 6-7: Check for digits
        if re.search(r'\b\d+\b', text):
            self.violations.append("⚠ Numbers should be spelled out - write 'one two three' not '123' (Images 6-7: Number Rules)")
        
        # Image 6-7: Check for hyphens between numbers
        if re.search(r'\d+-\d+', text):
            self.violations.append("⚠ No hyphens between numbers - write 'two six four eight' not '26-48' (Image 7)")
        
        # Check for compound number words with hyphens (TWENTY-NINE should be TWENTY NINE)
        if re.search(r'(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)-(one|two|three|four|five|six|seven|eight|nine)', text, re.IGNORECASE):
            self.violations.append("⚠ No hyphens in number words - write 'TWENTY NINE' not 'TWENTY-NINE' (Image 7)")
        
        # Evaluation-specific: Check for AO2 which should be "a oh two"
        if re.search(r'\bAO2\b', text, flags=re.IGNORECASE):
            self.violations.append("⚠ 'AO2' should be transcribed as 'a oh two' instead of an acronym")
    
    def check_violations_after(self, original, formatted):
        """Check for violations after formatting. All messages reference FAA AIM and FAA Order JO 7110.65."""
        # Image 5: Check for incorrect capitalization of non-callsign words
        non_callsign_caps = ['Airport', 'Tower', 'Runway', 'Ground', 'Approach', 'Super', 'Heavy']
        for word in non_callsign_caps:
            if word in original:
                self.violations.append(f"⚠ '{word}' should not be capitalized - it's not a callsign (Image 5: Capitalization)")
        
        # Images 9-10: Check for empty brackets
        if '<>' in formatted or '< >' in formatted:
            self.violations.append("⚠ Empty angled brackets - always transcribe your best guess (Images 9-10: Brackets)")
        
        # Image 9-10: Check for wrong bracket types in original
        if '(' in original or ')' in original:
            self.violations.append("⚠ Use angled brackets <> for uncertainty, not parentheses () (Images 9-10, FAA AIM/JO 7110.65)")
        
        if '[' in original or ']' in original:
            self.violations.append("⚠ Use angled brackets <> for uncertainty, not square brackets [] (Images 9-10, FAA AIM/JO 7110.65)")
        
        # Image 11: Check for partial callsign capitalization
        # Look for patterns like "Volaris" or "United" instead of "VOLARIS", "UNITED"
        mixed_case_pattern = r'\b[A-Z][a-z]+\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|ZERO)\b'
        if re.search(mixed_case_pattern, original):
            self.violations.append("⚠ Entire callsign should be ALL CAPS - write 'VOLARIS' not 'Volaris' (Image 11, FAA Order JO 7110.65 §2-4-20)")

def classify_speaker_role(utterance):
    """Heuristic ATC/Pilot/Unknown classifier aligned to evaluation guidance."""
    text = (utterance or '').strip()
    lowered = text.lower()
    if not text:
        return {'speaker_role': 'Unknown', 'confidence': 0.0, 'reason': 'Empty utterance'}

    # Non-ATC/Pilot channels should remain Unknown in this project rubric.
    if any(term in lowered for term in (' ramp', 'ramp ', 'atis', 'vehicle', 'ops ')):
        return {'speaker_role': 'Unknown', 'confidence': 0.9, 'reason': 'Contains ramp/atis/vehicle cues'}

    atc_score = 0
    pilot_score = 0

    if re.search(r'\b(cleared|taxi|hold short|maintain|climb|descend|contact|turn|cross)\b', lowered):
        atc_score += 2
    if re.search(r'\b(request|ready|with you|wilco|unable|confirm|roger)\b', lowered):
        pilot_score += 2
    if re.match(r'^[A-Z][A-Z0-9 ]{2,},', text):
        atc_score += 1
    if re.search(r',\s*[A-Z][A-Z0-9 ]+$', text):
        pilot_score += 1

    if atc_score == pilot_score:
        return {'speaker_role': 'Unknown', 'confidence': 0.5, 'reason': 'Ambiguous cue mix'}
    if atc_score > pilot_score:
        confidence = min(0.99, 0.55 + 0.1 * (atc_score - pilot_score))
        return {'speaker_role': 'ATC', 'confidence': round(confidence, 2), 'reason': 'Instruction-oriented phraseology'}
    confidence = min(0.99, 0.55 + 0.1 * (pilot_score - atc_score))
    return {'speaker_role': 'Pilot', 'confidence': round(confidence, 2), 'reason': 'Readback/request-oriented phraseology'}


def extract_callsign_key(utterance):
    """Extract a stable callsign key from the beginning of an utterance when present."""
    text = (utterance or '').strip()
    if not text:
        return None
    head = text.split(',')[0].strip()
    if re.match(r'^[A-Z]{2,}( [A-Z0-9]{1,}){1,5}$', head):
        return head
    return None

def _audio_confidence_01(avg_logprob):
    """Map faster-whisper segment avg_logprob to [0, 1]; higher is more confident."""
    if avg_logprob is None:
        return None
    lo, hi = -2.5, -0.35
    t = (float(avg_logprob) - lo) / (hi - lo)
    return max(0.0, min(1.0, t))


def _format_quality_01(violations):
    """Fewer violations => score closer to 1."""
    if not violations:
        return 1.0
    penalty = min(0.88, 0.11 * len(violations))
    return max(0.12, 1.0 - penalty)


def _violation_hint(text):
    """Short reviewer hint for a violation string (best-effort pattern match)."""
    if 'Period' in text or 'Punctuation' in text or 'Question marks' in text:
        return 'Punctuation: ATC-style transcripts use commas, not sentence punctuation.'
    if 'Numbers should be spelled' in text or 'hyphen' in text.lower():
        return 'Numbers: spell digits and avoid hyphenated number forms where rules say so.'
    if 'bracket' in text.lower() or 'parentheses' in text.lower():
        return 'Uncertainty: use angled brackets <like this>, not () or [].'
    if 'callsign' in text.lower() or 'VOLARIS' in text or 'capitalized' in text.lower():
        return 'Callsign / capitalization: callsign tokens stay ALL CAPS; facility words stay lowercase.'
    if 'Prohibited phrase' in text:
        return 'Phraseology: replace non-standard radiotelephony with FAA/ICAO terms.'
    if 'No standard ATC phraseology' in text:
        return 'Phraseology: add recognizable ATC terms so the line reads as ATC comms.'
    return 'See training rules / violations tab for this item.'


def build_review_assessment(raw_text, formatted, violations, speaker, avg_logprob=None):
    """
    Confidence-driven review signals: combine optional ASR logprob with role + format quality.
    Returns JSON-serializable dict for API responses.
    """
    raw_text = raw_text or ''
    violations = violations or []
    ac01 = _audio_confidence_01(avg_logprob)

    flags = []
    if avg_logprob is not None and float(avg_logprob) < -1.15:
        flags.append({
            'code': 'LOW_AUDIO_CONFIDENCE',
            'detail': f'Segment avg log-probability is {float(avg_logprob):.2f}; audio decode may be uncertain.',
        })
    if len(violations) >= 2:
        flags.append({
            'code': 'MULTIPLE_VIOLATIONS',
            'detail': f'{len(violations)} rule checks flagged; compare raw vs formatted carefully.',
        })
    for v in violations:
        if 'No standard ATC phraseology' in v:
            flags.append({
                'code': 'NO_STANDARD_PHRASEOLOGY',
                'detail': 'Heuristic did not find common ATC terms in the formatted line.',
            })
            break
    role = speaker.get('speaker_role')
    rc = float(speaker.get('confidence', 0))
    reason = speaker.get('reason', '')
    if role == 'Unknown' and ('Ambiguous' in reason or rc <= 0.52):
        flags.append({'code': 'AMBIGUOUS_ROLE', 'detail': reason})
    if role in ('ATC', 'Pilot') and rc < 0.58:
        flags.append({
            'code': 'LOW_ROLE_CONFIDENCE',
            'detail': f"Role {role} confidence is only {rc:.2f}; verify against audio/context.",
        })

    seen = set()
    deduped = []
    for f in flags:
        if f['code'] in seen:
            continue
        seen.add(f['code'])
        deduped.append(f)
    flags = deduped

    fq = _format_quality_01(violations)
    role_score = rc

    if ac01 is None:
        overall = 0.48 * role_score + 0.52 * fq
    else:
        overall = 0.32 * ac01 + 0.33 * role_score + 0.35 * fq

    needs_review = (
        overall < 0.62
        or len(flags) >= 2
        or (ac01 is not None and ac01 < 0.34)
        or len(violations) >= 3
    )

    if overall < 0.42 or len(violations) >= 4 or (ac01 is not None and ac01 < 0.22):
        priority = 'high'
    elif overall < 0.62 or len(violations) >= 1 or needs_review:
        priority = 'medium'
    else:
        priority = 'low'

    return {
        'overall_score': round(overall * 100, 1),
        'overall_01': round(overall, 3),
        'needs_review': bool(needs_review),
        'priority': priority,
        'risk_flags': flags,
        'components': {
            'audio_confidence_01': None if ac01 is None else round(ac01, 3),
            'avg_logprob': None if avg_logprob is None else round(float(avg_logprob), 4),
            'role_confidence': round(rc, 3),
            'format_quality_01': round(fq, 3),
        },
        'speaker_explain': {
            'speaker_role': role,
            'confidence': speaker.get('confidence'),
            'reason': reason,
        },
        'violation_explain': [
            {'text': v, 'hint': _violation_hint(v)} for v in violations
        ],
    }


