#!/usr/bin/env python3
"""
Lightweight local web UI for the HunyuanOCR endpoint used in test_simple.sh.
- Lets you submit an image URL to the OCR service
- Shows progress updates and the raw text (unicode-friendly)
- Lists detected text blocks with coordinates in a formatted table
- Renders an annotated image with bounding rectangles in rotating colors

HunyuanOCR Coordinate System:
-----------------------------
HunyuanOCR outputs coordinates normalized to a [0, 1000] scale regardless
of the original image dimensions. This web app automatically converts these
normalized coordinates to actual pixel coordinates based on the image size.

See ocr_utils.py for reusable coordinate conversion functions.
"""

import base64
import json
import os
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple

import requests
from flask import Flask, jsonify, render_template_string, request
from PIL import Image, ImageDraw, ImageFont

# Import coordinate utilities
from ocr_utils import (
    HUNYUAN_COORD_RANGE,
    TextBlock,
    convert_blocks_to_pixels,
    get_scale_factors,
    parse_ocr_content,
)

# Flask will emit unicode as-is (no ASCII escaping)
app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

# Defaults mirror test_simple.sh
OCR_ENDPOINT = os.getenv(
    "HY_OCR_ENDPOINT",
    "https://hunyuan-ocr.ashybay-2b080a17.japaneast.azurecontainerapps.io/v1",
)
OCR_MODEL = os.getenv("HY_OCR_MODEL", "/app/models/HunyuanOCR")
DEFAULT_PROMPT = os.getenv(
    "HY_OCR_PROMPT",
    "Detect and recognize text in the image, and output the text coordinates in a formatted manner.",
)
DEFAULT_IMAGE_URL = os.getenv(
    "HY_OCR_SAMPLE_IMAGE",
    "https://ev-cuhk.net/tmp/t01.jpg",
)

COLOR_PALETTE = [
    "#f97316",
    "#22c55e",
    "#0ea5e9",
    "#a855f7",
    "#e11d48",
    "#06b6d4",
    "#d97706",
    "#10b981",
]

# Settings persistence
SETTINGS_FILE = Path(__file__).parent / "ocr_settings.json"


def load_settings():
    """Load saved settings from JSON file."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_settings(settings):
    """Save settings to JSON file."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def fetch_and_annotate_image(
    image_url: str, 
    blocks: List[TextBlock],
    image: Optional[Image.Image] = None,
) -> Tuple[str, Tuple[int, int]]:
    """
    Download the image (or use provided), draw bounding boxes for each block,
    and return a base64 data URI for inline display.
    
    HunyuanOCR returns coordinates normalized to [0-1000] range. This function
    converts them to pixel coordinates based on the actual image dimensions.
    
    Args:
        image_url: URL of the image
        blocks: List of TextBlock objects with normalized coordinates
        image: Optional pre-loaded PIL Image (to avoid re-downloading)
        
    Returns:
        Tuple of (base64_data_uri, (width, height))
    """
    if image is None:
        response = requests.get(image_url, timeout=20)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content)).convert("RGB")
    
    # Respect EXIF orientation so coordinates line up with the displayed image
    try:
        from PIL import ImageOps
        image = ImageOps.exif_transpose(image)
    except Exception:
        pass

    width, height = image.size
    
    # Convert normalized coordinates to pixel coordinates
    # HunyuanOCR uses [0-1000] normalized range
    converted_blocks = convert_blocks_to_pixels(blocks, width, height)
    
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    for idx, block in enumerate(converted_blocks, 1):
        color = COLOR_PALETTE[(idx - 1) % len(COLOR_PALETTE)]
        
        # Use pixel coordinates (already converted from normalized)
        x1 = block.pixel_x1 if block.pixel_x1 is not None else 0
        y1 = block.pixel_y1 if block.pixel_y1 is not None else 0
        x2 = block.pixel_x2 if block.pixel_x2 is not None else 0
        y2 = block.pixel_y2 if block.pixel_y2 is not None else 0

        # Normalize ordering and clamp to the image bounds
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))
        x1 = max(0, min(x1, width - 1))
        y1 = max(0, min(y1, height - 1))
        x2 = max(0, min(x2, width - 1))
        y2 = max(0, min(y2, height - 1))

        draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=3)

        # Label the box with its index and a short text snippet for clarity
        label = f"{idx}"
        snippet = block.text[:14] + ("…" if len(block.text) > 14 else "")
        label_text = f"{label} {snippet}"
        text_bg = draw.textbbox((x1 + 4, y1 + 4), label_text, font=font)
        draw.rectangle(text_bg, fill=color)
        draw.text((x1 + 4, y1 + 4), label_text, fill="black", font=font)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}", (width, height)


def call_ocr(image_url: str, prompt: str = None):
    """Call the OCR endpoint and return the JSON payload."""
    if prompt is None:
        prompt = DEFAULT_PROMPT
    
    payload = {
        "model": OCR_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "temperature": 0.0,
        "top_k": 1,
        "repetition_penalty": 1.2,  # Added penalty to prevent repetition loops
        "max_tokens": 8192,  # Doubled for very dense text (200+ blocks, leaves room for ~8000 image tokens)
    }
    response = requests.post(
        f"{OCR_ENDPOINT}/chat/completions", json=payload, timeout=(10, 120)
    )
    response.raise_for_status()
    return response.json()


@app.route("/")
def index():
    """Render the main page with saved settings."""
    settings = load_settings()
    return render_template_string(
        PAGE_TEMPLATE,
        default_url=settings.get("image_url", DEFAULT_IMAGE_URL),
        endpoint=OCR_ENDPOINT,
        model=OCR_MODEL,
        prompt=settings.get("prompt", DEFAULT_PROMPT),
    )


@app.post("/api/settings")
def api_save_settings():
    """Save user settings (image URL and prompt)."""
    body = request.get_json(force=True, silent=True) or {}
    settings = {
        "image_url": body.get("image_url", ""),
        "prompt": body.get("prompt", ""),
    }
    success = save_settings(settings)
    return jsonify({"success": success}), 200 if success else 500


@app.post("/api/ocr")
def api_ocr():
    """
    Process an image through HunyuanOCR and return detected text with coordinates.
    
    HunyuanOCR returns coordinates normalized to [0-1000] range. This endpoint
    converts them to actual pixel coordinates based on the image dimensions.
    
    Request body:
        {
            "image_url": "https://example.com/image.jpg",
            "prompt": "Optional custom prompt"
        }
        
    Response includes:
        - raw_text: The raw OCR output string
        - blocks: List of detected text blocks with coordinates
        - image_with_boxes: Base64 annotated image
        - image_size: Actual image dimensions in pixels
        - coord_info: Coordinate system information
    """
    body = request.get_json(force=True, silent=True) or {}
    image_url = (body.get("image_url") or "").strip()
    prompt = (body.get("prompt") or "").strip()
    
    if not image_url:
        return jsonify({"error": "image_url is required"}), 400
    
    # Save settings for next time
    save_settings({"image_url": image_url, "prompt": prompt or DEFAULT_PROMPT})

    steps = ["Received request"]
    try:
        steps.append("Calling OCR endpoint")
        ocr_json = call_ocr(image_url, prompt or None)

        steps.append("Parsing OCR response")
        choices = ocr_json.get("choices") or []
        raw_text = ""
        if choices and choices[0].get("message", {}).get("content"):
            raw_text = choices[0]["message"]["content"]
        
        # Parse blocks using utility function (returns normalized coordinates)
        blocks = parse_ocr_content(raw_text) if raw_text else []

        annotated_image = None
        converted_blocks: List[TextBlock] = []
        image_size = None
        scale_x = scale_y = None
        
        if blocks:
            # Fetch image to get actual dimensions for coordinate conversion
            steps.append("Fetching image for dimension analysis")
            try:
                resp = requests.get(image_url, timeout=20)
                resp.raise_for_status()
                img = Image.open(BytesIO(resp.content)).convert("RGB")
                try:
                    from PIL import ImageOps
                    img = ImageOps.exif_transpose(img)
                except Exception:
                    pass
                
                image_size = img.size
                
                # Calculate scale factors for normalized -> pixel conversion
                # HunyuanOCR uses [0-1000] normalized coordinate range
                scale_x, scale_y = get_scale_factors(img.size[0], img.size[1])
                
                # Convert normalized coordinates to pixel coordinates
                converted_blocks = convert_blocks_to_pixels(blocks, img.size[0], img.size[1])
                
                steps.append("Rendering bounding boxes")
                annotated_image, _ = fetch_and_annotate_image(image_url, blocks, img)
                
            except Exception as e:
                steps.append(f"Warning: Could not fetch image - {e}")
                # Fallback: use normalized coordinates without conversion
                converted_blocks = blocks
                image_size = None

        steps.append("Done")
        
        # Build response with both normalized and pixel coordinates
        blocks_response = []
        for idx, block in enumerate(converted_blocks):
            block_data = {
                "index": idx + 1,
                "text": block.text,
                "color": COLOR_PALETTE[idx % len(COLOR_PALETTE)],
                # Normalized coordinates (0-1000 range from HunyuanOCR)
                "normalized": {
                    "x1": block.norm_x1,
                    "y1": block.norm_y1,
                    "x2": block.norm_x2,
                    "y2": block.norm_y2,
                    "width": block.norm_width,
                    "height": block.norm_height,
                },
            }
            # Add pixel coordinates if available
            if block.pixel_x1 is not None:
                block_data["pixel"] = {
                    "x1": block.pixel_x1,
                    "y1": block.pixel_y1,
                    "x2": block.pixel_x2,
                    "y2": block.pixel_y2,
                    "width": block.pixel_width,
                    "height": block.pixel_height,
                }
                # For backwards compatibility, also include at top level
                block_data["x1"] = block.pixel_x1
                block_data["y1"] = block.pixel_y1
                block_data["x2"] = block.pixel_x2
                block_data["y2"] = block.pixel_y2
                block_data["width"] = block.pixel_width
                block_data["height"] = block.pixel_height
            else:
                # If no conversion, use normalized values
                block_data["x1"] = block.norm_x1
                block_data["y1"] = block.norm_y1
                block_data["x2"] = block.norm_x2
                block_data["y2"] = block.norm_y2
                block_data["width"] = block.norm_width
                block_data["height"] = block.norm_height
            
            blocks_response.append(block_data)
        
        return (
            jsonify(
                {
                    "raw_text": raw_text,
                    "blocks": blocks_response,
                    "image_with_boxes": annotated_image,
                    "image_size": {"width": image_size[0], "height": image_size[1]} if image_size else None,
                    "coord_info": {
                        "normalized_range": HUNYUAN_COORD_RANGE,
                        "scale_x": scale_x,
                        "scale_y": scale_y,
                        "description": f"HunyuanOCR outputs coordinates normalized to [0-{HUNYUAN_COORD_RANGE}] range",
                    },
                    "steps": steps,
                    "endpoint": OCR_ENDPOINT,
                    "model": OCR_MODEL,
                }
            ),
            200,
        )
    except requests.HTTPError as exc:
        return jsonify({"error": f"OCR request failed: {exc}", "steps": steps}), 502
    except Exception as exc:  # pylint: disable=broad-except
        return jsonify({"error": str(exc), "steps": steps}), 500


PAGE_TEMPLATE = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>HunyuanOCR Web UI</title>
  <style>
    :root {
      --bg: #0f172a;
      --panel: #111827;
      --accent: #38bdf8;
      --muted: #94a3b8;
      --border: #1f2937;
      --success: #22c55e;
      --danger: #ef4444;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 0;
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      background: radial-gradient(circle at 20% 20%, #0b1224, #0f172a 45%),
                  radial-gradient(circle at 80% 0%, #0b1a2a, #0f172a 40%),
                  #0f172a;
      color: #e2e8f0;
    }
    .container {
      max-width: 1100px;
      margin: 32px auto 48px;
      padding: 0 20px;
    }
    h1 {
      font-weight: 700;
      letter-spacing: -0.5px;
      margin-bottom: 6px;
    }
    p.subtitle {
      margin-top: 0;
      color: var(--muted);
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px 20px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.35);
      margin-bottom: 16px;
    }
    label {
      display: block;
      font-weight: 600;
      margin-bottom: 8px;
    }
    input[type="url"], textarea {
      width: 100%;
      padding: 12px 14px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: #0b1220;
      color: #e2e8f0;
      font-size: 15px;
      font-family: inherit;
    }
    textarea {
      resize: vertical;
      min-height: 80px;
    }
    button {
      background: var(--accent);
      border: none;
      color: #0b1220;
      padding: 12px 18px;
      border-radius: 10px;
      font-weight: 700;
      cursor: pointer;
      transition: transform 120ms ease, box-shadow 120ms ease, opacity 120ms ease;
      margin-top: 12px;
    }
    button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    button:hover:not(:disabled) {
      transform: translateY(-1px);
      box-shadow: 0 12px 30px rgba(56,189,248,0.25);
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
    }
    .status {
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      background: #0b1220;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px;
      min-height: 60px;
    }
    .status .ok { color: var(--success); }
    .status .err { color: var(--danger); }
    pre {
      white-space: pre-wrap;
      word-wrap: break-word;
      margin: 0;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 8px;
    }
    th, td {
      border-bottom: 1px solid var(--border);
      padding: 8px 10px;
      text-align: left;
    }
    th {
      color: var(--muted);
      font-weight: 600;
      font-size: 14px;
      letter-spacing: 0.2px;
    }
    td {
      font-size: 14px;
      vertical-align: top;
    }
    .tag {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 6px;
      background: #0b1220;
      border: 1px solid var(--border);
      font-size: 12px;
      color: var(--muted);
    }
    img.annotated {
      width: 100%;
      border-radius: 12px;
      border: 1px solid var(--border);
      background: #0b1220;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      padding: 4px 10px;
      border-radius: 999px;
      background: #0b1220;
      border: 1px solid var(--border);
      color: #cbd5e1;
      font-size: 13px;
      gap: 8px;
    }
    .pill span.dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      display: inline-block;
      background: var(--accent);
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>HunyuanOCR Visualizer</h1>
    <p class="subtitle">Endpoint: {{ endpoint }} | Model: {{ model }}</p>

    <div class="panel">
      <label for="image-url">Image URL</label>
      <input type="url" id="image-url" value="{{ default_url }}" placeholder="Paste an image URL">
      
      <div style="margin-top:16px;">
        <label for="prompt">Prompt</label>
        <textarea id="prompt" rows="3" placeholder="Enter OCR prompt">{{ prompt }}</textarea>
      </div>
      
      <button id="run-btn">Run OCR</button>
    </div>
    
    <div class="panel">
      <strong>Image Preview</strong>
      <div style="margin-top:10px; position:relative;">
        <img id="preview-image" class="annotated" alt="Image preview will appear here" style="display:none;">
        <div id="preview-error" style="display:none; padding:20px; text-align:center; color:var(--danger); border:1px dashed var(--border); border-radius:12px; background:#0b1220;">
          ⚠️ Failed to load image
        </div>
        <div id="preview-loading" style="padding:20px; text-align:center; color:var(--muted); border:1px dashed var(--border); border-radius:12px; background:#0b1220;">
          📷 Enter an image URL to preview
        </div>
      </div>
    </div>

    <div class="grid">
      <div class="panel">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
          <strong>Status</strong>
          <div class="pill"><span class="dot"></span><span id="status-label">Idle</span></div>
        </div>
        <div class="status" id="status-log"></div>
      </div>
      <div class="panel">
        <strong>Raw Text</strong>
        <div class="status" style="margin-top:8px; min-height:200px;">
          <pre id="raw-text"></pre>
        </div>
      </div>
    </div>

    <div class="panel">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
        <strong>Detected Text Blocks</strong>
        <div id="coord-info" class="pill" style="font-size:12px;"></div>
      </div>
      <div id="table-container"></div>
    </div>

    <div class="panel">
      <strong>Annotated Image</strong>
      <div style="margin-top:10px;">
        <img id="annotated-image" class="annotated" alt="Annotated OCR result will appear here">
      </div>
    </div>
  </div>

  <script>
    const runBtn = document.getElementById("run-btn");
    const statusLog = document.getElementById("status-log");
    const statusLabel = document.getElementById("status-label");
    const rawTextEl = document.getElementById("raw-text");
    const tableContainer = document.getElementById("table-container");
    const coordInfo = document.getElementById("coord-info");
    const annotatedImg = document.getElementById("annotated-image");
    const urlInput = document.getElementById("image-url");
    const promptInput = document.getElementById("prompt");
    const previewImg = document.getElementById("preview-image");
    const previewError = document.getElementById("preview-error");
    const previewLoading = document.getElementById("preview-loading");

    function setStatus(message, type="info") {
      const colorClass = type === "error" ? "err" : "ok";
      statusLabel.textContent = message;
      statusLog.innerHTML = `<div class="${colorClass}">${message}</div>`;
    }

    function appendSteps(steps=[]) {
      statusLog.innerHTML = steps.map(step => `<div>${step}</div>`).join("");
      const finalStep = steps[steps.length - 1];
      statusLabel.textContent = finalStep || "Idle";
    }

    function clearOutputs() {
      rawTextEl.textContent = "";
      tableContainer.innerHTML = "";
      coordInfo.innerHTML = "";
      annotatedImg.src = "";
    }
    
    function loadImagePreview() {
      const imageUrl = urlInput.value.trim();
      
      // Hide all preview states
      previewImg.style.display = "none";
      previewError.style.display = "none";
      previewLoading.style.display = "none";
      
      if (!imageUrl) {
        previewLoading.textContent = "📷 Enter an image URL to preview";
        previewLoading.style.display = "block";
        return;
      }
      
      // Show loading state
      previewLoading.textContent = "⏳ Loading image...";
      previewLoading.style.display = "block";
      
      // Load image
      const img = new Image();
      
      img.onload = function() {
        previewLoading.style.display = "none";
        previewImg.src = imageUrl;
        previewImg.style.display = "block";
      };
      
      img.onerror = function() {
        previewLoading.style.display = "none";
        previewError.style.display = "block";
      };
      
      img.src = imageUrl;
    }

    function renderCoordInfo(info, imageSize) {
      if (!info) {
        coordInfo.innerHTML = "";
        return;
      }
      let html = `<span class="dot" style="background:#22c55e;"></span>`;
      if (imageSize) {
        html += `Image: ${imageSize.width}×${imageSize.height}px`;
      }
      if (info.scale_x && info.scale_y) {
        html += ` | Scale: ${info.scale_x.toFixed(3)}×${info.scale_y.toFixed(3)}`;
      }
      html += ` | Norm: 0-${info.normalized_range}`;
      coordInfo.innerHTML = html;
    }

    function renderTable(blocks=[], hasPixelCoords=false) {
      if (!blocks.length) {
        tableContainer.innerHTML = '<div style="color: var(--muted);">No blocks detected.</div>';
        return;
      }
      
      // Build table with both normalized and pixel coordinates if available
      const rows = blocks.map(block => {
        const norm = block.normalized || {};
        const pixel = block.pixel || {};
        const hasPixel = pixel.x1 !== undefined;
        
        let coordCell = "";
        if (hasPixel) {
          coordCell = `
            <div class="tag" style="margin-bottom:4px;" title="Pixel coordinates">
              📍 (${Math.round(pixel.x1)},${Math.round(pixel.y1)}) → (${Math.round(pixel.x2)},${Math.round(pixel.y2)})
            </div>
            <div class="tag" style="font-size:11px; opacity:0.7;" title="Normalized 0-1000">
              📐 (${Math.round(norm.x1)},${Math.round(norm.y1)}) → (${Math.round(norm.x2)},${Math.round(norm.y2)})
            </div>
          `;
        } else {
          coordCell = `<div class="tag">(${Math.round(norm.x1)},${Math.round(norm.y1)}) → (${Math.round(norm.x2)},${Math.round(norm.y2)})</div>`;
        }
        
        const sizeCell = hasPixel 
          ? `<div class="tag">${Math.round(pixel.width)}×${Math.round(pixel.height)}px</div>`
          : `<div class="tag">${Math.round(norm.width)}×${Math.round(norm.height)}</div>`;
        
        return `
          <tr>
            <td style="width:60px;"><span class="tag" style="border-color:${block.color}; color:${block.color};">#${block.index}</span></td>
            <td>${block.text || "&nbsp;"}</td>
            <td>${coordCell}</td>
            <td>${sizeCell}</td>
          </tr>
        `;
      }).join("");
      
      tableContainer.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Id</th>
              <th>Text</th>
              <th>Coordinates<br><small style="font-weight:normal;color:var(--muted);">📍 Pixel / 📐 Normalized</small></th>
              <th>Size</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      `;
    }

    async function runOcr() {
      const imageUrl = urlInput.value.trim();
      const prompt = promptInput.value.trim();
      
      if (!imageUrl) {
        setStatus("Please provide an image URL", "error");
        return;
      }

      runBtn.disabled = true;
      clearOutputs();
      setStatus("Submitting to OCR...");

      try {
        const response = await fetch("/api/ocr", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            image_url: imageUrl,
            prompt: prompt 
          })
        });
        const payload = await response.json();
        if (!response.ok) {
          const steps = payload.steps || [];
          appendSteps(steps);
          throw new Error(payload.error || "Request failed");
        }

        appendSteps(payload.steps);
        rawTextEl.textContent = payload.raw_text || "";
        
        // Render coordinate info
        renderCoordInfo(payload.coord_info, payload.image_size);
        
        // Render table with both normalized and pixel coords
        const hasPixelCoords = payload.blocks?.length > 0 && payload.blocks[0].pixel;
        renderTable(payload.blocks || [], hasPixelCoords);
        
        if (payload.image_with_boxes) {
          annotatedImg.src = payload.image_with_boxes;
        } else {
          annotatedImg.removeAttribute("src");
        }
        setStatus("Complete");
      } catch (err) {
        setStatus(err.message, "error");
      } finally {
        runBtn.disabled = false;
      }
    }

    runBtn.addEventListener("click", (e) => {
      e.preventDefault();
      runOcr();
    });
    
    // Load image preview when URL changes
    urlInput.addEventListener("input", () => {
      loadImagePreview();
    });
    
    // Load image preview on page load
    window.addEventListener("DOMContentLoaded", () => {
      loadImagePreview();
    });
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
