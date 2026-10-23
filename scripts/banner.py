#!/usr/bin/env python3
# PersonaStudio — Copyright (c) 2026 yusufsametkarlidag. PolyForm Noncommercial 1.0.0 lisanslıdır.
"""
YouTube kanal banner'i (2560x1440) ve logo (800x800) ureticisi.

YouTube banner'i uc farkli alanda kirpar:
  - TV            : 2560 x 1440  (tamami)
  - Masaustu      : 2560 x 423   (yatay serit)
  - Telefon/HEPSI : 1546 x 423   (ORTADA — butun yazilar buraya sigmali)
Bu script butun metni ve logoyu "guvenli alan" dedigimiz orta 1546x423'e yerlestirir.

Kullanim (ornek en altta):
  banner(bg="...jpg", portre="...jpg", baslik_beyaz="THE", baslik_vurgu="THIRD TEAM", ...)
"""
import pathlib
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

W, H = 2560, 1440
GUVENLI_W, GUVENLI_H = 1546, 423
GX = (W - GUVENLI_W) // 2          # 507
GY = (H - GUVENLI_H) // 2          # 508
IMPACT = "/System/Library/Fonts/Supplemental/Impact.ttf"
ARIAL_B = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
SARI = (255, 214, 10)
KIRMIZI = (214, 40, 40)
BEYAZ = (255, 255, 255)
SIYAH = (0, 0, 0)


def _fit(im, w, h):
    """Kirpmadan doldur (cover)."""
    o = im.width / im.height
    if o > w / h:
        yeni = (int(h * o), h)
    else:
        yeni = (w, int(w / o))
    im = im.resize(yeni, Image.LANCZOS)
    return im.crop(((im.width - w) // 2, (im.height - h) // 2,
                    (im.width - w) // 2 + w, (im.height - h) // 2 + h))


def _kart(d, x, y, w, h, renk, aci, golge=True):
    """Egik duran bir oyun karti cizer."""
    kat = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    kd = ImageDraw.Draw(kat)
    kd.rounded_rectangle([20, 20, 20 + w, 20 + h], radius=int(w * 0.08), fill=renk + (255,))
    kat = kat.rotate(aci, resample=Image.BICUBIC, expand=True)
    if golge:
        g = Image.new("RGBA", kat.size, (0, 0, 0, 0))
        g.paste((0, 0, 0, 150), (0, 0), kat.split()[3])
        g = g.filter(ImageFilter.GaussianBlur(14))
        d._image.paste(g, (x + 8, y + 10), g)
    d._image.paste(kat, (x, y), kat)


def banner(bg, portre, baslik_beyaz, baslik_vurgu, serit, alt_bilgi, cikti,
           vurgu=SARI, kart_motifi=True):
    bgim = _fit(Image.open(bg).convert("RGB"), W, H)
    bgim = bgim.filter(ImageFilter.GaussianBlur(9))
    bgim = ImageEnhance.Brightness(bgim).enhance(0.42)
    bgim = ImageEnhance.Color(bgim).enhance(0.55)

    # ustten ve alttan karartma + ortaya dogru hafif acilma (metin okunurlugu)
    kat = Image.new("L", (1, H))
    for y in range(H):
        d = abs(y - H / 2) / (H / 2)
        kat.putpixel((0, y), int(215 * (d ** 1.4)))
    kat = kat.resize((W, H))
    bgim = Image.composite(Image.new("RGB", (W, H), (8, 10, 9)), bgim, kat)

    im = bgim.convert("RGB")
    d = ImageDraw.Draw(im)
    d._image = im

    # --- portre karti (guvenli alanin solu)
    pz = 330
    px, py = GX + 26, GY + (GUVENLI_H - pz) // 2
    p = Image.open(portre).convert("RGB")
    k = min(p.width, p.height)
    p = p.crop(((p.width - k) // 2, max(0, int(p.height * 0.03)),
                (p.width - k) // 2 + k, max(0, int(p.height * 0.03)) + k))
    p = p.resize((pz, pz), Image.LANCZOS)
    maske = Image.new("L", (pz, pz), 0)
    ImageDraw.Draw(maske).rounded_rectangle([0, 0, pz, pz], radius=34, fill=255)
    d.rounded_rectangle([px - 5, py - 5, px + pz + 5, py + pz + 5], radius=39, fill=vurgu)
    im.paste(p, (px, py), maske)

    # --- metin blogu
    tx = px + pz + 56
    f_bas = ImageFont.truetype(IMPACT, 128)
    f_serit = ImageFont.truetype(IMPACT, 54)
    f_alt = ImageFont.truetype(ARIAL_B, 42)

    by = GY + 44
    w1 = d.textlength(baslik_beyaz + " ", font=f_bas)
    for dx, dy in [(-4, 0), (4, 0), (0, -4), (0, 4), (-3, -3), (3, 3), (-3, 3), (3, -3)]:
        d.text((tx + dx, by + dy), baslik_beyaz, font=f_bas, fill=SIYAH)
        d.text((tx + w1 + dx, by + dy), baslik_vurgu, font=f_bas, fill=SIYAH)
    d.text((tx, by), baslik_beyaz, font=f_bas, fill=BEYAZ)
    d.text((tx + w1, by), baslik_vurgu, font=f_bas, fill=vurgu)

    # siyah seritte alt baslik
    sy = by + 150
    sw = d.textlength(serit, font=f_serit)
    d.rectangle([tx - 14, sy - 10, tx + sw + 18, sy + 70], fill=SIYAH)
    d.text((tx, sy), serit, font=f_serit, fill=vurgu)

    # tebesir cizgisi (saha cizgisi motifi)
    cy = sy + 96
    d.rectangle([tx, cy, tx + 430, cy + 4], fill=(235, 235, 235))

    # alt bilgi
    d.text((tx, cy + 24), alt_bilgi, font=f_alt, fill=(232, 232, 232))

    # --- sari + kirmizi kart motifi (guvenli alanin sag ucu)
    if kart_motifi:
        kw, kh = 128, 184
        kx = GX + GUVENLI_W - 250
        ky = GY + (GUVENLI_H - kh) // 2 - 10
        _kart(d, kx, ky + 16, kw, kh, KIRMIZI, -14)
        _kart(d, kx + 58, ky, kw, kh, SARI, 9)

    pathlib.Path(cikti).parent.mkdir(parents=True, exist_ok=True)
    im.save(cikti, quality=95)
    return cikti


def logo(portre, cikti, halka=SARI, boyut=800):
    p = Image.open(portre).convert("RGB")
    k = int(min(p.width, p.height) * 0.72)
    cx = p.width // 2
    cy = int(p.height * 0.40)
    p = p.crop((cx - k // 2, max(0, cy - k // 2), cx + k // 2, max(0, cy - k // 2) + k))
    p = p.resize((boyut, boyut), Image.LANCZOS)
    im = Image.new("RGB", (boyut, boyut), (12, 14, 13))
    maske = Image.new("L", (boyut, boyut), 0)
    kalin = int(boyut * 0.035)
    ImageDraw.Draw(maske).ellipse([kalin, kalin, boyut - kalin, boyut - kalin], fill=255)
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, boyut, boyut], fill=halka)
    im.paste(p, (0, 0), maske)
    pathlib.Path(cikti).parent.mkdir(parents=True, exist_ok=True)
    im.save(cikti, quality=95)
    return cikti


# ----------------------------------------------------------------- saha stili
def _aralikli_yaz(d, xy, metin, font, fill, aralik=0):
    x, y = xy
    for ch in metin:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + aralik
    return x


def _aralikli_genislik(d, metin, font, aralik=0):
    return sum(d.textlength(c, font=font) + aralik for c in metin) - aralik


def banner_saha(baslik_beyaz, baslik_vurgu, ustyazi, alt_bilgi, cikti,
                portre=None, vurgu=SARI, baslik_px=150):
    """Futbol sahasi grafigi + buyuk tipografi. Blok guvenli alana ortalanir."""
    im = Image.new("RGB", (W, H), (10, 20, 14))
    d = ImageDraw.Draw(im, "RGBA")
    d._image = im

    for i in range(0, W, 170):
        if (i // 170) % 2 == 0:
            d.rectangle([i, 0, i + 170, H], fill=(13, 27, 18))

    kat = Image.new("L", (1, H))
    for y in range(H):
        t = abs(y - H / 2) / (H / 2)
        kat.putpixel((0, y), int(200 * (t ** 1.5)))
    im.paste(Image.composite(Image.new("RGB", (W, H), (4, 8, 6)), im, kat.resize((W, H))))

    CZ = (255, 255, 255, 58)
    kal = 7
    d.ellipse([-430, H // 2 - 430, 430, H // 2 + 430], outline=CZ, width=kal)
    d.line([(0, H - 250), (W, H - 250)], fill=CZ, width=kal)
    d.line([(W - 520, 0), (W - 520, H)], fill=CZ, width=kal)
    d.arc([W - 760, H // 2 - 240, W - 280, H // 2 + 240], 300, 60, fill=CZ, width=kal)
    d.ellipse([W - 528, H // 2 - 9, W - 510, H // 2 + 9], fill=(255, 255, 255, 80))

    f_ust = ImageFont.truetype(ARIAL_B, 38)
    f_bas = ImageFont.truetype(IMPACT, baslik_px)
    f_alt = ImageFont.truetype(ARIAL_B, 38)

    kw, kh = 118, 170
    kart_w = 52 + kw
    bosluk = 104
    w_ust = _aralikli_genislik(d, ustyazi, f_ust, 5)
    w_bas = d.textlength(baslik_beyaz, font=f_bas) + d.textlength(baslik_vurgu, font=f_bas)
    w_alt = d.textlength(alt_bilgi, font=f_alt)
    w_metin = max(w_ust, w_bas, w_alt)
    pz = 300
    blok = kart_w + bosluk + w_metin + ((56 + pz) if portre else 0)
    x = GX + max(10, int((GUVENLI_W - blok) / 2))

    ky = GY + (GUVENLI_H - kh) // 2
    _kart(d, x, ky + 14, kw, kh, KIRMIZI, -13)
    _kart(d, x + 52, ky, kw, kh, SARI, 8)
    tx = x + kart_w + bosluk

    uy = GY + 36
    _aralikli_yaz(d, (tx, uy), ustyazi, f_ust, vurgu, aralik=5)

    by = uy + 62
    w1 = d.textlength(baslik_beyaz, font=f_bas)
    for dx, dy in [(-5, 0), (5, 0), (0, -5), (0, 5), (-4, -4), (4, 4), (-4, 4), (4, -4)]:
        d.text((tx + dx, by + dy), baslik_beyaz, font=f_bas, fill=SIYAH)
        d.text((tx + w1 + dx, by + dy), baslik_vurgu, font=f_bas, fill=SIYAH)
    d.text((tx, by), baslik_beyaz, font=f_bas, fill=BEYAZ)
    d.text((tx + w1, by), baslik_vurgu, font=f_bas, fill=vurgu)

    cy = by + int(baslik_px * 1.15)
    d.rectangle([tx, cy, tx + min(w_bas, 540), cy + 4], fill=(240, 240, 240, 200))
    d.text((tx, cy + 22), alt_bilgi, font=f_alt, fill=(222, 226, 223))

    if portre:
        px = tx + int(w_metin) + 56
        py = GY + (GUVENLI_H - pz) // 2
        pim = Image.open(portre).convert("RGB")
        k = int(min(pim.width, pim.height) * 0.78)
        cx, cyy = pim.width // 2, int(pim.height * 0.38)
        pim = pim.crop((cx - k // 2, max(0, cyy - k // 2), cx + k // 2, max(0, cyy - k // 2) + k))
        pim = pim.resize((pz, pz), Image.LANCZOS)
        m = Image.new("L", (pz, pz), 0)
        ImageDraw.Draw(m).ellipse([0, 0, pz, pz], fill=255)
        d.ellipse([px - 6, py - 6, px + pz + 6, py + pz + 6], fill=vurgu)
        im.paste(pim, (px, py), m)

    pathlib.Path(cikti).parent.mkdir(parents=True, exist_ok=True)
    im.save(cikti, quality=95)
    return cikti
