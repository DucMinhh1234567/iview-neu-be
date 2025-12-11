"""
Ephemeral CV/JD ingestion utilities (OCR/PDF) without persisting to DB.
"""
from __future__ import annotations

import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple

import requests
from PIL import Image
import pytesseract

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None  # type: ignore

# Optional PDF->image OCR fallback if pdf2image is installed
try:
    from pdf2image import convert_from_path  # type: ignore
    PDF2IMAGE_AVAILABLE = True
except Exception:  # pragma: no cover
    PDF2IMAGE_AVAILABLE = False


SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".pdf"}


def _guess_suffix(url: str, content_type: Optional[str]) -> str:
    """
    Guess file suffix from URL or content-type. Defaults to .pdf if unknown.
    """
    url_suffix = Path(url.split("?", 1)[0]).suffix.lower()
    if url_suffix in SUPPORTED_EXTS:
        return url_suffix

    if content_type:
        ct = content_type.lower()
        if "pdf" in ct:
            return ".pdf"
        if "png" in ct:
            return ".png"
        if "jpeg" in ct or "jpg" in ct:
            return ".jpg"
        if "tiff" in ct or "tif" in ct:
            return ".tiff"
        if "bmp" in ct:
            return ".bmp"

    return ".pdf"


def _download_to_temp(url: str) -> Path:
    """
    Download a file to a temporary path.
    Caller is responsible for cleanup.
    """
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    suffix = _guess_suffix(url, resp.headers.get("Content-Type"))
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(resp.content)
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


def _ocr_image(image_path: Path) -> str:
    try:
        with Image.open(image_path) as img:
            return pytesseract.image_to_string(img)
    except pytesseract.TesseractNotFoundError:
        return ""
    except Exception:
        return ""


def _extract_text_from_pdf(pdf_path: Path) -> str:
    text_chunks = []
    if PdfReader is not None:
        try:
            reader = PdfReader(str(pdf_path))
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_chunks.append(page_text)
        except Exception:
            pass
    if not any(chunk.strip() for chunk in text_chunks) and PDF2IMAGE_AVAILABLE:
        try:
            images = convert_from_path(str(pdf_path))
            for img in images:
                text = pytesseract.image_to_string(img)
                if text.strip():
                    text_chunks.append(text)
        except Exception:
            pass
    return "\n\n".join(t.strip() for t in text_chunks if t.strip())


def extract_text_from_cv(path: Path) -> str:
    """
    Extract text from CV/JD file (image/PDF). Raises for unsupported type.
    """
    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}:
        return _ocr_image(path)
    if suffix == ".pdf":
        return _extract_text_from_pdf(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def load_and_extract(path_or_url: str) -> Tuple[str, Optional[Path]]:
    """
    Load a CV/JD from local path or URL, extract text, and return (text, temp_path_if_any).
    Caller should delete the temp file if returned.
    """
    is_remote = path_or_url.lower().startswith(("http://", "https://"))
    file_path: Path
    if is_remote:
        file_path = _download_to_temp(path_or_url)
    else:
        file_path = Path(path_or_url)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

    if file_path.suffix.lower() not in SUPPORTED_EXTS:
        if is_remote:
            try:
                file_path.unlink(missing_ok=True)
            except Exception:
                pass
        raise ValueError(f"Unsupported file type: {file_path.suffix}")

    text = extract_text_from_cv(file_path)
    return text, (file_path if is_remote else None)


def cleanup_temp(temp_path: Optional[Path]) -> None:
    """Delete temp file if provided."""
    if temp_path and temp_path.exists():
        try:
            if temp_path.is_dir():
                shutil.rmtree(temp_path, ignore_errors=True)
            else:
                temp_path.unlink(missing_ok=True)
        except Exception:
            pass


