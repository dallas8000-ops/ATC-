# ATC-

# ATC Transcription Tool

A professional Windows-based application for transcribing Air Traffic Control (ATC) communications according to FAA/ICAO phraseology and formatting standards.

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

### ✅ Auto-Formatting
- Automatically removes prohibited punctuation (periods, question marks, quotes)
- Converts all numbers to spelled-out words
- Applies proper capitalization rules
- Maintains commas (the only allowed punctuation)

### ✅ Audio To Text (Web App)
- Upload an audio file and transcribe it to text
- Capture speaker/system audio from the browser and transcribe it
- Automatically runs the ATC formatter on transcribed text
- Shows raw transcript and formatted transcript side by side for quick review/copy

### ✅ Callsign Detection & Validation
- Identifies and capitalizes callsigns (airlines, tail numbers, NATO phonetics)
- Recognizes common airline callsigns (UNITED, AMERICAN, DELTA, etc.)
- Detects facility names and acronyms
- Ensures non-callsign words remain lowercase

### ✅ Real-Time Rule Violation Warnings
- Detects formatting violations in real-time
- Provides specific feedback on what's wrong
- Highlights common mistakes:
  - Using periods, question marks, or quotes
  - Numbers not spelled out
  - Incorrect capitalization
  - Empty angled brackets
  - Using parentheses instead of angled brackets

### ✅ Syntax Highlighting
- Callsigns highlighted in blue
- Number words highlighted in orange
- Filler words (uh, um, etc.) in gray italics
- Uncertain words in angled brackets in red

### ✅ User-Friendly Interface
- Clean, professional GUI
- Side-by-side input/output panels
- Tabbed interface for violations and rules
- Keyboard shortcuts (F5 for auto-format)
- Copy to clipboard functionality

## Installation

### Prerequisites
- Python 3.7 or higher
- Windows 10/11 (primary target, but works on macOS/Linux too)

### Step 1: Install Python
Download and install Python from [python.org](https://www.python.org/downloads/)

**Important:** During installation, check "Add Python to PATH"

### Step 2: Install Dependencies
Open Command Prompt and run:
```bash
pip install -r requirements.txt
```

Or install PyQt5 directly:
```bash
pip install PyQt5
```

### Step 3: Run the Application
```bash
python atc_transcription_app.py
```

### Step 4: Run the Web App (Audio-to-Text + HTML UI)
```bash
python webapp/app.py
```
Open http://127.0.0.1:5000 in your browser.

## Usage

### Basic Workflow

1. **Enter or paste your transcription** in the left "Input Transcript" panel
2. **Click "Auto-Format"** (or press F5)
3. **Review the formatted output** in the right panel
4. **Check for violations** in the "Violations" tab
5. **Copy or save** your formatted transcript

### Web Audio Workflow
1. Start the web app: `python webapp/app.py`
2. Open the page in a Chromium-based browser
3. Use one of these options:
  - `Upload Audio` to transcribe an existing recording
  - `Record Mic` to capture microphone audio
  - `Capture Speaker Audio` to capture tab/system playback audio
4. Wait for transcription to complete
5. Copy from `Formatted Transcript` and paste where needed

### Example

**Input:**
```
"November 998 Bravo Bravo, radar services terminated. Squawk VFR, change to advisory is approved."
```

**Output:**
```
NOVEMBER NINE NINE EIGHT BRAVO BRAVO radar services terminated, squawk VFR change to advisory is approved
```

**Violations Detected:**
- ⚠ Quotation marks should not be used
- ⚠ Periods should not be used
- ⚠ Numbers should be spelled out (e.g., 'one two three' not '123')

### Keyboard Shortcuts
- **F5** - Auto-format the input text
- **Ctrl+S** - Save formatted transcript

## ATC Formatting Rules

### 1. Punctuation Rules
- ✅ **USE:** Commas only
- ❌ **DON'T USE:** Periods, question marks, exclamation points, quotation marks

### 2. Number Rules
- ✅ **CORRECT:** "one two three four"
- ❌ **INCORRECT:** "1234" or "12-34"
- All numbers must be spelled out as individual digits
- No hyphens between numbers
- "NINER" → "NINE", "TREE" → "THREE"

### 3. Capitalization Rules

**ALL CAPS:**
- Callsigns: `UNITED TWO SIX FORTY EIGHT`
- Airport/facility names: `ATLANTIC CITY`
- NATO phonetics: `NOVEMBER NINE NINE EIGHT BRAVO`
- Aviation acronyms: `VFR`, `IFR`, `CTAC`

**lowercase:**
- airport
- tower
- runway
- super
- heavy
- ground
- approach
- ramp
- clearance
- altimeter

### 4. Filler Words
Always transcribe when audible:
- uh
- um
- oh
- ah
- hmm

### 5. Angled Brackets
- Use `<word>` for uncertain words
- Always include your best guess - never leave empty `<>`
- Use ONLY angled brackets (not parentheses or square brackets)
- Example: `<roger that> MEDEVAC`

### 6. Callsign Identification Tips
- Usually at the beginning or end of transmission
- Pattern: WORD/TELEPHONY + NUMBERS + LETTERS
- Controllers often address aircraft by callsign before instructions
- Example: `AMERICAN EIGHT FIVE SEVEN, taxi via Juliet`

## Advanced Features (Coming Soon)

- 🎤 **Audio Transcription:** Upload audio files for automatic speech-to-text
- ⏱️ **Timestamp Support:** Add timestamps to transcriptions
- 🎵 **Audio Playback:** Built-in audio player with playback controls
- 📊 **Statistics:** Track your transcription accuracy over time
- 💾 **Batch Processing:** Process multiple audio files at once
- 🌐 **Export Formats:** Export to various formats (TXT, DOCX, PDF)

## Troubleshooting

### "PyQt5 not found" error
```bash
pip install PyQt5 --upgrade
```

### Application won't start
- Verify Python 3.7+ is installed: `python --version`
- Check PyQt5 is installed: `pip show PyQt5`
- Try running with: `python -m atc_transcription_app`

### Display issues on high-DPI screens
Add this to the top of `atc_transcription_app.py`:
```python
import os
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
```

## Creating a Windows Executable

To create a standalone .exe file that doesn't require Python:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed atc_transcription_app.py
```

The .exe file will be in the `dist/` folder.

## File Structure

```
atc-transcription-tool/
│
├── atc_transcription_app.py    # Main application file
├── requirements.txt             # Python dependencies
├── README.md                    # This file
│
└── (future additions)
    ├── audio_processor.py       # Audio transcription module
    ├── config.py                # Configuration settings
    └── resources/               # Icons and assets
```

## Contributing

Contributions are welcome! Areas for improvement:
- Audio file transcription using speech-to-text APIs
- Additional ATC phraseology rules
- Export to different formats
- Better callsign detection algorithms
- Multi-language support

## Common ATC Callsigns Recognized

**Airlines:**
- UNITED, AMERICAN, DELTA, SOUTHWEST
- JETBLUE, ALASKA, SPIRIT, FRONTIER
- HAWAIIAN, ALLEGIANT, VOLARIS, VIVA

**General Aviation:**
- CESSNA, PIPER, CIRRUS, SKYHAWK

**Special:**
- MEDEVAC, AIR FORCE ONE, MARINE ONE

## License

MIT License - feel free to use and modify for your needs.

## Acknowledgments

Built according to FAA Order JO 7110.65 and ICAO Annex 10 standards for ATC phraseology.

## Support

For issues or questions:
1. Check the "Formatting Rules" tab in the application
2. Review the examples in this README
3. Ensure you're using the latest version

---

**Version:** 1.0  
**Last Updated:** February 2026  
**Author:** Aviation Transcription Tools
