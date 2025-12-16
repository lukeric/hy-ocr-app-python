#!/usr/bin/env python3
"""
Lightweight local web UI for the HunyuanOCR endpoint used in test_simple.sh.
- Lets you submit an image URL to the OCR service
- Shows progress updates and the raw text (unicode-friendly)
- Lists detected text blocks with coordinates in a formatted table
- Renders an annotated image with bounding rectangles in rotating colors
"""

import base64
import os
import re
from dataclasses import dataclass
from io import BytesIO
from typing import List, Tuple

import requests
from flask import Flask, jsonify, render_template_string, request
from PIL import Image, ImageDraw, ImageFont

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
    "https://ev-cuhk.net/tmp/image-771x1024_156936ba.png",
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


@dataclass
class TextBlock:
    text: str
    top_left: Tuple[float, float]
    bottom_right: Tuple[float, float]
    raw_top_left: Tuple[float, float]
    raw_bottom_right: Tuple[float, float]

    @property
    def width(self) -> int:
        return max(0, self.bottom_right[0] - self.top_left[0])

    @property
    def height(self) -> int:
        return max(0, self.bottom_right[1] - self.top_left[1])


def parse_text_blocks(content: str) -> List[TextBlock]:
    """Parse text(x1,y1),(x2,y2) style entries from the OCR response content."""
    pattern = re.compile(
        r"([^()]+?)\(([-+]?\d+(?:\.\d+)?),([-+]?\d+(?:\.\d+)?)\),\(([-+]?\d+(?:\.\d+)?),([-+]?\d+(?:\.\d+)?)\)"
    )
    blocks: List[TextBlock] = []
    for match in pattern.finditer(content):
        text = match.group(1).strip()
        x1, y1, x2, y2 = map(float, match.groups()[1:])
        blocks.append(
            TextBlock(
                text=text,
                top_left=(x1, y1),
                bottom_right=(x2, y2),
                raw_top_left=(x1, y1),
                raw_bottom_right=(x2, y2),
            )
        )
    return blocks


def rescale_blocks_to_image(blocks: List[TextBlock], image_size: Tuple[int, int]) -> List[TextBlock]:
    """
    The official docs do not clearly state coordinate space. Empirically, the API
    sometimes returns coordinates on a resized image (smaller than the original).
    We up-scale to the downloaded image size when we detect a clear mismatch.
    """
    if not blocks:
        return blocks

    img_w, img_h = image_size
    max_x = max(b.bottom_right[0] for b in blocks)
    max_y = max(b.bottom_right[1] for b in blocks)

    # If the coordinates look too small compared to the actual image, stretch them.
    scale_x = img_w / max_x if max_x > 0 and img_w / max_x > 1.1 else 1.0
    scale_y = img_h / max_y if max_y > 0 and img_h / max_y > 1.1 else 1.0

    if scale_x == 1.0 and scale_y == 1.0:
        return blocks

    scaled: List[TextBlock] = []
    for b in blocks:
        x1 = b.top_left[0] * scale_x
        y1 = b.top_left[1] * scale_y
        x2 = b.bottom_right[0] * scale_x
        y2 = b.bottom_right[1] * scale_y
        scaled.append(
            TextBlock(
                text=b.text,
                top_left=(x1, y1),
                bottom_right=(x2, y2),
                raw_top_left=b.raw_top_left,
                raw_bottom_right=b.raw_bottom_right,
            )
        )
    return scaled


def fetch_and_annotate_image(image_url: str, blocks: List[TextBlock]) -> str:
    """
    Download the image, draw bounding boxes for each block, and return a base64
    data URI for inline display.
    """
    response = requests.get(image_url, timeout=20)
    response.raise_for_status()

    image = Image.open(BytesIO(response.content)).convert("RGB")
    # Respect EXIF orientation so coordinates line up with the displayed image
    try:
        from PIL import ImageOps

        image = ImageOps.exif_transpose(image)
    except Exception:
        pass

    blocks = rescale_blocks_to_image(blocks, image.size)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    width, height = image.size

    for idx, block in enumerate(blocks, 1):
        color = COLOR_PALETTE[(idx - 1) % len(COLOR_PALETTE)]
        x1_raw, y1_raw = block.top_left
        x2_raw, y2_raw = block.bottom_right

        # If the model returned normalized coords (0-1), scale them
        if all(0.0 <= c <= 1.0 for c in (x1_raw, y1_raw, x2_raw, y2_raw)):
            x1_raw, x2_raw = x1_raw * width, x2_raw * width
            y1_raw, y2_raw = y1_raw * height, y2_raw * height

        # Normalize ordering and clamp to the image bounds
        x1, x2 = sorted((x1_raw, x2_raw))
        y1, y2 = sorted((y1_raw, y2_raw))
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
    return f"data:image/png;base64,{encoded}"


def call_ocr(image_url: str):
    """Call the OCR endpoint and return the JSON payload."""
    payload = {
        "model": OCR_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": DEFAULT_PROMPT},
                ],
            }
        ],
        "temperature": 0.0,
        "top_k": 1,
        "repetition_penalty": 1.0,
        "max_tokens": 3000,
    }
    response = requests.post(
        f"{OCR_ENDPOINT}/chat/completions", json=payload, timeout=(10, 120)
    )
    response.raise_for_status()
    return response.json()


@app.route("/")
def index():
    return render_template_string(
        PAGE_TEMPLATE,
        default_url=DEFAULT_IMAGE_URL,
        endpoint=OCR_ENDPOINT,
        model=OCR_MODEL,
        prompt=DEFAULT_PROMPT,
    )


@app.post("/api/ocr")
def api_ocr():
    body = request.get_json(force=True, silent=True) or {}
    image_url = (body.get("image_url") or "").strip()
    if not image_url:
        return jsonify({"error": "image_url is required"}), 400

    steps = ["Received request"]
    try:
        steps.append("Calling OCR endpoint")
        ocr_json = call_ocr(image_url)

        steps.append("Parsing OCR response")
        choices = ocr_json.get("choices") or []
        raw_text = ""
        if choices and choices[0].get("message", {}).get("content"):
            raw_text = choices[0]["message"]["content"]
        blocks = parse_text_blocks(raw_text) if raw_text else []

        annotated_image = None
        scaled_blocks: List[TextBlock] = []
        model_space_w = model_space_h = None
        scale_x = scale_y = None
        image_size = None
        if blocks:
            # Rescale boxes to image dimensions before drawing/returning
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
                model_space_w = max(b.bottom_right[0] for b in blocks)
                model_space_h = max(b.bottom_right[1] for b in blocks)
                scaled_blocks = rescale_blocks_to_image(blocks, img.size)
                if scaled_blocks:
                    scale_x = img.size[0] / model_space_w if model_space_w else None
                    scale_y = img.size[1] / model_space_h if model_space_h else None
            except Exception:
                # Fallback: no rescale if we fail to fetch image here
                scaled_blocks = blocks
                image_size = None

            steps.append("Rendering bounding boxes")
            annotated_image = fetch_and_annotate_image(image_url, scaled_blocks or blocks)

        steps.append("Done")
        return (
            jsonify(
                {
                    "raw_text": raw_text,
                    "blocks": [
                        {
                            "index": idx + 1,
                            "text": block.text,
                            "x1": block.top_left[0],
                            "y1": block.top_left[1],
                            "x2": block.bottom_right[0],
                            "y2": block.bottom_right[1],
                            "width": block.width,
                            "height": block.height,
                            "color": COLOR_PALETTE[idx % len(COLOR_PALETTE)],
                            "raw": {
                                "x1": block.raw_top_left[0],
                                "y1": block.raw_top_left[1],
                                "x2": block.raw_bottom_right[0],
                                "y2": block.raw_bottom_right[1],
                            },
                        }
                        for idx, block in enumerate(scaled_blocks or blocks)
                    ],
                    "image_with_boxes": annotated_image,
                    "image_size": {"width": image_size[0], "height": image_size[1]} if image_size else None,
                    "model_space": {"width": model_space_w, "height": model_space_h},
                    "scale": {"x": scale_x, "y": scale_y},
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
    input[type="url"] {
      width: 100%;
      padding: 12px 14px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: #0b1220;
      color: #e2e8f0;
      font-size: 15px;
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
      <button id="run-btn">Run OCR</button>
      <div style="margin-top:10px; color: var(--muted); font-size: 13px;">
        Prompt: {{ prompt }}
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
      <strong>Detected Text Blocks</strong>
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
    const annotatedImg = document.getElementById("annotated-image");
    const urlInput = document.getElementById("image-url");

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
      annotatedImg.src = "";
    }

    function renderTable(blocks=[]) {
      if (!blocks.length) {
        tableContainer.innerHTML = '<div style="color: var(--muted);">No blocks detected.</div>';
        return;
      }
      const rows = blocks.map(block => `
        <tr>
          <td style="width:60px;"><span class="tag" style="border-color:${block.color}; color:${block.color};">#${block.index}</span></td>
          <td>${block.text || "&nbsp;"}</td>
          <td><div class="tag">(${block.x1},${block.y1}) → (${block.x2},${block.y2})</div></td>
          <td><div class="tag">w:${block.width}, h:${block.height}</div></td>
        </tr>
      `).join("");
      tableContainer.innerHTML = `
        <table>
          <thead>
            <tr><th>Id</th><th>Text</th><th>Coordinates</th><th>Size</th></tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      `;
    }

    async function runOcr() {
      const imageUrl = urlInput.value.trim();
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
          body: JSON.stringify({ image_url: imageUrl })
        });
        const payload = await response.json();
        if (!response.ok) {
          const steps = payload.steps || [];
          appendSteps(steps);
          throw new Error(payload.error || "Request failed");
        }

        appendSteps(payload.steps);
        rawTextEl.textContent = payload.raw_text || "";
        renderTable(payload.blocks || []);
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
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
