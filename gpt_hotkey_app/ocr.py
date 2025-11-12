"""OCR module for capturing screen regions and extracting text."""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import shutil
from typing import TYPE_CHECKING, Tuple

import pytesseract
from PIL import Image, ImageGrab, ImageOps

if TYPE_CHECKING:
    from PIL.Image import Image


def capture_active_window_image() -> Image:
    """Capture the active window and return it as a PIL Image."""
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom))


def extract_text_from_active_window() -> str:
    """Extract text from the active window using Tesseract OCR."""
    _resolve_tesseract_path()
    lang = os.getenv("OCR_LANG", "eng")
    img = capture_active_window_image()
    img = ImageOps.autocontrast(img.convert("L"))
    text = pytesseract.image_to_string(img, lang=lang)
    return text.strip()


def capture_region_image(bbox: Tuple[int, int, int, int]) -> Image:
    """Capture a screen region and return it as a PIL Image."""
    return ImageGrab.grab(bbox=bbox)


def extract_text_from_region(bbox: Tuple[int, int, int, int]) -> str:
    """Extract text from a screen region using Tesseract OCR."""
    _resolve_tesseract_path()
    lang = os.getenv("OCR_LANG", "eng")
    img = capture_region_image(bbox)
    img = ImageOps.autocontrast(img.convert("L"))
    text = pytesseract.image_to_string(img, lang=lang)
    return text.strip()


def _resolve_tesseract_path() -> None:
    """Resolve the Tesseract executable path and set it for pytesseract."""
    tess_cmd = os.getenv("TESSERACT_CMD")
    if tess_cmd and os.path.exists(tess_cmd):
        pytesseract.pytesseract.tesseract_cmd = tess_cmd
        return

    tess_cmd = shutil.which("tesseract")
    if tess_cmd:
        pytesseract.pytesseract.tesseract_cmd = tess_cmd
        return

    # Common install paths for Windows
    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for path in common_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return

    raise RuntimeError(
        "Tesseract executable not found. Please install Tesseract and set the "
        "TESSERACT_CMD environment variable to its path."
    )
