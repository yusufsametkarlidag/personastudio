#!/usr/bin/env python3
# PersonaStudio — Copyright (c) 2026 yusufsametkarlidag. PolyForm Noncommercial 1.0.0 lisanslıdır: ticari kullanım yasaktır. Ayrıntı: LICENSE.md
"""
PersonaStudio — persona kanalı (avatar + cümle senkron B-roll) üretim arayüzü.

Akış (her adım bir düğme):
  1 Paket      claude.ai'den PAKET → PAKET.md / SCRIPT.txt; script'i HeyGen için kopyala
  2 Avatar     HeyGen videosunu İndirilenler'den al → avatar/avatar.mp4
  3 Sahneler   whisper ile zaman damgalı sahne listesi → panoya (claude.ai'ye yapıştır)
  4 Harita     claude.ai'nin SAHNE HARİTASI cevabını panodan kaydet
  5 Kaynaklar  Pexels stokları indir · Flow mesajları/oto-devam · Flow indirilenlerini al
  6 Render     test (ilk 90 sn) / tam render → output/<başlık>.mp4
  7 Kapak      kapak promptunu kopyala · taban görseli seç → kapak/kapak.jpg
"""
import io
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
import harita  # noqa: E402
import kapak  # noqa: E402
import persona_tools as pt  # noqa: E402
import pexels  # noqa: E402
import render as render_mod  # noqa: E402
import sahne  # noqa: E402
import settings  # noqa: E402

MONO = ("Menlo", 11)


class _Writer(io.TextIOBase):
    def __init__(self, q):
        self.q = q

    def write(self, s):
        if s:
            self.q.put(s)
        return len(s)


def safe_name(s: str) -> str:
    s = re.sub(r'[\\/:*?"<>|]', "", s).strip()
    return s[:120] or "video"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = settings.load()
        self.title(f"PersonaStudio — {self.cfg['kanal']}")
        self.geometry("980x760")
        self.q = queue.Queue()
        self.busy = False
        self._build()
        self.refresh_vids()
        self.after(100, self._pump)

    # ------------------------------------------------------------ arayuz
    def _build(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        kanallar = settings.kanal_listesi()
        if len(kanallar) > 1:
            ttk.Label(top, text="Kanal:").pack(side="left")
            self.kanal_var = tk.StringVar(value=self.cfg.get("aktif_kanal", kanallar[0]))
            self.kanal_box = ttk.Combobox(top, textvariable=self.kanal_var, width=8,
                                          state="readonly", values=kanallar)
            self.kanal_box.pack(side="left", padx=(4, 12))
            self.kanal_box.bind("<<ComboboxSelected>>", lambda e: self.switch_channel())
        ttk.Label(top, text="Video:").pack(side="left")
        self.vid_var = tk.StringVar()
        self.vid_box = ttk.Combobox(top, textvariable=self.vid_var, width=14, state="readonly")
        self.vid_box.pack(side="left", padx=4)
        self.vid_box.bind("<<ComboboxSelected>>", lambda e: self.show_status())
        ttk.Button(top, text="Yeni video", command=self.new_vid).pack(side="left", padx=2)
        ttk.Button(top, text="Klasörü aç", command=lambda: self._open(self.vid())).pack(side="left", padx=2)
        ttk.Button(top, text="claude.ai projesi", command=self.open_claude).pack(side="left", padx=2)
        ttk.Button(top, text="Durum", command=self.show_status).pack(side="left", padx=2)
        self.title_lbl = ttk.Label(top, text="", foreground="#555")
        self.title_lbl.pack(side="left", padx=10)

        body = ttk.Frame(self, padding=(8, 0))
        body.pack(fill="x")
        steps = [
            ("1 · Paket (claude.ai)", [
                ("Paketi panodan kaydet", self.save_package),
                ("Script'i kopyala (HeyGen)", lambda: self.copy_field("SCRIPT")),
                ("Başlık + açıklamayı kopyala", self.copy_upload_text),
            ]),
            ("2 · Avatar (HeyGen)", [
                ("İndirilenler'den avatarı al", self.import_avatar),
                ("Avatar dosyası seç…", self.pick_avatar),
            ]),
            ("3 · Sahne listesi", [
                ("Sahne listesi oluştur + kopyala", self.build_scenes),
            ]),
            ("4 · Sahne haritası", [
                ("Haritayı panodan kaydet", self.save_map),
            ]),
            ("5 · Kaynaklar", [
                ("Stokları indir (Pixabay/Pexels)", self.fetch_stock),
                ("Flow görsel mesajı", lambda: self.copy_msg("gorsel")),
                ("Flow video mesajı", lambda: self.copy_msg("video")),
                ("Oto-devam (görsel)", lambda: self.copy_oto("gorsel")),
                ("Oto-devam (video)", lambda: self.copy_oto("video")),
                ("Flow görsel indirme betiği", self.copy_dl_script),
                ("Flow indirilenlerini al", self.import_flow),
            ]),
            ("6 · Render", [
                ("Test render (ilk 90 sn)", lambda: self.do_render(test=True)),
                ("Tam render", lambda: self.do_render(test=False)),
            ]),
            ("7 · Kapak", [
                ("Kapak görsel promptunu kopyala", lambda: self.copy_field("GORSEL_PROMPT")),
                ("Taban görsel seç → kapak", self.make_thumb),
            ]),
        ]
        for r, (name, buttons) in enumerate(steps):
            f = ttk.LabelFrame(body, text=name, padding=6)
            f.grid(row=r // 2, column=r % 2, sticky="nsew", padx=4, pady=4)
            for i, (label, cmd) in enumerate(buttons):
                ttk.Button(f, text=label, command=cmd).grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2)
            f.columnconfigure(0, weight=1)
            f.columnconfigure(1, weight=1)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        self.prog = ttk.Progressbar(self, mode="determinate")
        self.prog.pack(fill="x", padx=12, pady=(6, 0))
        self.log = tk.Text(self, height=16, font=MONO, wrap="word")
        self.log.pack(fill="both", expand=True, padx=12, pady=8)

    # ------------------------------------------------------------ yardimcilar
    def _pump(self):
        try:
            while True:
                s = self.q.get_nowait()
                m = re.search(r"\[(\d+)/(\d+)\]", s)
                if m:
                    self.prog["maximum"] = int(m.group(2))
                    self.prog["value"] = int(m.group(1))
                self.log.insert("end", s)
                self.log.see("end")
        except queue.Empty:
            pass
        self.after(100, self._pump)

    def say(self, s):
        self.q.put(s.rstrip("\n") + "\n")

    def vid(self) -> Path:
        name = self.vid_var.get()
        if not name:
            raise RuntimeError("Önce bir video seç ya da 'Yeni video' oluştur.")
        return settings.base_dir() / name

    def switch_channel(self):
        """Aktif kanali degistirir: ayarlari yeniden yukler, video listesini bastan kurar."""
        ad = self.kanal_var.get()
        if ad == self.cfg.get("aktif_kanal"):
            return
        if self.busy:
            messagebox.showinfo("Meşgul", "Önceki işlem bitmeden kanal değiştirilemez.")
            self.kanal_var.set(self.cfg.get("aktif_kanal", ad))
            return
        settings.kanal_sec(ad)
        self.cfg = settings.load()
        self.title(f"PersonaStudio — {self.cfg['kanal']}")
        self.vid_var.set("")
        self.refresh_vids()

    def refresh_vids(self, select=None):
        names = [p.name for p in pt.vid_dirs()]
        self.vid_box["values"] = names
        if select:
            self.vid_var.set(select)
        elif names and not self.vid_var.get():
            self.vid_var.set(names[-1])
        self.show_status()

    def run(self, fn, *args, done=None):
        if self.busy:
            messagebox.showinfo("Meşgul", "Önceki işlem sürüyor.")
            return

        def work():
            self.busy = True
            w = _Writer(self.q)
            try:
                with redirect_stdout(w), redirect_stderr(w):
                    res = fn(*args)
                if done:
                    self.after(0, lambda: done(res))
            except SystemExit:
                pass
            except Exception as e:  # noqa: BLE001
                self.say(f"❌ {e}")
            finally:
                self.busy = False
        threading.Thread(target=work, daemon=True).start()

    def guard(self, fn):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            self.say(f"❌ {e}")

    @staticmethod
    def _open(path):
        subprocess.run(["open", str(path)])

    # ------------------------------------------------------------ eylemler
    def new_vid(self):
        v = pt.new_vid()
        self.say(f"Yeni klasör: {v}")
        self.refresh_vids(select=v.name)

    def open_claude(self):
        url = self.cfg.get("claude_proje_url")
        if url:
            subprocess.run(["open", url])

    def show_status(self):
        def f():
            v = self.vid()
            t = pt.title(v) if (v / "PAKET.md").exists() else ""
            self.title_lbl.config(text=t)
            parts = [f"— {v.name} —"]
            parts.append("PAKET ✅" if (v / "PAKET.md").exists() else "PAKET ✗")
            parts.append("avatar ✅" if (v / "avatar" / "avatar.mp4").exists() else "avatar ✗")
            parts.append("sahneler ✅" if (v / "sahneler.json").exists() else "sahneler ✗")
            parts.append("harita ✅" if (v / "plan.json").exists() else "harita ✗")
            self.say("  ".join(parts))
            if (v / "plan.json").exists():
                self.say(harita.status(v))
        if self.vid_var.get():
            self.guard(f)

    def save_package(self):
        def f():
            t, w = pt.save_package(self.vid(), pt.clipboard_get())
            self.say(f"PAKET kaydedildi: \"{t}\" — script {w} kelime (~{w / 150:.0f} dk).")
            self.title_lbl.config(text=t)
        self.guard(f)

    def copy_field(self, key):
        def f():
            text = pt.package_field(self.vid(), key)
            if not text:
                raise RuntimeError(f"PAKET.md içinde {key} bulunamadı.")
            if key == "GORSEL_PROMPT":
                ref = Path(self.cfg.get("avatar_referans", "")).expanduser()
                self.say(f"Flow'da bu promptla birlikte referans fotoğrafı ekle: {ref}")
            pt.clipboard_set(text)
            self.say(f"{key} panoya kopyalandı ({len(text)} karakter).")
        self.guard(f)

    def copy_upload_text(self):
        def f():
            v = self.vid()
            text = (f"{pt.title(v)}\n\n{pt.package_field(v, 'AÇIKLAMA')}\n\n"
                    f"ETİKETLER: {pt.package_field(v, 'ETİKETLER')}")
            pt.clipboard_set(text)
            self.say("Başlık + açıklama + etiketler panoya kopyalandı.")
        self.guard(f)

    def import_avatar(self, src=None):
        def f():
            name, dest = pt.import_avatar(self.vid(), src)
            self.say(f"Avatar: {name} → {dest} ({sahne.fmt(sahne.media_duration(dest))})")
        self.guard(f)

    def pick_avatar(self):
        p = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.mov")])
        if p:
            self.import_avatar(Path(p))

    def build_scenes(self):
        def done(txt):
            pt.clipboard_set(txt)
            self.say("SAHNE LİSTESİ panoya kopyalandı → claude.ai projesindeki sohbete yapıştır.")
        self.run(sahne.build, self.vid(), done=done)

    def save_map(self):
        def f():
            plan, problems = harita.build_plan(self.vid(), pt.clipboard_get())
            self.say(f"Harita: {len(plan['plan'])} sahne — {harita.summary(plan)}")
            for p in problems:
                self.say(f"⚠️  {p}")
        self.guard(f)

    def fetch_stock(self):
        self.run(pexels.fetch, self.vid())

    def copy_msg(self, kind):
        def f():
            msg = harita.message(self.vid(), kind)
            pt.clipboard_set(msg)
            self.say(f"Flow {kind} mesajı panoya kopyalandı ({msg.count(chr(10) + '- ')} öğe). "
                     "Flow'da yeni proje → Ajan modu → yapıştır.")
        self.guard(f)

    def copy_oto(self, kind):
        pt.clipboard_set(pt.oto_devam_script(kind, kind == "video"))
        self.say(f"Oto-devam betiği ({kind}) kopyalandı → Flow sekmesinde DevTools Console'a yapıştır.")

    def copy_dl_script(self):
        pt.clipboard_set(pt.indir_script())
        self.say("İndirme betiği kopyalandı → Flow görsel projesinde DevTools Console'a (Cmd+Option+J) yapıştır, "
                 "Enter. Bitince 'Flow indirilenlerini al'.")

    def import_flow(self):
        def f():
            pt.import_flow(self.vid())
            print(harita.status(self.vid()))
        self.run(f)

    def do_render(self, test):
        r = self.cfg["render"]

        def f():
            v = self.vid()
            entries, missing = harita.write_edl(v)
            if missing:
                print(f"⚠️  {len(missing)} eksik sahne önceki B-roll ile dolduruldu: {', '.join(missing[:8])}…")
            out = "test.mp4" if test else f"{safe_name(pt.title(v) or v.name)}.mp4"
            res = render_mod.render(
                v, until_seconds=90 if test else None, crossfade=r["crossfade"], effects=True,
                style=r["style"], effect_intensity=r["effect_intensity"], warmgrade=r["warmgrade"],
                vignette=False, kenburns=r["kenburns"], loudnorm=r["loudnorm"], transition_variety=False,
                letterbox=False, captions=r["captions"], out_name=out)
            return res
        self.run(f, done=lambda res: res and self._open(res["out_path"]))

    def make_thumb(self):
        p = filedialog.askopenfilename(filetypes=[("Görsel", "*.jpg *.jpeg *.png *.webp")])
        if not p:
            return

        def f():
            v = self.vid()
            y1, y2 = kapak.read_texts(v)
            out = kapak.compose(Path(p), y1, y2, v / "kapak" / "kapak.jpg")
            self.say(f"Kapak: {out}")
            self._open(out)
        self.guard(f)


if __name__ == "__main__":
    App().mainloop()
