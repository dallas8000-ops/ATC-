import os
import json
import re
import time
from threading import Lock
from flask import Flask, request, jsonify, send_from_directory, render_template
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB max

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Remove old files from uploads/ (fail-open if env unset)
UPLOAD_MAX_AGE_SEC = int(os.environ.get('UPLOAD_MAX_AGE_HOURS', '24')) * 3600
UPLOAD_CLEANUP_INTERVAL_SEC = float(os.environ.get('UPLOAD_CLEANUP_INTERVAL_SEC', '3600'))
_upload_cleanup_last = 0.0
_upload_cleanup_lock = Lock()


def cleanup_stale_uploads():
    """Delete regular files in UPLOAD_FOLDER older than UPLOAD_MAX_AGE_SEC."""
    folder = app.config['UPLOAD_FOLDER']
    if not os.path.isdir(folder):
        return
    now = time.time()
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        try:
            if os.path.isfile(path) and now - os.path.getmtime(path) > UPLOAD_MAX_AGE_SEC:
                os.unlink(path)
        except OSError:
            pass


@app.before_request
def _periodic_upload_cleanup():
    global _upload_cleanup_last
    if UPLOAD_MAX_AGE_SEC <= 0:
        return
    now = time.time()
    with _upload_cleanup_lock:
        if now - _upload_cleanup_last < UPLOAD_CLEANUP_INTERVAL_SEC:
            return
        _upload_cleanup_last = now
    cleanup_stale_uploads()

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


import sys
from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from atc_core import (
    ATCFormatter,
    classify_speaker_role,
    extract_callsign_key,
    build_review_assessment,
)

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
        segments = list(segments)
        parts = []
        total_lp = 0.0
        n_lp = 0
        for seg in segments:
            t = (getattr(seg, "text", None) or "").strip()
            if t:
                parts.append(t)
            lp = getattr(seg, "avg_logprob", None)
            if lp is not None:
                total_lp += float(lp)
                n_lp += 1
        avg_logprob = (total_lp / n_lp) if n_lp else None
        text = re.sub(r'\s+', ' ', " ".join(parts)).strip()
        return text, avg_logprob

transcriber = AudioTranscriber()


def _format_with_fresh_formatter(text):
    """Use a new ATCFormatter per request so concurrent users cannot share violation state."""
    return ATCFormatter().format_transcript(text)


@app.route('/api/format', methods=['POST'])
def format_transcript():
    data = _json_body()
    text = data.get('text', '')
    formatted, violations = _format_with_fresh_formatter(text)
    speaker = classify_speaker_role(text)
    assessment = build_review_assessment(text, formatted, violations, speaker, avg_logprob=None)
    return jsonify({
        'formatted': formatted,
        'violations': violations,
        'speaker': speaker,
        'assessment': assessment,
    })


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
        raw_text, avg_logprob = transcriber.transcribe(file_path)
    except Exception as exc:
        return jsonify({'error': f'Transcription failed: {exc}'}), 500

    formatted, violations = _format_with_fresh_formatter(raw_text)
    speaker = classify_speaker_role(raw_text)
    assessment = build_review_assessment(raw_text, formatted, violations, speaker, avg_logprob)
    return jsonify({
        'raw_text': raw_text,
        'formatted': formatted,
        'violations': violations,
        'filename': safe_filename,
        'avg_logprob': avg_logprob,
        'speaker': speaker,
        'assessment': assessment,
    })

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # Never enable debug on a host reachable by others (interactive debugger = RCE risk).
    _debug = os.environ.get('FLASK_DEBUG', '').strip().lower() in ('1', 'true', 'yes')
    with app.app_context():
        cleanup_stale_uploads()
    app.run(debug=_debug, host=os.environ.get('FLASK_HOST', '127.0.0.1'), port=int(os.environ.get('FLASK_PORT', '5000')))
