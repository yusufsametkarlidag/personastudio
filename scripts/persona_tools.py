#!/usr/bin/env python3
# PersonaStudio — Copyright (c) 2026 yusufsametkarlidag. PolyForm Noncommercial 1.0.0 lisanslıdır: ticari kullanım yasaktır. Ayrıntı: LICENSE.md
"""
Video klasoru islemleri: yeni vidN, PAKET kaydetme, HeyGen avatarini alma,
Flow indirilenlerini aktarma, Flow oto-devam betigi.

Komut satiri:
  python3 persona_tools.py yeni
  python3 persona_tools.py paket <vid>            (panodan)
  python3 persona_tools.py avatar <vid> [mp4]     (yoksa Indirilenler'deki en yeni mp4)
  python3 persona_tools.py flow-al <vid> [zip/dosya ...]
  python3 persona_tools.py oto gorsel|video
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import zipfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
import check_assets  # noqa: E402
import settings  # noqa: E402
from platform_tools import ffmpeg_bin  # noqa: E402

APP_DIR = SCRIPTS_DIR.parent
OTO_DEVAM_JS = APP_DIR / "flow" / "flow_oto_devam.js"
DOWNLOADS = Path.home() / "Downloads"
SUBDIRS = ["avatar", "stok", "gorseller", "videolar", "kapak", "output"]

OTO_CFG = {
    "gorsel": {
        "adKontrol": "^Görsel #\\d+",
        "devamMesaji": "Onaylıyorum, sıradaki partı oluştur. Her görselin adı listedeki numarayla "
                       "\"Görsel #numara\" olsun. Partı bitirince yine onayımı bekle.",
        "tekrarMesaji": "Bu partta başarısız olan görsel(ler) var. Başarısız olanları aynı numara ve aynı adla "
                        "(Görsel #numara) yeniden üret, sonra onayımı bekle.",
    },
    "video": {
        "devamMesaji": "Onaylıyorum, sıradaki adıma geç. Videolar sessiz ve 8 saniye olsun, adları "
                       "Vid<numara> — <başlık> şeklinde olsun. Bu adımı bitirince yine onayımı bekle.",
        "tekrarMesaji": "Bu adımda başarısız olan video var. Başarısız olanları aynı adla yeniden oluştur "
                        "(sessiz, Vid<numara> — <başlık>), sonra onayımı bekle.",
    },
}


def clipboard_get() -> str:
    return subprocess.run(["pbpaste"], capture_output=True, text=True).stdout


def clipboard_set(text: str):
    subprocess.run(["pbcopy"], input=text, text=True)


# ------------------------------------------------------------ klasorler
def vid_dirs():
    base = settings.base_dir()
    if not base.exists():
        return []
    ds = [p for p in base.iterdir() if p.is_dir() and re.fullmatch(r"vid\d+", p.name)]
    return sorted(ds, key=lambda p: int(p.name[3:]))


def new_vid() -> Path:
    base = settings.base_dir()
    base.mkdir(parents=True, exist_ok=True)
    nums = [int(p.name[3:]) for p in vid_dirs()]
    vid = base / f"vid{max(nums, default=0) + 1}"
    for s in SUBDIRS:
        (vid / s).mkdir(parents=True, exist_ok=True)
    return vid


# ------------------------------------------------------------ paket
def _section(md, name):
    m = re.search(rf"^## {name}\s*$(.*?)(?=^## |\Z)", md, re.M | re.S)
    return m.group(1).strip() if m else ""


# KAPAK alanlari ve "In this one" listesi tek satira yapismis olabilir: claude.ai artifact'i
# markdown'a cevirirken TEK satir sonlarini yutuyor (vid6'da goruldu). kapak.py "^YAZI_1:" /
# "^YAZI_2:" satirlarini aradigi icin bu sessizce kapagi bozuyordu. Kaydederken geri ayiriyoruz.
_KAPAK_ANAHTARLARI = ("YAZI_2:", "MIMIK:", "NESNE:", "GORSEL_PROMPT:")


def _satirlari_onar(text: str) -> str:
    for key in _KAPAK_ANAHTARLARI:
        text = re.sub(r"(?<!\n)[ \t]+" + re.escape(key), "\n" + key, text)

    def _bol(m):
        govde = re.sub(r"[ \t]+(\d+)[ \t]+—[ \t]+", lambda k: "\n" + k.group(1) + " — ", m.group(1))
        return "In this one:\n" + govde.lstrip("\n ")

    return re.sub(r"In this one:[ \t]*(.+?)(?=\n\n)", _bol, text, flags=re.S)


def save_package(vid: Path, text: str):
    if "## SCRIPT" not in text:
        raise ValueError("Panodaki metinde \"## SCRIPT\" bölümü yok — claude.ai'deki PAKET dosyasını kopyala.")
    text = _satirlari_onar(text)
    (vid / "PAKET.md").write_text(text.strip() + "\n", encoding="utf-8")
    script = _section(text, "SCRIPT")
    (vid / "SCRIPT.txt").write_text(script + "\n", encoding="utf-8")
    title = _section(text, "BAŞLIK").splitlines()[0].strip() if _section(text, "BAŞLIK") else ""
    words = len(script.split())
    return title, words


def package_field(vid: Path, key: str) -> str:
    md = (vid / "PAKET.md").read_text(encoding="utf-8")
    if key in ("SCRIPT", "AÇIKLAMA", "BAŞLIK", "ETİKETLER"):
        return _section(md, key)
    m = re.search(rf"^{key}:\s*(.+)$", md, re.M)
    return m.group(1).strip() if m else ""


def title(vid: Path) -> str:
    try:
        return package_field(vid, "BAŞLIK").splitlines()[0].strip()
    except Exception:
        return ""


# ------------------------------------------------------------ avatar
def recent_downloads(exts, since_seconds=8 * 3600):
    if not DOWNLOADS.exists():
        return []
    cutoff = time.time() - since_seconds
    fs = [p for p in DOWNLOADS.iterdir() if p.is_file() and p.suffix.lower() in exts
          and p.stat().st_mtime >= cutoff and not p.name.endswith(".crdownload")]
    return sorted(fs, key=lambda p: p.stat().st_mtime, reverse=True)


def import_avatar(vid: Path, src: Path = None):
    if src is None:
        cands = [p for p in recent_downloads({".mp4"}) if p.stat().st_size > 5_000_000]
        if not cands:
            raise FileNotFoundError("İndirilenler'de son 8 saatte HeyGen videosu (mp4) yok.")
        src = cands[0]
    dest = vid / "avatar" / "avatar.mp4"
    dest.parent.mkdir(exist_ok=True)
    shutil.move(str(src), dest)
    (vid / "avatar" / "kelimeler.json").unlink(missing_ok=True)
    return src.name, dest


# ------------------------------------------------------------ Flow indirilenleri
def _zip_name(info: zipfile.ZipInfo) -> str:
    name = info.filename
    if not info.flag_bits & 0x800:
        try:
            name = name.encode("cp437").decode("utf-8")
        except UnicodeError:
            pass
    return unicodedata.normalize("NFC", Path(name).name)


def import_flow(vid: Path, sources=None, log=print):
    exts = {".zip"} | check_assets.IMAGE_EXTS | check_assets.VIDEO_EXTS
    if not sources:
        sources = [p for p in recent_downloads(exts)
                   if p.suffix.lower() == ".zip" or re.match(r"(Görsel|Gorsel|Vid)", unicodedata.normalize("NFC", p.name))]
    added = {"gorsel": 0, "video": 0}
    with tempfile.TemporaryDirectory() as tmp:
        staged = []
        for src in sorted(map(Path, sources), key=lambda p: p.stat().st_mtime):
            if src.suffix.lower() == ".zip":
                with zipfile.ZipFile(src) as z:
                    for info in z.infolist():
                        if info.is_dir():
                            continue
                        out = Path(tmp) / f"{len(staged):05d}" / _zip_name(info)
                        out.parent.mkdir(parents=True)
                        out.write_bytes(z.read(info))
                        staged.append(out)
            else:
                staged.append(src)
        for f in staged:
            name = unicodedata.normalize("NFC", f.name)
            n = check_assets.file_number(Path(name))
            if n is None:
                continue
            if f.suffix.lower() in check_assets.IMAGE_EXTS and re.match(r"G(ö|o)rsel", name):
                dest_dir, kind = vid / "gorseller", "gorsel"
            elif f.suffix.lower() in check_assets.VIDEO_EXTS and name.startswith("Vid"):
                dest_dir, kind = vid / "videolar", "video"
            else:
                continue
            dest_dir.mkdir(exist_ok=True)
            for old in check_assets.list_media(dest_dir, check_assets.IMAGE_EXTS | check_assets.VIDEO_EXTS):
                if check_assets.file_number(old) == n and old.name != name:
                    old.unlink()
            dest = dest_dir / name
            if kind == "video":
                subprocess.run([ffmpeg_bin(), "-y", "-nostdin", "-v", "error", "-i", str(f), "-map", "0:v",
                                "-c:v", "copy", "-an", "-movflags", "+faststart", str(dest)], check=True)
            else:
                shutil.copy2(f, dest)
            added[kind] += 1
    log(f"Flow: {added['gorsel']} görsel, {added['video']} video aktarıldı.")
    return added


def indir_script() -> str:
    return (APP_DIR / "flow" / "flow_gorsel_indir.js").read_text(encoding="utf-8")


def oto_devam_script(kind: str, kredi_onayi_otomatik: bool = False) -> str:
    cfg = json.dumps({**OTO_CFG[kind], "krediOnayiOtomatik": kredi_onayi_otomatik}, ensure_ascii=False)
    return f"window.FLOW_OTO_CFG = {cfg};\n" + OTO_DEVAM_JS.read_text(encoding="utf-8")


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(2)
    if a[0] == "yeni":
        print(new_vid())
    elif a[0] == "paket":
        t, w = save_package(Path(a[1]), clipboard_get())
        print(f"PAKET kaydedildi: {t} ({w} kelime)")
    elif a[0] == "avatar":
        name, dest = import_avatar(Path(a[1]), Path(a[2]) if len(a) > 2 else None)
        print(f"{name} → {dest}")
    elif a[0] == "flow-al":
        import_flow(Path(a[1]), a[2:] or None)
    elif a[0] == "oto":
        print(oto_devam_script(a[1], a[1] == "video"))
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
