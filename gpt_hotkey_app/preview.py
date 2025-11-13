from __future__ import annotations

import tkinter as tk
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageTk

from .preview_ui import call_on_ui_thread, get_root

BBox = Tuple[int, int, int, int]


def _draw_boxes_multi(
    image: Image.Image,
    obj_boxes: List[BBox],
    txt_boxes: List[BBox],
    obj_color: str = "lime",
    txt_color: str = "dodgerblue",
    width: int = 3,
) -> Image.Image:
    img = image.convert("RGB").copy()
    draw = ImageDraw.Draw(img)
    for (x1, y1, x2, y2) in obj_boxes:
        draw.rectangle([(x1, y1), (x2, y2)], outline=obj_color, width=width)
    for (x1, y1, x2, y2) in txt_boxes:
        draw.rectangle([(x1, y1), (x2, y2)], outline=txt_color, width=width)
    return img


def _show_preview_ui(
    base_image: Image.Image,
    object_dets: List[Tuple[int, int, int, int, float, str]],
    text_dets: List[Tuple[int, int, int, int, float, str]] | None = None,
    max_w: int = 1200,
    thumb_size: int = 160,
) -> None:
    """UI-thread function: builds a Toplevel window attached to the hidden root."""
    root = get_root()
    text_dets = text_dets or []
    obj_boxes = [(x1, y1, x2, y2) for (x1, y1, x2, y2, _, _) in object_dets]
    txt_boxes = [(x1, y1, x2, y2) for (x1, y1, x2, y2, _, _) in text_dets]

    annotated = _draw_boxes_multi(base_image, obj_boxes, txt_boxes)
    width, height = annotated.size
    if width > max_w:
        scale = max_w / float(width)
        annotated = annotated.resize((int(width * scale), int(height * scale)), Image.LANCZOS)

    window = tk.Toplevel(root)
    window.title("Objects & Text preview (F10)")
    window.attributes("-topmost", True)

    main_frame = tk.Frame(window)
    main_frame.pack(fill=tk.BOTH, expand=True)

    left_label = tk.Label(main_frame)
    left_label.pack(side=tk.LEFT, padx=10, pady=10)

    right_frame = tk.Frame(main_frame)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

    canvas = tk.Canvas(right_frame)
    scrollbar = tk.Scrollbar(right_frame, orient=tk.VERTICAL, command=canvas.yview)
    inner = tk.Frame(canvas)
    inner.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    refs: list[ImageTk.PhotoImage] = []

    big_image = ImageTk.PhotoImage(annotated)
    refs.append(big_image)
    left_label.configure(image=big_image)

    def add_thumbnail(section: str, crop: Image.Image, caption: str) -> None:
        row = tk.Frame(inner, bd=1, relief=tk.SOLID)
        row.pack(fill=tk.X, pady=4)
        tk.Label(row, text=section, width=10, anchor="w").pack(side=tk.LEFT, padx=6)
        crop_width, crop_height = crop.size
        if max(crop_width, crop_height) > thumb_size:
            if crop_width >= crop_height:
                crop = crop.resize((thumb_size, max(1, int(crop_height * thumb_size / crop_width))), Image.LANCZOS)
            else:
                crop = crop.resize((max(1, int(crop_width * thumb_size / crop_height)), thumb_size), Image.LANCZOS)
        thumb_image = ImageTk.PhotoImage(crop)
        refs.append(thumb_image)
        tk.Label(row, image=thumb_image).pack(side=tk.LEFT, padx=6, pady=6)
        tk.Label(row, text=caption, anchor="w", justify="left").pack(side=tk.LEFT, padx=6)

    for (x1, y1, x2, y2, score, cls) in object_dets:
        add_thumbnail("Object", base_image.crop((x1, y1, x2, y2)), f"{cls} {score:.2f}")

    for (x1, y1, x2, y2, conf, txt) in text_dets:
        preview_text = (txt[:40] + "…") if len(txt) > 40 else txt
        add_thumbnail("Text", base_image.crop((x1, y1, x2, y2)), f"{conf:.2f}  {preview_text}")

    window._img_refs = refs  # type: ignore[attr-defined]

    tk.Button(window, text="Close", command=window.destroy).pack(side=tk.BOTTOM, pady=8)


def show_annotation_preview(
    base_image: Image.Image,
    object_dets: List[Tuple[int, int, int, int, float, str]],
    text_dets: List[Tuple[int, int, int, int, float, str]] | None = None,
    max_w: int = 1200,
    thumb_size: int = 160,
) -> None:
    return call_on_ui_thread(
        _show_preview_ui,
        base_image,
        object_dets,
        text_dets,
        max_w,
        thumb_size,
    )
