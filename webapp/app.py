import os
import json
from flask import Flask, request, jsonify, send_from_directory, render_template
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB max

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

EXAMPLES_FILE = 'examples.json'
RULES_FILE = 'custom_rules.json'

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
    data = request.json
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
    data = request.json
    save_custom_rules(data)
    return jsonify({'status': 'ok'})

# ATCFormatter logic ported from desktop app
import re
class ATCFormatter:
    PILOT_PHRASEOLOGY = [
        'roger', 'wilco', 'affirmative', 'negative', 'standby', 'unable', 'cleared',
        'ready', 'request', 'with you', 'leaving', 'passing', 'descending', 'climbing',
        'maintain', 'contact', 'squawk', 'ident', 'line up', 'hold short', 'taxi',
        'pushback', 'readback', 'copy', 'repeat', 'say again', 'go ahead', 'over', 'out'
    ]
    CONTROLLER_PHRASEOLOGY = [
        'cleared', 'contact', 'descend', 'climb', 'maintain', 'expect', 'hold',
        'proceed', 'turn', 'squawk', 'change', 'frequency', 'radar contact',
        'radar services terminated', 'line up', 'wait', 'cross', 'taxi', 'pushback',
        'monitor', 'report', 'advise', 'approved', 'standby', 'affirmative', 'negative'
    ]
    PROHIBITED_WORDS = [
        'repeat', 'repeat back', 'over and out', 'ten four', 'copy that', 'breaker', 'come in', 'do you read'
    ]

    NATO_PHONETIC = {
        'A': 'ALPHA', 'B': 'BRAVO', 'C': 'CHARLIE', 'D': 'DELTA',
        'E': 'ECHO', 'F': 'FOXTROT', 'G': 'GOLF', 'H': 'HOTEL',
        'I': 'INDIA', 'J': 'JULIETT', 'K': 'KILO', 'L': 'LIMA',
        'M': 'MIKE', 'N': 'NOVEMBER', 'O': 'OSCAR', 'P': 'PAPA',
        'Q': 'QUEBEC', 'R': 'ROMEO', 'S': 'SIERRA', 'T': 'TANGO',
        'U': 'UNIFORM', 'V': 'VICTOR', 'W': 'WHISKEY', 'X': 'XRAY',
        'Y': 'YANKEE', 'Z': 'ZULU'
    }
    NATO_PHONETIC_REVERSE = {v: k for k, v in NATO_PHONETIC.items()}
    NUMBER_WORDS = {
        '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
        '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'
    }
    SPECIAL_NUMBERS = {
        'niner': 'nine',
        'tree': 'three',
        'fife': 'five'
    }
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
    FILLER_WORDS = ['uh', 'um', 'oh', 'ah', 'hmm']
    AIRLINE_CALLSIGNS = [
        'UNITED', 'AMERICAN', 'DELTA', 'SOUTHWEST', 'JETBLUE', 'ALASKA',
        'SPIRIT', 'FRONTIER', 'HAWAIIAN', 'ALLEGIANT', 'VOLARIS', 'VIVA',
        'MEDEVAC', 'MOBILE', 'CESSNA', 'PIPER', 'CIRRUS', 'SKYHAWK',
        'NOVEMBER', 'CHARLIE', 'ALPHA', 'BRAVO', 'DELTA', 'ECHO',
        'FOXTROT', 'GOLF', 'HOTEL', 'INDIA', 'JULIET', 'KILO',
        'LIMA', 'MIKE', 'OSCAR', 'PAPA', 'QUEBEC', 'ROMEO',
        'SIERRA', 'TANGO', 'UNIFORM', 'VICTOR', 'WHISKEY', 'XRAY',
        'YANKEE', 'ZULU', 'VOLARIS', 'AVIAN', 'SCANDINAVIAN',
        'PHOENIX', 'ATLANTIC', 'KANSAS', 'CITY', 'CHICAGO', 'OHARE'
    ]
    AVIATION_ACRONYMS = [
        'VFR', 'IFR', 'CTAC', 'ATIS', 'AWOS', 'ASOS', 'ATC',
        'ILS', 'VOR', 'NDB', 'DME', 'GPS', 'RNAV', 'SID', 'STAR'
    ]

    def __init__(self):
        self.violations = []

    def format_transcript(self, text):
        self.violations = []
        if not text.strip():
            return text, []
        original_text = text
        self.check_violations_before(original_text)
        formatted = self.remove_punctuation(text)
        formatted = self.convert_special_numbers(formatted)
        formatted = self.convert_numbers_to_words(formatted)
        formatted = self.apply_capitalization(formatted)
        formatted = self.validate_brackets(formatted)
        self.check_phraseology(formatted)
        self.check_violations_after(original_text, formatted)
        return formatted, self.violations

    def check_phraseology(self, text):
        text_lower = text.lower()
        for word in self.PROHIBITED_WORDS:
            if word in text_lower:
                self.violations.append(f"Prohibited phrase: '{word}' is not standard ATC phraseology (FAA AIM/JO 7110.65)")
        if not any(phrase in text_lower for phrase in self.PILOT_PHRASEOLOGY + self.CONTROLLER_PHRASEOLOGY):
            self.violations.append("No standard ATC phraseology detected. Use proper FAA/ICAO terms (e.g., 'roger', 'cleared', 'contact', etc.)")

    def remove_punctuation(self, text):
        text = re.sub(r'[.?!"\']', '', text)
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
                result = ' '.join(self.NUMBER_WORDS.get(d, d) for d in parts[0])
                result += ' point '
                result += ' '.join(self.NUMBER_WORDS.get(d, d) for d in parts[1])
                return result
            return ' '.join(self.NUMBER_WORDS.get(digit, digit) for digit in number)
        text = re.sub(r'\d+\.?\d*', replace_number, text)
        return text

    def apply_capitalization(self, text):
        words = text.split()
        formatted_words = []
        i = 0
        callsign_mode = True
        while i < len(words):
            word = words[i]
            word_upper = word.upper()
            word_lower = word.lower()
            # Handle uncertain words in brackets
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
            # Call sign logic: uppercase for call sign and numbers in call sign
            if callsign_mode:
                if word_upper in self.NATO_PHONETIC.values() or word_upper in self.AIRLINE_CALLSIGNS or word_upper in self.AVIATION_ACRONYMS:
                    formatted_words.append(word_upper)
                elif word.isdigit():
                    # Spell out each digit in uppercase
                    spelled = ' '.join(self.NUMBER_WORDS[d].upper() for d in word)
                    formatted_words.append(spelled)
                else:
                    formatted_words.append(word_upper)
                # End call sign mode if next word is not part of call sign (but allow multi-word call signs)
                if (i + 1 < len(words) and (words[i + 1].lower() in self.NON_CALLSIGN_WORDS or words[i + 1].lower() in self.FILLER_WORDS)):
                    callsign_mode = False
            else:
                if word_upper in self.AVIATION_ACRONYMS:
                    formatted_words.append(word_upper)
                elif word_lower in self.NON_CALLSIGN_WORDS:
                    formatted_words.append(word_lower)
                    if word_lower in ['contact', 'squawk', 'radar', 'change']:
                        callsign_mode = False
                elif word_lower in self.FILLER_WORDS:
                    formatted_words.append(word_lower)
                elif word_lower in self.NUMBER_WORDS.values() or word_lower == 'point':
                    formatted_words.append(word_lower)
                else:
                    formatted_words.append(word_lower)
                    if word_lower not in ['and', 'to', 'via', 'at', 'is']:
                        callsign_mode = False
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
        if '"' in text or "'" in text or '"' in text or '"' in text:
            self.violations.append("⚠ Quotation marks should not be used (Image 3: Punctuation Rules)")
        if re.search(r'\b\d+\b', text):
            self.violations.append("⚠ Numbers should be spelled out - write 'one two three' not '123' (Images 6-7: Number Rules)")
        if re.search(r'\d+-\d+', text):
            self.violations.append("⚠ No hyphens between numbers - write 'two six four eight' not '26-48' (Image 7)")
        if re.search(r'(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)-(one|two|three|four|five|six|seven|eight|nine)', text, re.IGNORECASE):
            self.violations.append("⚠ No hyphens in number words - write 'TWENTY NINE' not 'TWENTY-NINE' (Image 7)")

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

formatter = ATCFormatter()

@app.route('/api/format', methods=['POST'])
def format_transcript():
    data = request.json
    text = data.get('text', '')
    formatted, violations = formatter.format_transcript(text)
    return jsonify({'formatted': formatted, 'violations': violations})

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

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
