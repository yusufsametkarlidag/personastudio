#!/usr/bin/env python3
# PersonaStudio — Copyright (c) 2026 yusufsametkarlidag. PolyForm Noncommercial 1.0.0 lisanslıdır: ticari kullanım yasaktır. Ayrıntı: LICENSE.md
"""
plan.json'daki STOK sahneleri icin Pixabay ve/veya Pexels'ten video bulup indirir (stok/S012.mp4).

- Pixabay/Pexels lisansi: ucretsiz ticari kullanim, kaynak gosterme zorunlu degil.
- API anahtarlari ayarlar.json -> "pixabay_api_key" (pixabay.com/api/docs, uye olunca verilir)
  ve/veya "pexels_api_key". Ikisi de varsa her sorguda once Pixabay, sonra Pexels denenir.
- Ayni video bir videoda iki kez kullanilmaz; indirilenler ortak kutuphanede
  onbelleklenir (<ana_klasor>/_stok_kutuphane), tekrar indirilmez.
- Sorgu sonuc vermezse sorgu kisaltilarak tekrar denenir.
- Indirilen klibin sesi kaldirilir, 1080p'ye kucultulur (render zaten normalize eder).

Kullanim:
  python3 pexels.py <vid_klasoru> [--yeniden]
"""
import json
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
import settings  # noqa: E402
from platform_tools import ffmpeg_bin  # noqa: E402

API = "https://api.pexels.com/videos/search"
PIXABAY_API = "https://pixabay.com/api/videos/"
UA = "PersonaStudio/1.0"


def _get(url, key):
    req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def search(query, key, per_page=20):
    q = urllib.parse.urlencode({"query": query, "orientation": "landscape", "size": "medium",
                                "per_page": per_page})
    return _get(f"{API}?{q}", key).get("videos", [])


def pixabay_search(query, key, per_page=60):
    q = urllib.parse.urlencode({"key": key, "q": query, "per_page": per_page, "safesearch": "true"})
    req = urllib.request.Request(f"{PIXABAY_API}?{q}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        hits = json.loads(r.read().decode("utf-8")).get("hits", [])
    out = []
    for h in hits:
        vs = h.get("videos", {})
        pick = None
        for size in ("large", "medium"):
            f = vs.get(size) or {}
            if f.get("url") and f.get("width", 0) >= 1280 and f.get("width", 0) > f.get("height", 0):
                pick = f
                break
        if pick:
            out.append({"id": f"pixabay_{h['id']}", "duration": h.get("duration", 0), "link": pick["url"],
                        "url": h.get("pageURL"), "author": h.get("user"), "width": pick["width"],
                        "tags": h.get("tags", "")})
    out.sort(key=lambda c: abs(c["width"] - 1920) > 200)  # ~1080p olanlar once
    return out


def pexels_search(query, key):
    out = []
    for v in search(query, key):
        f = best_file(v)
        if f:
            slug = (v.get("url") or "").rstrip("/").split("/")[-1].replace("-", " ")
            out.append({"id": f"pexels_{v['id']}", "duration": v.get("duration", 0), "link": f["link"],
                        "url": v.get("url"), "author": (v.get("user") or {}).get("name"), "width": f["width"],
                        "tags": slug})
    return out


STOP = set("""a an the of in on at to into onto with without and or for from by over under near across
closeup close up macro wide shot medium slow motion pan push tilt view top aerial shallow depth field
detail details texture light lit morning afternoon evening golden hour warm soft natural scene background
small big large tiny thick thin old new one two three single few many some its their his her""".split())

# Stokta konuya uyan klip yoksa sahne en fazla bu kadar kez yedek gorsele (Flow) cevrilir
MAX_YEDEK_GORSEL = 40

# Uygun klip bulunamazsa kullanilacak genel B-roll sorgulari. Kanal profili: stok_yedek_sorgular
# Sorgu kelimesi -> stok sitesinde karsiligi olan varyantlar. Kanal profili: stok_sorgu_varyant
# ("pitch" Pixabay'de zift/perde getiriyor; futbol sahasi "soccer field" olarak etiketleniyor.)
QVAR = {}

FALLBACKS = ["autumn leaves falling", "fallen leaves ground", "garden soil hands", "raking leaves",
             "autumn garden", "vegetable garden", "compost", "autumn trees"]


# Kelime koklerini esitleyen sozluk. Kanal profili: stok_esanlam
SYN = {"leav": "leaf", "leave": "leaf", "tre": "tree", "flower": "flower", "mow": "mower", "gardening": "garden",
       "gardener": "garden", "rak": "rake", "composting": "compost", "soils": "soil", "dirt": "soil", "earth": "soil"}


def _stem(w):
    w = w.lower().strip(".,;:!?'\"()")
    for suf in ("ing", "es", "s"):
        if len(w) > 4 and w.endswith(suf):
            w = w[: -len(suf)]
            # "dripping" -> "dripp" -> "drip", "running" -> "runn" -> "run"
            if len(w) > 3 and w[-1] == w[-2] and w[-1] not in "aeiou":
                w = w[:-1]
            break
    # Sondaki "e" her kelimeden atilir ki tekil/cogul ayni koke insin:
    # "pipe"/"pipes" -> "pip", "hinge"/"hinges" -> "hing", "glove"/"gloves" -> "glov"
    if len(w) > 3 and w.endswith("e"):
        w = w[:-1]
    return SYN.get(w, w)


def content_words(q):
    return {_stem(w) for w in q.split() if _stem(w) and _stem(w) not in STOP and not w.isdigit()}


# Kanal konusu: klip etiketlerinde bunlardan en az biri olmali.
# Asagidakiler yalnizca varsayilandir; aktif kanalin profili (ayarlar.json -> kanallar.<ad>.stok_konu_kelimeleri)
# _load_domain() icinde bunlarin yerine gecer. Ayni sekilde BANNED/FALLBACKS/SYN de kanaldan gelir.
DOMAIN = set("""leaf autumn fall garden soil compost tree lawn grass rake mulch yard root worm earthworm frost
mower shovel spade hoe seed plant farm farmhouse barn field crop vegetable harvest wheelbarrow branch bark
bee insect butterfly bird cocoon moth flower oak maple forest wood wooden fence gate shed porch rural country
countryside meadow dirt ground pumpkin apple basket jar tool glove hand farming gardening winter snow train
calendar truck house""".split())
# Bu etiketlerden biri varsa klip kullanilmaz (konu disi / insan yuzu). Kanal profili: stok_yasak_kelimeler
BANNED = set("""beach sea ocean coast wave city street neon urban moon night space star galaxy universe tulip
cherry blossom bedroom bed money coin drone desert temple cartoon animation illustration abstract wallpaper
text portrait face man woman girl boy people person model fashion couple child baby smile selfie christmas
halloween fire flame cup coffee tea mug laptop computer swan duck castle palace monument landmark salad sushi
restaurant""".split())


def tag_set(tags):
    return {_stem(t) for t in tags.replace(",", " ").split()}


def tag_set_raw(tags):
    """Etiketler, kok alinmadan. Yasak listesi bununla karsilastirilir ki
    kok cakismasi ('game'->'gam'<-'gaming', 'training'->'train', 'winning'->'win'<-'wine')
    konuya tam uyan klipleri elemesin."""
    return {t.lower().strip(".,;:!?'\"()-") for t in tags.replace(",", " ").split()}


def acceptable(tags):
    ts = tag_set(tags)
    dom = {_stem(w) for w in DOMAIN}
    ban = {w.lower() for w in BANNED}
    return bool(ts & dom) and not (tag_set_raw(tags) & ban)


def relevance(query, tags):
    """Sorgunun icerik kelimelerinden kacinin klip etiketlerinde gectigi."""
    want = content_words(query)
    have = {_stem(t) for t in tags.replace(",", " ").split()}
    return len(want & have), len(want)


# Bir klibin kabul edilmesi icin sorgu kelimelerinin en az bu kadari etiketlerde gecmeli.
# Kisaltilmis (bozulmus) sorgularda ve genel yedek sorgularda cita daha yuksek tutulur.
MIN_ORAN = 0.5
MIN_ORAN_KISALTILMIS = 0.67
# Bu orani yakalayan klip hemen secilir; altindakiler "en iyi aday" olarak saklanip
# daha iyisi cikmazsa kullanilir. Boylece bozuk bir kisa sorgu, tam sorgunun onune gecemez.
IYI_ORAN = 0.8


def score(query, tags):
    """(oran, isabet) — oran 0-1 arasi; siralamada once oran, esitlikte isabet sayisi."""
    hit, want = relevance(query, tags)
    return (hit / want if want else 0.0), hit


def best_file(video):
    files = [f for f in video.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width")]
    hd = [f for f in files if 1280 <= f["width"] <= 2560 and f["width"] > f.get("height", 0)]
    pool = hd or files
    if not pool:
        return None
    return min(pool, key=lambda f: abs(f["width"] - 1920))


def _variants(q):
    """Sorgunun stok sitesi diline cevrilmis hallerini uretir."""
    words = q.lower().split()
    out = []
    for i, w in enumerate(words):
        for alt in _words(QVAR.get(w, [])):
            v = words[:i] + alt.split() + words[i + 1:]
            v = " ".join(dict.fromkeys(v))  # tekrar eden kelimeyi at
            if v != q and v not in out:
                out.append(v)
    return out


def _queries(q):
    words = q.split()
    yield q
    for v in _variants(q):
        yield v
    if len(words) > 3:
        yield " ".join(words[:3])
    if len(words) > 2:
        yield " ".join(words[-2:])


def _words(v):
    return v.split() if isinstance(v, str) else list(v)


def _load_domain():
    """Stok filtrelerini aktif kanalin profilinden yukler (ayarlar.json -> kanallar.<ad>)."""
    cfg = settings.load()
    for key, target in (("stok_konu_kelimeleri", DOMAIN), ("stok_yasak_kelimeler", BANNED)):
        v = cfg.get(key)
        if v:
            target.clear()
            target.update(_words(v))
    fb = cfg.get("stok_yedek_sorgular")
    if fb:
        FALLBACKS[:] = _words(fb)
    qv = cfg.get("stok_sorgu_varyant")
    QVAR.clear()
    if qv:
        QVAR.update(qv)
    syn = cfg.get("stok_esanlam")
    if syn:
        SYN.clear()
        SYN.update(syn)


def library_dir():
    d = settings.base_dir() / "_stok_kutuphane"
    d.mkdir(parents=True, exist_ok=True)
    return d


def fetch(vid: Path, redo=False, log=print):
    cfg = settings.load()
    _load_domain()
    providers = []
    if cfg.get("pixabay_api_key", "").strip():
        providers.append(("Pixabay", pixabay_search, cfg["pixabay_api_key"].strip()))
    if cfg.get("pexels_api_key", "").strip():
        providers.append(("Pexels", pexels_search, cfg["pexels_api_key"].strip()))
    if not providers:
        raise RuntimeError("Stok API anahtarı yok. pixabay.com/api/docs adresinden ücretsiz anahtar alıp "
                           "ayarlar.json → \"pixabay_api_key\" alanına yaz.")
    plan_path = vid / "plan.json"
    plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
    plan = plan_data["plan"]
    items = [p for p in plan if p["type"] == "STOK"]
    yedek_used = sum(1 for p in plan if p.get("stoktan_gorsele"))
    global MAX_YEDEK_GORSEL
    MAX_YEDEK_GORSEL = int(cfg.get("max_yedek_gorsel", MAX_YEDEK_GORSEL))
    to_image = []
    out_dir = vid / "stok"
    out_dir.mkdir(exist_ok=True)
    lib = library_dir()
    index_path = out_dir / "kaynaklar.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    used = {v["id"] for v in index.values() if "id" in v}
    failed = []
    for n, p in enumerate(items, 1):
        dest = out_dir / f"{p['id']}.mp4"
        if dest.exists() and not redo:
            continue
        need = p["end"] - p["start"] + 0.6
        chosen = None
        tam_sorgu = p["prompt"]
        queries = list(_queries(tam_sorgu))
        # (oran, isabet, klip, sorgu_etiketi, saglayici) — tum sorgular arasindaki en iyi aday
        en_iyi = None
        for q in queries + FALLBACKS:
            is_fb = q in FALLBACKS
            if is_fb and p.get("yedek") and yedek_used < MAX_YEDEK_GORSEL:
                break  # genel klibe dusmeden once yedek gorsele cevir
            if is_fb and en_iyi:
                break  # elde kabul edilebilir bir aday varken genel B-roll'a dusme
            if not is_fb and not content_words(q):
                continue
            # yalnizca KISALTILMIS sorgularda cita yukselir; varyant sorgu (ayni uzunluk) tam sorgu sayilir
            kisaltilmis = (not is_fb) and len(q.split()) < len(tam_sorgu.split())
            # Cita: tam sorgu < kisaltilmis sorgu < genel yedek sorgu
            esik = MIN_ORAN if not kisaltilmis else MIN_ORAN_KISALTILMIS
            if is_fb:
                esik = 1.0  # genel sorguda kelimelerin hepsi tutmali
            for pname, fn, key in providers:
                try:
                    cands = fn(q, key)
                except Exception as e:  # ag/limit hatasi
                    log(f"  {p['id']}: {pname} arama hatası ({e}); 20 sn bekleniyor…")
                    time.sleep(20)
                    try:
                        cands = fn(q, key)
                    except Exception:
                        cands = []
                for c in cands:
                    if c["id"] in used or c["duration"] < need or not acceptable(c.get("tags", "")):
                        continue
                    # Puan her zaman SAHNENIN kendi promptuna gore; kisa sorgu iyi klip getirse de
                    # klip asil cumleyi anlatmiyorsa secilmez.
                    oran, isabet = score(tam_sorgu, c.get("tags", ""))
                    if isabet < 1 or oran < esik:
                        continue
                    aday = (oran, isabet, c, q + (" (genel)" if is_fb else ""), pname)
                    if en_iyi is None or aday[:2] > en_iyi[:2]:
                        en_iyi = aday
                if en_iyi and en_iyi[0] >= IYI_ORAN:
                    break  # yeterince iyi; baska sorgu/saglayici deneme
            if en_iyi and en_iyi[0] >= IYI_ORAN:
                break
        if en_iyi:
            chosen = (en_iyi[2], en_iyi[3], en_iyi[4])
        if not chosen and p.get("yedek") and yedek_used < MAX_YEDEK_GORSEL:
            to_image.append(p)
            yedek_used += 1
            log(f"  [{n}/{len(items)}] {p['id']}: \"{p['prompt']}\" stokta yok → yedek GÖRSEL (Flow) 🖼")
            continue
        if not chosen:
            failed.append(p["id"])
            log(f"  [{n}/{len(items)}] {p['id']}: \"{p['prompt']}\" için uygun klip yok ❌")
            continue
        c, q, pname = chosen
        cached = lib / f"{c['id']}.mp4"
        if not cached.exists():
            tmp = cached.with_suffix(".part")
            req = urllib.request.Request(c["link"], headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as r, open(tmp, "wb") as fh:
                shutil.copyfileobj(r, fh)
            subprocess.run([ffmpeg_bin(), "-y", "-nostdin", "-v", "error", "-i", str(tmp), "-an",
                            "-vf", "scale='min(1920,iw)':-2", "-c:v", "libx264", "-crf", "18",
                            "-preset", "veryfast", "-movflags", "+faststart", str(cached)], check=True)
            tmp.unlink()
        shutil.copy2(cached, dest)
        used.add(c["id"])
        index[p["id"]] = {"id": c["id"], "url": c.get("url"), "query": q, "author": c.get("author"),
                          "duration": c["duration"], "tags": c.get("tags", "")}
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"  [{n}/{len(items)}] {p['id']}: \"{q}\" → {pname} ({c['duration']} sn) ✅")
    if to_image:
        for p in to_image:
            p.update(type="GORSEL", stok_sorgu=p["prompt"], prompt=p["yedek"], stoktan_gorsele=True)
            (out_dir / f"{p['id']}.mp4").unlink(missing_ok=True)
            index.pop(p["id"], None)
        plan_path.write_text(json.dumps(plan_data, ensure_ascii=False, indent=1), encoding="utf-8")
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"{len(to_image)} sahne yedek görsele çevrildi → Flow görsel mesajını yeniden kopyala.")
    log(f"Stok: {len(items) - len(failed) - len(to_image)}/{len(items)} hazır"
        + (f" · bulunamayan: {', '.join(failed)} (haritada bunları GORSEL yap ya da sorguyu değiştir)"
           if failed else ""))
    return failed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(1 if fetch(Path(sys.argv[1]), redo="--yeniden" in sys.argv) else 0)
