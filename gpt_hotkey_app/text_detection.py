from PIL import Image, ImageOps
import pytesseract, os, shutil
from typing import List, Tuple

Det = Tuple[int,int,int,int,float,str]  # x1,y1,x2,y2,conf,text

def _resolve_tesseract_path() -> str | None:
    p = os.getenv("TESSERACT_CMD") or shutil.which("tesseract")
    return p if p and os.path.isfile(p) else None

def detect_text_boxes(img: Image.Image, min_conf: int = 60, lang: str | None = None) -> List[Det]:
    """Detects words on the image and returns bounding boxes + text + confidence."""
    tess = _resolve_tesseract_path()
    if not tess: return []
    pytesseract.pytesseract.tesseract_cmd = tess
    lang = lang or os.getenv("OCR_LANG", "eng")
    gray = ImageOps.autocontrast(img.convert("L"))
    data = pytesseract.image_to_data(gray, lang=lang, output_type=pytesseract.Output.DICT)
    n = len(data["text"])
    out = []
    for i in range(n):
        txt = (data["text"][i] or "").strip()
        if not txt: continue
        conf = int(data.get("conf", ["-1"])[i])
        if conf < min_conf: continue
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        out.append((x, y, x + w, y + h, conf / 100.0, txt))
    return out
