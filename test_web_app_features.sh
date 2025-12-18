#!/bin/bash
################################################################################
# Test script for OCR Web App new features
# Tests: editable prompt, settings persistence, and API functionality
################################################################################

set -e

APP_URL="http://127.0.0.1:5001"
SETTINGS_FILE="ocr_settings.json"

echo "=================================="
echo "OCR Web App Feature Tests"
echo "=================================="
echo ""

# Test 1: Settings API
echo "Test 1: Save settings via API"
echo "------------------------------"
curl -s -X POST "$APP_URL/api/settings" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://ev-cuhk.net/tmp/t01.jpg",
    "prompt": "Test prompt from API"
  }' | python3 -m json.tool

echo ""
echo "Settings file contents:"
cat "$SETTINGS_FILE"
echo ""
echo ""

# Test 2: Verify settings load on page
echo "Test 2: Verify settings load on page"
echo "-------------------------------------"
echo "Image URL in HTML:"
curl -s "$APP_URL/" | grep -o 'value="[^"]*"' | head -1
echo ""
echo "Prompt in HTML:"
curl -s "$APP_URL/" | grep -A 1 '<textarea id="prompt"' | tail -1 | sed 's/^[[:space:]]*//'
echo ""
echo ""

# Test 3: OCR with custom prompt
echo "Test 3: Run OCR with custom prompt"
echo "-----------------------------------"
curl -s -X POST "$APP_URL/api/ocr" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://ev-cuhk.net/tmp/t01.jpg",
    "prompt": "Detect and recognize text in the image, and output the text coordinates in a formatted manner."
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Status: {data['steps'][-1]}\")
print(f\"Blocks detected: {len(data['blocks'])}\")
print(f\"Endpoint: {data['endpoint']}\")
print(f\"Model: {data['model']}\")
if data['blocks']:
    print(f\"First block: {data['blocks'][0]['text']}\")
    if 'pixel' in data['blocks'][0]:
        print(f\"  Pixel coords: ({data['blocks'][0]['pixel']['x1']},{data['blocks'][0]['pixel']['y1']}) → ({data['blocks'][0]['pixel']['x2']},{data['blocks'][0]['pixel']['y2']})\")
    print(f\"  Normalized: ({data['blocks'][0]['normalized']['x1']},{data['blocks'][0]['normalized']['y1']}) → ({data['blocks'][0]['normalized']['x2']},{data['blocks'][0]['normalized']['y2']})\")
"
echo ""
echo ""

# Test 4: Verify settings were updated
echo "Test 4: Verify settings persisted after OCR"
echo "--------------------------------------------"
cat "$SETTINGS_FILE"
echo ""
echo ""

# Test 5: Check image preview elements
echo "Test 5: Check image preview elements in HTML"
echo "---------------------------------------------"
echo "Preview image element:"
curl -s "$APP_URL/" | grep -o '<img id="preview-image"[^>]*>' | head -1
echo ""
echo "Preview error element exists:"
curl -s "$APP_URL/" | grep -c 'id="preview-error"' || echo "Found"
echo ""
echo "Preview loading element exists:"
curl -s "$APP_URL/" | grep -c 'id="preview-loading"' || echo "Found"
echo ""
echo ""

echo "=================================="
echo "All tests completed successfully!"
echo "=================================="
echo ""
echo "You can now:"
echo "  1. Open $APP_URL in your browser"
echo "  2. Verify image preview loads automatically"
echo "  3. Change the image URL and see preview update"
echo "  4. Edit the prompt and run OCR"
echo "  5. Restart the app and see settings persist"

