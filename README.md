# HunyuanOCR Python App - Development Tools

This directory contains scripts and utilities for working with the HunyuanOCR API deployed on Azure Container Apps.

## 📐 HunyuanOCR Coordinate System

**Important:** HunyuanOCR outputs coordinates normalized to a **[0-1000] scale** regardless of the original image dimensions. This is a common practice in VLM-based OCR models.

### Conversion Formula
```python
# To convert normalized coordinates to actual pixel coordinates:
actual_x = normalized_x * (image_width / 1000)
actual_y = normalized_y * (image_height / 1000)

# Example for a 2428 x 1438 image:
# normalized (53, 27) → actual (128, 38) pixels
```

### Using the Utility Module
```python
from ocr_utils import (
    parse_ocr_content,
    convert_blocks_to_pixels,
    get_scale_factors,
    HUNYUAN_COORD_RANGE,  # = 1000
)

# Parse OCR response
blocks = parse_ocr_content(raw_ocr_text)

# Convert to pixel coordinates
converted = convert_blocks_to_pixels(blocks, image_width=2428, image_height=1438)

for block in converted:
    print(f"{block.text}: ({block.pixel_x1}, {block.pixel_y1}) → ({block.pixel_x2}, {block.pixel_y2})")
```

## Files

| File | Description |
|------|-------------|
| `ocr_utils.py` | **Reusable utility module** for coordinate conversion and OCR parsing |
| `ocr_web_app.py` | Flask web UI for testing OCR with visual annotations |
| `test_simple.sh` | Shell script for quick OCR testing with coordinate conversion |
| `keep_alive.sh` | Keeps Azure Container Apps warm during development |
| `requirements.txt` | Python dependencies |

## Scripts

### 1. `keep_alive.sh` - Keep ACA Active

**Purpose:** Prevents Azure Container Apps from scaling down to zero by calling the health API regularly.

**Default Settings:**
- **Interval:** 30 seconds (calls every 30 seconds)
- **Duration:** 3 hours (automatically stops after 3 hours)

**Usage:**
```bash
# Use defaults (30 seconds interval, 3 hours duration)
./keep_alive.sh

# Custom interval and duration
./keep_alive.sh [interval_seconds] [duration_hours]

# Examples:
./keep_alive.sh 30 3    # 30 seconds interval, 3 hours
./keep_alive.sh 60 2    # 60 seconds interval, 2 hours
./keep_alive.sh 10 1    # 10 seconds interval, 1 hour
```

**When to use:**
- During development when you need the OCR service available for several hours
- Before working sessions to ensure the service stays warm
- When you want to avoid cold start delays

**What it does:**
- Calls `https://hunyuan-ocr.ashybay-2b080a17.japaneast.azurecontainerapps.io/health` at your specified interval (default: every 30 seconds)
- Displays colorful output showing each health check status
- Shows remaining time until automatic shutdown
- Stops automatically after the specified duration to avoid running forever
- Flexible configuration via command-line arguments

### 2. `test_simple.sh` - Simple OCR Test

**Purpose:** Tests the full OCR functionality with a sample image using curl, including coordinate conversion.

**Usage:**
```bash
# Auto-detect image dimensions
./test_simple.sh

# Provide dimensions manually (faster)
./test_simple.sh 2428 1438
```

**What it does:**
- Sends an OCR request to the API
- Auto-detects image dimensions from URL
- Converts normalized [0-1000] coordinates to actual pixels
- Displays both normalized and pixel coordinates in a formatted table
- Shows scale factors used for conversion

### 3. `ocr_web_app.py` - Web UI

**Purpose:** Provides a visual web interface for testing OCR with annotated bounding boxes.

**Usage:**
```bash
# Install dependencies
pip install -r requirements.txt

# Run the web app
python ocr_web_app.py

# Open http://localhost:5000 in your browser
```

**Features:**
- Visual bounding box annotations on images
- Shows both normalized (0-1000) and pixel coordinates
- Displays coordinate scale factors
- Color-coded text blocks
- Real-time processing status

### 4. `ocr_utils.py` - Utility Module

**Purpose:** Reusable Python utilities for HunyuanOCR coordinate handling.

**Key Functions:**
- `parse_ocr_content(text)` - Parse OCR response to TextBlock objects
- `convert_blocks_to_pixels(blocks, width, height)` - Convert normalized to pixel coords
- `normalized_to_pixel(x, y, width, height)` - Convert single coordinate
- `get_scale_factors(width, height)` - Get conversion scale factors
- `get_image_dimensions_from_url(url)` - Fetch image dimensions without PIL

**Example:**
```python
from ocr_utils import parse_ocr_content, convert_blocks_to_pixels

# Parse raw OCR output
blocks = parse_ocr_content("文字(53,27),(139,55)另一段(100,200),(300,400)")

# Convert to pixels for a 2000x1500 image
converted = convert_blocks_to_pixels(blocks, 2000, 1500)

for b in converted:
    print(f"Text: {b.text}")
    print(f"  Normalized: ({b.norm_x1}, {b.norm_y1}) → ({b.norm_x2}, {b.norm_y2})")
    print(f"  Pixels: ({b.pixel_x1}, {b.pixel_y1}) → ({b.pixel_x2}, {b.pixel_y2})")
```

## Typical Development Workflow

1. **Before starting work:**
   ```bash
   # Start the keep-alive script with defaults (30s interval, 3 hours)
   ./keep_alive.sh &
   
   # Or customize the timing
   ./keep_alive.sh 45 2 &  # 45 seconds interval, 2 hours duration
   ```

2. **Check if it's working (optional):**
   ```bash
   # In another terminal, verify the API is responding
   ./test_simple.sh
   ```

3. **Continue your work:**
   - The service will stay active for your specified duration (default: 3 hours)
   - No cold starts during your development session
   - Health checks happen every 30 seconds by default (customizable)

4. **After the duration expires:**
   - The keep-alive script stops automatically
   - ACA will scale down to zero after the idle timeout
   - No unnecessary resource consumption

## Notes

- **Cost Optimization:** The script runs for only 3 hours by default to avoid keeping the service running when not needed
- **Development Focus:** These scripts are designed for development, not production monitoring
- **Flexible Configuration:** Easily customize interval and duration via command-line arguments
- **Fast Interval:** Default 30-second interval ensures the service stays very responsive

## Health Endpoint

The health endpoint checks if the vLLM model is loaded and ready:
- **URL:** `https://hunyuan-ocr.ashybay-2b080a17.japaneast.azurecontainerapps.io/health`
- **Response (healthy):** `{"status": "healthy", "model": "/app/models/HunyuanOCR"}`
- **Response (not ready):** HTTP 503 with error message

## API Endpoint

The full OCR API is available at:
- **Base URL:** `https://hunyuan-ocr.ashybay-2b080a17.japaneast.azurecontainerapps.io/v1`
- **Chat Completions:** `POST /v1/chat/completions`
- **List Models:** `GET /v1/models`

For more details, see the server documentation in the `hy-ocr-server` directory.

