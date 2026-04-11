"""
OMR service — oemer-based pipeline. Inputs: JPG, PNG, SVG, PDF.
PDF is converted to PNG (first page) via pdf2image before processing.
Uses oemer as an in-process Python library (not subprocess) to avoid
model re-loading overhead on each request.
"""
import subprocess
import tempfile
import os
import logging
from argparse import Namespace
from pathlib import Path

logger = logging.getLogger(__name__)

# Target ~1.5M pixels instead of oemer's default 3-4.35M to keep
# inference time under 120s on Cloud Run CPU.
_TARGET_PIXELS_LB = 1_000_000
_TARGET_PIXELS_UB = 1_500_000


def _patch_oemer():
    """Monkey-patch oemer.inference.resize_image to target fewer pixels."""
    import oemer.inference as inf
    from PIL import Image as PILImage
    import numpy as np

    _original_resize = inf.resize_image

    def _fast_resize(image: PILImage.Image):
        w, h = image.size
        pix = w * h
        if _TARGET_PIXELS_LB <= pix <= _TARGET_PIXELS_UB:
            return image
        lb = _TARGET_PIXELS_LB / pix
        ub = _TARGET_PIXELS_UB / pix
        ratio = pow((lb + ub) / 2, 0.5)
        tar_w = round(ratio * w)
        tar_h = round(ratio * h)
        logger.info(f"OMR resize: {w}x{h} -> {tar_w}x{tar_h} ({tar_w*tar_h} px)")
        return image.resize((tar_w, tar_h))

    inf.resize_image = _fast_resize


_patch_oemer()


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


def _validate_image(image_path: str) -> None:
    """Reject images too small for OMR processing."""
    from PIL import Image
    img = Image.open(image_path)
    w, h = img.size
    if w < 100 or h < 100:
        raise RuntimeError(f"Image too small for OMR ({w}x{h}). Minimum 100x100 pixels.")


def _run_oemer(image_path: str, output_dir: str) -> str:
    """Run oemer in-process on image_path, return path to output MusicXML."""
    _validate_image(image_path)

    from oemer.ete import extract, clear_data
    from oemer import MODULE_PATH

    chk_path = os.path.join(MODULE_PATH, "checkpoints/unet_big/model.onnx")
    if not os.path.exists(chk_path):
        raise RuntimeError(f"oemer checkpoints not found at {chk_path}")

    args = Namespace(
        img_path=image_path,
        output_path=output_dir,
        use_tf=False,
        save_cache=False,
        without_deskew=True,
    )

    try:
        clear_data()
        xml_path = extract(args)
        logger.info(f"oemer produced: {xml_path}")
        return xml_path
    except Exception as e:
        logger.error(f"oemer processing error: {e}")
        raise RuntimeError(f"oemer failed: {e}")


def parse_omr_file(file_bytes: bytes, filename: str) -> dict:
    """
    Main entry: raw bytes + filename -> ParsedScore dict.
    Handles PDF (converts first page), SVG (converts to PNG), JPG/PNG directly.
    """
    from app.services.score_parser import parse_music_file
    suffix = Path(filename).suffix.lower()

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, filename)
        with open(input_path, "wb") as f:
            f.write(file_bytes)

        # Convert to PNG if needed
        if suffix == ".pdf":
            image_path = _pdf_to_png(input_path, tmpdir)
        elif suffix == ".svg":
            image_path = _svg_to_png(input_path, tmpdir)
        else:
            image_path = input_path  # JPG/PNG: pass directly

        output_dir = os.path.join(tmpdir, "oemer_output")
        os.makedirs(output_dir)
        xml_path = _run_oemer(image_path, output_dir)

        # Parse MusicXML via existing score_parser (music21 path)
        parsed = parse_music_file(xml_path, os.path.basename(xml_path))

    chords = [
        {
            "measure_number": c.measure_number,
            "beat_position": c.beat_position,
            "chord_symbol": c.chord_symbol,
            "chord_order": c.chord_order,
        }
        for c in parsed.chords
    ]
    result = {
        "title": parsed.title or Path(filename).stem,
        "key": parsed.key,
        "time_signature": parsed.time_signature,
        "tempo": parsed.tempo,
        "chords": chords,
    }
    if not chords:
        result["warning"] = "No chord symbols detected. Try a cleaner scan."
    return result
