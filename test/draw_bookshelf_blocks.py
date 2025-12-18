#!/usr/bin/env python3
"""
Draw compartment detection blocks on images.
Reads normalized coordinates (0-1000 scale) from a JSON file
and draws bounding boxes on the specified image.

Usage:
    python draw_bookshelf_blocks.py <image_file> <json_file>
    python draw_bookshelf_blocks.py --image pexels.jpg --json blocks.json
    python draw_bookshelf_blocks.py -i pexels.jpg -j blocks.json
"""

import argparse
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# HunyuanOCR normalized coordinate range
HUNYUAN_COORD_RANGE = 1000

# Color palette for different compartments
COLORS = [
    "#f97316",  # Orange
    "#22c55e",  # Green
    "#0ea5e9",  # Blue
    "#a855f7",  # Purple
    "#e11d48",  # Red
    "#06b6d4",  # Cyan
    "#f59e0b",  # Amber
    "#10b981",  # Emerald
]
LINE_WIDTH = 4

def normalized_to_pixel(norm_coord, pixel_size):
    """
    Convert normalized coordinate (0-1000) to pixel coordinate.
    
    Args:
        norm_coord: Normalized coordinate in [0-1000] range
        pixel_size: Actual pixel dimension (width or height)
    
    Returns:
        Pixel coordinate
    """
    return int((norm_coord / HUNYUAN_COORD_RANGE) * pixel_size)

def draw_blocks(image_filename="pexels-photo-1370295.jpeg", json_filename="bookshelf_blocks.json"):
    """Draw compartment blocks on the image."""
    
    # Load the JSON data
    json_path = Path(__file__).parent / json_filename
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Determine the format of the data
    if isinstance(data, list):
        # Direct list of compartments (new format with box_2d)
        compartments = data
    elif isinstance(data, dict):
        # Dictionary with a key containing compartments
        if 'detections' in data:
            compartments = data['detections']
        elif 'compartments' in data:
            compartments = data['compartments']
        elif 'shelf_compartments' in data:
            compartments = data['shelf_compartments']
        else:
            raise ValueError("JSON dict must contain 'detections', 'compartments', or 'shelf_compartments' key")
    else:
        raise ValueError("JSON must be a list or dict")
    
    # Load the image
    img_path = Path(__file__).parent / image_filename
    if not img_path.exists():
        raise FileNotFoundError(f"Image not found: {img_path}")
    
    image = Image.open(img_path).convert("RGB")
    
    # Respect EXIF orientation so the image displays correctly
    try:
        from PIL import ImageOps
        image = ImageOps.exif_transpose(image)
    except Exception:
        pass
    
    width, height = image.size
    
    # Calculate scale factors
    scale_x = width / HUNYUAN_COORD_RANGE
    scale_y = height / HUNYUAN_COORD_RANGE
    
    print(f"Image: {image_filename}")
    print(f"Image dimensions: {width}x{height} pixels")
    print(f"Normalized coordinate range: 0-{HUNYUAN_COORD_RANGE}")
    print(f"Scale factors: x={scale_x:.3f}, y={scale_y:.3f}")
    print(f"Total compartments: {len(compartments)}")
    
    # Create drawing context
    draw = ImageDraw.Draw(image)
    
    # Try to load a font, fallback to default if not available
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except:
        font = ImageFont.load_default()
    
    # Draw compartments
    print("\nDrawing compartments:")
    for idx, compartment in enumerate(compartments, 1):
        # Handle different coordinate formats
        if 'box_2d' in compartment:
            # New format: box_2d = [x1, y1, x2, y2]
            box = compartment['box_2d']
            norm_x1, norm_y1, norm_x2, norm_y2 = box[0], box[1], box[2], box[3]
            label = compartment.get('label', f'comp_{idx}')
        else:
            # Old format: separate x1, y1, x2, y2 keys
            norm_x1 = compartment['x1']
            norm_y1 = compartment['y1']
            norm_x2 = compartment['x2']
            norm_y2 = compartment['y2']
            label = f'Comp {idx}'
        
        # Convert to pixel coordinates
        x1 = normalized_to_pixel(norm_x1, width)
        y1 = normalized_to_pixel(norm_y1, height)
        x2 = normalized_to_pixel(norm_x2, width)
        y2 = normalized_to_pixel(norm_y2, height)
        
        pixel_width = x2 - x1
        pixel_height = y2 - y1
        
        if idx <= 5 or idx > len(compartments) - 2:  # Show first 5 and last 2
            print(f"  Compartment {idx}:")
            print(f"    Normalized: ({norm_x1},{norm_y1}) → ({norm_x2},{norm_y2})")
            print(f"    Pixel:      ({x1},{y1}) → ({x2},{y2}) [{pixel_width}x{pixel_height}px]")
        elif idx == 6:
            print(f"  ... ({len(compartments) - 7} more compartments) ...")
        
        # Get color for this compartment
        color = COLORS[(idx - 1) % len(COLORS)]
        
        # Draw rectangle
        draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=LINE_WIDTH)
        
        # Draw label (use label from above, either from JSON or default)
        display_label = label if 'box_2d' not in compartment else f"C{idx}"
        text_bg = draw.textbbox((x1 + 8, y1 + 8), display_label, font=font)
        draw.rectangle(text_bg, fill=color)
        draw.text((x1 + 8, y1 + 8), display_label, fill="white", font=font)
    
    # Save the output
    # Generate output filename: input.jpg -> input_annotated.jpg
    input_stem = Path(image_filename).stem
    output_filename = f"{input_stem}_annotated.jpg"
    output_path = Path(__file__).parent / output_filename
    image.save(output_path, format="JPEG", quality=95)
    
    print(f"\n✅ Saved annotated image to: {output_path}")
    print(f"   Total compartments drawn: {len(compartments)}")
    
    return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Draw bounding boxes on images from normalized coordinate data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s image.jpg data.json
  %(prog)s --image image.jpg --json data.json
  %(prog)s -i image.jpg -j data.json
  
Coordinate Format:
  JSON should contain normalized coordinates in [0-1000] range.
  Supports formats:
    - [{"label": "...", "x1": 0, "y1": 0, "x2": 100, "y2": 100}]
    - [{"label": "...", "box_2d": [x1, y1, x2, y2]}]
        """
    )
    
    parser.add_argument(
        'image_file',
        nargs='?',
        help='Input image filename (e.g., image.jpg)'
    )
    parser.add_argument(
        'json_file',
        nargs='?',
        help='Input JSON filename with coordinates (e.g., blocks.json)'
    )
    parser.add_argument(
        '-i', '--image',
        dest='image_flag',
        help='Input image filename (alternative to positional argument)'
    )
    parser.add_argument(
        '-j', '--json',
        dest='json_flag',
        help='Input JSON filename (alternative to positional argument)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output filename (default: <image>_annotated.jpg)'
    )
    
    args = parser.parse_args()
    
    # Determine image and JSON files from arguments
    image_file = args.image_flag or args.image_file
    json_file = args.json_flag or args.json_file
    
    # Validate inputs
    if not image_file:
        parser.error("Image file is required. Use: script.py <image> <json> or -i <image>")
    if not json_file:
        parser.error("JSON file is required. Use: script.py <image> <json> or -j <json>")
    
    # Run the drawing function
    try:
        output_path = draw_blocks(image_file, json_file)
        print(f"\n✨ Success! Annotated image saved.")
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

