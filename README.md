# PersonaStudio

Bir metinden, yayına hazır uzun metrajlı videoya kadar tüm süreci yöneten otomatik video üretim hattı.

Konuşmayı kelime düzeyinde çözümler, sahnelere böler, her sahneye uygun görsel/video kaynağını eşleştirir,
hepsini tek bir zaman çizelgesinde birleştirir ve kapak görselini üretir. Birden fazla kanalı tek
konfigürasyon dosyasından yönetir.

**Durum:** Aktif kullanımda. Üç ayrı kanal için 30'dan fazla uzun metrajlı video üretti.

---

## Çözdüğü problem

Elle yapıldığında 14 dakikalık bir videonun kurgusu saatler sürüyor: konuşmayı dinleyip sahnelere bölmek,
her sahneye görsel bulmak, hepsini zamanında kesmek, kapak hazırlamak. Üstelik her sahnenin süresi
konuşmaya saniyesi saniyesine oturmak zorunda — tek bir kayma videonun geri kalanını bozuyor.

PersonaStudio bu süreci tek komuta indiriyor ve **200 sahnelik bir videoyu hedef süreden 0,05 saniye
sapmayla** üretiyor.

---

## Akış

```
konuşma videosu
      │
      ▼
 [ sahne.py ]      Whisper ile kelime düzeyinde zaman damgası
      │            → cümlelere, cümleler 2–8 sn'lik sahnelere bölünür
      │            → her sahneye tip atanır (konuşan kişi / B-roll)
      ▼
 [ harita.py ]     sahne planı (plan.json) + varlık istekleri
      │
      ▼
 [ pexels.py ]     stok video indirme (Pixabay / Pexels API)
 [ arsiv.py  ]     kamu malı arşiv görüntüsü (Internet Archive)
      │
      ▼
 [ harita.py ]     kaynak doğrulama → edl.json (kesme listesi)
      │
      ▼
 [ render.py ]     FFmpeg ile birleştirme: crossfade, Ken Burns,
      │            ses normalizasyonu, süre doğrulama
      ▼
 [ kapak.py ]      Pillow ile kapak görseli (1280×720)
      │
      ▼
   çıktı.mp4
```

---

## Teknik olarak öne çıkan kısımlar

**Zaman hassasiyeti.** Render motoru EDL (kesme listesi) üzerinden çalışıyor ve her sahnenin süresi
konuşmanın kendi zaman damgasından geliyor. 200 sahnelik videolarda hedef süreden sapma 0,05 saniyenin
altında kalıyor; her render sonunda bu fark otomatik raporlanıyor.

**Sahne bölümleme algoritması.** Whisper'ın kelime zamanlarından cümle sınırları çıkarılıyor, cümleler
2–8 saniyelik sahnelere bölünüyor ve konuşan kişinin ekranda görüneceği anlar belirli bir dağılıma göre
otomatik seçiliyor (açılışta, sonra belirli aralıklarla, izleyiciye doğrudan hitap edilen cümleler tercih
edilerek).

**Çok kanallı mimari.** Her kanalın kendi varlık kuralları, görsel kimliği ve çıktı şablonu var. Ayarlar
tek dosyada tutuluyor; aktif kanalın ayarları ortak ayarların üzerine biniyor, böylece yeni bir kanal
eklemek kod değişikliği gerektirmiyor.

**Kaynak doğrulama.** Render öncesi eksik görsel/video otomatik tespit ediliyor ve hangi sahnelerin
eksik olduğu raporlanıyor. Böylece yarım kaynakla render alınıp 15 dakikalık çıktının ortasında boş
kare çıkması engelleniyor.

**Lisans güvenliği.** Arşiv modülü yalnızca kamu malı / CC0 koleksiyonlardan arama yapıyor; lisansı
belirsiz sonuçlar filtreleniyor.

---

## Modüller

| Dosya | İşi |
|---|---|
| `gui.py` | Adım adım üretim arayüzü (Tkinter) |
| `sahne.py` | Whisper ile konuşma çözümleme ve sahne bölümleme |
| `harita.py` | Sahne planı, kaynak doğrulama, EDL üretimi |
| `pexels.py` | Pixabay / Pexels stok video indirme ve önbellekleme |
| `arsiv.py` | Internet Archive kamu malı arşiv görüntüsü |
| `render.py` | FFmpeg render motoru |
| `kapak.py` | Pillow ile kapak görseli üretimi |
| `banner.py` | Kanal banner üretimi |
| `settings.py` | Çok kanallı konfigürasyon yönetimi |
| `check_assets.py` | Dosya eşleme ve doğrulama yardımcıları |

---

## Kurulum

Gereksinimler: Python 3.10+, FFmpeg, OpenAI Whisper, Pillow

```bash
git clone https://github.com/yusufsametkarlidag/personastudio.git
cd personastudio
cp ayarlar.ornek.json ayarlar.json   # kendi ayarlarınızı girin
python3 scripts/gui.py
```

API anahtarları `ayarlar.json` içine girilir; bu dosya sürüm kontrolüne dahil değildir.
Örnek yapı için `ayarlar.ornek.json` dosyasına bakın.

Ayrıntılı kullanım: [KULLANIM.md](KULLANIM.md)

---

## Sonuçlar

- 200 sahneye kadar video, hedef süreden **0,05 sn sapmayla**
- 14–15 dakikalık bir videonun render süresi: yaklaşık 10 dakika
- Üç kanal, 30'dan fazla yayınlanmış video
- Haftalarca kesintisiz kullanım

---

## Notlar

Geliştirme sürecinde yapay zeka destekli kodlama araçlarından yararlandım; mimari kararlar, modül
ayrımı ve zaman hassasiyeti gereksinimleri bana ait.

## Lisans

[PolyForm Noncommercial 1.0.0](LICENSE.md) — ticari kullanım için izin gereklidir.
