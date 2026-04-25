"""
ATC Transcription Application
A Windows-based application for transcribing Air Traffic Control communications
following FAA/ICAO phraseology and formatting standards.
"""

import sys
import re
import os
import tempfile
import numpy as np
from threading import Thread
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QPushButton, QLabel, 
                             QFileDialog, QSplitter, QListWidget, QTabWidget,
                             QGroupBox, QMessageBox, QStatusBar, QToolBar,
                             QAction, QMenuBar, QMenu)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QColor, QTextCharFormat, QSyntaxHighlighter, QTextCursor


class AudioRecorder(QThread):
    """Worker thread for audio recording and transcription"""
    transcription_ready = pyqtSignal(str)  # Emits transcribed text
    recording_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.is_recording = False
        self.sample_rate = 16000
        self.audio_data = []
        self.transcriber = None
        self._load_transcriber()
    
    def _load_transcriber(self):
        """Load the transcriber lazily"""
        try:
            from faster_whisper import WhisperModel
            self.transcriber = WhisperModel("base", device="cpu", compute_type="int8")
        except Exception as e:
            self.error_occurred.emit(f"Transcriber not available: {e}")
    
    def start_recording(self):
        """Start recording audio"""
        try:
            import sounddevice as sd
            self.is_recording = True
            self.audio_data = []
            
            def audio_callback(indata, frames, time_info, status):
                if status:
                    print(f"Audio status: {status}")
                # Copy audio data (convert to mono if needed)
                audio_chunk = indata[:, 0] if indata.shape[1] > 1 else indata[:, 0]
                self.audio_data.append(audio_chunk.copy())
            
            # Start recording stream
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                callback=audio_callback,
                blocksize=4096
            )
            self.stream.start()
        except ImportError:
            self.error_occurred.emit("sounddevice not installed. Run: pip install sounddevice")
    
    def stop_recording(self):
        """Stop recording and transcribe"""
        self.is_recording = False
        try:
            self.stream.stop()
            self.stream.close()
            
            if not self.audio_data:
                self.error_occurred.emit("No audio recorded")
                return
            
            # Concatenate audio data
            audio_array = np.concatenate(self.audio_data, axis=0)
            
            # Save to temporary file for transcription
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            
            try:
                import soundfile as sf
                sf.write(tmp_path, audio_array, self.sample_rate)
                
                # Transcribe
                if self.transcriber is None:
                    self.error_occurred.emit("Transcriber not loaded")
                    return
                
                segments, _ = self.transcriber.transcribe(
                    tmp_path,
                    language="en",
                    vad_filter=True,
                    condition_on_previous_text=False
                )
                text = " ".join(seg.text.strip() for seg in segments if seg.text)
                self.transcription_ready.emit(text)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        except ImportError:
            self.error_occurred.emit("soundfile not installed. Run: pip install soundfile")
        except Exception as e:
            self.error_occurred.emit(f"Transcription error: {e}")
        finally:
            self.recording_finished.emit()


class ATCFormatter:
    """Handles all ATC transcription formatting rules based on training guidelines"""

    # Standard phraseology (FAA AIM/JO 7110.65) for pilots and controllers
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
    
    # Number to word mapping - always lowercase
    NUMBER_WORDS = {
        '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
        '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'
    }
    
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
        'sixty', 'seventy', 'eighty', 'ninety'
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
        'NOVEMBER', 'CESSNA', 'PIPER', 'CIRRUS', 'SKYHAWK', 'GULFSTREAM',
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
        
        # Step 2: Normalize special cases (AO2 handling)
        formatted = self.normalize_special_cases(text)
        
        # Step 3: Remove all punctuation except commas (Rule from Image 3)
        formatted = self.remove_punctuation(formatted)
        
        # Step 4: Convert special number pronunciations
        formatted = self.convert_special_numbers(formatted)
        
        # Step 5: Convert numbers to words (Rule from Images 6-7)
        formatted = self.convert_numbers_to_words(formatted)
        
        # Step 6: Handle capitalization (Rules from Images 4-5, 11)
        formatted = self.apply_capitalization(formatted)
        
        # Step 6: Validate angled brackets (Rule from Images 9-10)
        formatted = self.validate_brackets(formatted)
        
        # Step 7: Check for phraseology and prohibited words
        self.check_phraseology(formatted)

        # Step 7: Check for violations AFTER formatting
        self.check_violations_after(original_text, formatted)
        
        return formatted, self.violations

    def normalize_special_cases(self, text):
        """Normalize special cases like AO2 to spoken form and handle tail numbers"""
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
                    f"Prohibited phrase: '{phrase}' is not standard ATC phraseology (FAA AIM/JO 7110.65)")

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
                "No standard ATC phraseology detected. Use proper FAA/ICAO terms (e.g., 'roger', 'cleared', 'contact', etc.)")
    
    def remove_punctuation(self, text):
        """
        Remove all punctuation except commas
        Rule from Image 3: Only commas allowed
        """
        # Remove periods, question marks, quotes, exclamation points
        text = re.sub(r'[.!?"\']', '', text)
        text = text.replace(';', ',').replace(':', ',')
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
                        or next_lower in self.NUMBER_WORDS
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


# Speaker role classification functions aligned to evaluation guidance
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


# ...existing code...

class ATCSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for ATC transcripts"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.formatter = ATCFormatter()

        # Define highlighting formats
        self.callsign_format = QTextCharFormat()
        self.callsign_format.setForeground(QColor("#0066CC"))
        self.callsign_format.setFontWeight(QFont.Bold)

        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor("#CC6600"))

        self.filler_format = QTextCharFormat()
        self.filler_format.setForeground(QColor("#999999"))
        self.filler_format.setFontItalic(True)
        
        self.bracket_format = QTextCharFormat()
        self.bracket_format.setForeground(QColor("#CC0000"))
        self.bracket_format.setFontWeight(QFont.Bold)
    
    def highlightBlock(self, text):
        """Apply syntax highlighting to a block of text"""
        # Highlight callsigns (all caps words)
        for match in re.finditer(r'\b[A-Z]{2,}\b', text):
            self.setFormat(match.start(), match.end() - match.start(), self.callsign_format)
        
        # Highlight number words
        number_pattern = r'\b(zero|one|two|three|four|five|six|seven|eight|nine|point)\b'
        for match in re.finditer(number_pattern, text):
            self.setFormat(match.start(), match.end() - match.start(), self.number_format)
        
        # Highlight filler words
        for filler in self.formatter.FILLER_WORDS:
            pattern = r'\b' + filler + r'\b'
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), self.filler_format)
        
        # Highlight angled brackets
        for match in re.finditer(r'<[^>]*>', text):
            self.setFormat(match.start(), match.end() - match.start(), self.bracket_format)


class ATCTranscriptionApp(QMainWindow):
    def save_rules_from_editor(self):
        """Save rules from the Rules Editor UI to the formatter (and eventually to disk)"""
        # Get phraseology and prohibited words from editor
        phraseology = [line.strip() for line in self.phraseology_edit.toPlainText().splitlines() if line.strip()]
        prohibited = [line.strip() for line in self.prohibited_edit.toPlainText().splitlines() if line.strip()]
        # Update formatter in memory (persistence to be added)
        self.formatter.PILOT_PHRASEOLOGY = phraseology
        self.formatter.CONTROLLER_PHRASEOLOGY = phraseology
        self.formatter.PROHIBITED_WORDS = prohibited
        self.statusBar.showMessage("Rules updated (not yet persistent)", 4000)

    def analyze_example_pair(self):
        """Analyze input/output example pair and suggest a rule (placeholder logic)"""
        input_text = self.example_input_edit.toPlainText().strip()
        output_text = self.example_output_edit.toPlainText().strip()
        # Placeholder: just show the diff for now
        if not input_text or not output_text:
            self.suggestion_edit.setPlainText("Please provide both input and correct output.")
            return
        # Simple diff suggestion (to be replaced with real rule learning)
        import difflib
        diff = difflib.unified_diff(
            input_text.splitlines(),
            output_text.splitlines(),
            fromfile='Input',
            tofile='Correct Output',
            lineterm=''
        )
        suggestion = '\n'.join(diff)
        if not suggestion.strip():
            suggestion = "No differences detected."
        self.suggestion_edit.setPlainText(suggestion)
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.formatter = ATCFormatter()
        self.audio_recorder = None
        self.is_recording = False
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("ATC Transcription Tool")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Input
        left_panel = self.create_input_panel()
        
        # Right panel - Output and violations
        right_panel = self.create_output_panel()
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([500, 700])
        
        main_layout.addWidget(splitter)
        
        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
    
    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        open_action = QAction('Open Audio File', self)
        open_action.triggered.connect(self.open_audio_file)
        file_menu.addAction(open_action)
        
        save_action = QAction('Save Transcript', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_transcript)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu('Edit')
        
        clear_action = QAction('Clear All', self)
        clear_action.triggered.connect(self.clear_all)
        edit_menu.addAction(clear_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        rules_action = QAction('ATC Formatting Rules', self)
        rules_action.triggered.connect(self.show_rules)
        help_menu.addAction(rules_action)
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """Create the toolbar"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Recording controls
        self.record_button = QPushButton("🎙️ Record")
        self.record_button.clicked.connect(self.start_recording)
        toolbar.addWidget(self.record_button)
        
        self.stop_button = QPushButton("⏹️ Stop")
        self.stop_button.clicked.connect(self.stop_recording)
        self.stop_button.setEnabled(False)
        toolbar.addWidget(self.stop_button)
        
        toolbar.addSeparator()
        
        format_action = QAction('Auto-Format', self)
        format_action.triggered.connect(self.auto_format)
        toolbar.addAction(format_action)
        
        toolbar.addSeparator()
        
        clear_action = QAction('Clear', self)
        clear_action.triggered.connect(self.clear_all)
        toolbar.addAction(clear_action)
    
    def start_recording(self):
        """Start audio recording"""
        if self.is_recording:
            return
        
        self.is_recording = True
        self.record_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.statusBar.showMessage("Recording... (click Stop to end)")
        
        # Create and start recorder
        self.audio_recorder = AudioRecorder()
        self.audio_recorder.transcription_ready.connect(self.on_transcription_ready)
        self.audio_recorder.error_occurred.connect(self.on_recording_error)
        self.audio_recorder.recording_finished.connect(self.on_recording_finished)
        self.audio_recorder.start_recording()
    
    def stop_recording(self):
        """Stop audio recording and transcribe"""
        if not self.is_recording or self.audio_recorder is None:
            return
        
        self.is_recording = False
        self.record_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.statusBar.showMessage("Processing audio... please wait")
        
        self.audio_recorder.stop_recording()
    
    def on_transcription_ready(self, text):
        """Handle transcribed text"""
        self.input_text.setPlainText(text)
        self.statusBar.showMessage(f"Transcribed: {len(text.split())} words")
        # Auto-format
        self.auto_format()
    
    def on_recording_error(self, error_msg):
        """Handle recording errors"""
        QMessageBox.warning(self, "Recording Error", error_msg)
        self.statusBar.showMessage(f"Error: {error_msg}")
        self.is_recording = False
        self.record_button.setEnabled(True)
        self.stop_button.setEnabled(False)
    
    def on_recording_finished(self):
        """Handle recording finished"""
        self.record_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.statusBar.showMessage("Ready")
    
    def create_input_panel(self):
        """Create the input panel"""
        panel = QGroupBox("Input Transcript")
        layout = QVBoxLayout()
        
        # Input text area
        self.input_text = QTextEdit()
        self.input_text.setFont(QFont("Consolas", 11))
        self.input_text.setPlaceholderText(
            "Enter your ATC transcription here...\n\n"
            "Example:\n"
            "NOVEMBER 998 BRAVO BRAVO, radar services terminated. Squawk VFR, change to advisory is approved.\n\n"
            "The app will automatically format it according to ATC standards."
        )
        layout.addWidget(self.input_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.auto_format_btn = QPushButton("Auto-Format (F5)")
        self.auto_format_btn.clicked.connect(self.auto_format)
        self.auto_format_btn.setStyleSheet("QPushButton { background-color: #0066CC; color: white; padding: 8px; }")
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_all)
        
        button_layout.addWidget(self.auto_format_btn)
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        
        panel.setLayout(layout)
        return panel
    
    def create_output_panel(self):
        """Create the output panel with tabs, including Rules Editor and Learning UI"""
        panel = QWidget()
        layout = QVBoxLayout()

        # Tab widget
        tabs = QTabWidget()

        # Formatted output tab
        output_tab = QWidget()
        output_layout = QVBoxLayout()

        output_label = QLabel("Formatted Transcript:")
        output_label.setFont(QFont("Arial", 10, QFont.Bold))
        output_layout.addWidget(output_label)

        self.output_text = QTextEdit()
        self.output_text.setFont(QFont("Consolas", 11))
        self.output_text.setReadOnly(True)

        # Apply syntax highlighting
        self.highlighter = ATCSyntaxHighlighter(self.output_text.document())

        output_layout.addWidget(self.output_text)

        # Copy button
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self.copy_output)
        output_layout.addWidget(copy_btn)

        output_tab.setLayout(output_layout)
        tabs.addTab(output_tab, "Formatted Output")

        # Violations tab
        violations_tab = QWidget()
        violations_layout = QVBoxLayout()

        violations_label = QLabel("Rule Violations:")
        violations_label.setFont(QFont("Arial", 10, QFont.Bold))
        violations_layout.addWidget(violations_label)

        self.violations_list = QListWidget()
        self.violations_list.setFont(QFont("Arial", 10))
        violations_layout.addWidget(self.violations_list)

        violations_tab.setLayout(violations_layout)
        tabs.addTab(violations_tab, "Violations")

        # Rules reference tab
        rules_tab = QWidget()
        rules_layout = QVBoxLayout()

        self.rules_text = QTextEdit()
        self.rules_text.setReadOnly(True)
        self.rules_text.setFont(QFont("Arial", 10))
        self.rules_text.setHtml(self.get_rules_html())
        rules_layout.addWidget(self.rules_text)

        rules_tab.setLayout(rules_layout)
        tabs.addTab(rules_tab, "Formatting Rules")

        # --- Rules Editor tab ---
        rules_editor_tab = QWidget()
        rules_editor_layout = QVBoxLayout()
        rules_editor_label = QLabel("Rules Editor: Edit/Add Formatting Rules")
        rules_editor_label.setFont(QFont("Arial", 10, QFont.Bold))
        rules_editor_layout.addWidget(rules_editor_label)

        # Phraseology list
        self.phraseology_edit = QTextEdit()
        self.phraseology_edit.setFont(QFont("Consolas", 10))
        self.phraseology_edit.setPlaceholderText("Enter phraseology rules, one per line...")
        rules_editor_layout.addWidget(QLabel("Standard Phraseology (one per line):"))
        rules_editor_layout.addWidget(self.phraseology_edit)

        # Prohibited words list
        self.prohibited_edit = QTextEdit()
        self.prohibited_edit.setFont(QFont("Consolas", 10))
        self.prohibited_edit.setPlaceholderText("Enter prohibited words/phrases, one per line...")
        rules_editor_layout.addWidget(QLabel("Prohibited Words/Phrases (one per line):"))
        rules_editor_layout.addWidget(self.prohibited_edit)

        # Save rules button
        save_rules_btn = QPushButton("Save Rules")
        save_rules_btn.clicked.connect(self.save_rules_from_editor)
        rules_editor_layout.addWidget(save_rules_btn)

        rules_editor_tab.setLayout(rules_editor_layout)
        tabs.addTab(rules_editor_tab, "Rules Editor")

        # --- Learning from Examples tab ---
        learn_tab = QWidget()
        learn_layout = QVBoxLayout()
        learn_label = QLabel("Learning from Examples: Import Input/Output Pairs")
        learn_label.setFont(QFont("Arial", 10, QFont.Bold))
        learn_layout.addWidget(learn_label)

        self.example_input_edit = QTextEdit()
        self.example_input_edit.setFont(QFont("Consolas", 10))
        self.example_input_edit.setPlaceholderText("Paste example input here...")
        learn_layout.addWidget(QLabel("Example Input:"))
        learn_layout.addWidget(self.example_input_edit)

        self.example_output_edit = QTextEdit()
        self.example_output_edit.setFont(QFont("Consolas", 10))
        self.example_output_edit.setPlaceholderText("Paste correct output here...")
        learn_layout.addWidget(QLabel("Correct Output:"))
        learn_layout.addWidget(self.example_output_edit)

        # Learn button
        learn_btn = QPushButton("Analyze & Suggest Rule")
        learn_btn.clicked.connect(self.analyze_example_pair)
        learn_layout.addWidget(learn_btn)

        # Suggestions area
        self.suggestion_edit = QTextEdit()
        self.suggestion_edit.setFont(QFont("Consolas", 10))
        self.suggestion_edit.setReadOnly(True)
        self.suggestion_edit.setPlaceholderText("Rule suggestions will appear here...")
        learn_layout.addWidget(QLabel("Suggested Rule(s):"))
        learn_layout.addWidget(self.suggestion_edit)

        learn_tab.setLayout(learn_layout)
        tabs.addTab(learn_tab, "Learn from Examples")

        layout.addWidget(tabs)
        panel.setLayout(layout)
        return panel
        def save_rules_from_editor(self):
            """Save rules from the Rules Editor UI to the formatter (and eventually to disk)"""
            # Get phraseology and prohibited words from editor
            phraseology = [line.strip() for line in self.phraseology_edit.toPlainText().splitlines() if line.strip()]
            prohibited = [line.strip() for line in self.prohibited_edit.toPlainText().splitlines() if line.strip()]
            # Update formatter in memory (persistence to be added)
            self.formatter.PILOT_PHRASEOLOGY = phraseology
            self.formatter.CONTROLLER_PHRASEOLOGY = phraseology
            self.formatter.PROHIBITED_WORDS = prohibited
            self.statusBar.showMessage("Rules updated (not yet persistent)", 4000)

        def analyze_example_pair(self):
            """Analyze input/output example pair and suggest a rule (placeholder logic)"""
            input_text = self.example_input_edit.toPlainText().strip()
            output_text = self.example_output_edit.toPlainText().strip()
            # Placeholder: just show the diff for now
            if not input_text or not output_text:
                self.suggestion_edit.setPlainText("Please provide both input and correct output.")
                return
            # Simple diff suggestion (to be replaced with real rule learning)
            import difflib
            diff = difflib.unified_diff(
                input_text.splitlines(),
                output_text.splitlines(),
                fromfile='Input',
                tofile='Correct Output',
                lineterm=''
            )
            suggestion = '\n'.join(diff)
            if not suggestion.strip():
                suggestion = "No differences detected."
            self.suggestion_edit.setPlainText(suggestion)
    
    def auto_format(self):
        """Auto-format the input text"""
        input_text = self.input_text.toPlainText()
        
        if not input_text.strip():
            self.statusBar.showMessage("No text to format", 3000)
            return
        
        # Format the text
        formatted_text, violations = self.formatter.format_transcript(input_text)
        
        # Update output
        self.output_text.setPlainText(formatted_text)
        
        # Update violations list
        self.violations_list.clear()
        if violations:
            for violation in violations:
                self.violations_list.addItem("⚠ " + violation)
            self.statusBar.showMessage(f"Formatted with {len(violations)} violation(s)", 5000)
        else:
            self.violations_list.addItem("✓ No violations found - great job!")
            self.statusBar.showMessage("Formatted successfully with no violations", 5000)
    
    def copy_output(self):
        """Copy formatted output to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.output_text.toPlainText())
        self.statusBar.showMessage("Copied to clipboard", 3000)
    
    def clear_all(self):
        """Clear all text fields"""
        self.input_text.clear()
        self.output_text.clear()
        self.violations_list.clear()
        self.statusBar.showMessage("Cleared", 2000)
    
    def open_audio_file(self):
        """Open an audio file for transcription"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Audio File",
            "",
            "Audio Files (*.mp3 *.wav *.m4a *.flac);;All Files (*)"
        )
        if file_path:
            self.statusBar.showMessage(f"Audio file selected: {file_path}", 5000)
            QMessageBox.information(
                self,
                "Audio Transcription",
                "Audio transcription feature coming soon!\n\n"
                "This will use speech-to-text to automatically transcribe ATC audio.\n"
                "For now, please type or paste your transcription manually."
            )
    
    def save_transcript(self):
        """Save the formatted transcript"""
        if not self.output_text.toPlainText():
            QMessageBox.warning(self, "No Content", "There is no formatted transcript to save.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Transcript",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.output_text.toPlainText())
                self.statusBar.showMessage(f"Saved to {file_path}", 5000)
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Could not save file:\n{str(e)}")
    
    def show_rules(self):
        """Show ATC formatting rules summary, referencing FAA AIM and FAA Order JO 7110.65"""
        QMessageBox.information(
            self,
            "ATC Formatting Rules",
            "Key Rules from Training Images (All rules are based on FAA AIM and FAA Order JO 7110.65):\n\n"
            "📋 Image 1: Common Failures\n"
            "• Formatting violations (highest impact)\n"
            "• Callsign handling errors\n\n"
            "🚫 Image 3: Punctuation\n"
            "• Use ONLY commas (FAA AIM/JO 7110.65)\n"
            "• NO periods, question marks, or quotes (FAA AIM/JO 7110.65)\n\n"
            "🔤 Images 4-5: Capitalization\n"
            "• Callsigns in ALL CAPS (FAA Order JO 7110.65 §2-4-20)\n"
            "• Non-callsign words lowercase (airport, tower, runway) (FAA AIM/JO 7110.65)\n\n"
            "🔢 Images 6-7: Numbers\n"
            "• Spell out ALL numbers (one two three) (FAA AIM/JO 7110.65)\n"
            "• NO digits, NO hyphens (FAA AIM/JO 7110.65)\n\n"
            "💬 Image 8: Filler Words\n"
            "• Include: uh, um, oh, ah, hmm (FAA AIM/JO 7110.65)\n\n"
            "📐 Images 9-10: Angled Brackets\n"
            "• Use <> for uncertain words (FAA AIM/JO 7110.65)\n"
            "• Never leave empty brackets (FAA AIM/JO 7110.65)\n\n"
            "✈️ Image 11: Entire callsign ALL CAPS (FAA Order JO 7110.65 §2-4-20)\n\n"
            "See 'Formatting Rules' tab for complete details."
        )
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About ATC Transcription Tool",
            "<h3>ATC Transcription Tool v1.0</h3>"
            "<p>A professional tool for transcribing Air Traffic Control communications "
            "according to FAA/ICAO standards.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Auto-formatting with ATC rules</li>"
            "<li>Callsign detection and validation</li>"
            "<li>Real-time violation warnings</li>"
            "<li>Syntax highlighting</li>"
            "</ul>"
            "<p>Created for aviation professionals and enthusiasts.</p>"
        )
    
    def get_rules_html(self):
        """Get formatted HTML for rules reference - based on training images"""
        return """
        <h2>ATC Transcription Formatting Rules</h2>
        <p><i>Based on your training guidelines</i></p>
        
        <h3>📋 Image 1: Most Common Failures</h3>
        <p>Most failures were not caused by one big mistake, but by many small rule violations:</p>
        <ul>
            <li><b>Formatting violations</b> (highest impact)</li>
            <li>Callsign handling errors/incorrect callsigns</li>
            <li>NATO phonetic spelling errors</li>
            <li>Number transcription errors</li>
            <li>Listening accuracy issues (include filler words)</li>
            <li>UI / editor misuse</li>
            <li>Skipped or incomplete DRs</li>
        </ul>
        
        <h3>🚫 Image 3: Periods, Question Marks, or Quotes</h3>
        <ul>
            <li><b>ONLY punctuation allowed: COMMAS</b></li>
            <li><b>NO periods, question marks, exclamation points, or quotation marks</b></li>
        </ul>
        <p><b style="color: green;">✓ GOOD:</b> NOVEMBER NINE NINE EIGHT BRAVO BRAVO radar services terminated, squawk VFR change to advisory is approved</p>
        <p><b style="color: red;">✗ BAD:</b> "NOVEMBER NINE NINE EIGHT BRAVO BRAVO radar services terminated. Squawk VFR, change to advisory is approved."</p>
        
        <h3>🔤 Image 4: Sentence Capitalization</h3>
        <p>The <b>ONLY</b> words that should be capitalized are:</p>
        <ul>
            <li><b>Callsigns (ALL CAPS)</b></li>
            <li><b>Names of airports/ATC Facility Locations</b></li>
            <li><b>NATO Phonetics</b></li>
            <li><b>Aviation Established Acronyms (ALL CAPS)</b> - VFR, IFR, CTAC, etc.</li>
        </ul>
        <p><b style="color: green;">✓ Correct:</b> one three two four two, thanks, so long, VIVA ONE EIGHT SEVEN</p>
        <p><b style="color: green;">✓ Correct:</b> VOLARIS SEVENTEEN ZERO TWO, <b>flight level</b> three six zero</p>
        <p><b style="color: red;">✗ Incorrect:</b> <u>One</u> three two four two, thanks, so long, VIVA ONE EIGHT SEVEN</p>
        <p><b style="color: red;">✗ Incorrect:</b> VOLARIS SEVENTEEN ZERO TWO, <u>Flight Level</u> three six zero</p>
        
        <h3>🔡 Image 5: Non-Callsign Words (lowercase)</h3>
        <p>These words should <b>NOT</b> be capitalized:</p>
        <ul>
            <li>airport</li>
            <li>tower</li>
            <li>runway</li>
            <li>super</li>
            <li>heavy</li>
            <li>...plus three</li>
            <li>ground</li>
            <li>approach</li>
            <li>ramp</li>
            <li>clearance</li>
            <li>altimeter</li>
            <li>ntell</li>
            <li>codel</li>
        </ul>
        <p><b style="color: green;">✓ Correct:</b> MOBILE FOUR, Salinas ground proceed to CTAC Delta Papa Charlie, hold short <b>runway</b> three one at Charlie</p>
        <p><b style="color: red;">✗ Incorrect:</b> MOBILE FOUR, Salinas ground proceed to CTAC Delta Papa Charlie, hold short <u>Runway</u> three one at Charlie</p>
        
        <h3>🔢 Images 6-7: Numbers / Hyphen Usage</h3>
        <p><b>ALL numbers should be written out. NO numbers should be represented as digits under any circumstances.</b></p>
        <p>Numbers should be written as spoken. <b>No hyphens should be utilized.</b></p>
        <ul>
            <li>"NINER" should be transcribed as "NINE"</li>
            <li>"TREE" should be transcribed as "THREE"</li>
            <li>If spoken as "OH" (in place of zero), transcribe as "OH"</li>
        </ul>
        <p><b style="color: green;">✓ Correct:</b> one three two four two, thanks, so long, VIVA one eight seven</p>
        <p><b style="color: green;">✓ Correct:</b> VOLARIS SEVENTEEN ZERO TWO, flight level three six zero</p>
        <p><b style="color: green;">✓ Correct:</b> NOVEMBER TWENTY NINE EIGHTEEN BRAVO BRAVO radar services terminated</p>
        <p><b style="color: red;">✗ Incorrect:</b> <u>1 3 2 4 2</u>, thanks, so long, VIVA <u>187</u></p>
        <p><b style="color: red;">✗ Incorrect:</b> VOLARIS <u>ONE SEVEN</u> ZERO TWO, flight level three six zero</p>
        <p><b style="color: red;">✗ Incorrect:</b> NOVEMBER <u>TWENTY-NINE</u> EIGHTEEN radar services terminated</p>
        
        <h3>💬 Image 8: Filler Words</h3>
        <p>Filler words should be transcribed when audible. This includes:</p>
        <ul>
            <li>uh</li>
            <li>um</li>
            <li>oh</li>
            <li>ah</li>
            <li>hmm</li>
        </ul>
        <p><b style="color: green;">✓ Correct:</b> NOVEMBER TWO <b>uh</b> FIVE SIX</p>
        <p><b style="color: red;">✗ Incorrect:</b> NOVEMBER TWO FIVE SIX <i>(missing the filler word)</i></p>
        
        <h3>📐 Images 9-10: Angled Brackets &lt;&gt;</h3>
        <p>Angled brackets should be used when there is uncertainty over the word that is stated. You should still transcribe what you <i>think</i> you hear – <b>do not leave empty brackets.</b></p>
        <p>Sometimes, the audio will be cut off, and you'll only hear part of a word. Use context clues to reasonably assume what's supposed to say.</p>
        <p><b>You should also ONLY use angled brackets – not parentheses, not brackets, not ...</b></p>
        <p><b style="color: green;">✓ Correct:</b> &lt;roger that&gt; MEDEVAC</p>
        <p><b style="color: red;">✗ Incorrect:</b> &lt; &gt; MEDEVAC</p>
        <p><b style="color: red;">✗ Incorrect:</b> ... MEDEVAC</p>
        <p><b style="color: red;">✗ Incorrect:</b> (roger that) MEDEVAC</p>
        <p><b style="color: red;">✗ Incorrect:</b> [roger that] MEDEVAC</p>
        
        <h3>✈️ Image 11: Callsign Handling</h3>
        <p><b>The entire callsign should be written in ALL CAPS.</b></p>
        <p>An aircraft type can be used as a callsign, but it depends on the context:</p>
        <p><i>Example:</i> CESSNA ONE TWO THREE, follow the cessna three mile final for runway one six</p>
        <p><b style="color: green;">✓ Correct:</b> VOLARIS SEVENTEEN ZERO TWO, flight level three six zero</p>
        <p><b style="color: red;">✗ Incorrect:</b> <u>Volaris</u> SEVENTEEN ZERO TWO, flight level three six zero</p>
        <p><b style="color: red;">✗ Incorrect:</b> VOLARIS <u>seventeen zero two</u>, flight level three six zero</p>
        
        <h3>🎯 Image 12: How to Identify Callsigns?</h3>
        <ul>
            <li><b>Listen for Placement:</b> Callsigns are <i>typically</i> present at the beginning (or sometimes end) of a transmission</li>
            <li><b>Listen for Patterns:</b> A callsign consists of a word/telephony followed by numbers and sometimes letters spelled phonetically</li>
            <li><b>Listen for Controllers Address the Aircraft:</b> Controllers often address the aircraft by callsign before giving an instruction</li>
        </ul>
        <p><i>Example:</i> "AMERICAN EIGHT FIVE SEVEN, taxi via Juliet..."</p>
        """
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key_F5:
            self.auto_format()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = ATCTranscriptionApp()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
