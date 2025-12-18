# OCR Web App - Feature Updates

## Changes Made (December 2025)

### 1. **Editable Prompt Field**
- Changed prompt from display-only to an editable textarea
- Users can now customize the OCR prompt for different use cases
- Textarea is resizable and has a minimum height of 80px

### 2. **Settings Persistence**
- Added automatic saving of user settings to `ocr_settings.json`
- Settings include:
  - Image URL
  - Custom prompt
- Settings are:
  - Saved automatically when OCR runs
  - Loaded automatically when the app restarts
  - Persisted across browser sessions

### 3. **Image Preview**
- Added real-time image preview panel
- Preview automatically loads when:
  - The app launches (with saved URL)
  - The image URL input changes
- Graceful error handling:
  - Shows loading state while fetching
  - Shows error message if image fails to load
  - Shows placeholder when no URL is provided

### 4. **API Enhancements**
- `/api/ocr` endpoint now accepts optional `prompt` parameter
- Added `/api/settings` endpoint for explicit settings management
- Settings are automatically saved on each OCR request

## Technical Details

### New Dependencies
- `json` (built-in)
- `pathlib` (built-in)

### New Files Created
- `ocr_settings.json` - Stores user settings (auto-generated)

### Modified Functions
1. `call_ocr()` - Now accepts optional `prompt` parameter
2. `index()` - Loads saved settings and passes to template
3. `api_ocr()` - Accepts prompt from request and saves settings

### New Functions
1. `load_settings()` - Loads settings from JSON file
2. `save_settings()` - Saves settings to JSON file
3. `loadImagePreview()` (JavaScript) - Handles image preview loading

## Testing

All features have been tested and verified:
- ✅ Settings persistence works correctly
- ✅ Prompt field is editable and values are passed to API
- ✅ Image preview loads on page load
- ✅ Image preview updates when URL changes
- ✅ Graceful error handling for invalid/failed image URLs
- ✅ Settings survive app restarts
- ✅ OCR functionality works with custom prompts
- ✅ Coordinate conversion still works correctly

## Usage Example

### Default Prompt (Text Detection with Coordinates)
```
Detect and recognize text in the image, and output the text coordinates in a formatted manner.
```

### Custom Prompt Examples
```
Extract only the titles from the document.
```

```
Identify all phone numbers in the image.
```

```
Translate the text in the image to English.
```

## Server Configuration

The app respects the `PORT` environment variable:
```bash
PORT=5001 python ocr_web_app.py
```

## Notes

- Settings file is created automatically in the same directory as `ocr_web_app.py`
- The app fails gracefully if settings file cannot be read/written
- Image preview uses client-side loading to avoid server overhead
- Preview failures don't affect OCR functionality

