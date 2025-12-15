#!/bin/bash

# Simplest possible cURL test for HunyuanOCR API

ENDPOINT="https://hunyuan-ocr.ashybay-2b080a17.japaneast.azurecontainerapps.io/v1"
IMAGE_URL="https://ev-cuhk.net/tmp/t01.jpg"

echo "================================================================================"
echo "Testing HunyuanOCR API with cURL"
echo "================================================================================"
echo ""
echo "Endpoint: $ENDPOINT"
echo "Image URL: $IMAGE_URL"
echo ""
echo "================================================================================"

curl -X POST "${ENDPOINT}/chat/completions" \
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
  }' | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2, ensure_ascii=False))"

echo ""
echo "================================================================================"

