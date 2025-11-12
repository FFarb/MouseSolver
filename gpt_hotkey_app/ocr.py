"""OCR module for capturing the active window and extracting text."""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
from typing import TYPE_CHECKING

import pytesseract
from PIL import ImageGrab

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
    tess_cmd = os.getenv("TESSERACT_CMD")
    if tess_cmd:
        pytesseract.pytesseract.tesseract_cmd = tess_cmd
    lang = os.getenv("OCR_LANG", "eng")
    img = capture_active_window_image()
    text = pytesseract.image_to_string(img, lang=lang)
    return text.strip()
