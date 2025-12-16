#!/usr/bin/env python3
"""
HunyuanOCR Utility Functions

This module provides reusable utilities for working with HunyuanOCR output,
including coordinate normalization/conversion functions.

HunyuanOCR Coordinate System:
-----------------------------
HunyuanOCR outputs coordinates normalized to a [0, 1000] scale regardless
of the original image dimensions. This is a common practice in VLM-based
OCR models to provide resolution-independent coordinate outputs.

To convert normalized coordinates to actual pixel coordinates:
    actual_x = normalized_x * (image_width / 1000)
    actual_y = normalized_y * (image_height / 1000)

To convert pixel coordinates back to normalized:
    normalized_x = actual_x * (1000 / image_width)
    normalized_y = actual_y * (1000 / image_height)
"""

import re
import struct
import urllib.request
from dataclasses import dataclass
from typing import List, Optional, Tuple

# HunyuanOCR normalizes coordinates to this range
HUNYUAN_COORD_RANGE = 1000


@dataclass
class TextBlock:
    """Represents a detected text block with coordinates."""
    
    text: str
    # Normalized coordinates (0-1000 range from HunyuanOCR)
    norm_x1: float
    norm_y1: float
    norm_x2: float
    norm_y2: float
    # Actual pixel coordinates (after conversion)
    pixel_x1: Optional[float] = None
    pixel_y1: Optional[float] = None
    pixel_x2: Optional[float] = None
    pixel_y2: Optional[float] = None

    @property
    def norm_top_left(self) -> Tuple[float, float]:
        """Normalized top-left coordinate."""
        return (self.norm_x1, self.norm_y1)

    @property
    def norm_bottom_right(self) -> Tuple[float, float]:
        """Normalized bottom-right coordinate."""
        return (self.norm_x2, self.norm_y2)

    @property
    def pixel_top_left(self) -> Optional[Tuple[float, float]]:
        """Pixel top-left coordinate (if converted)."""
        if self.pixel_x1 is not None and self.pixel_y1 is not None:
            return (self.pixel_x1, self.pixel_y1)
        return None

    @property
    def pixel_bottom_right(self) -> Optional[Tuple[float, float]]:
        """Pixel bottom-right coordinate (if converted)."""
        if self.pixel_x2 is not None and self.pixel_y2 is not None:
            return (self.pixel_x2, self.pixel_y2)
        return None

    @property
    def pixel_width(self) -> Optional[float]:
        """Width in pixels (if converted)."""
        if self.pixel_x1 is not None and self.pixel_x2 is not None:
            return max(0, self.pixel_x2 - self.pixel_x1)
        return None

    @property
    def pixel_height(self) -> Optional[float]:
        """Height in pixels (if converted)."""
        if self.pixel_y1 is not None and self.pixel_y2 is not None:
            return max(0, self.pixel_y2 - self.pixel_y1)
        return None

    @property
    def norm_width(self) -> float:
        """Width in normalized units (0-1000)."""
        return max(0, self.norm_x2 - self.norm_x1)

    @property
    def norm_height(self) -> float:
        """Height in normalized units (0-1000)."""
        return max(0, self.norm_y2 - self.norm_y1)


def parse_ocr_content(content: str) -> List[TextBlock]:
    """
    Parse text(x1,y1),(x2,y2) style entries from HunyuanOCR response content.
    
    The coordinates returned are in the normalized [0-1000] range.
    
    Args:
        content: Raw content string from HunyuanOCR response
        
    Returns:
        List of TextBlock objects with normalized coordinates
    """
    # Pattern matches: text(x1,y1),(x2,y2)
    pattern = re.compile(
        r"([^()]+?)\(([-+]?\d+(?:\.\d+)?),([-+]?\d+(?:\.\d+)?)\),"
        r"\(([-+]?\d+(?:\.\d+)?),([-+]?\d+(?:\.\d+)?)\)"
    )
    
    blocks: List[TextBlock] = []
    for match in pattern.finditer(content):
        text = match.group(1).strip()
        x1, y1, x2, y2 = map(float, match.groups()[1:])
        blocks.append(
            TextBlock(
                text=text,
                norm_x1=x1,
                norm_y1=y1,
                norm_x2=x2,
                norm_y2=y2,
            )
        )
    return blocks


def normalized_to_pixel(
    norm_x: float,
    norm_y: float,
    image_width: int,
    image_height: int,
    coord_range: int = HUNYUAN_COORD_RANGE,
) -> Tuple[int, int]:
    """
    Convert normalized coordinates to pixel coordinates.
    
    Args:
        norm_x: Normalized X coordinate (0-1000 for HunyuanOCR)
        norm_y: Normalized Y coordinate (0-1000 for HunyuanOCR)
        image_width: Actual image width in pixels
        image_height: Actual image height in pixels
        coord_range: The normalization range (default: 1000 for HunyuanOCR)
        
    Returns:
        Tuple of (pixel_x, pixel_y) as integers
    """
    scale_x = image_width / coord_range
    scale_y = image_height / coord_range
    return (int(norm_x * scale_x), int(norm_y * scale_y))


def pixel_to_normalized(
    pixel_x: int,
    pixel_y: int,
    image_width: int,
    image_height: int,
    coord_range: int = HUNYUAN_COORD_RANGE,
) -> Tuple[float, float]:
    """
    Convert pixel coordinates to normalized coordinates.
    
    Args:
        pixel_x: X coordinate in pixels
        pixel_y: Y coordinate in pixels
        image_width: Actual image width in pixels
        image_height: Actual image height in pixels
        coord_range: The normalization range (default: 1000 for HunyuanOCR)
        
    Returns:
        Tuple of (norm_x, norm_y) as floats
    """
    scale_x = coord_range / image_width
    scale_y = coord_range / image_height
    return (pixel_x * scale_x, pixel_y * scale_y)


def get_scale_factors(
    image_width: int,
    image_height: int,
    coord_range: int = HUNYUAN_COORD_RANGE,
) -> Tuple[float, float]:
    """
    Calculate the scale factors for converting normalized to pixel coordinates.
    
    Args:
        image_width: Actual image width in pixels
        image_height: Actual image height in pixels
        coord_range: The normalization range (default: 1000 for HunyuanOCR)
        
    Returns:
        Tuple of (scale_x, scale_y)
    """
    return (image_width / coord_range, image_height / coord_range)


def convert_blocks_to_pixels(
    blocks: List[TextBlock],
    image_width: int,
    image_height: int,
    coord_range: int = HUNYUAN_COORD_RANGE,
) -> List[TextBlock]:
    """
    Convert all blocks' coordinates from normalized to pixel values.
    
    This creates new TextBlock objects with pixel coordinates filled in.
    
    Args:
        blocks: List of TextBlock objects with normalized coordinates
        image_width: Actual image width in pixels
        image_height: Actual image height in pixels
        coord_range: The normalization range (default: 1000 for HunyuanOCR)
        
    Returns:
        List of TextBlock objects with both normalized and pixel coordinates
    """
    scale_x, scale_y = get_scale_factors(image_width, image_height, coord_range)
    
    converted: List[TextBlock] = []
    for block in blocks:
        converted.append(
            TextBlock(
                text=block.text,
                norm_x1=block.norm_x1,
                norm_y1=block.norm_y1,
                norm_x2=block.norm_x2,
                norm_y2=block.norm_y2,
                pixel_x1=int(block.norm_x1 * scale_x),
                pixel_y1=int(block.norm_y1 * scale_y),
                pixel_x2=int(block.norm_x2 * scale_x),
                pixel_y2=int(block.norm_y2 * scale_y),
            )
        )
    return converted


def get_image_size_from_bytes(data: bytes) -> Optional[Tuple[int, int]]:
    """
    Get image dimensions from raw bytes without requiring PIL.
    
    Supports: PNG, JPEG, GIF, BMP
    
    Args:
        data: Raw image bytes (at least first 64KB)
        
    Returns:
        Tuple of (width, height) or None if format not recognized
    """
    # Check for PNG
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        w, h = struct.unpack('>LL', data[16:24])
        return (int(w), int(h))
    
    # Check for JPEG
    if data[:2] == b'\xff\xd8':
        idx = 2
        while idx < len(data):
            if data[idx] != 0xff:
                idx += 1
                continue
            marker = data[idx + 1]
            if marker == 0xd9:  # EOI
                break
            if marker in (0xc0, 0xc2):  # SOF0 or SOF2
                h, w = struct.unpack('>HH', data[idx + 5:idx + 9])
                return (int(w), int(h))
            if marker in (0xd0, 0xd1, 0xd2, 0xd3, 0xd4, 0xd5, 0xd6, 0xd7, 0xd8, 0x01):
                idx += 2
            else:
                length = struct.unpack('>H', data[idx + 2:idx + 4])[0]
                idx += 2 + length
        return None
    
    # Check for GIF
    if data[:6] in (b'GIF87a', b'GIF89a'):
        w, h = struct.unpack('<HH', data[6:10])
        return (int(w), int(h))
    
    # Check for BMP
    if data[:2] == b'BM':
        w, h = struct.unpack('<II', data[18:26])
        return (int(w), int(h))
    
    return None


def get_image_dimensions_from_url(url: str, timeout: int = 10) -> Optional[Tuple[int, int]]:
    """
    Fetch an image from URL and return its dimensions.
    
    First tries to parse dimensions from image header bytes (fast),
    falls back to PIL if available.
    
    Args:
        url: URL of the image
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (width, height) or None if unable to determine
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            # Read enough bytes to get dimensions from header
            img_data = response.read(65536)  # 64KB should be enough
        
        dims = get_image_size_from_bytes(img_data)
        if dims:
            return dims
        
        # Fallback: try PIL if available
        try:
            from PIL import Image
            from io import BytesIO
            
            # Need to read full image for PIL
            with urllib.request.urlopen(url, timeout=timeout) as response:
                full_data = response.read()
            img = Image.open(BytesIO(full_data))
            return img.size
        except ImportError:
            pass
        
        return None
    except Exception:
        return None


def format_coordinate_info(
    blocks: List[TextBlock],
    image_size: Optional[Tuple[int, int]] = None,
) -> str:
    """
    Format blocks with coordinate information as a human-readable string.
    
    Args:
        blocks: List of TextBlock objects
        image_size: Optional tuple of (width, height) in pixels
        
    Returns:
        Formatted string with coordinate information
    """
    lines = []
    
    if image_size:
        w, h = image_size
        scale_x, scale_y = get_scale_factors(w, h)
        lines.append(f"Image dimensions: {w} x {h} pixels")
        lines.append(f"Scale factors: x={scale_x:.3f}, y={scale_y:.3f}")
        lines.append(f"(HunyuanOCR uses normalized coordinates in [0-{HUNYUAN_COORD_RANGE}] range)")
        lines.append("")
    
    lines.append(f"Found {len(blocks)} text elements:")
    lines.append("-" * 80)
    
    if image_size:
        lines.append(f"{'No.':>4}  {'Text':<35}  {'Normalized':<20}  {'Pixels'}")
        lines.append("-" * 80)
        
        converted = convert_blocks_to_pixels(blocks, image_size[0], image_size[1])
        for i, block in enumerate(converted, 1):
            text = block.text[:33] + ".." if len(block.text) > 35 else block.text
            norm = f"({block.norm_x1:.0f},{block.norm_y1:.0f})→({block.norm_x2:.0f},{block.norm_y2:.0f})"
            pixel = f"({block.pixel_x1},{block.pixel_y1})→({block.pixel_x2},{block.pixel_y2})"
            lines.append(f"{i:>4}  {text:<35}  {norm:<20}  {pixel}")
    else:
        lines.append(f"{'No.':>4}  {'Text':<40}  {'Coordinates (normalized 0-1000)'}")
        lines.append("-" * 80)
        
        for i, block in enumerate(blocks, 1):
            text = block.text[:38] + ".." if len(block.text) > 40 else block.text
            coords = f"({block.norm_x1:.0f},{block.norm_y1:.0f}) → ({block.norm_x2:.0f},{block.norm_y2:.0f})"
            lines.append(f"{i:>4}  {text:<40}  {coords}")
    
    lines.append("-" * 80)
    return "\n".join(lines)


# For backwards compatibility with existing code
def rescale_blocks_to_image(
    blocks: List[TextBlock],
    image_size: Tuple[int, int],
) -> List[TextBlock]:
    """
    Convert blocks from normalized coordinates to pixel coordinates.
    
    This is a compatibility wrapper around convert_blocks_to_pixels().
    
    Args:
        blocks: List of TextBlock objects with normalized coordinates
        image_size: Tuple of (width, height) in pixels
        
    Returns:
        List of TextBlock objects with pixel coordinates filled in
    """
    return convert_blocks_to_pixels(blocks, image_size[0], image_size[1])

