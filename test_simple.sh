#!/bin/bash

# Simplest possible cURL test for HunyuanOCR API

ENDPOINT="https://hunyuan-ocr.ashybay-2b080a17.japaneast.azurecontainerapps.io/v1"
IMAGE_URL="https://ev-cuhk.net/tmp/image-771x1024_156936ba.png"

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

def get_image_dimensions(url):
    '''Fetch image and get its dimensions'''
    try:
        # Try to get image dimensions from header first (faster)
        from PIL import Image
        from io import BytesIO
        
        with urllib.request.urlopen(url, timeout=10) as response:
            img_data = response.read()
        
        img = Image.open(BytesIO(img_data))
        return img.size  # (width, height)
    except ImportError:
        # PIL not available, try alternative method
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

