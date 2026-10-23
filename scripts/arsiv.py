#!/usr/bin/env python3
# PersonaStudio — Copyright (c) 2026 yusufsametkarlidag. PolyForm Noncommercial 1.0.0 lisanslidir.
"""
Internet Archive'dan kamu mali arsiv goruntusu bulur, indirir ve sahneye kesip koyar.

Pexels/Pixabay'in bulamadigi ANI ve HIKAYE sahneleri icin: 1940-1980 arasi gercek
ciftlik, mutfak, kiler, atolye goruntuleri. API anahtari gerekmez.

Yalnizca kamu mali / CC0 koleksiyonlardan arar (prelinger ve benzeri), boylece
telif riski olmaz. Sonuclar tam film oldugu icin akis su sekilde:

    1) ara      -> aday filmleri listeler
    2) getir    -> secilen filmi bir kez _stok_kutuphane/ icine indirir
    3) kontak   -> filmden kare tablosu uretir (hangi saniye ne gosteriyor)
    4) kes      -> secilen saniyeden sahne suresi kadar kesip stok/SXXX.mp4 yapar

Kullanim:
    python3 arsiv.py ara "root cellar potatoes"
    python3 arsiv.py getir <identifier>
    python3 arsiv.py kontak <identifier> [--adim 20]
    python3 arsiv.py kes <identifier> <vid_klasoru> <SAHNE_ID> <baslangic_sn>
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
import settings  # noqa: E402

SEARCH = "https://archive.org/advancedsearch.php"
META = "https://archive.org/metadata/"
DL = "https://archive.org/download/"

# Yalnizca yeniden kullanimi serbest koleksiyonlar. Yeni koleksiyon eklemeden once
# o koleksiyonun lisansini DOGRULA; buraya sadece kamu mali / CC0 olanlar girer.
GUVENLI_KOLEKSIYONLAR = ("prelinger", "prelingerhomemovies", "academic_films")
# Kabul edilen licenseurl parcalari (kamu mali ya da CC0).
GUVENLI_LISANS = ("publicdomain", "zero/1.0", "/mark/1.0")

VIDEO_FORMATLARI = ("512kb mpeg4", "h.264", "mpeg4")
UA = {"User-Agent": "PersonaStudio/1.0 (kisisel arsiv aramasi)"}


def _json(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def kutuphane() -> Path:
    """Indirilen filmlerin paylasilan deposu (kanal klasorunun yaninda)."""
    cfg = settings.load()
    ana = Path(cfg.get("ana_klasor", "~/Desktop")).expanduser()
    d = ana / "_arsiv_kutuphane"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ara(sorgu: str, sayi: int = 12):
    koll = " OR ".join(f"collection:{c}" for c in GUVENLI_KOLEKSIYONLAR)
    q = f"({koll}) AND mediatype:movies AND ({sorgu})"
    url = (f"{SEARCH}?q={urllib.parse.quote(q)}"
           "&fl%5B%5D=identifier&fl%5B%5D=title&fl%5B%5D=year&fl%5B%5D=licenseurl"
           f"&rows={sayi}&page=1&output=json")
    docs = _json(url)["response"]["docs"]
    out = []
    for d in docs:
        lis = (d.get("licenseurl") or "").lower()
        if lis and not any(g in lis for g in GUVENLI_LISANS):
            continue  # lisansi belirsizse atla
        out.append({"id": d["identifier"], "baslik": d.get("title", ""),
                    "yil": d.get("year", ""), "lisans": lis or "koleksiyon geregi kamu mali"})
    return out


def _dosya_sec(identifier: str):
    d = _json(META + identifier)
    en_iyi = None
    for f in d.get("files", []):
        fmt = (f.get("format") or "").lower()
        if fmt in VIDEO_FORMATLARI and f.get("name", "").lower().endswith((".mp4", ".m4v")):
            boyut = int(f.get("size") or 0)
            # 512kb surumu tercih et: yeterince iyi, cok daha kucuk
            oncelik = 0 if fmt == "512kb mpeg4" else 1
            aday = (oncelik, boyut, f["name"], float(f.get("length") or 0))
            if en_iyi is None or aday[:2] < en_iyi[:2]:
                en_iyi = aday
    if not en_iyi:
        raise SystemExit(f"{identifier}: indirilebilir mp4 bulunamadi")
    return en_iyi[2], en_iyi[3]


def getir(identifier: str) -> Path:
    hedef = kutuphane() / f"{identifier}.mp4"
    if hedef.exists():
        print(f"zaten var: {hedef}")
        return hedef
    ad, sure = _dosya_sec(identifier)
    url = DL + identifier + "/" + urllib.parse.quote(ad)
    print(f"indiriliyor: {identifier} ({sure/60:.1f} dk) …")
    gecici = hedef.with_suffix(".indiriliyor")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=300) as r, open(gecici, "wb") as o:
        while True:
            parca = r.read(1 << 20)
            if not parca:
                break
            o.write(parca)
    gecici.rename(hedef)
    print(f"tamam: {hedef} ({hedef.stat().st_size/1e6:.0f} MB)")
    return hedef


def _ffmpeg():
    for c in ("/opt/homebrew/bin/ffmpeg", "ffmpeg"):
        if subprocess.run(["which", c], capture_output=True).returncode == 0 or Path(c).exists():
            return c
    raise SystemExit("ffmpeg bulunamadi")


KONTAK_SUTUN, KONTAK_SATIR = 6, 8


def kontak(identifier: str, adim: int = 20, sayfa: int = 1) -> Path:
    """Filmden her <adim> saniyede bir kare alip kontak tablosu uretir.

    drawtext filtresi her ffmpeg derlemesinde yok; o yuzden zaman damgasi kareye
    basilmaz. Kareler soldan saga, yukaridan asagiya sirayla dizilir ve i. karenin
    zamani  (sayfa-1)*SUTUN*SATIR*adim + i*adim  saniyedir. Fonksiyon bu esleme
    icin bir cetvel yazdirir.
    """
    kaynak = kutuphane() / f"{identifier}.mp4"
    if not kaynak.exists():
        kaynak = getir(identifier)
    kare = KONTAK_SUTUN * KONTAK_SATIR
    atla = (sayfa - 1) * kare * adim
    cik = kutuphane() / f"{identifier}_kontak{sayfa}.jpg"
    ff = _ffmpeg()
    subprocess.run([ff, "-y", "-v", "error", "-ss", str(atla), "-i", str(kaynak),
                    "-vf", f"fps=1/{adim},scale=320:-1,"
                           f"tile={KONTAK_SUTUN}x{KONTAK_SATIR}:margin=4:padding=4",
                    "-frames:v", "1", str(cik)], check=True)
    print(f"kontak: {cik}")
    print(f"  sayfa {sayfa}, {KONTAK_SUTUN}x{KONTAK_SATIR}, kareler {adim} sn arayla, "
          f"{atla} sn'den basliyor")
    for satir in range(KONTAK_SATIR):
        t0 = atla + satir * KONTAK_SUTUN * adim
        damga = [f"{(t0 + s*adim)//60:d}:{(t0 + s*adim)%60:02d}" for s in range(KONTAK_SUTUN)]
        print(f"  {satir+1}. satir: " + "  ".join(damga))
    return cik


def kes(identifier: str, vid: Path, sahne_id: str, baslangic: float):
    """Sahne suresini plan.json'dan okur, o kadarini kesip stok/SXXX.mp4 yapar."""
    plan = json.loads((vid / "plan.json").read_text(encoding="utf-8"))["plan"]
    s = next((x for x in plan if x["id"].upper() == sahne_id.upper()), None)
    if s is None:
        raise SystemExit(f"{sahne_id} plan.json'da yok")
    sure = round(s["end"] - s["start"], 3)
    kaynak = kutuphane() / f"{identifier}.mp4"
    if not kaynak.exists():
        kaynak = getir(identifier)
    (vid / "stok").mkdir(exist_ok=True)
    hedef = vid / "stok" / f"{sahne_id.upper()}.mp4"
    ff = _ffmpeg()
    subprocess.run([ff, "-y", "-v", "error", "-ss", str(baslangic), "-i", str(kaynak),
                    "-t", str(sure + 0.5), "-an",
                    "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,"
                           "crop=1920:1080,setsar=1",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                    "-movflags", "+faststart", str(hedef)], check=True)
    # plan'daki tipi STOK'a cek (GORSEL'den donuyorsa)
    if s["type"] != "STOK":
        tam = json.loads((vid / "plan.json").read_text(encoding="utf-8"))
        for x in tam["plan"]:
            if x["id"] == s["id"]:
                x["type"] = "STOK"
        (vid / "plan.json").write_text(json.dumps(tam, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  plan: {s['id']} {s['type']} -> STOK")
    print(f"kesildi: {hedef} ({sure:.2f} sn, kaynak {baslangic:.0f}. sn)")
    print(f"  kaynak: archive.org/details/{identifier} (kamu mali)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="komut", required=True)

    a = sub.add_parser("ara"); a.add_argument("sorgu"); a.add_argument("--sayi", type=int, default=12)
    g = sub.add_parser("getir"); g.add_argument("identifier")
    k = sub.add_parser("kontak"); k.add_argument("identifier")
    k.add_argument("--adim", type=int, default=20); k.add_argument("--sayfa", type=int, default=1)
    c = sub.add_parser("kes")
    c.add_argument("identifier"); c.add_argument("vid"); c.add_argument("sahne"); c.add_argument("baslangic", type=float)

    args = ap.parse_args()
    if args.komut == "ara":
        for r in ara(args.sorgu, args.sayi):
            print(f"{r['id']:<34} {r['yil'] or '----'}  {r['baslik'][:60]}")
    elif args.komut == "getir":
        getir(args.identifier)
    elif args.komut == "kontak":
        kontak(args.identifier, args.adim, args.sayfa)
    else:
        kes(args.identifier, Path(args.vid).expanduser(), args.sahne, args.baslangic)


if __name__ == "__main__":
    main()
