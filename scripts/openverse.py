#!/usr/bin/env python3
"""
Openverse'ten SAHNE HARİTASI'na göre telifsiz (CC0 / kamu malı) görsel indirir.

Neden Openverse: API anahtarı istemiyor ve yalnızca `license=cc0,pdm` ile
sorgulandığında dönen görseller ATIF GEREKTİRMİYOR. CC-BY'ler bilerek dışarıda
bırakılıyor; video açıklamasına kaynak listesi koymak zorunda kalmayalım diye.

Kullanım:
  python3 openverse.py <vid_klasoru>            # haritadaki OPENVERSE sahnelerini indir
  python3 openverse.py <vid_klasoru> --yeniden  # var olanları da yeniden indir
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.openverse.org/v1/images/"
UA = {"User-Agent": "PersonaStudio/1.0 (kisisel gorsel aramasi)"}
LISANS = "cc0,pdm"           # yalnizca atif gerektirmeyenler
EN_AZ_GENISLIK = 1280
ISTEK_ARASI = 0.35


def log(*a):
    print(*a, flush=True)


def _json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def ara(sorgu, sayi=20):
    q = urllib.parse.urlencode({"q": sorgu, "page_size": sayi, "license": LISANS})
    try:
        return _json(f"{API}?{q}").get("results", [])
    except Exception as e:
        log(f"    ! arama hatasi: {str(e)[:60]}")
        return []


def _puan(r, sorgu):
    """Genislik, yatay olma ve baslik/etiket eslesmesine gore basit puan."""
    w = r.get("width") or 0
    h = r.get("height") or 1
    if w < EN_AZ_GENISLIK:
        return -1
    p = 0.0
    p += min(w / 1920.0, 2.0)                      # cozunurluk
    if w > h:
        p += 1.5                                   # yatay tercih
        if 1.5 <= w / h <= 2.0:
            p += 0.7                               # 16:9'a yakin
    metin = " ".join(filter(None, [
        (r.get("title") or "").lower(),
        " ".join(t.get("name", "") for t in (r.get("tags") or [])).lower(),
    ]))
    kelimeler = [w2 for w2 in re.findall(r"[a-z]+", sorgu.lower()) if len(w2) > 2]
    if kelimeler:
        p += 2.0 * sum(1 for k in kelimeler if k in metin) / len(kelimeler)
    return p


def en_iyi(sonuclar, sorgu):
    puanli = [(_puan(r, sorgu), r) for r in sonuclar]
    puanli = [(p, r) for p, r in puanli if p > 0]
    if not puanli:
        return None
    puanli.sort(key=lambda x: -x[0])
    return puanli[0][1]


def indir(url, hedef: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=40) as r:
            veri = r.read()
        if len(veri) < 20_000:
            return False
        hedef.write_bytes(veri)
        return True
    except Exception as e:
        log(f"    ! indirme hatasi: {str(e)[:60]}")
        return False


def harita_oku(vid: Path):
    """SAHNE_HARITASI.txt -> [(sahne_id, sorgu), ...] yalnizca OPENVERSE satirlari."""
    yol = vid / "SAHNE_HARITASI.txt"
    if not yol.exists():
        raise SystemExit(f"{yol} yok. Once sahne haritasini uret.")
    cikti = []
    for satir in yol.read_text(encoding="utf-8").splitlines():
        parcalar = [p.strip() for p in satir.split("|")]
        if len(parcalar) >= 5 and parcalar[3] == "OPENVERSE":
            cikti.append((parcalar[0], parcalar[4]))
    return cikti


def main(vid: Path, yeniden=False):
    hedef_dir = vid / "gorseller"
    hedef_dir.mkdir(parents=True, exist_ok=True)
    isler = harita_oku(vid)
    log(f"{len(isler)} OPENVERSE sahnesi · lisans: {LISANS} (atif gerektirmez)")

    olan = eksik = 0
    kaynaklar = []
    for i, (sid, sorgu) in enumerate(isler, 1):
        hedef = hedef_dir / f"{sid}.jpg"
        if hedef.exists() and not yeniden:
            olan += 1
            continue
        sonuclar = ara(sorgu)
        time.sleep(ISTEK_ARASI)
        secim = en_iyi(sonuclar, sorgu)
        if not secim:
            log(f"  [{i}/{len(isler)}] {sid}: \"{sorgu}\" → uygun görsel yok")
            eksik += 1
            continue
        url = secim.get("url") or secim.get("thumbnail")
        if url and indir(url, hedef):
            olan += 1
            kaynaklar.append({"sahne": sid, "sorgu": sorgu,
                              "baslik": secim.get("title"), "lisans": secim.get("license"),
                              "kaynak": secim.get("foreign_landing_url")})
            log(f"  [{i}/{len(isler)}] {sid}: {(secim.get('title') or '')[:46]} "
                f"[{secim.get('license')}] {secim.get('width')}x{secim.get('height')}")
        else:
            eksik += 1
            log(f"  [{i}/{len(isler)}] {sid}: indirilemedi")

    if kaynaklar:
        (vid / "gorsel_kaynaklari.json").write_text(
            json.dumps(kaynaklar, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"\nbitti · indirilen/var olan: {olan} · eksik: {eksik}")
    log(f"eksik kalanlar Flow görseliyle doldurulacak.")
    return eksik


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(Path(sys.argv[1]).expanduser(), "--yeniden" in sys.argv)
