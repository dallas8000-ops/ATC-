# Quick Start Guide - ATC Transcription Tool

## Installation (5 minutes)

### Step 1: Install Python
1. Go to https://www.python.org/downloads/
2. Download Python 3.7 or higher
3. During installation, **CHECK "Add Python to PATH"**
4. Click "Install Now"

### Step 2: Install the App
1. Extract all files to a folder (e.g., `C:\ATC-Tool\`)
2. Double-click `install.bat`
3. Wait for installation to complete

### Step 3: Run the App
- Double-click `run_app.bat`
- Or open Command Prompt and type: `python atc_transcription_app.py`

## First Use

### Method 1: Type or Paste
1. Type or paste your ATC transcription in the left panel
2. Click "Auto-Format" or press F5
3. Review formatted output on the right
4. Check "Violations" tab for any errors
5. Click "Copy to Clipboard" to use the formatted text

### Method 2: Example Test
1. Open `example_transcripts.txt`
2. Copy one of the BEFORE examples
3. Paste into the app
4. Click "Auto-Format"
5. Compare with the AFTER example

## Common Issues

### "Python not found"
- Reinstall Python and CHECK "Add Python to PATH"
- Restart your computer after installation

### "PyQt5 not found"
- Open Command Prompt
- Type: `pip install PyQt5`
- Press Enter and wait

### App won't start
- Make sure you're in the correct folder
- Right-click on file > "Run as Administrator"

## Quick Reference

### What the App Does:
✅ Removes periods, quotes, question marks  
✅ Converts 123 → "one two three"  
✅ Capitalizes callsigns (UNITED, NOVEMBER)  
✅ Keeps other words lowercase (airport, tower)  
✅ Shows you any formatting mistakes  

### Keyboard Shortcuts:
- **F5** - Auto-format
- **Ctrl+S** - Save transcript

### Example:
**Input:** "United 456, turn left heading 090."  
**Output:** UNITED FOUR FIVE SIX turn left heading zero nine zero

## Need Help?

1. Check the "Formatting Rules" tab in the app
2. Read the full README.md
3. Review example_transcripts.txt
4. Check that Python and PyQt5 are installed correctly

## Next Steps

Once comfortable with basic formatting:
1. Try the practice sentences in example_transcripts.txt
2. Learn the detailed rules in the "Formatting Rules" tab
3. Practice with real ATC recordings
4. Use the violations checker to improve accuracy

---

**Ready to start?** Double-click `run_app.bat`!
