#!/usr/bin/env python3
"""
make_birthday_card.py

Add a recipient's name to a birthday card template.
- Centers the name inside a configurable rectangle.
- Auto-resizes font to fit.
- Optional date text.
- Optional email sending via SMTP (e.g., Gmail app password).

Usage examples:
  python make_birthday_card.py template.png "Christian" --out out/Christian.png
  python make_birthday_card.py template.png "María José" --y_offset 40
  python make_birthday_card.py template.png "Laura" --box 0,0,1080,260 --font_path "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
  python make_birthday_card.py template.png "Ana" --send_to "ana@example.com" --smtp_user "you@gmail.com" --smtp_pass "APP_PASSWORD"

CSV batch mode (name,email on each row; headers optional):
  python make_birthday_card.py template.png --csv birthdays.csv --out_dir out --send_to_column email --name_column name --subject "¡Feliz Cumple!"

Author: ChatGPT
"""

from __future__ import annotations

import argparse
import csv
import os
import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

# -------- Text helpers --------


def load_font(font_path: Optional[str], size: int) -> ImageFont.FreeTypeFont:
    if font_path and os.path.exists(font_path):
        return ImageFont.truetype(font_path, size=size)
    # Fallback fonts (likely available on most systems)
    try:
        return ImageFont.truetype("DejaVuSerif.ttf", size=size)
    except:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size=size)
        except:
            return ImageFont.load_default()


def text_bbox(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont
) -> Tuple[int, int]:
    # returns (width, height) for given text/font
    bbox = draw.textbbox((0, 0), text, font=font, anchor="lt")
    return (bbox[2] - bbox[0], bbox[3] - bbox[1])


def fit_font_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: Optional[str],
    target_w: int,
    target_h: int,
    max_size: int,
    min_size: int = 16,
) -> ImageFont.ImageFont:
    lo, hi = min_size, max_size
    best = load_font(font_path, lo)
    while lo <= hi:
        mid = (lo + hi) // 2
        f = load_font(font_path, mid)
        w, h = text_bbox(draw, text, f)
        if w <= target_w and h <= target_h:
            best = f
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def draw_centered_text(
    img: Image.Image,
    box: Tuple[int, int, int, int],
    text: str,
    font_path: Optional[str],
    color=(234, 199, 77),
    shadow=False,
    stroke=1,
):
    """Draw text centered in the given (x,y,w,h) box. Auto size to fit."""
    x, y, w, h = box
    draw = ImageDraw.Draw(img)
    font = fit_font_size(
        draw, text, font_path, target_w=w - 8, target_h=h - 8, max_size=int(h * 0.7)
    )
    # Optional shadow for readability
    if shadow:
        off = max(1, int(font.size * 0.04))
        for dx, dy in [(-off, -off), (off, off), (off, -off), (-off, off)]:
            draw.text(
                (x + w / 2 + dx, y + h / 2 + dy),
                text,
                font=font,
                fill=(0, 0, 0, 120),
                anchor="mm",
                stroke_width=0,
            )
    draw.text(
        (x + w / 2, y + h / 2),
        text,
        font=font,
        fill=color,
        anchor="mm",
        stroke_width=stroke,
        stroke_fill=(0, 0, 0, 30),
    )


# -------- Email helpers --------


def send_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
    to_addr: str,
    subject: str,
    body: str,
    attachment_path: str,
):
    msg = EmailMessage()
    msg["From"] = smtp_user
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    with open(attachment_path, "rb") as f:
        data = f.read()
    msg.add_attachment(
        data,
        maintype="image",
        subtype="png",
        filename=os.path.basename(attachment_path),
    )
    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


# -------- Main pipeline --------


@dataclass
class Args:
    template: str
    name: Optional[str]
    out: Optional[str]
    out_dir: str
    font_path: Optional[str]
    # Name box config
    box: Optional[str]
    bottom_ratio: float
    margin: int
    y_offset: int
    color: str
    shadow: bool
    csv: Optional[str]
    name_column: str
    send_to_column: Optional[str]
    smtp_user: Optional[str]
    smtp_pass: Optional[str]
    smtp_host: str
    smtp_port: int
    subject: str
    body: str
    add_date: bool


def parse_args() -> Args:
    p = argparse.ArgumentParser()
    p.add_argument("template", help="Path to the base card image (PNG/JPG).")
    p.add_argument("name", nargs="?", help="Recipient name to place on the card.")
    p.add_argument(
        "--out", help="Output image path (PNG). If not set, uses out_dir/NAME.png"
    )
    p.add_argument("--out_dir", default="out", help="Output directory (for CSV/batch).")
    p.add_argument("--font_path", default=None, help="Path to a .ttf/.otf font to use.")
    p.add_argument(
        "--box",
        default="80,1210,410,180",
        help="x,y,w,h for the name area. If omitted, uses a bottom band (bottom_ratio).",
    )
    p.add_argument(
        "--bottom_ratio",
        type=float,
        default=0.23,
        help="Height ratio of bottom band when --box not provided.",
    )
    p.add_argument(
        "--margin",
        type=int,
        default=24,
        help="Inner margin in pixels for the text box.",
    )
    p.add_argument(
        "--y_offset",
        type=int,
        default=0,
        help="Vertical offset inside the box (+down).",
    )
    p.add_argument(
        "--color", default="234,199,77", help="Text color as 'R,G,B'. (Default: golden)"
    )
    p.add_argument(
        "--shadow", action="store_true", help="Add subtle shadow behind text."
    )
    # batch / email
    p.add_argument(
        "--csv", help="CSV with name and optional email columns for batch processing."
    )
    p.add_argument(
        "--name_column", default="name", help="Column name for recipient names in CSV."
    )
    p.add_argument(
        "--send_to_column", default=None, help="Column name for recipient email in CSV."
    )
    p.add_argument(
        "--smtp_user",
        default=os.getenv("SMTP_USER"),
        help="SMTP username/email (e.g., Gmail address).",
    )
    p.add_argument(
        "--smtp_pass",
        default=os.getenv("SMTP_PASS"),
        help="SMTP password/app password.",
    )
    p.add_argument("--smtp_host", default="smtp.gmail.com")
    p.add_argument("--smtp_port", type=int, default=465)
    p.add_argument("--subject", default="¡Feliz cumpleaños de Club Discóbolo!")
    p.add_argument(
        "--body",
        default="¡Que tengas un gran día! Te enviamos tu tarjeta de cumpleaños 🎂",
    )
    p.add_argument(
        "--add_date",
        action="store_true",
        help="Add today's date (small) above the name.",
    )
    args = p.parse_args()
    return Args(
        template=args.template,
        name=args.name,
        out=args.out,
        out_dir=args.out_dir,
        font_path=args.font_path,
        box=args.box,
        bottom_ratio=args.bottom_ratio,
        margin=args.margin,
        y_offset=args.y_offset,
        color=args.color,
        shadow=args.shadow,
        csv=args.csv,
        name_column=args.name_column,
        send_to_column=args.send_to_column,
        smtp_user=args.smtp_user,
        smtp_pass=args.smtp_pass,
        smtp_host=args.smtp_host,
        smtp_port=args.smtp_port,
        subject=args.subject,
        body=args.body,
        add_date=args.add_date,
    )


def parse_box(box_str: str, W: int, H: int) -> Tuple[int, int, int, int]:
    x, y, w, h = [int(v) for v in box_str.split(",")]
    return x, y, w, h


def default_bottom_box(
    W: int, H: int, bottom_ratio: float, margin: int
) -> Tuple[int, int, int, int]:
    h = int(H * bottom_ratio)
    x = margin
    w = W - 2 * margin
    y = H - h + margin
    h = h - 2 * margin
    return x, y, w, h


def compose_card(
    template_path: str,
    name: str,
    font_path: Optional[str],
    box: Optional[Tuple[int, int, int, int]],
    color_tuple: Tuple[int, int, int],
    y_offset: int = 0,
    add_date: bool = False,
    shadow: bool = False,
) -> Image.Image:
    img = Image.open(template_path).convert("RGBA")
    W, H = img.size
    if box is None:
        box = default_bottom_box(W, H, bottom_ratio=0.23, margin=24)
    x, y, w, h = box
    # optional date line (small, above name)
    if add_date:
        draw_centered_text(
            img,
            (x, y, w, int(h * 0.3)),
            datetime.now().strftime("%A %d %B").title(),
            font_path,
            color=color_tuple,
            shadow=False,
            stroke=0,
        )
        y += int(h * 0.35)
        h = int(h * 0.65)
    draw_centered_text(
        img,
        (x, y + y_offset, w, h),
        name,
        font_path,
        color=color_tuple,
        shadow=shadow,
        stroke=1,
    )
    return img


def process_single(a: Args):
    os.makedirs(a.out_dir, exist_ok=True)
    color_tuple = tuple(int(c.strip()) for c in a.color.split(","))
    # Determine name box
    base = Image.open(a.template).convert("RGBA")
    W, H = base.size
    box = (
        parse_box(a.box, W, H)
        if a.box
        else default_bottom_box(W, H, a.bottom_ratio, a.margin)
    )
    # Compose
    card = compose_card(
        a.template,
        a.name,
        a.font_path,
        box,
        color_tuple,
        a.y_offset,
        add_date=a.add_date,
        shadow=a.shadow,
    )
    out_path = a.out or os.path.join(a.out_dir, f"{a.name}.png")
    card.save(out_path)
    print(out_path)
    return out_path


def process_csv(a: Args):
    os.makedirs(a.out_dir, exist_ok=True)
    color_tuple = tuple(int(c.strip()) for c in a.color.split(","))
    base = Image.open(a.template).convert("RGBA")
    W, H = base.size
    box = (
        parse_box(a.box, W, H)
        if a.box
        else default_bottom_box(W, H, a.bottom_ratio, a.margin)
    )
    with open(a.csv, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # tolerate headerless CSV (name,email)
        if reader.fieldnames is None or a.name_column not in reader.fieldnames:
            f.seek(0)
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                nm = row[0]
                to = row[1] if len(row) > 1 else None
                out_path = os.path.join(a.out_dir, f"{nm}.png")
                img = compose_card(
                    a.template,
                    nm,
                    a.font_path,
                    box,
                    color_tuple,
                    a.y_offset,
                    add_date=a.add_date,
                    shadow=a.shadow,
                )
                img.save(out_path)
                if to and a.smtp_user and a.smtp_pass:
                    send_email(
                        a.smtp_host,
                        a.smtp_port,
                        a.smtp_user,
                        a.smtp_pass,
                        to,
                        a.subject,
                        a.body,
                        out_path,
                    )
                print(out_path)
            return
        # DictReader path
        for row in reader:
            nm = row[a.name_column].strip()
            to = (
                row.get(a.send_to_column).strip()
                if a.send_to_column and row.get(a.send_to_column)
                else None
            )
            out_path = os.path.join(a.out_dir, f"{nm}.png")
            img = compose_card(
                a.template,
                nm,
                a.font_path,
                box,
                color_tuple,
                a.y_offset,
                add_date=a.add_date,
                shadow=a.shadow,
            )
            img.save(out_path)
            if to and a.smtp_user and a.smtp_pass:
                send_email(
                    a.smtp_host,
                    a.smtp_port,
                    a.smtp_user,
                    a.smtp_pass,
                    to,
                    a.subject,
                    a.body,
                    out_path,
                )
            print(out_path)


def main():
    a = parse_args()
    if a.csv:
        process_csv(a)
    else:
        if not a.name:
            raise SystemExit("Provide a NAME or use --csv for batch mode.")
        process_single(a)


if __name__ == "__main__":
    main()
