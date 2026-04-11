"""
OMR service — oemer-based pipeline. Inputs: JPG, PNG, SVG, PDF.
PDF is converted to PNG (first page) via pdf2image before processing.
"""
import subprocess
import tempfile
import os
import glob
import logging
from pathlib import Path

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


def _run_oemer(image_path: str, output_dir: str) -> str:
    """Run oemer CLI on image_path, return path to output MusicXML."""
    result = subprocess.run(
        ["oemer", image_path, "-o", output_dir, "--without-deskew"],
        capture_output=True, text=True, timeout=300
    )
    logger.info(f"oemer stdout: {result.stdout[-1000:]}")
    if result.returncode != 0:
        logger.error(f"oemer stderr: {result.stderr[-1000:]}")
        raise RuntimeError(f"oemer failed (rc={result.returncode}): {result.stderr[-400:]}")

    xml_files = glob.glob(os.path.join(output_dir, "*.musicxml")) + \
                glob.glob(os.path.join(output_dir, "*.xml"))
    if not xml_files:
        raise RuntimeError("oemer produced no MusicXML output. The image may not contain recognizable music notation.")
    return xml_files[0]


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
