#!/usr/bin/env python3
"""Generate design-spec figures. Orthogonal arrows only (no diagonals)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent

BG = (255, 255, 255)
INK = (45, 55, 72)
MUTED = (100, 110, 125)
FRAME = (175, 185, 200)

BLUE_F, BLUE_B = (230, 240, 255), (90, 140, 220)
ORANGE_F, ORANGE_B = (255, 236, 214), (210, 140, 70)
TAN_F, TAN_B = (252, 243, 228), (190, 150, 100)
GREY_F, GREY_B = (242, 244, 247), (140, 150, 165)
GREEN_F, GREEN_B = (226, 245, 232), (70, 150, 100)
RED_F, RED_B = (255, 232, 232), (200, 90, 90)
BADGE_F, BADGE_B = (255, 176, 96), (200, 110, 40)
SHADOW = (0, 0, 0, 32)


def font(size: int, bold: bool = False):
    paths = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default()


F_TITLE = font(28, True)
F_BOX = font(17, True)
F_SUB = font(13)
F_LABEL = font(12)
F_BADGE = font(11, True)
F_NOTE = font(13)
F_FRAME = font(14, True)


class Box:
    __slots__ = ("x", "y", "w", "h", "title", "subtitle", "fill", "border")

    def __init__(self, x, y, w, h, title, subtitle, fill, border):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.title, self.subtitle = title, subtitle
        self.fill, self.border = fill, border

    @property
    def cx(self):
        return self.x + self.w // 2

    @property
    def cy(self):
        return self.y + self.h // 2

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.w

    @property
    def top(self):
        return self.y

    @property
    def bottom(self):
        return self.y + self.h


def round_rect(draw, xy, r, fill, outline, width=2):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def shadow(img, box, r=14, off=3):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(
        (box.x + off, box.y + off, box.right + off, box.bottom + off),
        radius=r,
        fill=SHADOW,
    )
    img.alpha_composite(layer)


def draw_box(img, draw, box, r=14):
    shadow(img, box, r=r)
    round_rect(draw, (box.x, box.y, box.right, box.bottom), r, box.fill, box.border, 2)
    if not box.title and not box.subtitle:
        return
    if box.subtitle:
        draw.text((box.cx, box.y + 18), box.title, fill=INK, font=F_BOX, anchor="mt")
        # wrap subtitle
        words, lines, cur = box.subtitle.split(), [], ""
        max_w = box.w - 24
        for w in words:
            trial = f"{cur} {w}".strip()
            if draw.textlength(trial, font=F_SUB) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        sy = box.y + 42
        for line in lines[:3]:
            draw.text((box.cx, sy), line, fill=MUTED, font=F_SUB, anchor="mt")
            sy += 16
    else:
        draw.text((box.cx, box.cy), box.title, fill=INK, font=F_BOX, anchor="mm")


def arrowhead(draw, tip, direction, color=INK, size=8):
    x, y = tip
    if direction == "right":
        pts = [(x, y), (x - size, y - 5), (x - size, y + 5)]
    elif direction == "left":
        pts = [(x, y), (x + size, y - 5), (x + size, y + 5)]
    elif direction == "down":
        pts = [(x, y), (x - 5, y - size), (x + 5, y - size)]
    else:
        pts = [(x, y), (x - 5, y + size), (x + 5, y + size)]
    draw.polygon(pts, fill=color)


def _seg(draw, a, b, color, width, dashed):
    x0, y0 = a
    x1, y1 = b
    # Enforce axis-aligned segments only
    assert x0 == x1 or y0 == y1, f"diagonal forbidden: {a} -> {b}"
    if not dashed:
        draw.line([a, b], fill=color, width=width)
        return
    dx, dy = x1 - x0, y1 - y0
    length = abs(dx) + abs(dy)
    if length == 0:
        return
    ux = 0 if dx == 0 else (1 if dx > 0 else -1)
    uy = 0 if dy == 0 else (1 if dy > 0 else -1)
    pos, on, dash, gap = 0, True, 7, 5
    while pos < length:
        step = min(dash if on else gap, length - pos)
        if on:
            draw.line(
                (x0 + ux * pos, y0 + uy * pos, x0 + ux * (pos + step), y0 + uy * (pos + step)),
                fill=color,
                width=width,
            )
        pos += step
        on = not on


def wire(draw, points, *, dashed=False, color=INK, width=2, head=None, label=None, label_at=None):
    for i in range(len(points) - 1):
        _seg(draw, points[i], points[i + 1], color, width, dashed)
    if head:
        arrowhead(draw, (head[0], head[1]), head[2], color)
    if label and label_at:
        draw.text(label_at, label, fill=MUTED, font=F_LABEL, anchor="mm")


def badge(draw, cx, cy, text):
    tw = draw.textlength(text, font=F_BADGE)
    w, h = tw + 20, 22
    x0, y0 = cx - w / 2, cy - h / 2
    round_rect(draw, (x0, y0, x0 + w, y0 + h), 11, BADGE_F, BADGE_B, 1)
    draw.text((cx, cy), text, fill=(80, 40, 10), font=F_BADGE, anchor="mm")


def generate_01():
    W, H = 1520, 980
    img = Image.new("RGBA", (W, H), BG + (255,))
    draw = ImageDraw.Draw(img)
    draw.text((48, 28), "Connector Service", fill=INK, font=F_TITLE)

    fx0, fy0, fx1, fy1 = 280, 125, 1200, 830
    round_rect(draw, (fx0, fy0, fx1, fy1), 18, (252, 253, 255), FRAME, 2)
    draw.text((fx0 + 20, fy0 + 12), "Connector Service", fill=MUTED, font=F_FRAME)

    admin = Box(540, 40, 400, 68, "Connector Admin UI", "operators create, configure, and monitor pipelines", BLUE_F, BLUE_B)
    sources = Box(40, 290, 200, 210, "Data sources", "", GREY_F, GREY_B)

    # Align API / Fetch centers over DB so feeds are pure vertical (no elbows)
    db = Box(480, 340, 440, 105, "Connector database", "payloads, records, configuration, history", TAN_F, TAN_B)
    api = Box(db.x + 20, 185, 180, 80, "Service API", "receives pushed payloads", BLUE_F, BLUE_B)
    fetch = Box(db.right - 200, 185, 180, 80, "Fetch worker", "reads from sources", ORANGE_F, ORANGE_B)

    sched = Box(320, 510, 250, 80, "Job scheduler", "starts work on interval", BLUE_F, BLUE_B)
    queue = Box(900, 510, 250, 80, "Task queue", "jobs wait for a free worker", TAN_F, TAN_B)
    push = Box(480, 670, 440, 95, "Push worker", "reads waiting records and sends them in batches", ORANGE_F, ORANGE_B)
    registry = Box(1255, 670, 230, 100, "OpenG2P Registry", "Partner API", GREEN_F, GREEN_B)

    for b in (admin, sources, api, fetch, db, sched, queue, push, registry):
        draw_box(img, draw, b)

    by = sources.y + 52
    for line in ("Partner systems", "Survey platforms", "Other registries"):
        draw.text((sources.cx, by), line, fill=MUTED, font=F_SUB, anchor="mt")
        by += 24

    wire(draw, [(admin.cx, admin.bottom), (admin.cx, fy0)], head=(admin.cx, fy0, "down"))

    # push — straight horizontal into API
    y_push = api.cy
    # drop from sources to API height first if needed, then across
    wire(
        draw,
        [
            (sources.right, sources.cy - 40),
            (240, sources.cy - 40),
            (240, y_push),
            (api.left, y_push),
        ],
        head=(api.left, y_push, "right"),
        label="push",
        label_at=(240 + (api.left - 240) // 2, y_push - 14),
    )
    badge(draw, 240 + (api.left - 240) // 2, y_push + 18, "partner key validated")

    # fetch — top rail then left rail into sources
    top_rail = 158
    left_rail = 240
    wire(
        draw,
        [
            (fetch.cx, fetch.top),
            (fetch.cx, top_rail),
            (left_rail, top_rail),
            (left_rail, sources.cy + 40),
            (sources.right, sources.cy + 40),
        ],
        head=(sources.right, sources.cy + 40, "left"),
        label="fetch",
        label_at=(left_rail - 28, (top_rail + sources.cy + 40) // 2),
    )

    # Pure verticals into DB
    wire(draw, [(api.cx, api.bottom), (api.cx, db.top)], head=(api.cx, db.top, "down"))
    wire(draw, [(fetch.cx, fetch.bottom), (fetch.cx, db.top)], head=(fetch.cx, db.top, "down"))

    # Scheduler → queue
    y_job = sched.cy
    mid_job = (sched.right + queue.left) // 2
    wire(
        draw,
        [(sched.right, y_job), (queue.left, y_job)],
        dashed=True,
        head=(queue.left, y_job, "right"),
        label="posts a job",
        label_at=(mid_job, y_job - 14),
    )

    # Queue → Fetch along right rail (H + V + H only)
    right_rail = 1175
    wire(
        draw,
        [
            (queue.right, queue.cy),
            (right_rail, queue.cy),
            (right_rail, fetch.cy),
            (fetch.right, fetch.cy),
        ],
        dashed=True,
        head=(fetch.right, fetch.cy, "left"),
        label="takes a job",
        label_at=(right_rail - 55, (queue.cy + fetch.cy) // 2),
    )

    # Queue → Push: vertical down then horizontal into push top
    under_q = 620
    wire(
        draw,
        [
            (queue.cx, queue.bottom),
            (queue.cx, under_q),
            (push.cx + 120, under_q),
            (push.cx + 120, push.top),
        ],
        dashed=True,
        head=(push.cx + 120, push.top, "down"),
        label="takes a job",
        label_at=(queue.cx + 75, (queue.bottom + under_q) // 2),
    )

    y_bat = push.cy
    mid_bat = (push.right + registry.left) // 2
    wire(
        draw,
        [(push.right, y_bat), (registry.left, y_bat)],
        head=(registry.left, y_bat, "right"),
        label="batches",
        label_at=(mid_bat, y_bat - 14),
    )
    badge(draw, mid_bat, y_bat + 18, "connector key validated")

    draw.text(
        (48, H - 36),
        "Dashed lines show scheduled work. "
        "The job scheduler posts a job to the queue; whichever worker is free takes it.",
        fill=MUTED,
        font=F_NOTE,
    )

    out = OUT / "diagram-01-architecture.png"
    img.convert("RGB").save(out, "PNG", optimize=True)
    print(f"wrote {out}")


def generate_02():
    W, H = 1400, 900
    img = Image.new("RGBA", (W, H), BG + (255,))
    draw = ImageDraw.Draw(img)

    y1 = 60
    b1 = Box(60, y1, 280, 90, "Payload arrives", "partner key validated", BLUE_F, BLUE_B)
    b2 = Box(420, y1, 280, 90, "Stored as received", "kept unchanged", BLUE_F, BLUE_B)
    b3 = Box(780, y1, 280, 90, "Split into records", "one per person or entry", BLUE_F, BLUE_B)

    pool = Box(200, 220, 1000, 140, "", "", TAN_F, TAN_B)

    y3 = 430
    push = Box(60, y3, 300, 100, "Push worker", "takes the next batch of waiting records", ORANGE_F, ORANGE_B)
    signed = Box(460, y3, 300, 100, "Signed for delivery", "connector key applied", ORANGE_F, ORANGE_B)
    registry = Box(860, y3, 320, 100, "OpenG2P Registry", "Partner API · key validated", GREEN_F, GREEN_B)

    y4 = 640
    outcome = Box(520, y4, 340, 90, "Outcome recorded", "against every record in the batch", BLUE_F, BLUE_B)
    dlq = Box(60, y4, 320, 90, "Dead letter queue", "held for review and replay", RED_F, RED_B)

    for b in (b1, b2, b3, pool, push, signed, registry, outcome, dlq):
        draw_box(img, draw, b)

    draw.text(
        (pool.cx, pool.y + 16),
        "records waiting in the connector database",
        fill=MUTED,
        font=F_SUB,
        anchor="mt",
    )
    chip_w, chip_h, gap = 110, 36, 24
    chips = 5
    total = chips * chip_w + (chips - 1) * gap
    sx = pool.cx - total // 2
    cy = pool.y + 78
    for i in range(chips):
        x = sx + i * (chip_w + gap)
        chip = Box(x, cy - chip_h // 2, chip_w, chip_h, "record", "", ORANGE_F, ORANGE_B)
        shadow(img, chip, r=10, off=2)
        round_rect(draw, (chip.x, chip.y, chip.right, chip.bottom), 10, chip.fill, chip.border, 2)
        draw.text((chip.cx, chip.cy), "record", fill=INK, font=F_SUB, anchor="mm")

    wire(draw, [(b1.right, b1.cy), (b2.left, b2.cy)], head=(b2.left, b1.cy, "right"))
    wire(draw, [(b2.right, b2.cy), (b3.left, b3.cy)], head=(b3.left, b2.cy, "right"))
    wire(draw, [(b3.cx, b3.bottom), (b3.cx, pool.top)], head=(b3.cx, pool.top, "down"))
    wire(draw, [(pool.cx, pool.bottom), (pool.cx, signed.top)], head=(pool.cx, signed.top, "down"))
    wire(draw, [(push.right, push.cy), (signed.left, signed.cy)], head=(signed.left, push.cy, "right"))
    mid = (signed.right + registry.left) // 2
    wire(
        draw,
        [(signed.right, signed.cy), (registry.left, registry.cy)],
        head=(registry.left, signed.cy, "right"),
        label="one call per batch",
        label_at=(mid, signed.cy - 16),
    )
    drop_x = registry.cx
    wire(
        draw,
        [(drop_x, registry.bottom), (drop_x, outcome.cy), (outcome.right, outcome.cy)],
        head=(outcome.right, outcome.cy, "left"),
        label="response",
        label_at=(drop_x + 48, (registry.bottom + outcome.cy) // 2),
    )
    wire(
        draw,
        [(outcome.left, outcome.cy), (dlq.right, dlq.cy)],
        head=(dlq.right, dlq.cy, "left"),
        label="after repeated failure",
        label_at=((outcome.left + dlq.right) // 2, outcome.cy - 16),
    )

    out = OUT / "diagram-02-processing.png"
    img.convert("RGB").save(out, "PNG", optimize=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    generate_01()
    generate_02()
