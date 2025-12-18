# OCR Web App - Feature Guide

## Overview

The OCR Web App now includes enhanced features for a better user experience:
- ✨ **Editable prompts** - Customize OCR behavior
- 💾 **Persistent settings** - Settings saved across sessions
- 🖼️ **Image preview** - See your image before processing
- 🛡️ **Graceful error handling** - Robust failure handling

## Features

### 1. Editable Prompt Field

The prompt field is now fully editable, allowing you to customize the OCR behavior for different use cases.

**Default Prompt:**
```
Detect and recognize text in the image, and output the text coordinates in a formatted manner.
```

**Example Custom Prompts:**

| Use Case | Custom Prompt |
|----------|---------------|
| Text extraction only | `Extract all text from the image.` |
| Document parsing | `Extract all information from the document and represent it in markdown format.` |
| Translation | `First extract the text, then translate it to English.` |
| Information extraction | `Extract the content of the fields: ['name', 'email', 'phone'] and return in JSON format.` |
| Subtitle extraction | `Extract the subtitles from the image.` |

### 2. Settings Persistence

All settings are automatically saved and restored:

**What's saved:**
- Image URL
- Custom prompt

**When it's saved:**
- Automatically when you run OCR
- Can also use the settings API endpoint

**Where it's stored:**
- `ocr_settings.json` in the app directory

**How to verify:**
1. Enter an image URL and custom prompt
2. Click "Run OCR"
3. Restart the app (press Ctrl+C and restart)
4. Open the web UI - your settings are restored!

### 3. Image Preview

The image preview loads automatically to help you verify your image before running OCR.

**Preview behavior:**
- ✅ Loads automatically when the app starts (if URL is saved)
- ✅ Updates automatically when you change the image URL
- ✅ Shows loading state while fetching
- ✅ Shows error message if image fails to load
- ✅ Supports all standard image formats (JPG, PNG, GIF, WebP)

**Preview states:**

| State | Display |
|-------|---------|
| No URL | 📷 Enter an image URL to preview |
| Loading | ⏳ Loading image... |
| Success | Shows the actual image |
| Error | ⚠️ Failed to load image |

**Important:** Preview failures don't affect OCR functionality. Even if the preview fails, OCR might still work if the remote service can access the image.

### 4. Enhanced UI

The web interface now includes:

**Input Panel:**
- Image URL field
- Editable prompt textarea (resizable)
- Run OCR button

**Image Preview Panel:**
- Real-time image preview
- Loading and error states

**Results Panels:**
- Status log with progress steps
- Raw text output
- Text blocks table with coordinates
- Annotated image with bounding boxes

## Usage Examples

### Example 1: Standard Text Detection with Coordinates

1. Enter image URL: `https://example.com/document.jpg`
2. Keep default prompt or use:
   ```
   Detect and recognize text in the image, and output the text coordinates in a formatted manner.
   ```
3. Click "Run OCR"
4. View results with coordinates in both normalized (0-1000) and pixel coordinates

### Example 2: Custom Information Extraction

1. Enter image URL: `https://example.com/business-card.jpg`
2. Change prompt to:
   ```
   Extract the content of the fields: ['name', 'email', 'phone', 'company'] from the image and return it in JSON format.
   ```
3. Click "Run OCR"
4. Get structured JSON output

### Example 3: Document Translation

1. Enter image URL: `https://example.com/chinese-doc.jpg`
2. Change prompt to:
   ```
   First extract the text, then translate the text content into English.
   ```
3. Click "Run OCR"
4. Get translated text

## API Usage

### OCR with Custom Prompt

```bash
curl -X POST http://localhost:5001/api/ocr \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/image.jpg",
    "prompt": "Your custom prompt here"
  }'
```

### Save Settings

```bash
curl -X POST http://localhost:5001/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/image.jpg",
    "prompt": "Your custom prompt"
  }'
```

## Troubleshooting

### Image Preview Not Loading

**Problem:** Preview shows "Failed to load image"

**Possible causes:**
- Image URL is incorrect
- Image requires authentication
- CORS restrictions
- Network connectivity issues

**Solution:**
- Verify the URL in your browser
- Use publicly accessible images
- Check if the image loads directly in a new tab
- Preview failure doesn't prevent OCR from working

### Settings Not Persisting

**Problem:** Settings reset after restart

**Possible causes:**
- File write permissions
- `ocr_settings.json` is deleted
- App directory is not writable

**Solution:**
- Check file permissions on the app directory
- Verify `ocr_settings.json` exists and is writable
- Check app logs for any error messages

### Prompt Not Working

**Problem:** Custom prompt not producing expected results

**Possible causes:**
- Prompt format is incorrect
- OCR model doesn't understand the instruction
- Image content doesn't match the prompt

**Solution:**
- Try the recommended prompts from the guide
- Use clear, specific instructions
- Test with the default prompt first
- Refer to HunyuanOCR documentation for supported tasks

## Running the App

### Start the server:

```bash
cd hy-ocr-app-python(20251215)
source venv/bin/activate
python ocr_web_app.py
```

### Or with a custom port:

```bash
PORT=5001 python ocr_web_app.py
```

### Open in browser:

```
http://localhost:5000
```
or
```
http://localhost:5001
```

## Additional Resources

- [HunyuanOCR Documentation](https://github.com/Tencent-Hunyuan/HunyuanOCR)
- [Coordinate System Documentation](ocr_utils.py)
- [Sample OCR Output](doc/sample_ocr_output.txt)

## Support

For issues or questions:
1. Check the CHANGELOG_WEB_APP.md for recent changes
2. Review the troubleshooting section above
3. Test with the provided test script: `./test_web_app_features.sh`

