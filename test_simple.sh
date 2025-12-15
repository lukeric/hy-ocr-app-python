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

data = json.load(sys.stdin)

# Print full JSON response
print(json.dumps(data, indent=2, ensure_ascii=False))

# Extract and format the content
if 'choices' in data and len(data['choices']) > 0:
    content = data['choices'][0]['message']['content']
    
    print()
    print('=' * 80)
    print('📋 ORGANIZED OCR RESULTS')
    print('=' * 80)
    
    # Parse text with coordinates: pattern is text(x1,y1),(x2,y2)
    # Match: any text followed by (num,num),(num,num)
    pattern = r'([^()]+?)\((\d+),(\d+)\),\((\d+),(\d+)\)'
    matches = re.findall(pattern, content)
    
    if matches:
        print(f'Found {len(matches)} text elements:')
        print('-' * 80)
        print(f'{\"No.\":>4}  {\"Text\":<40}  {\"Coordinates\"}')
        print('-' * 80)
        for i, (text, x1, y1, x2, y2) in enumerate(matches, 1):
            text = text.strip()
            coords = f'({x1},{y1}) → ({x2},{y2})'
            # Truncate long text
            display_text = text[:38] + '..' if len(text) > 40 else text
            print(f'{i:>4}  {display_text:<40}  {coords}')
        print('-' * 80)
    else:
        # If pattern doesn't match, just print the raw content
        print('Raw content:')
        print(content)
"

echo ""
echo "================================================================================"

