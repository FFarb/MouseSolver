from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageTk, ImageOps

Det = Tuple[int, int, int, int, float, str]

_img_refs = []  # Global list to hold PhotoImage references

def show_annotation_preview(
    base_image: Image.Image,
    object_dets: List[Det],
    text_dets: List[Det] | None = None,
    max_w: int = 1200,
    thumb_size: int = 160,
) -> None:
    """
    Displays a topmost Tkinter window with:
      - left: annotated region (green=objects, blue=text)
      - right: scrollable thumbnails for each detected object and text box
    """
    global _img_refs
    _img_refs.clear()
    text_dets = text_dets or []

    root = tk.Tk()
    root.title(f"Detection Preview ({len(object_dets)} objects, {len(text_dets)} text boxes)")
    root.attributes("-topmost", True)

    main_frame = ttk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # --- Annotated Image ---
    annotated_img = base_image.copy()
    draw = ImageDraw.Draw(annotated_img)
    for det in object_dets:
        draw.rectangle(det[:4], outline="lime", width=2)
    for det in text_dets:
        draw.rectangle(det[:4], outline="dodgerblue", width=2)

    # Rescale if too large
    if annotated_img.width > max_w:
        ratio = max_w / annotated_img.width
        annotated_img = annotated_img.resize((max_w, int(annotated_img.height * ratio)))

    img_tk = ImageTk.PhotoImage(annotated_img)
    _img_refs.append(img_tk)
    img_label = tk.Label(main_frame, image=img_tk)
    img_label.pack(side=tk.LEFT, padx=10, pady=10)

    # --- Thumbnails ---
    canvas = tk.Canvas(main_frame, width=thumb_size + 40)
    scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side=tk.LEFT, fill="y", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Object thumbnails
    for x1, y1, x2, y2, score, name in object_dets:
        crop = base_image.crop((x1, y1, x2, y2))
        crop_thumb = ImageOps.pad(crop, (thumb_size, thumb_size))
        thumb_tk = ImageTk.PhotoImage(crop_thumb)
        _img_refs.append(thumb_tk)

        thumb_label = tk.Label(scrollable_frame, image=thumb_tk)
        thumb_label.pack(pady=5)
        info = f"{name} ({score:.2f})"
        info_label = ttk.Label(scrollable_frame, text=info, foreground="green")
        info_label.pack()

    # Text thumbnails
    for x1, y1, x2, y2, score, txt in text_dets:
        crop = base_image.crop((x1, y1, x2, y2))
        crop_thumb = ImageOps.pad(crop, (thumb_size, thumb_size))
        thumb_tk = ImageTk.PhotoImage(crop_thumb)
        _img_refs.append(thumb_tk)

        thumb_label = tk.Label(scrollable_frame, image=thumb_tk)
        thumb_label.pack(pady=5)
        display_txt = (txt[:40] + "…") if len(txt) > 40 else txt
        info = f'"{display_txt}" ({score:.2f})'
        info_label = ttk.Label(scrollable_frame, text=info, foreground="blue")
        info_label.pack()

    root.mainloop()
