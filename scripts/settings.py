#!/usr/bin/env python3
# PersonaStudio — Copyright (c) 2026 yusufsametkarlidag. PolyForm Noncommercial 1.0.0 lisanslıdır: ticari kullanım yasaktır. Ayrıntı: LICENSE.md
"""
Kullanıcıya/kanala özel ayarlar (ayarlar.json, uygulama klasöründe; git'e girmez).

Dosya iki katmanlıdır:

  ORTAK (üst düzey)   Bütün kanallarda aynı olan şeyler: API anahtarları, render ayarları.
  kanallar            Kanal adı -> o kanala özel alanlar (aşağıdaki liste).
  aktif_kanal         Şu an üzerinde çalışılan kanalın adı.

Kanala özel alanlar:
  kanal                   Kanal/persona adı (pencere başlığı)
  ana_klasor              vid1, vid2 … klasörlerinin bulunduğu klasör
  claude_proje_url        claude.ai proje adresi (paket + sahne haritası burada istenir)
  avatar_referans         Kapak görselleri için persona referans fotoğrafı
  heygen.avatar / heygen.ses / heygen.motion_engine
  stok_konu_kelimeleri    Klip etiketlerinde en az biri bulunmalı (pexels.py DOMAIN)
  stok_yasak_kelimeler    Bu etiketlerden biri varsa klip elenir (pexels.py BANNED)
  stok_yedek_sorgular     Uygun klip yoksa denenecek genel B-roll sorguları (pexels.py FALLBACKS)
  stok_esanlam            Kelime köklerini eşitleyen sözlük (pexels.py SYN)
  max_yedek_gorsel        Stoktan görsele çevrilecek en fazla sahne sayısı

Ortak alanlar:
  pixabay_api_key         pixabay.com/api/docs ücretsiz anahtar (stok videolar)
  pexels_api_key          pexels.com/api (yeni anahtar verilmiyorsa boş kalabilir)
  render                  Varsayılan render ayarları

load() çağrıldığında aktif kanalın alanları üst düzeye bindirilir; bu yüzden çağıran kodun
kanaldan haberi olması gerekmez (cfg["ana_klasor"], cfg["heygen"]["ses"] … hep çalışır).
Eski (tek kanallı, "kanallar" içermeyen) ayarlar.json dosyaları da aynen çalışmaya devam eder.
"""
import json
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
SETTINGS_FILE = APP_DIR / "ayarlar.json"
EXAMPLE_FILE = APP_DIR / "ayarlar.ornek.json"

DEFAULTS = {
    "kanal": "Persona",
    "ana_klasor": str(Path.home() / "Desktop" / "Persona"),
    "claude_proje_url": "",
    "pixabay_api_key": "",
    "pexels_api_key": "",
    "avatar_referans": "",
    "heygen": {"avatar": "", "ses": "", "motion_engine": "Avatar III"},
    "render": {"crossfade": 0.3, "style": "modern", "effect_intensity": "light", "warmgrade": True,
               "kenburns": True, "loudnorm": True, "captions": False},
}


def _merge(base: dict, extra: dict) -> dict:
    out = dict(base)
    for k, v in extra.items():
        out[k] = _merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def _raw() -> dict:
    """ayarlar.json'un kendisi (kanal bindirmesi yapılmadan). Yazarken bunu kullan."""
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    return {}


def load() -> dict:
    data = DEFAULTS
    for f in (EXAMPLE_FILE, SETTINGS_FILE):
        if f.exists():
            data = _merge(data, json.loads(f.read_text(encoding="utf-8")))
    kanallar = data.get("kanallar") or {}
    if kanallar:
        ad = data.get("aktif_kanal")
        if ad not in kanallar:
            ad = next(iter(kanallar))
        data = _merge(data, kanallar[ad])
        data["aktif_kanal"] = ad
    return data


def save(data: dict):
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def base_dir() -> Path:
    return Path(load()["ana_klasor"]).expanduser()


# ----------------------------------------------------------------- kanallar
def kanal_listesi() -> list:
    """ayarlar.json'daki kanal adları (tek kanallı eski dosyada tek elemanlı liste)."""
    raw = _raw()
    kanallar = raw.get("kanallar") or {}
    return list(kanallar) if kanallar else [load()["kanal"]]


def aktif_kanal() -> str:
    return load().get("aktif_kanal") or load()["kanal"]


def kanal_sec(ad: str):
    """Aktif kanalı değiştirir. Sadece aktif_kanal satırı yazılır, profiller bozulmaz."""
    raw = _raw()
    kanallar = raw.get("kanallar") or {}
    if ad not in kanallar:
        raise ValueError(f"ayarlar.json içinde '{ad}' kanalı yok. Olanlar: {', '.join(kanallar) or '(yok)'}")
    raw["aktif_kanal"] = ad
    save(raw)
