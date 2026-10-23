#!/usr/bin/env python3
# PersonaStudio — Copyright (c) 2026 yusufsametkarlidag. PolyForm Noncommercial 1.0.0 lisanslıdır: ticari kullanım yasaktır. Ayrıntı: LICENSE.md
"""
HeyGen avatar.mp4 -> zaman damgali SAHNE LISTESI.

1) Sesi whisper ile kelime kelime cozer (avatar/kelimeler.json, bir kez).
2) Kelimeleri cumlelere, cumleleri 2-8 sn'lik sahnelere boler.
3) Avatar anlarini rakip analizindeki duzene gore secer:
     - acilis (~ilk 12-16 sn) avatar
     - hikaye bolumu (sure %7'sine kadar, en az 45 sn) avatarsiz
     - %58'e kadar her ~25-40 sn'de bir 4-12 sn'lik kisa avatar,
       tercihen izleyiciye dogrudan konusulan cumlelerde
     - kalan kisim avatarsiz (B-roll ile hizlanan final)
4) sahneler.json + SAHNE_LISTESI.txt yazar (claude.ai'ye yapistirilacak).

Kullanim:
  python3 sahne.py <vid_klasoru>
"""
import json
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
import captions  # noqa: E402
from platform_tools import ffmpeg_bin, ffprobe_bin  # noqa: E402
import subprocess  # noqa: E402

MIN_SHOT = 2.0
MAX_SHOT = 7.5
TARGET_SPLIT = 4.5

HOOK_MIN = 12.0
HOOK_MAX = 18.0
STORY_END_RATIO = 0.07
STORY_END_MIN = 45.0
INSERT_END_RATIO = 0.58
INSERT_GAPS = [26, 22, 32, 24, 29, 21, 34, 27]   # avatar girisleri arasi hedef aralik (sn), dongusel
INSERT_MIN, INSERT_MAX = 5.0, 12.0
SEARCH_WINDOW = 12.0

# izleyiciye dogrudan konusma / gecis isaretleri -> avatar icin uygun
DIRECT_RE = re.compile(
    r"\b(you|your|you're|you'll|i|i'm|i've|i'd|me|my|here's|here is|listen|honest|honestly|"
    r"failure|mistake|piece|now|but|so|remember|trust|promise|tell)\b", re.I)
# somut nesne/islem/tarih anlatimi -> B-roll icin daha uygun
VISUAL_RE = re.compile(r"\b(\d{4}|soil|seed|seeds|water|leaf|leaves|row|rows|jar|jars|pot|pots|"
                       r"plant|plants|roots|compost|bucket|spade|hoe|tomato|tomatoes|frost|rain)\b", re.I)


def fmt(t: float) -> str:
    m = int(t // 60)
    return f"{m}:{t - 60 * m:04.1f}"


def media_duration(path: Path) -> float:
    r = subprocess.run([ffprobe_bin(), "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


# ------------------------------------------------------------ transkript
def transcribe(vid_dir: Path, model="small.en", log=print):
    avatar = vid_dir / "avatar" / "avatar.mp4"
    out = vid_dir / "avatar" / "kelimeler.json"
    if out.exists() and out.stat().st_mtime > avatar.stat().st_mtime:
        return json.loads(out.read_text(encoding="utf-8"))
    work = vid_dir / "work_sahne"
    work.mkdir(exist_ok=True)
    dur = media_duration(avatar)
    log(f"Ses çözülüyor (whisper {model}, {fmt(dur)})… birkaç dakika sürebilir.")
    wav = work / "ses.wav"
    captions.extract_audio_wav(avatar, wav, 0.0, dur, ffmpeg_bin())
    model_path = captions.ensure_model(model, log=log)
    words = captions.transcribe_words(wav, model_path, "en", work)
    words = [{"t": w["text"], "s": w["start_ms"] / 1000, "e": w["end_ms"] / 1000} for w in words]
    data = {"duration": dur, "words": words}
    out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    import shutil
    shutil.rmtree(work, ignore_errors=True)
    return data


# ------------------------------------------------------------ bolme
def sentences(words):
    out, cur = [], []
    for w in words:
        cur.append(w)
        if re.search(r"[.!?][\"')]*$", w["t"]):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def split_sentence(ws):
    """Uzun cumleyi virgul/kelime sinirindan ~TARGET_SPLIT sn'lik parcalara boler."""
    dur = ws[-1]["e"] - ws[0]["s"]
    if dur <= MAX_SHOT or len(ws) < 4:
        return [ws]
    n = max(2, round(dur / TARGET_SPLIT))
    parts, start = [], 0
    for k in range(1, n):
        target_t = ws[0]["s"] + dur * k / n
        best, best_score = None, None
        for i in range(start + 2, len(ws) - 1):
            score = abs(ws[i]["s"] - target_t) - (1.2 if ws[i - 1]["t"].endswith((",", ";", ":", "—")) else 0)
            if best_score is None or score < best_score:
                best, best_score = i, score
        if best is None:
            break
        parts.append(ws[start:best])
        start = best
    parts.append(ws[start:])
    return [p for p in parts if p]


def build_shots(data):
    words = data["words"]
    total = data["duration"]
    raw = []
    for s in sentences(words):
        raw.extend(split_sentence(s))
    # surekli zaman cizgisi: her sahne bir sonrakinin ilk kelimesine kadar surer
    shots = []
    for i, ws in enumerate(raw):
        start = 0.0 if i == 0 else ws[0]["s"]
        end = raw[i + 1][0]["s"] if i + 1 < len(raw) else total
        shots.append({"start": start, "end": end, "text": " ".join(w["t"] for w in ws).strip(),
                      "sentence_end": bool(re.search(r"[.!?][\"')]*$", ws[-1]["t"]))})
    # cok kisa sahneleri sonrakiyle birlestir
    merged = []
    for sh in shots:
        if merged and (merged[-1]["end"] - merged[-1]["start"]) < MIN_SHOT:
            m = merged[-1]
            m["end"] = sh["end"]
            m["text"] += " " + sh["text"]
            m["sentence_end"] = sh["sentence_end"]
        else:
            merged.append(dict(sh))
    if len(merged) > 1 and merged[-1]["end"] - merged[-1]["start"] < MIN_SHOT:
        last = merged.pop()
        merged[-1]["end"] = last["end"]
        merged[-1]["text"] += " " + last["text"]
    return merged


# ------------------------------------------------------------ avatar secimi
def _dur(sh):
    return sh["end"] - sh["start"]


def _direct_score(sh):
    return len(DIRECT_RE.findall(sh["text"])) - 0.7 * len(VISUAL_RE.findall(sh["text"]))


def assign_avatar(shots, total):
    for sh in shots:
        sh["type"] = "?"
    # 1) acilis
    acc = 0.0
    for sh in shots:
        sh["type"] = "AVATAR"
        acc = sh["end"]
        if acc >= HOOK_MIN and (sh["sentence_end"] or acc >= HOOK_MAX):
            break
    story_end = max(STORY_END_MIN, total * STORY_END_RATIO)
    insert_end = total * INSERT_END_RATIO

    # 2) ara girisler
    k = 0
    target = story_end
    while target < insert_end:
        cands = [i for i, sh in enumerate(shots)
                 if abs(sh["start"] - target) <= SEARCH_WINDOW and sh["start"] >= story_end
                 and sh["end"] <= insert_end and shots[i]["type"] == "?"
                 and (i == 0 or (shots[i - 1]["type"] == "?" and shots[i - 1]["sentence_end"]))]
        if not cands:
            target += 5
            continue
        best = max(cands, key=lambda i: (_direct_score(shots[i]), -abs(shots[i]["start"] - target)))
        group = [best]
        # cumle sonuna kadar ve en az INSERT_MIN sn olacak sekilde uzat (INSERT_MAX'i gecmeden)
        while group[-1] + 1 < len(shots):
            span = shots[group[-1]]["end"] - shots[best]["start"]
            if span >= INSERT_MIN and shots[group[-1]]["sentence_end"]:
                break
            nxt = group[-1] + 1
            if shots[nxt]["end"] - shots[best]["start"] > INSERT_MAX:
                break
            group.append(nxt)
        for i in group:
            shots[i]["type"] = "AVATAR"
        target = shots[group[-1]]["end"] + INSERT_GAPS[k % len(INSERT_GAPS)]
        k += 1
    return shots


# ------------------------------------------------------------ cikti
def build(vid_dir: Path, log=print):
    vid_dir = Path(vid_dir)
    data = transcribe(vid_dir, log=log)
    shots = assign_avatar(build_shots(data), data["duration"])
    for i, sh in enumerate(shots, 1):
        sh["id"] = f"S{i:03d}"
    (vid_dir / "sahneler.json").write_text(
        json.dumps({"duration": data["duration"], "shots": shots}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    lines = ["SAHNE LİSTESİ"]
    for sh in shots:
        lines.append(f"{sh['id']} | {fmt(sh['start'])}-{fmt(sh['end'])} | {sh['type']} | {sh['text']}")
    txt = "\n".join(lines) + "\n"
    (vid_dir / "SAHNE_LISTESI.txt").write_text(txt, encoding="utf-8")

    av = sum(_dur(s) for s in shots if s["type"] == "AVATAR")
    blocks = sum(1 for i, s in enumerate(shots)
                 if s["type"] == "AVATAR" and (i == 0 or shots[i - 1]["type"] != "AVATAR"))
    broll = [s for s in shots if s["type"] != "AVATAR"]
    log(f"{len(shots)} sahne · süre {fmt(data['duration'])} · avatar {blocks} giriş, {av:.0f} sn "
        f"(%{100 * av / data['duration']:.0f}) · B-roll {len(broll)} sahne, "
        f"ort. {sum(map(_dur, broll)) / max(1, len(broll)):.1f} sn")
    return txt


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    build(Path(sys.argv[1]))
