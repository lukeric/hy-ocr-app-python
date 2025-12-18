# Quick Start Guide - OCR Web App

## 🚀 Start the App

```bash
cd hy-ocr-app-python(20251215)
source venv/bin/activate
PORT=5001 python ocr_web_app.py
```

Then open: **http://localhost:5001**

## 🎯 Feature Demonstrations

### Demo 1: Basic Usage with Default Settings

1. **The app loads with default settings:**
   - Image URL: `https://ev-cuhk.net/tmp/t01.jpg`
   - Prompt: Default OCR prompt for text detection

2. **Image preview loads automatically** - You'll see the image displayed

3. **Click "Run OCR"** - Results appear with:
   - Status updates
   - Raw text output
   - Table of detected text blocks with coordinates
   - Annotated image with bounding boxes

### Demo 2: Custom Prompt for Information Extraction

1. **Change the prompt to:**
   ```
   Extract all phone numbers and email addresses from the image.
   ```

2. **Click "Run OCR"** - Get filtered results

3. **Check the settings file:**
   ```bash
   cat ocr_settings.json
   ```
   Your custom prompt is saved!

### Demo 3: Settings Persistence

1. **Enter a new image URL:**
   ```
   https://example.com/your-image.jpg
   ```

2. **Modify the prompt:**
   ```
   Extract all text from the image.
   ```

3. **Click "Run OCR"**

4. **Restart the app:**
   ```bash
   # Press Ctrl+C to stop
   PORT=5001 python ocr_web_app.py
   ```

5. **Open http://localhost:5001** - Your settings are still there! ✨

### Demo 4: Image Preview with Different URLs

1. **Try a valid image URL:**
   ```
   https://ev-cuhk.net/tmp/t01.jpg
   ```
   ✅ Preview loads successfully

2. **Try an invalid URL:**
   ```
   https://invalid-url-does-not-exist.com/image.jpg
   ```
   ⚠️ Preview shows error message (but OCR can still be attempted)

3. **Clear the URL:**
   - Delete all text from URL field
   - 📷 Preview shows "Enter an image URL to preview"

## 🧪 Run Tests

```bash
./test_web_app_features.sh
```

Expected output:
```
==================================
OCR Web App Feature Tests
==================================

Test 1: Save settings via API
------------------------------
{"success": true}

Test 2: Verify settings load on page
-------------------------------------
Image URL in HTML: value="https://ev-cuhk.net/tmp/t01.jpg"

Test 3: Run OCR with custom prompt
-----------------------------------
Status: Done
Blocks detected: 15
Endpoint: https://hunyuan-ocr...
...

==================================
All tests completed successfully!
==================================
```

## 📖 Example Use Cases

### Use Case 1: Business Card Scanning
```
Prompt: Extract the content of the fields: ['name', 'company', 'email', 'phone'] and return in JSON format.
```

### Use Case 2: Document Translation
```
Prompt: First extract the text, then translate the text content into English.
```

### Use Case 3: Receipt Processing
```
Prompt: Extract the total amount, date, and merchant name from the receipt.
```

### Use Case 4: Subtitle Extraction
```
Prompt: Extract the subtitles from the video frame.
```

### Use Case 5: Form Data Extraction
```
Prompt: Extract all form fields and their values, return as JSON.
```

## 🔧 Troubleshooting

### Port Already in Use
```bash
# Use a different port
PORT=5002 python ocr_web_app.py
```

### Settings Not Saving
```bash
# Check file permissions
ls -la ocr_settings.json

# Manually create with correct format
echo '{"image_url": "", "prompt": ""}' > ocr_settings.json
```

### Preview Not Loading
- Check if the URL is publicly accessible
- Try opening the URL directly in your browser
- Check browser console for CORS errors
- Remember: Preview failure doesn't prevent OCR from working

## 📚 More Information

- **Feature Guide**: See `FEATURE_GUIDE.md`
- **Changelog**: See `CHANGELOG_WEB_APP.md`
- **Implementation Details**: See `IMPLEMENTATION_SUMMARY.md`
- **Test Script**: Run `./test_web_app_features.sh`

## 🎉 You're All Set!

Enjoy the enhanced OCR Web App with:
- ✨ Customizable prompts
- 💾 Persistent settings
- 🖼️ Real-time image preview
- 🛡️ Graceful error handling

Happy OCR processing! 🚀

