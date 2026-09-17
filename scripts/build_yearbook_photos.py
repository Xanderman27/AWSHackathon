"""Turn the twelve source portraits into a matching set of school yearbook photos.

The source photos are twelve unrelated stock pictures: different backgrounds, different
crops, different light. Side by side in a class list they read as a scrapbook. A yearbook
page reads as one set because three things are held constant — the backdrop, the framing
and the grade — so that is what this does, leaving the children themselves alone.

    source: data/faces-src/student-NN.jpg   (originals, never modified)
    output: apps/web/public/faces/student-NN.jpg

Each child is segmented out of their original background (rembg / u2netp) and placed on a
graduated studio backdrop. Cutting the subject out rather than vignetting over them is what
makes the framing possible at all: the sources are already tight 400x400 crops, so there is
no room to zoom out for head-and-shoulders framing, but once the background is synthetic the
empty space can simply be backdrop instead of invented pixels.

Framing comes from a face box per learner. Haar detection finds most of them and is wrong
about the rest, so the numbers are committed here rather than detected at build time: a
table someone can correct by looking at the output beats a detector that silently moves a
child's head. Boxes are (x, y, w, h) in the 400x400 source.

Needs pillow, rembg and onnxruntime (opencv-python-headless too, but only for --detect,
which proposes boxes when a photo is swapped). The u2netp model downloads once on first run.

    python scripts/build_yearbook_photos.py            # build all twelve
    python scripts/build_yearbook_photos.py --detect   # propose face boxes
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "faces-src"
OUT = ROOT / "apps" / "web" / "public" / "faces"

SIZE = 512                 # square; the app masks it to a circle in most places
HEAD_HEIGHT = 0.54         # head height as a share of the frame — the yearbook constant
HEAD_TOP = 0.13            # where the top of the hair sits
HAIR_ABOVE = 0.30          # hair above the face box, as a share of the box
HEAD_DEPTH = 1.55          # full head height (hair to chin) as a share of the face box

# (x, y, w, h) of the face in the source image. Detected with --detect where the detector
# found a face, measured off the silhouette by hand where it did not (05, 07, 12).
FACES: dict[str, tuple[int, int, int, int]] = {
    "student-01": (324, 199, 189, 189),
    "student-02": (374, 211, 303, 303),
    "student-03": (265, 250, 502, 502),
    "student-04": (90, 447, 397, 397),
    "student-05": (407, 451, 163, 163),
    "student-06": (269, 410, 359, 359),
    "student-07": (223, 95, 148, 148),
    "student-08": (154, 247, 520, 520),
    "student-09": (318, 232, 261, 261),
    "student-10": (328, 209, 211, 211),
    "student-11": (380, 109, 137, 137),
    "student-12": (392, 153, 231, 231),
}

# The classic photographer's mottled muslin: a cool mid-grey, lit brighter behind the head
# and falling away at the corners. Grey rather than a colour on purpose — it is what a school
# photographer actually hangs, and it stays out of the way of the mastery-band colours that
# sit beside these faces in the class list.
BACKDROP_CENTRE = (156, 159, 164)
BACKDROP_EDGE = (88, 93, 101)
MOTTLE = 26            # how far the cloudy texture swings either side of the base tone
MOTTLE_SEED = 7        # fixed, so a rebuild produces the identical backdrop


def backdrop(size: int) -> Image.Image:
    """Mottled studio muslin: a radial falloff with cloud texture painted over it.

    A perfectly smooth gradient reads as a computer background. Real muslin is blotchy, and
    that blotchiness is most of what makes a school photo look like a school photo, so the
    falloff is modulated by blurred value noise rather than left clean.
    """
    small = 64
    grad = Image.new("RGB", (small, small))
    pixels = grad.load()
    cx, cy = small / 2, small * 0.40
    longest = ((small / 2) ** 2 + (small * 0.60) ** 2) ** 0.5
    for y in range(small):
        for x in range(small):
            t = min(1.0, (((x - cx) ** 2 + (y - cy) ** 2) ** 0.5) / longest) ** 1.2
            pixels[x, y] = tuple(round(a + (b - a) * t) for a, b in zip(BACKDROP_CENTRE, BACKDROP_EDGE))
    card = grad.resize((size, size), Image.LANCZOS).filter(ImageFilter.GaussianBlur(size / 80))

    # Two octaves of blurred noise: broad clouds plus a finer grain over the top.
    rng = random.Random(MOTTLE_SEED)
    clouds = Image.new("L", (size, size), 128)
    for cells, weight in ((7, 1.0), (19, 0.5)):
        noise = Image.new("L", (cells, cells))
        noise.putdata([rng.randrange(256) for _ in range(cells * cells)])
        noise = noise.resize((size, size), Image.BICUBIC).filter(ImageFilter.GaussianBlur(size / 26))
        clouds = Image.blend(clouds, noise, weight / 2)

    shade = clouds.point(lambda v: 128 + round((v - 128) * (MOTTLE / 128)))
    return Image.blend(card, Image.composite(
        ImageEnhance.Brightness(card).enhance(1.18),
        ImageEnhance.Brightness(card).enhance(0.84), shade), 0.85)


def cutout(path: Path) -> Image.Image:
    """The child, with their original background removed."""
    from rembg import new_session, remove

    global _SESSION
    try:
        session = _SESSION
    except NameError:
        session = _SESSION = new_session("u2netp")
    cut = remove(Image.open(path).convert("RGB"), session=session)
    # Soften the mask edge by a hair. A segmentation edge is pixel-sharp and reads as a
    # sticker against a smooth backdrop; one pixel of feather reads as depth of field.
    r, g, b, a = cut.split()
    return Image.merge("RGBA", (r, g, b, a.filter(ImageFilter.GaussianBlur(0.8))))


def place(cut: Image.Image, face: tuple[int, int, int, int]) -> Image.Image:
    """Scale and position so every head is the same size at the same height in the frame."""
    fx, fy, fw, fh = face
    scale = (HEAD_HEIGHT * SIZE) / (fh * HEAD_DEPTH)
    scaled = cut.resize((round(cut.width * scale), round(cut.height * scale)), Image.LANCZOS)

    # Line the top of the hair up with HEAD_TOP, and the face's centre line with the middle.
    head_top = (fy - fh * HAIR_ABOVE) * scale
    face_centre = (fx + fw / 2) * scale
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    canvas.paste(scaled, (round(SIZE / 2 - face_centre), round(HEAD_TOP * SIZE - head_top)), scaled)
    return canvas


def grade(rgba: Image.Image) -> Image.Image:
    """One light grade for all twelve, so they look lit by the same lamp."""
    rgb = rgba.convert("RGB")
    rgb = ImageEnhance.Color(rgb).enhance(0.88)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.05)
    rgb = ImageEnhance.Brightness(rgb).enhance(1.03)
    return Image.merge("RGBA", (*rgb.split(), rgba.split()[-1]))


def build(name: str, face: tuple[int, int, int, int]) -> None:
    subject = grade(place(cutout(SRC / f"{name}.jpg"), face))
    card = backdrop(SIZE)

    # A soft shadow cast down and to the right, so the child sits in the scene rather than
    # on it. Offset and blur are both large: studio key light is close and diffuse.
    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    shadow.paste((18, 24, 33, 105), (0, 0, SIZE, SIZE), subject.split()[-1])
    shadow = shadow.filter(ImageFilter.GaussianBlur(SIZE * 0.045))
    offset = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    offset.paste(shadow, (round(SIZE * 0.022), round(SIZE * 0.028)), shadow)

    card = Image.alpha_composite(card.convert("RGBA"), offset)
    card = Image.alpha_composite(card, subject).convert("RGB")

    # A gentle corner vignette, the last thing every school photo has in common.
    vignette = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(vignette).ellipse(
        [-SIZE * 0.16, -SIZE * 0.16, SIZE * 1.16, SIZE * 1.16], fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(SIZE * 0.10))
    card = Image.composite(card, ImageEnhance.Brightness(card).enhance(0.72), vignette)

    card.save(OUT / f"{name}.jpg", quality=88, optimize=True, progressive=True)


def detect() -> None:
    """Propose face boxes for the table above. Only run when a photo is swapped."""
    import cv2

    finder = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    for path in sorted(SRC.glob("student-*.jpg")):
        grey = cv2.equalizeHist(cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2GRAY))
        found = finder.detectMultiScale(grey, 1.08, 4, minSize=(30, 30))
        best = max(found.tolist(), key=lambda f: f[2]) if len(found) else None
        print(f'    "{path.stem}": {tuple(best) if best else "NOT FOUND — set by hand"},')


def main() -> None:
    if "--detect" in sys.argv:
        detect()
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for name, face in sorted(FACES.items()):
        build(name, face)
        print(f"{name}  ok")


if __name__ == "__main__":
    main()
