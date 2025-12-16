#!/bin/bash

# HunyuanOCR API Test Script with Coordinate Conversion
#
# Usage: ./test_simple.sh [image_width image_height]
#   Example: ./test_simple.sh 2428 1438
#   Example: ./test_simple.sh   # Will try to auto-detect dimensions
#
# Note: HunyuanOCR outputs coordinates normalized to [0-1000] range.
#       Provide image dimensions to convert to actual pixel coordinates.

ENDPOINT="https://hunyuan-ocr.ashybay-2b080a17.japaneast.azurecontainerapps.io/v1"
IMAGE_URL="https://ev-cuhk.net/tmp/t01.jpg"

# Optional: specify image dimensions as arguments
IMAGE_WIDTH="${1:-}"
IMAGE_HEIGHT="${2:-}"

echo "================================================================================"
echo "Testing HunyuanOCR API with cURL"
echo "================================================================================"
echo ""
echo "Endpoint: $ENDPOINT"
echo "Image URL: $IMAGE_URL"
echo ""
echo "================================================================================"

curl -s -X POST "${ENDPOINT}/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "/app/models/HunyuanOCR",
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "image_url", "image_url": {"url": "'"${IMAGE_URL}"'"}},
          {"type": "text", "text": "Detect and recognize text in the image, and output the text coordinates in a formatted manner."}
        ]
      }
    ],
    "temperature": 0.0,
    "top_k": 1,
    "repetition_penalty": 1.0,
    "max_tokens": 3000
  }' | python3 -c "
import sys, json, re
import urllib.request
import struct

# ============================================================================
# HunyuanOCR Coordinate System Documentation:
# ============================================================================
# HunyuanOCR outputs coordinates normalized to a [0, 1000] scale regardless
# of the original image dimensions. To convert to actual pixel coordinates:
#
#   actual_x = normalized_x * (image_width / 1000)
#   actual_y = normalized_y * (image_height / 1000)
#
# This is a common practice in VLM-based OCR models to provide resolution-
# independent coordinate outputs.
# ============================================================================

IMAGE_URL = '${IMAGE_URL}'
# Command-line provided dimensions (if any)
CMD_WIDTH = '${IMAGE_WIDTH}' or None
CMD_HEIGHT = '${IMAGE_HEIGHT}' or None

def get_image_size_from_bytes(data):
    '''Get image dimensions from raw bytes without PIL'''
    # Check for PNG
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        w, h = struct.unpack('>LL', data[16:24])
        return int(w), int(h)
    
    # Check for JPEG
    if data[:2] == b'\xff\xd8':
        idx = 2
        while idx < len(data):
            if data[idx] != 0xff:
                idx += 1
                continue
            marker = data[idx+1]
            if marker == 0xd9:  # EOI
                break
            if marker == 0xc0 or marker == 0xc2:  # SOF0 or SOF2
                h, w = struct.unpack('>HH', data[idx+5:idx+9])
                return int(w), int(h)
            if marker in (0xd0, 0xd1, 0xd2, 0xd3, 0xd4, 0xd5, 0xd6, 0xd7, 0xd8, 0x01):
                idx += 2
            else:
                length = struct.unpack('>H', data[idx+2:idx+4])[0]
                idx += 2 + length
        return None
    
    # Check for GIF
    if data[:6] in (b'GIF87a', b'GIF89a'):
        w, h = struct.unpack('<HH', data[6:10])
        return int(w), int(h)
    
    # Check for BMP
    if data[:2] == b'BM':
        w, h = struct.unpack('<II', data[18:26])
        return int(w), int(h)
    
    return None

def get_image_dimensions(url):
    '''Fetch image and get its dimensions'''
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            # Read enough bytes to get dimensions
            img_data = response.read(65536)  # 64KB should be enough for header
        
        dims = get_image_size_from_bytes(img_data)
        if dims:
            return dims
        
        # Fallback: try PIL if available
        try:
            from PIL import Image
            from io import BytesIO
            # Need to read full image for PIL
            with urllib.request.urlopen(url, timeout=10) as response:
                full_data = response.read()
            img = Image.open(BytesIO(full_data))
            return img.size
        except ImportError:
            pass
        
        return None
    except Exception as e:
        print(f'Warning: Could not fetch image dimensions: {e}')
        return None

data = json.load(sys.stdin)

# Print full JSON response
print(json.dumps(data, indent=2, ensure_ascii=False))

# Extract and format the content
if 'choices' in data and len(data['choices']) > 0:
    content = data['choices'][0]['message']['content']
    
    # Get actual image dimensions for coordinate conversion
    # Priority: command-line args > auto-detect
    if CMD_WIDTH and CMD_HEIGHT:
        try:
            img_dims = (int(CMD_WIDTH), int(CMD_HEIGHT))
            print(f'📏 Using provided dimensions: {img_dims[0]} x {img_dims[1]}')
        except:
            img_dims = get_image_dimensions(IMAGE_URL)
    else:
        img_dims = get_image_dimensions(IMAGE_URL)
    
    print()
    print('=' * 80)
    print('📋 ORGANIZED OCR RESULTS')
    print('=' * 80)
    
    if img_dims:
        img_width, img_height = img_dims
        scale_x = img_width / 1000.0
        scale_y = img_height / 1000.0
        print(f'🖼️  Image dimensions: {img_width} x {img_height} pixels')
        print(f'📐 Coordinate scale factors: x={scale_x:.3f}, y={scale_y:.3f}')
        print(f'   (HunyuanOCR outputs normalized coordinates in [0-1000] range)')
    else:
        scale_x = scale_y = None
        print('⚠️  Could not determine image dimensions for coordinate conversion')
        print('   (Install Pillow: pip install Pillow)')
    
    print('=' * 80)
    
    # Parse text with coordinates: pattern is text(x1,y1),(x2,y2)
    # Match: any text followed by (num,num),(num,num)
    pattern = r'([^()]+?)\((\d+),(\d+)\),\((\d+),(\d+)\)'
    matches = re.findall(pattern, content)
    
    if matches:
        print(f'Found {len(matches)} text elements:')
        print()
        
        if scale_x and scale_y:
            # Show both normalized and actual coordinates
            print('─' * 100)
            print(f'{\"No.\":>4}  {\"Text\":<35}  {\"Normalized (0-1000)\":<22}  {\"Actual Pixels\"}')
            print('─' * 100)
            for i, (text, x1, y1, x2, y2) in enumerate(matches, 1):
                text = text.strip()
                # Normalized coordinates
                norm_coords = f'({x1},{y1})→({x2},{y2})'
                # Actual pixel coordinates
                ax1 = int(int(x1) * scale_x)
                ay1 = int(int(y1) * scale_y)
                ax2 = int(int(x2) * scale_x)
                ay2 = int(int(y2) * scale_y)
                actual_coords = f'({ax1},{ay1})→({ax2},{ay2})'
                # Truncate long text
                display_text = text[:33] + '..' if len(text) > 35 else text
                print(f'{i:>4}  {display_text:<35}  {norm_coords:<22}  {actual_coords}')
            print('─' * 100)
        else:
            # Show only normalized coordinates
            print('─' * 80)
            print(f'{\"No.\":>4}  {\"Text\":<40}  {\"Coordinates (normalized 0-1000)\"}')
            print('─' * 80)
            for i, (text, x1, y1, x2, y2) in enumerate(matches, 1):
                text = text.strip()
                coords = f'({x1},{y1}) → ({x2},{y2})'
                display_text = text[:38] + '..' if len(text) > 40 else text
                print(f'{i:>4}  {display_text:<40}  {coords}')
            print('─' * 80)
    else:
        # If pattern doesn't match, just print the raw content
        print('Raw content:')
        print(content)
"

echo ""
echo "================================================================================"

