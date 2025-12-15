# HunyuanOCR Python App - Development Tools

This directory contains scripts for working with the HunyuanOCR API deployed on Azure Container Apps.

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

**Purpose:** Tests the full OCR functionality with a sample image using curl.

**Usage:**
```bash
./test_simple.sh
```

**What it does:**
- Sends an OCR request to the API
- Uses a test image to extract text
- Displays the JSON response with pretty formatting

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

