import os
import json
import re
from threading import Lock
from flask import Flask, request, jsonify, send_from_directory, render_template
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB max

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

EXAMPLES_FILE = 'examples.json'
RULES_FILE = 'custom_rules.json'


def _json_body(default=None):
    """Safely parse JSON body and fall back to a default payload."""
    if default is None:
        default = {}
    return request.get_json(silent=True) or default

def load_examples():
    if os.path.exists(EXAMPLES_FILE):
        with open(EXAMPLES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_examples(examples):
    with open(EXAMPLES_FILE, 'w', encoding='utf-8') as f:
        json.dump(examples, f, indent=2)

def load_custom_rules():
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_custom_rules(rules):
    with open(RULES_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules, f, indent=2)

# API: Examples
@app.route('/api/examples', methods=['GET'])
def get_examples():
    return jsonify(load_examples())

@app.route('/api/examples', methods=['POST'])
def add_example():
    data = _json_body()
    examples = load_examples()
    examples.append({
        'input': data.get('input', ''),
        'output': data.get('output', '')
    })
    save_examples(examples)
    return jsonify({'status': 'ok'})

# API: Custom Rules
@app.route('/api/rules', methods=['GET'])
def get_rules():
    return jsonify(load_custom_rules())

@app.route('/api/rules', methods=['POST'])
def update_rules():
    data = _json_body({})
    save_custom_rules(data)
    return jsonify({'status': 'ok'})


class ATCFormatter:
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

    NUMBER_DIGITS = {
        '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
        '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'
    }
    SPECIAL_NUMBERS = {
        'niner': 'nine',
        'tree': 'three',
        'fife': 'five'
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
        self.violations = []
        if not text.strip():
            return text, []
        original_text = text
        self.check_violations_before(original_text)
        formatted = self.normalize_special_cases(text)
        formatted = self.remove_punctuation(formatted)
        formatted = self.convert_special_numbers(formatted)
        formatted = self.convert_numbers_to_words(formatted)
        formatted = self.apply_capitalization(formatted)
        formatted = self.validate_brackets(formatted)
        self.check_phraseology(formatted)
        self.check_violations_after(original_text, formatted)
        return formatted, self.violations

    def normalize_special_cases(self, text):
        # Evaluation-specific rule: AO2 is spoken as "a oh two" and should not be treated like an acronym.
        return re.sub(r'\bAO2\b', 'a oh two', text, flags=re.IGNORECASE)

    def check_phraseology(self, text):
        text_lower = text.lower()
        for phrase in self.PROHIBITED_PHRASES:
            if re.search(r'\b' + re.escape(phrase) + r'\b', text_lower):
                self.violations.append(
                    f"Prohibited phrase: '{phrase}' is not standard ATC phraseology (FAA AIM/JO 7110.65)"
                )
        known = self.PILOT_PHRASEOLOGY.union(self.CONTROLLER_PHRASEOLOGY)
        if not any(phrase in text_lower for phrase in known):
            self.violations.append("No standard ATC phraseology detected. Use proper FAA/ICAO terms (e.g., 'roger', 'cleared', 'contact', etc.)")

    def remove_punctuation(self, text):
        text = re.sub(r'[.!?"\']', '', text)
        text = text.replace(';', ',').replace(':', ',')
        return text

    def convert_special_numbers(self, text):
        words = text.split()
        converted = []
        for word in words:
            word_lower = word.lower()
            if word_lower in self.SPECIAL_NUMBERS:
                if word.isupper():
                    converted.append(self.SPECIAL_NUMBERS[word_lower].upper())
                else:
                    converted.append(self.SPECIAL_NUMBERS[word_lower])
            else:
                converted.append(word)
        return ' '.join(converted)

    def convert_numbers_to_words(self, text):
        text = re.sub(r'(\d+)-(\d+)', r'\1 \2', text)
        text = re.sub(r'(TWENTY|THIRTY|FORTY|FIFTY|SIXTY|SEVENTY|EIGHTY|NINETY)-(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE)', r'\1 \2', text, flags=re.IGNORECASE)
        def replace_number(match):
            number = match.group(0)
            if '.' in number:
                parts = number.split('.')
                result = ' '.join(self.NUMBER_DIGITS.get(d, d) for d in parts[0])
                result += ' point '
                result += ' '.join(self.NUMBER_DIGITS.get(d, d) for d in parts[1])
                return result
            return ' '.join(self.NUMBER_DIGITS.get(digit, digit) for digit in number)
        text = re.sub(r'\d+\.?\d*', replace_number, text)
        return text

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

            # Parse tail-number style callsigns: N123AB -> NOVEMBER ONE TWO THREE ALFA BRAVO
            tail_match = re.fullmatch(r'N(\d+)([A-Za-z]{0,3})', raw_word, flags=re.IGNORECASE)
            if tail_match:
                formatted_words.append('NOVEMBER')
                digits = tail_match.group(1)
                suffix = tail_match.group(2).upper()
                formatted_words.extend(self.NUMBER_DIGITS[d].upper() for d in digits)
                for char in suffix:
                    formatted_words.append('ALFA' if char == 'A' else char)
                if has_comma:
                    formatted_words[-1] = formatted_words[-1] + ','
                i += 1
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

    def validate_brackets(self, text):
        if '<>' in text or '< >' in text:
            self.violations.append("Empty angled brackets found - always include your best guess inside <>")
        if '(' in text or ')' in text:
            text = text.replace('(', '<').replace(')', '>')
            self.violations.append("Parentheses found - use angled brackets <> for uncertain words, not ()")
        if '[' in text or ']' in text:
            text = text.replace('[', '<').replace(']', '>')
            self.violations.append("Square brackets found - use angled brackets <> for uncertain words, not []")
        return text

    def check_violations_before(self, text):
        if '.' in text and not re.search(r'\d+\.\d+', text):
            self.violations.append("⚠ Periods should not be used (Image 3: Punctuation Rules)")
        if '?' in text:
            self.violations.append("⚠ Question marks should not be used (Image 3: Punctuation Rules)")
        if '!' in text:
            self.violations.append("⚠ Exclamation points should not be used (Image 3: Punctuation Rules)")
        if '"' in text or "'" in text or '"' in text or '"' in text:
            self.violations.append("⚠ Quotation marks should not be used (Image 3: Punctuation Rules)")
        if re.search(r'\b\d+\b', text):
            self.violations.append("⚠ Numbers should be spelled out - write 'one two three' not '123' (Images 6-7: Number Rules)")
        if re.search(r'\d+-\d+', text):
            self.violations.append("⚠ No hyphens between numbers - write 'two six four eight' not '26-48' (Image 7)")
        if re.search(r'(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)-(one|two|three|four|five|six|seven|eight|nine)', text, re.IGNORECASE):
            self.violations.append("⚠ No hyphens in number words - write 'TWENTY NINE' not 'TWENTY-NINE' (Image 7)")
        if re.search(r'\bAO2\b', text, flags=re.IGNORECASE):
            self.violations.append("⚠ 'AO2' should be transcribed as 'a oh two' instead of an acronym")

    def check_violations_after(self, original, formatted):
        non_callsign_caps = ['Airport', 'Tower', 'Runway', 'Ground', 'Approach', 'Super', 'Heavy']
        for word in non_callsign_caps:
            if word in original:
                self.violations.append(f"⚠ '{word}' should not be capitalized - it's not a callsign (Image 5: Capitalization)")
        if '<>' in formatted or '< >' in formatted:
            self.violations.append("⚠ Empty angled brackets - always transcribe your best guess (Images 9-10: Brackets)")
        if '(' in original or ')' in original:
            self.violations.append("⚠ Use angled brackets <> for uncertainty, not parentheses () (Image 9-10)")
        if '[' in original or ']' in original:
            self.violations.append("⚠ Use angled brackets <> for uncertainty, not square brackets [] (Image 9-10)")
        mixed_case_pattern = r'\b[A-Z][a-z]+\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|ZERO)\b'
        if re.search(mixed_case_pattern, original):
            self.violations.append("⚠ Entire callsign should be ALL CAPS - write 'VOLARIS' not 'Volaris' (Image 11)")


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


class AudioTranscriber:
    """Lazy-loaded faster-whisper wrapper for ATC audio transcription."""

    def __init__(self):
        self._model = None
        self._lock = Lock()

    def _load_model(self):
        with self._lock:
            if self._model is not None:
                return

            try:
                # Import lazily so web formatting still works even if the package is missing.
                from faster_whisper import WhisperModel
            except Exception as exc:
                raise RuntimeError(
                    "faster-whisper is not installed. Run: pip install -r requirements.txt"
                ) from exc

            # CPU-friendly default model for laptops/desktops.
            self._model = WhisperModel("base", device="cpu", compute_type="int8")

    def transcribe(self, audio_path):
        self._load_model()
        segments, _ = self._model.transcribe(
            audio_path,
            language="en",
            vad_filter=True,
            condition_on_previous_text=False,
            beam_size=1,
        )
        text = " ".join(seg.text.strip() for seg in segments if seg.text and seg.text.strip())
        return re.sub(r'\s+', ' ', text).strip()

formatter = ATCFormatter()
transcriber = AudioTranscriber()

@app.route('/api/format', methods=['POST'])
def format_transcript():
    data = _json_body()
    text = data.get('text', '')
    formatted, violations = formatter.format_transcript(text)
    return jsonify({'formatted': formatted, 'violations': violations})


@app.route('/api/classify', methods=['POST'])
def classify_single_utterance():
    data = _json_body()
    text = data.get('text', '')
    return jsonify(classify_speaker_role(text))


@app.route('/api/classify-sequence', methods=['POST'])
def classify_sequence():
    data = _json_body({'utterances': []})
    utterances = data.get('utterances', [])
    if not isinstance(utterances, list):
        return jsonify({'error': 'utterances must be a list of strings'}), 400

    speaker_map = {}
    next_id = 1
    results = []

    for utterance in utterances:
        item = classify_speaker_role(utterance)
        callsign_key = extract_callsign_key(utterance)

        if callsign_key:
            stable_key = f"{item['speaker_role']}::{callsign_key}"
        elif item['speaker_role'] == 'ATC':
            stable_key = 'ATC::channel'
        else:
            stable_key = f"UNKNOWN::{next_id}"

        if stable_key not in speaker_map:
            speaker_map[stable_key] = next_id
            next_id += 1

        item['speaker_id'] = speaker_map[stable_key]
        item['text'] = utterance
        results.append(item)

    return jsonify({'results': results})

@app.route('/api/upload', methods=['POST'])
def upload_audio():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    return jsonify({'filename': filename})


@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    data = _json_body()
    filename = data.get('filename', '').strip()
    if not filename:
        return jsonify({'error': 'filename is required'}), 400

    safe_filename = secure_filename(filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'Audio file not found'}), 404

    try:
        raw_text = transcriber.transcribe(file_path)
    except Exception as exc:
        return jsonify({'error': f'Transcription failed: {exc}'}), 500

    formatted, violations = formatter.format_transcript(raw_text)
    return jsonify({
        'raw_text': raw_text,
        'formatted': formatted,
        'violations': violations,
        'filename': safe_filename,
    })

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
