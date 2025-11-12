"""A simple Tkinter viewer for displaying object detection results."""
from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, List, Tuple

from PIL import ImageDraw, ImageTk

if TYPE_CHECKING:
    from PIL.Image import Image


def show_annotation_preview(
    img: Image, detections: List[Tuple[int, int, int, int, float, str]]
) -> None:
    """Show a preview window with the annotated image and thumbnails.

    Args:
        img: The original PIL Image.
        detections: A list of detected objects.
    """
    root = tk.Tk()
    root.title("Object Detection Preview")
    root.attributes("-topmost", True)

    # Main frame
    main_frame = tk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Annotated image on the left
    annotated_img = img.copy()
    draw = ImageDraw.Draw(annotated_img)
    for x1, y1, x2, y2, _, _ in detections:
        draw.rectangle([x1, y1, x2, y2], outline="lime", width=2)
    photo = ImageTk.PhotoImage(annotated_img)
    image_label = tk.Label(main_frame, image=photo)
    image_label.pack(side=tk.LEFT, padx=10, pady=10)

    # Thumbnails on the right
    thumb_frame = tk.Frame(main_frame)
    thumb_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

    for x1, y1, x2, y2, score, class_name in detections:
        cropped_img = img.crop((x1, y1, x2, y2)).resize((100, 100))
        thumb_photo = ImageTk.PhotoImage(cropped_img)
        thumb_label = tk.Label(thumb_frame, image=thumb_photo)
        thumb_label.image = thumb_photo  # Keep a reference
        thumb_label.pack()

        info_label = tk.Label(thumb_frame, text=f"{class_name} ({score:.2f})")
        info_label.pack()

    root.mainloop()
