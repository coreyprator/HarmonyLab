"""
OMR service — Claude Vision API pipeline. Inputs: JPG, PNG, SVG, PDF.
PDF is converted to PNG (first page) via pdf2image before processing.
SVG is converted to PNG via rsvg-convert before processing.
"""
import anthropic
import base64
import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image as PILImage

from config.settings import settings

logger = logging.getLogger(__name__)


def _pdf_to_png(pdf_path: str, output_dir: str) -> str:
    """Convert first page of PDF to PNG using pdf2image (requires poppler)."""
    from pdf2image import convert_from_path
    pages = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)
    if not pages:
        raise RuntimeError("pdf2image returned no pages from PDF.")
    png_path = os.path.join(output_dir, "page_1.png")
    pages[0].save(png_path, "PNG")
    logger.info(f"PDF converted to PNG: {png_path}")
    return png_path


def _svg_to_png(svg_path: str, output_dir: str) -> str:
    """Convert SVG to PNG via rsvg-convert."""
    png_path = os.path.join(output_dir, Path(svg_path).stem + ".png")
    result = subprocess.run(
        ["rsvg-convert", "-o", png_path, svg_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"SVG conversion failed: {result.stderr}")
    return png_path


def _resize_if_needed(image_path: str, max_px: int = 2000) -> str:
    """Resize image if largest dimension exceeds max_px."""
    img = PILImage.open(image_path)
    w, h = img.size
    if max(w, h) <= max_px:
        return image_path
    ratio = max_px / max(w, h)
    new_size = (int(w * ratio), int(h * ratio))
    resized = img.resize(new_size, PILImage.LANCZOS)
    out_path = image_path + "_resized.png"
    resized.save(out_path, "PNG")
    logger.info(f"OMR resize: {w}x{h} -> {new_size[0]}x{new_size[1]}")
    return out_path


def _run_vision_extraction(image_path: str) -> dict:
    """Extract chord symbols from a lead sheet image using Claude Vision API."""
    image_path = _resize_if_needed(image_path)
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode()

    ext = Path(image_path).suffix.lower()
    media_type = "image/jpeg" if ext in {".jpg", ".jpeg"} else "image/png"

    response = client.messages.create(
        model=settings.omr_model,
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": image_data}
                },
                {
                    "type": "text",
                    "text": """Extract all chord symbols from this jazz lead sheet.
Return ONLY valid JSON, no markdown, no prose:
{
  "title": "song title",
  "key": "e.g. Eb major",
  "time_signature": "e.g. 4/4",
  "tempo": "tempo marking or null",
  "chords": [
    {"measure": 1, "beat": 1, "symbol": "Fm7"}
  ]
}
Include every chord symbol left-to-right, top-to-bottom.
Preserve exact notation including alterations (b9, #11, maj7, dim, etc)."""
                }
            ]
        }]
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r'^```[a-z]*\n?', '', raw).rstrip('`').strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"json_parse:{e}")

    if not result.get("chords"):
        result["_warning"] = "No chord symbols found. Try a higher resolution image."

    return result


def parse_omr_file(file_bytes: bytes, filename: str) -> dict:
    """
    Main entry: raw bytes + filename -> parsed chord dict.
    Handles PDF (converts first page), SVG (converts to PNG), JPG/PNG directly.
    """
    from fastapi import HTTPException

    suffix = Path(filename).suffix.lower()
    original_filename = filename

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, filename)
        with open(input_path, "wb") as f:
            f.write(file_bytes)

        if suffix == ".pdf":
            image_path = _pdf_to_png(input_path, tmpdir)
        elif suffix == ".svg":
            image_path = _svg_to_png(input_path, tmpdir)
        elif suffix in {".jpg", ".jpeg", ".png"}:
            image_path = input_path
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

        try:
            result = _run_vision_extraction(image_path)
        except ValueError as e:
            stage, msg = str(e).split(":", 1) if ":" in str(e) else ("vision_api", str(e))
            raise HTTPException(status_code=422,
                detail={"detail": msg, "stage": stage})
        except anthropic.APIError as e:
            raise HTTPException(status_code=500,
                detail={"detail": str(e), "stage": "vision_api"})

    # BUG-018: Use original filename as title when Vision returns generic title
    if original_filename:
        stem = Path(original_filename).stem
        if not result.get("title") or result["title"].lower().startswith("page"):
            result["title"] = stem

    # Normalize chord format for frontend compatibility
    chords = []
    for c in result.get("chords", []):
        chords.append({
            "measure_number": c.get("measure", 1),
            "beat_position": c.get("beat", 1),
            "chord_symbol": c.get("symbol", ""),
            "chord_order": len(chords) + 1,
        })

    output = {
        "title": result.get("title", Path(filename).stem),
        "key": result.get("key"),
        "time_signature": result.get("time_signature"),
        "tempo": result.get("tempo"),
        "chords": chords,
    }
    if not chords:
        output["warning"] = result.get("_warning", "No chord symbols detected. Try a cleaner scan.")
    return output
