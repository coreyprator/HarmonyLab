"""OMR service — Audiveris subprocess wrapper. Inputs: PDF, JPG, PNG, SVG."""
import subprocess
import tempfile
import os
import glob
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
AUDIVERIS_HOME = os.getenv("AUDIVERIS_HOME", "/opt/audiveris")


def _find_audiveris_jar():
    candidates = glob.glob(os.path.join(AUDIVERIS_HOME, "**", "Audiveris*.jar"), recursive=True)
    if not candidates:
        raise RuntimeError(f"Audiveris JAR not found under {AUDIVERIS_HOME}")
    return candidates[0]


def run_audiveris(input_path: str, output_dir: str) -> str:
    jar = _find_audiveris_jar()
    cmd = ["java", "-jar", jar, "-batch", "-export", "-output", output_dir, "--", input_path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    logger.info(f"Audiveris rc={result.returncode} stdout={result.stdout[-1000:]}")
    if result.returncode != 0:
        raise RuntimeError(f"Audiveris failed (rc={result.returncode}): {result.stderr[-500:]}")
    found = glob.glob(os.path.join(output_dir, "**", "*.xml"), recursive=True) + \
            glob.glob(os.path.join(output_dir, "**", "*.mxl"), recursive=True)
    if not found:
        raise RuntimeError("Audiveris produced no MusicXML output.")
    return found[0]


def convert_svg_to_png(svg_path: str, png_path: str):
    r = subprocess.run(["rsvg-convert", "-o", png_path, svg_path], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"SVG conversion failed: {r.stderr}")


def parse_omr_file(file_bytes: bytes, filename: str) -> dict:
    from app.services.score_parser import parse_music_file
    suffix = Path(filename).suffix.lower()
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, filename)
        with open(input_path, "wb") as f:
            f.write(file_bytes)
        if suffix == ".svg":
            png_path = os.path.join(tmpdir, Path(filename).stem + ".png")
            convert_svg_to_png(input_path, png_path)
            input_path = png_path
        output_dir = os.path.join(tmpdir, "output")
        os.makedirs(output_dir)
        xml_path = run_audiveris(input_path, output_dir)
        parsed = parse_music_file(xml_path, os.path.basename(xml_path))
    return {
        "title": parsed.title or Path(filename).stem,
        "key": parsed.key,
        "time_signature": parsed.time_signature,
        "tempo": parsed.tempo,
        "chords": [{"measure_number": c.measure_number, "beat_position": c.beat_position,
                    "chord_symbol": c.chord_symbol, "chord_order": c.chord_order}
                   for c in parsed.chords]
    }
