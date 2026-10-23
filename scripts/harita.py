#!/usr/bin/env python3
# PersonaStudio — Copyright (c) 2026 yusufsametkarlidag. PolyForm Noncommercial 1.0.0 lisanslıdır: ticari kullanım yasaktır. Ayrıntı: LICENSE.md
"""
claude.ai'nin SAHNE HARITASI cevabi -> plan.json, Flow mesajlari, edl.json.

Harita satiri:  S012 | 1:04.2-1:08.9 | STOK | hands pressing seeds || <yedek gorsel promptu>
                S013 | ...            | VEO  | <text-to-video prompt>
                S014 | ...            | VEO  | @S013        (S013'un 8 sn'lik klibinin devami)
                S015 | ...            | GORSEL | <gorsel promptu>
Zamanlar her zaman sahneler.json'dan alinir (Claude'un yazdigi zamanlar yok sayilir).

Dosya adlari:
  stok/S012.mp4                     (pexels.py indirir)
  videolar/Vid13 — ....mp4          (Flow, numara = sahne numarasi)
  gorseller/Görsel #15 ....jpg      (Flow, numara = sahne numarasi)

Kullanim:
  python3 harita.py kaydet <vid> [harita.txt]   (dosya yoksa panodan okur)
  python3 harita.py mesaj gorsel|video <vid>
  python3 harita.py edl <vid>
  python3 harita.py durum <vid>
"""
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
import check_assets  # noqa: E402

LINE_RE = re.compile(r"^\s*`?(S\d{3})\s*\|\s*[^|]*\|\s*(AVATAR|STOK|VEO|GORSEL|GÖRSEL)\s*(?:\|\s*(.*?))?\s*`?$",
                     re.I)
VEO_CLIP_LEN = 8.0
MAX_VEO = 12

GORSEL_INTRO = (
    "Aşağıdaki görsel promptlarını 10'arlı partlar halinde oluştur; her partı bitirince onayımı bekle. "
    "Her görsel 16:9, fotogerçekçi ve tamamen doğal olacak; üzerinde yazı/logo olmayacak. "
    "Her görselin adı MUTLAKA listedeki numarayla \"Görsel #numara\" olacak (ör. Görsel #17); "
    "numaralar ardışık değil, listedeki numarayı aynen kullan. Açıklayıcı başka bir ad verme."
)
VIDEO_INTRO = (
    "Aşağıdaki video promptlarının her birini doğrudan text-to-video olarak oluştur (önce görsel üretme). "
    "Her video 8 saniye, 16:9, tamamen sessiz (müzik/efekt/konuşma yok) ve fotogerçekçi olacak; "
    "tanınabilir yüz olmayacak. Videoların adı listedeki numarayla başlayacak: \"Vid<numara> — <kısa başlık>\" "
    "(ör. Vid23 — Seeds in soil). Hepsini bitirince onayımı bekle."
)


def num(sid: str) -> int:
    return int(sid[1:])


def load_shots(vid: Path):
    return json.loads((vid / "sahneler.json").read_text(encoding="utf-8"))


def parse(text: str):
    rows = {}
    for line in text.splitlines():
        m = LINE_RE.match(line)
        if not m:
            continue
        sid, typ, content = m.group(1).upper(), m.group(2).upper().replace("Ö", "O"), (m.group(3) or "").strip()
        rows[sid] = (typ, content.strip("` "))
    return rows


def build_plan(vid: Path, text: str):
    data = load_shots(vid)
    rows = parse(text)
    problems, plan = [], []
    veo_new = 0
    for sh in data["shots"]:
        sid = sh["id"]
        typ, content = rows.get(sid, (None, ""))
        if sh["type"] == "AVATAR":
            typ, content = "AVATAR", ""
        elif typ is None:
            problems.append(f"{sid}: haritada yok")
            continue
        elif typ == "AVATAR":
            problems.append(f"{sid}: avatar olmayan sahneye AVATAR yazılmış → GORSEL bekleniyordu")
            continue
        elif not content:
            problems.append(f"{sid}: {typ} içeriği boş")
            continue
        item = {"id": sid, "start": sh["start"], "end": sh["end"], "type": typ, "text": sh["text"]}
        if typ == "VEO" and content.startswith("@"):
            item["reuse"] = content[1:].upper()
        elif typ == "STOK" and "||" in content:
            q, yedek = content.split("||", 1)
            item["prompt"] = q.strip()
            item["yedek"] = yedek.strip()
        else:
            item["prompt"] = content
            if typ == "VEO":
                veo_new += 1
        plan.append(item)

    # VEO devam kliplerine kaynak icindeki baslangic noktasi ver
    by_id = {p["id"]: p for p in plan}
    used = {}
    for p in plan:
        if p["type"] != "VEO":
            continue
        root = p
        seen = set()
        while "reuse" in root and root["reuse"] not in seen:
            seen.add(root["reuse"])
            nxt = by_id.get(root["reuse"])
            if nxt is None or nxt["type"] != "VEO":
                problems.append(f"{p['id']}: @{root['reuse']} geçerli bir VEO sahnesi değil")
                break
            root = nxt
        p["clip"] = root["id"]
        p["source_in"] = round(used.get(root["id"], 0.0), 3)
        used[root["id"]] = used.get(root["id"], 0.0) + (p["end"] - p["start"])
        if used[root["id"]] > VEO_CLIP_LEN + 0.05:
            problems.append(f"{p['id']}: {root['id']} klibinden {used[root['id']]:.1f} sn kullanılıyor "
                            f"(klip {VEO_CLIP_LEN:.0f} sn) — son kare donar")
    stok_n = sum(1 for p in plan if p["type"] == "STOK")
    no_yedek = sum(1 for p in plan if p["type"] == "STOK" and not p.get("yedek"))
    if stok_n and no_yedek:
        problems.append(f"{no_yedek}/{stok_n} STOK satırında yedek görsel promptu (|| …) yok")
    if veo_new > MAX_VEO:
        problems.append(f"{veo_new} yeni VEO var (sınır {MAX_VEO}) — Flow kredisi")

    out = {"duration": data["duration"], "plan": plan}
    (vid / "plan.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (vid / "SAHNE_HARITASI.txt").write_text(text, encoding="utf-8")
    return out, problems


def summary(plan):
    c = {}
    for p in plan["plan"]:
        k = p["type"] + ("+" if p.get("reuse") else "")
        c[k] = c.get(k, 0) + 1
    return " · ".join(f"{k} {v}" for k, v in sorted(c.items()))


def load_plan(vid: Path):
    return json.loads((vid / "plan.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------ Flow mesajlari
def message(vid: Path, kind: str, only_missing=True) -> str:
    """Flow mesaji; only_missing=True ise sadece dosyasi henuz olmayanlar listelenir."""
    plan = load_plan(vid)["plan"]
    have_g = _by_number(vid / "gorseller", check_assets.IMAGE_EXTS) if only_missing else {}
    have_v = _by_number(vid / "videolar", check_assets.VIDEO_EXTS) if only_missing else {}
    if kind == "gorsel":
        items = [p for p in plan if p["type"] == "GORSEL" and num(p["id"]) not in have_g]
        body = "\n".join(f"- Görsel #{num(p['id'])}: {p['prompt']}" for p in items)
        return f"{GORSEL_INTRO}\n\nToplam {len(items)} görsel.\n\n{body}\n"
    items = [p for p in plan if p["type"] == "VEO" and "prompt" in p and num(p["id"]) not in have_v]
    body = "\n".join(f"- Vid{num(p['id'])}: {p['prompt']}" for p in items)
    return f"{VIDEO_INTRO}\n\nToplam {len(items)} video.\n\n{body}\n"


# ------------------------------------------------------------ dosya bulma / edl
def _by_number(folder: Path, exts):
    out = {}
    if folder.exists():
        for f in check_assets.list_media(folder, exts):
            n = check_assets.file_number(f)
            if n is not None:
                out[n] = f
    return out


def resolve(vid: Path):
    """plan + bulunan dosyalar -> (entries, eksikler)"""
    plan = load_plan(vid)
    stok = {f.stem.upper(): f for f in (vid / "stok").glob("S*.mp4")} if (vid / "stok").exists() else {}
    gors = _by_number(vid / "gorseller", check_assets.IMAGE_EXTS)
    vids = _by_number(vid / "videolar", check_assets.VIDEO_EXTS)
    entries, missing = [], []
    for row, p in enumerate(plan["plan"], 1):
        e = {"row": row, "clip_id": p["id"], "start": p["start"], "end": p["end"],
             "duration": round(p["end"] - p["start"], 3)}
        if p["type"] == "AVATAR":
            e.update(type="avatar", source_in=p["start"], source_out=p["end"])
        elif p["type"] == "STOK":
            f = stok.get(p["id"])
            e.update(type="stok", path=str(f.relative_to(vid)) if f else None)
        elif p["type"] == "VEO":
            f = vids.get(num(p["clip"]))
            e.update(type="veo", path=str(f.relative_to(vid)) if f else None, source_in=p["source_in"])
        else:
            f = gors.get(num(p["id"]))
            e.update(type="gorsel", path=str(f.relative_to(vid)) if f else None)
        if e["type"] != "avatar" and not e["path"]:
            missing.append(f"{p['id']} {p['type']}" + (f" (klip {p['clip']})" if p["type"] == "VEO" else ""))
        entries.append(e)
    return entries, missing


def write_edl(vid: Path, fallback=True):
    """Eksik STOK/VEO sahneleri varsa (fallback=True) en yakin onceki B-roll ile doldurur."""
    entries, missing = resolve(vid)
    if missing and fallback:
        last = None
        for e in entries:
            if e["type"] != "avatar" and e.get("path"):
                last = e
            elif e["type"] != "avatar" and last is not None:
                e.update(type=last["type"], path=last["path"], source_in=last.get("source_in", 0.0),
                         filled_from=last["clip_id"])
    elif missing:
        raise RuntimeError("Eksik dosyalar: " + ", ".join(missing))
    (vid / "edl.json").write_text(json.dumps({"entries": entries}, ensure_ascii=False, indent=1),
                                  encoding="utf-8")
    return entries, missing


def status(vid: Path) -> str:
    _, missing = resolve(vid)
    plan = load_plan(vid)
    s = summary(plan)
    if not missing:
        return f"✅ Tüm kaynaklar hazır ({s})."
    return f"Eksik {len(missing)}: " + ", ".join(missing[:15]) + (" …" if len(missing) > 15 else "") + f"\n({s})"


def clipboard() -> str:
    return subprocess.run(["pbpaste"], capture_output=True, text=True).stdout


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(2)
    if a[0] == "kaydet":
        vid = Path(a[1])
        text = Path(a[2]).read_text(encoding="utf-8") if len(a) > 2 else clipboard()
        plan, problems = build_plan(vid, text)
        print(f"{len(plan['plan'])} sahne planlandı: {summary(plan)}")
        for p in problems:
            print("⚠️ ", p)
        sys.exit(1 if any("haritada yok" in p or "boş" in p for p in problems) else 0)
    elif a[0] == "mesaj":
        print(message(Path(a[2]), a[1]))
    elif a[0] == "edl":
        entries, missing = write_edl(Path(a[1]))
        print(f"edl.json: {len(entries)} sahne" + (f" · {len(missing)} eksik önceki sahneyle dolduruldu"
                                                   if missing else ""))
    elif a[0] == "durum":
        print(status(Path(a[1])))
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
