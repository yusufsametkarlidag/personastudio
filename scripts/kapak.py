#!/usr/bin/env python3
# PersonaStudio — Copyright (c) 2026 yusufsametkarlidag. PolyForm Noncommercial 1.0.0 lisanslıdır: ticari kullanım yasaktır. Ayrıntı: LICENSE.md
"""
Sabit kapak (thumbnail) sablonu: Flow'da uretilen taban gorsel + PAKET.md'deki
YAZI_1 / YAZI_2 -> kapak/kapak.jpg (1280x720, <2 MB).

Yerlesim (B stili, her videoda ayni; kullanici 2026-10-04 secti):
  - Persona sabit mekanda, anin icinde, solda/ortada; nesne sag on planda (taban gorsel promptu)
  - Sag ustte iri iki satir: YAZI_1'in ilk kelimesi beyaz, kalani sari (Futura Condensed ExtraBold)
  - Altinda siyah serit icinde sari YAZI_2 etiketi (kanal imzasi; PAKET.md'den okunur)
  - Blok hafif egik (4 derece) ve golgeli

Kullanim:
  python3 kapak.py <vid_klasoru> [taban_gorsel] [parlaklik]
      taban_gorsel yoksa kapak/ icindeki en yeni gorsel kullanilir.
      parlaklik varsayilan 1.0; karanlik taban gorseller icin 1.2-1.4 arasi verilebilir.
"""
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import settings  # noqa: E402

W, H = 1280, 720
FONT = "/System/Library/Fonts/Supplemental/Impact.ttf"
YELLOW = (255, 214, 10)
RED = (214, 40, 40)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

KART_KIRMIZI = (214, 28, 34)

# Kanal basina kapak stili. "varsayilan" JUNE ve HANK'in bugune kadarki gorunumu;
# degistirme, o iki kanalin kimligi buna bagli.
STILLER = {
    "varsayilan": {
        "vurgu": YELLOW,          # YAZI_1'in ikinci satiri
        "etiket_zemin": BLACK,    # YAZI_2 seridi
        "etiket_yazi": YELLOW,
        "egim": 4,                # blok donusu (derece)
        "yatiklik": 0.0,          # italik etkisi (shear)
        "doygunluk": 1.12,
        "alt_cizgi": None,        # yazinin altinda renkli kalin cizgi
        "koyultma": 150,          # sag ust karartma siddeti
    },
    # Hakem kanali: daha sert, daha hareketli. Sari yerine kart kirmizisi, italik blok,
    # ters yone egim (JUNE/HANK'ten ilk bakista ayrilsin), altta kalin kirmizi cizgi.
    "hakem": {
        "vurgu": KART_KIRMIZI,
        "etiket_zemin": KART_KIRMIZI,
        "etiket_yazi": WHITE,
        "egim": -3,
        "yatiklik": 0.16,
        "doygunluk": 0.98,
        "alt_cizgi": KART_KIRMIZI,
        "koyultma": 175,
    },
}

TEXT_LEFT = int(W * 0.40)     # yazi blogu bu x'ten saga
TEXT_RIGHT = int(W * 0.975)
TOP = 22


def read_texts(vid: Path):
    md = (vid / "PAKET.md").read_text(encoding="utf-8")
    y1 = re.search(r"^YAZI_1:\s*(.+)$", md, re.M)
    y2 = re.search(r"^YAZI_2:\s*(.+)$", md, re.M)
    if not (y1 and y2):
        raise ValueError("PAKET.md içinde YAZI_1 / YAZI_2 satırları bulunamadı.")
    clean = lambda s: re.sub(r"[<>*`]", "", s).strip().upper()
    return clean(y1.group(1)), clean(y2.group(1))


def cover(img: Image.Image) -> Image.Image:
    r = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))


def fit_font(text, max_w, max_size, min_size=50):
    size = max_size
    while size > min_size:
        f = ImageFont.truetype(FONT, size)
        if f.getlength(text) <= max_w:
            return f
        size -= 4
    return ImageFont.truetype(FONT, min_size)


def _wrap_two(text, max_w, size):
    """Tek satira sigmiyorsa iki satira bol."""
    f = ImageFont.truetype(FONT, size)
    if f.getlength(text) <= max_w or " " not in text:
        return [text]
    words = text.split()
    best = None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        m = max(f.getlength(a), f.getlength(b))
        if best is None or m < best[0]:
            best = (m, [a, b])
    return best[1]


def bezier(p0, p1, p2, n=40):
    pts = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        pts.append((x, y))
    return pts


def draw_arrow(d: ImageDraw.ImageDraw, start, ctrl, end, width=17, color=RED, head=(58, 36)):
    pts = bezier(start, ctrl, end)
    shaft = pts[:-5]
    d.line(shaft, fill=BLACK, width=width + 8, joint="curve")
    d.line(shaft, fill=color, width=width, joint="curve")
    # ok basi
    (x1, y1), (x2, y2) = pts[-6], pts[-1]
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    L, S = head
    tip = (x2, y2)
    left = (x2 - L * math.cos(ang) + S * math.sin(ang), y2 - L * math.sin(ang) - S * math.cos(ang))
    right = (x2 - L * math.cos(ang) - S * math.sin(ang), y2 - L * math.sin(ang) + S * math.cos(ang))
    d.polygon([tip, left, right], fill=color, outline=BLACK, width=4)


FUTURA = "/System/Library/Fonts/Supplemental/Futura.ttc"      # index 4: Condensed ExtraBold
AVENIR = "/System/Library/Fonts/Avenir Next Condensed.ttc"     # index 8: Heavy


def _font(path, size, index):
    return ImageFont.truetype(path, size, index=index)


def stil_sec(ad=None) -> dict:
    """Aktif kanalin kapak stili. ayarlar.json'da kanal altinda "kapak_stil": "hakem" gibi."""
    if ad is None:
        try:
            ad = settings.load().get("kapak_stil") or "varsayilan"
        except Exception:
            ad = "varsayilan"
    return STILLER.get(ad, STILLER["varsayilan"])


def compose(base_path: Path, y1: str, y2: str, out_path: Path, stil: dict = None, ayar: dict = None,
            parlaklik: float = 1.0):
    """Sag ustte iri iki satir (ilk kelime beyaz, kalani vurgu rengi), altinda etiket seridi,
    hafif egik ve golgeli. Persona solda/ortada, nesne sag onde. Renk/egim stile gore degisir."""
    s = stil or stil_sec()
    img = cover(Image.open(base_path).convert("RGB"))
    if parlaklik != 1.0:
        # taban gorsel cok karanlik geldiyse: once parlaklik, sonra hafif kontrast toparlama
        img = ImageEnhance.Brightness(img).enhance(parlaklik)
        img = ImageEnhance.Contrast(img).enhance(1.0 + (parlaklik - 1.0) * 0.35)
    img = ImageEnhance.Color(img).enhance(s["doygunluk"])

    # sag ust koseye hafif koyu gecis (okunurluk)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).ellipse((W * 0.5, -H * 0.6, W * 1.5, H * 0.7), fill=s["koyultma"])
    img = Image.composite(Image.new("RGB", (W, H), BLACK), img, mask.filter(ImageFilter.GaussianBlur(80)))

    words = y1.split()
    dx, dy, olcek = (ayar or {}).get("dx", 0), (ayar or {}).get("dy", 0), (ayar or {}).get("olcek", 1.0)
    line1, line2 = (words[0], " ".join(words[1:])) if len(words) > 1 else (y1, "")
    max_w = W * 0.38 * olcek
    size = int(150 * olcek)
    while size > 70:
        f = _font(FUTURA, size, 4)
        if max(f.getlength(line1), f.getlength(line2 or line1)) <= max_w:
            break
        size -= 6
    x0, y0 = W * 0.60 + dx, 10 + dy
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.text((x0, y0), line1, font=f, fill=WHITE, stroke_width=9, stroke_fill=BLACK)
    y = y0 + f.size * 0.92
    if line2:
        ld.text((x0, y), line2, font=f, fill=s["vurgu"], stroke_width=9, stroke_fill=BLACK)
        y += f.size * 1.03
    else:
        y += f.size * 0.11
    tsize = 44
    while tsize > 26:
        ft = _font(AVENIR, tsize, 8)
        if ft.getlength(y2) + 28 <= W - x0 - 20:
            break
        tsize -= 2
    ld.rectangle((x0, y, x0 + ft.getlength(y2) + 28, y + tsize * 1.32), fill=s["etiket_zemin"])
    ld.text((x0 + 14, y + tsize * 0.05), y2, font=ft, fill=s["etiket_yazi"])
    if s["alt_cizgi"]:
        kalin = max(8, int(f.size * 0.085))
        genis = max(f.getlength(line1), f.getlength(line2 or line1))
        cy = y + tsize * 1.32 + kalin * 1.4
        ld.rectangle((x0, cy, x0 + genis, cy + kalin), fill=s["alt_cizgi"])
    if s["yatiklik"]:
        # saga yatik (italik) etki: ust satirlar daha cok kayar
        k = s["yatiklik"]
        layer = layer.transform((W, H), Image.AFFINE, (1, k, -k * H * 0.35, 0, 1, 0),
                                resample=Image.BICUBIC)
    layer = layer.rotate(s["egim"], resample=Image.BICUBIC, center=(x0, 100))

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 170), mask=layer.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    out = img.convert("RGBA")
    out.alpha_composite(shadow, (8, 10))
    out.alpha_composite(layer)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.convert("RGB").save(out_path, "JPEG", quality=92, optimize=True)
    return out_path


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    vid = Path(sys.argv[1])
    if len(sys.argv) > 2:
        base = Path(sys.argv[2])
    else:
        cands = sorted([p for p in (vid / "kapak").glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
                        and p.name != "kapak.jpg"], key=lambda p: p.stat().st_mtime)
        if not cands:
            print("kapak/ klasöründe taban görsel yok.")
            sys.exit(1)
        base = cands[-1]
    parlaklik = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    y1, y2 = read_texts(vid)
    out = compose(base, y1, y2, vid / "kapak" / "kapak.jpg", parlaklik=parlaklik)
    print(f"Kapak: {out}")


if __name__ == "__main__":
    main()
