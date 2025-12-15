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
          {"type": "text", "text": "Extract all text from this image"},
          {"type": "image_url", "image_url": {"url": "'"${IMAGE_URL}"'"}}
        ]
      }
    ],
    "max_tokens": 2000
  }' | python3 -m json.tool

echo ""
echo "================================================================================"

