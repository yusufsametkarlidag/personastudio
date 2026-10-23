# PersonaStudio — Bir videoyu baştan sona kendin yapma rehberi

Uygulamayı açmak için `~/PersonaStudio/PersonaStudio.command` dosyasına çift tıkla.
Toplam süre yaklaşık 1,5–2 saat; bunun büyük kısmı bekleme.

## 0 · Kanal seçimi

Uygulama iki kanallı. Pencerenin sol üstündeki **Kanal** kutusundan seç; başlık ve video listesi anında değişir.

| Kanal | Klasör | HeyGen avatar / ses | claude.ai projesi | Kapak imzası |
|---|---|---|---|---|
| **JUNE** — June's Garden | `~/Desktop/JUNE` | JUNE / Nancy | JUNE'S GARDEN | GRANDMA'S OLD TRICK |
| **HANK** — Hank's Old Workshop | `~/Desktop/HANK` | HANK / Narrative Nolan | HANK'S OLD WORKSHOP | OLD SHOP TRICK |

Her kanalın kendi klasörü, claude.ai projesi, yüz referansı ve stok arama kelimeleri var; hepsi
`ayarlar.json` içindeki `kanallar` bölümünde. API anahtarları iki kanalda ortak.
Aşağıdaki adımlarda "JUNE / Nancy" yazan yerlerde **seçili kanalın** avatarını ve sesini kullan.

Hazırlık (bir kez): Pixabay anahtarı `~/PersonaStudio/ayarlar.json` dosyasında kayıtlı.

---

## 1 · Konu ve paket (claude.ai, ~5 dk)

1. Uygulamada **Yeni video**'ya bas (vid2 klasörü açılır).
2. **claude.ai projesi** düğmesi → projede **yeni sohbet** aç → yaz:
   `Yeni video: 3 konu ve başlık fikri ver.` → birini seç → `Onaylıyorum, X. fikir. PAKET'i hazırla.`
3. Gelen PAKET dosyasının sağ üstündeki **Copy** düğmesine bas.
4. Uygulamada **Paketi panodan kaydet**. Kayıtta kelime sayısı yazar; **2.700–3.000 kelime** olmalı.
   Daha kısaysa Claude'a "script'i 2.800–3.000 kelimeye çıkar" de, yeniden kopyala, yeniden kaydet.

## 2 · HeyGen avatar videosu (~25 dk, çoğu bekleme)

1. Uygulamada **Script'i kopyala (HeyGen)**.
2. HeyGen → AI Studio → **New video**. Sağ panelde avatar **JUNE** ve ses **Nancy** olmalı.
3. **Motion Engine → Avatar III**'ü seç (kredi harcamaz; her yeni videoda Avatar IV'e döner, unutma).
4. **Ses hızı:** sağ paneldeki ses ayarlarından hızı **0.9x** yap (daha sakin, nine gibi).
5. Script kutusuna tıkla → **Cmd+V** (yazarak değil, yapıştırarak).
6. **Generate** → başlık yaz → 1080p → **Submit**. Projects sayfasında %100 olunca kartı sağ tıkla → **Download**.
7. İndirme bitince uygulamada **İndirilenler'den avatarı al**.

## 3 · Sahne listesi → sahne haritası (claude.ai, ~10 dk)

1. Uygulamada **Sahne listesi oluştur + kopyala**. Uygulama sesi cümlelere böler ve avatarın ekranda
   görüneceği anları otomatik seçer; liste panoya kopyalanır.
2. Paketi yazdığın **aynı sohbete** yapıştır (ek dosya olarak görünür) ve şunu yaz:
   `Ekteki SAHNE LİSTESİ için SAHNE HARİTASI ver, .txt artifact olarak, eksiksiz.`
3. Gelen dosyada **Copy**'ye bas → uygulamada **Haritayı panodan kaydet**.
   Uyarı satırları çıkarsa (eksik satır, çok fazla VEO) Claude'dan düzeltmesini iste.

## 4 · Kaynaklar (~30 dk)

**Stok (otomatik):** **Stokları indir (Pixabay/Pexels)**. Uygulama konu dışı ve yüz içeren klipleri eler.
Bulamadığı sahneleri (en fazla 20) **görsele** çevirir; bunlar bir sonraki adımdaki Flow mesajına eklenir.

**Görseller (Flow):**
1. Uygulamada **Flow görsel mesajı** (stok indirmesinden **sonra** kopyala ki yedek görseller de olsun).
2. flow.google.com → **Yeni proje** → sağdaki ajan kutusuna yapıştır → gönder.
3. Ajan bitirince adlara bak: kartlar **"Görsel #12"** gibi adlandırılmamışsa ajana yaz:
   `Yeni görsel üretmeden, her görseli ilk mesajımdaki numarasıyla "Görsel #numara" olarak yeniden adlandır.`
4. **İndirme (kolay yol):** uygulamada **Flow görsel indirme betiği** → Flow sekmesinde **Cmd+Option+J**
   (Konsol) → yapıştır → Enter. Betik sayfayı kendisi kaydırır ve tüm "Görsel #N" kartlarını indirir
   (Chrome "birden fazla indirme" izni sorarsa izin ver). Bitince "Bitti: N görsel" uyarısı çıkar.
   Elle yol: kartların **dışındaki boş alandan** fareyle sürükleyerek seç → sağ tık → **İndir** (zip).

**Videolar (Flow):** aynısını **Flow video mesajı** ile ayrı bir projede yap. Flow kredi onayı sorar
(12 video ≈ 144 kredi). Adlar **"Vid33 — …"** gibi olmalı; değilse aynı şekilde yeniden adlandırt.

**Aktarma:** uygulamada **Flow indirilenlerini al** → **Durum**. "✅ Tüm kaynaklar hazır" yazmalı.
Eksik numara varsa Flow'da o kartı indirip tekrar **Flow indirilenlerini al**.

## 5 · Kontrol + render (~20 dk)

1. İstersen önce **Test render (ilk 90 sn)** ile bak.
2. **Tam render** → bitince video `vidN/output/<başlık>.mp4` olarak açılır. Altyazısız ve müziksiz.
   Kare hızı otomatik olarak avatarınkiyle aynı (25 fps), dudak senkronu korunur.

## 6 · Kapak (~5 dk)

1. Uygulamada **Kapak görsel promptunu kopyala**.
2. Flow'da (June'un portresinin olduğu eski projede) ajana yaz:
   `"June Close #1" görselini yüz referansı olarak kullanarak bu prompttan 3 adet 16:9 görsel üret:` + yapıştır.
3. En iyisini **2K** indir → uygulamada **Taban görsel seç → kapak**. Yazı (sağ üstte iri beyaz+sarı +
   siyah şeritte "GRANDMA'S OLD TRICK") otomatik eklenir → `vidN/kapak/kapak.jpg`.

## 7 · YouTube'a yükleme

**Başlık + açıklamayı kopyala** → YouTube Studio'ya yapıştır, etiketleri etiket alanına koy, kapağı yükle.
"Altered or synthetic content" (gerçekçi yapay zekâ içeriği) kutusunu **işaretle**.

---

### Sık sorunlar
- **Flow ajanı adlandırmayı unutuyor:** her seferinde normal; 4. adımdaki yeniden adlandırma mesajını gönder.
- **Flow "günlük limit":** Nano Banana Pro dolduysa ajana "Nano Banana 2 kullan" de.
- **Stokta alakasız klip:** `vidN/stok/kaynaklar.json`'da hangi sorgu ile neyin geldiği yazar. Sorunlu sahneyi
  haritada `GORSEL | <prompt>` yap → **Haritayı panodan kaydet** → Flow'da o görseli üret → render.
- **HeyGen Avatar IV'te kaldı:** kredi harcar; Submit'ten önce Motion Engine'in **Avatar III** olduğuna bak.
- İstediğin zaman Claude Code'a "vidN'i baştan sona sen yap" diyebilirsin; aynı adımları o yürütür.

## Arşiv görüntüsü (kamu malı, Internet Archive)

Stok sitelerinin bulamadığı **anı ve hikâye sahneleri** için: 1940–80 arası gerçek çiftlik, mutfak,
kiler, sokak, atölye görüntüleri. API anahtarı gerekmez, telif riski yoktur (sadece kamu malı
koleksiyonlardan arar). Flow'un ürettiği sahte eski fotoğraftan çok daha inandırıcı olur.

Arşiv araması **görüntüye değil, filmin metnine** bakar; yani gelen film konuyla ilgisiz olabilir.
O yüzden her zaman önce kontak tablosuna bakılır. Dört adım:

```
python3.10 arsiv.py ara "root cellar potatoes"          # aday filmleri listeler
python3.10 arsiv.py getir <identifier>                  # filmi bir kez indirir (paylaşılan kütüphane)
python3.10 arsiv.py kontak <identifier> --adim 25       # kare tablosu + hangi kare kaç. saniye
python3.10 arsiv.py kes <identifier> <vid> S180 200     # 200. saniyeden sahne süresi kadar keser
```

`kes` sahneyi plan.json'da otomatik STOK'a çevirir, yani o sahne için Flow görseli üretmeye gerek kalmaz.
İndirilen filmler `<ana_klasor>/_arsiv_kutuphane/` içinde birikir; aynı filmden birden çok sahne kesilebilir,
ikinci kez indirilmez.

Sınırı: kaynaklar eski ve düşük çözünürlüklü. Anı sahnelerinde bu bir artı, modern yakın çekimlerde
(klozet tankının içi gibi) işe yaramaz — orada GORSEL kalır.
