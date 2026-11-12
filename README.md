![Social Empires](templates/img/logo.png "Social Empires")

# Social Empires Türkçe

[![Testler](https://github.com/lahmacunveayran/socialempires-tr/actions/workflows/tests.yml/badge.svg)](https://github.com/lahmacunveayran/socialempires-tr/actions/workflows/tests.yml)
[![Lisans: GPLv3](https://img.shields.io/badge/lisans-GPLv3-blue.svg)](LICENSE)

Social Empires'ı **Türkçe** oynamak ve yerel olarak geliştirmek için hazırlanmış
bir topluluk çatalı. Oyun, Flash istemcisi ile konuşan bir Python/Flask
sunucusu üzerinde çalışır; Facebook hesabı gerekmez; internet yalnızca oyun varlıklarını ilk kez
indirmek için gerekir.

> Bu proje Social Point ile bağlantılı değildir. Yalnızca kültürel miras
> amaçlı bir koruma çalışmasıdır. Orijinal proje:
> [AcidCaos/socialemperors](https://github.com/AcidCaos/socialemperors).

---

## Özellikler

- **Tam Türkçe**: eşya, bina, birim, görev, yardım metinleri ve oyun
  SWF'sinin içindeki sabit arayüz yazıları ("İleri", "İptal", "YARDIM!"
  gibi); gömülü yazı tiplerine `ğ, Ğ, İ, ş, Ş` harfleri eklenir.
- **PvP**: istemcinin kurallarıyla (6 saatte 3 saldırı, aynı rakibe 4 saatte
  bir), ganimet, onur puanı, savaş raporları ve savunma raporları.
- **50 bot köyü** (ilk açılışta otomatik üretilir): adları ve resimleri oyunun kendi birimlerinden, kişilikler, öfke hafızası ve dünya
  simülasyonu.
- **Turnuvalar**: 4 kişilik odalar; boş koltuklar kendi ordularıyla bot
  köyleriyle dolar, birinciye turnuva ödülü verilir.
- **Dünya haritası**: her kıtada 7 rakip köy; hepsi fethedilince sonraki
  kıtaya geçilir.
- **Etkinlik takvimi**: eski etkinliklerin tema setleri (Çin, Viking, Mısır,
  Atlantis, Cadılar Bayramı, Mitoloji...) bayramlarda ve özel günlerde
  mağazaya açılır (`config/takvim.json`); bayram tarihleri Diyanet
  tablosundan. 15 Harika her zaman mağazada. Hepsini sürekli açmak için
  `ayarlar.json`'da `"magaza_tema_setleri": true`.
- **Oyun sayfası**: oyunun kendi manzarası, ekrana göre ölçeklenen oyun
  çerçevesi, hız seçici (Normal … 10 kat), "Sen yokken" özeti, Diyar Haberleri şeridi, Şeref Kürsüsü,
  haftalık turnuva tablosu (Elo; hafta bitince ilk 10'a ödül) ve tek tıkla
  kayıt yedeği indirme/yükleme. Günlük ödül oyunun kendi ödülüdür.
- **Ada Ocağı ve teklifler**: oyunun Ada Ocağı mini oyunu ve ejderha teklifleri açık; "arkadaşından
  iste" düğmelerinde bot köyleri yardım eder (her yer için günde bir).
- **Büyücünün İksirleri**: iksir kaynatıp nadir yaratıklar kazanılan şans
  oyunu; her 30 günde yenilenir.
- **İstemciyle birebir uyumlu komutlar**: sunucu, istemcinin gönderdiği
  158 komutun tamamını oyun SWF'sinin (1.4.07) bytecode'undan çıkarılan
  argüman sırasıyla işler; kayıt yeniden yüklendiğinde oyun aynı kalır.
- **Bayramlar**: bayram ve özel günlerde oyuna "kutlu olsun" hedefi gelir; milli bayramlarda
  oyunun Türk Kılıççı, Baltacı, Okçu ve Atlı birimleri mağazada açılır.
- **Yeni içerik**: Büyük Ev, Büyük Değirmen, Büyük Kule; Süper Şövalye,
  Süper Okçu, Süper Kılıçlı ve yeni mağaza paketleri.
- **Çevrimdışı paket**: oyun dosyaları bir kerede iner (temel ~225 MB, tam ~1,1 GB), sonra internet gerekmez.
- **Wi-Fi ile taşı**: imparatorluk, bilgisayar ile tablet arasında 6 haneli kodla aktarılır.
- **Android uygulaması**: sunucu tabletin içinde; iki parmakla yakınlaştırma ([ANDROID.md](ANDROID.md)).
- **Güvenli kayıt**: atomik yazım, `.bak` yedeği, günlük yedekler ve
  `USERID` doğrulaması.

---

## En kolay yol: hazır Windows paketi

Python kurmanız gerekmez.

1. [Sürümler](https://github.com/lahmacunveayran/socialempires-tr/releases)
   sayfasından en yeni `SocialEmpiresTR-...-windows.zip` dosyasını indirin.
   (İlk sürüm v0.1.0 henüz yayınlanmadı; o zamana kadar aşağıdaki kaynak koddan kurulum kullanılır.)
2. Zip'i bir klasöre açın ve `Social Empires.bat` dosyasına çift tıklayın.
3. Tarayıcı kendiliğinden açılır: <http://127.0.0.1:5050/>

Windows "bilgisayarınızı korudu" (SmartScreen) derse **Ek bilgi** >
**Yine de çalıştır**'a basın; paket imzasızdır. İndirilen dosyanın
değişmediğini yanındaki `.sha256` dosyasıyla denetleyebilirsiniz
(PowerShell: `Get-FileHash dosya.zip -Algorithm SHA256`). Her paket
yayınlanmadan önce temiz bir Windows makinesinde açılıp sınanır.

## Android telefon ve tablet

Oyunun tamamı tek bir uygulamada; bilgisayar gerekmez. Sürümler sayfasındaki
`SocialEmpiresTR-...-android.apk` dosyasını kurun (sürüm yayınlanana kadar APK, PR'ların
CI çıktısındadır). Ayrıntılar ve kayıtları taşıma:
[ANDROID.md](ANDROID.md).

## Kurulum (Windows, kaynak koddan)

1. **Python 3.12+** kurulu olsun.
2. Depoyu indirin veya klonlayın:
   ```bat
   git clone https://github.com/lahmacunveayran/socialempires-tr.git
   cd socialempires-tr
   ```
3. `baslat.bat` dosyasını çalıştırın.
   - Gerekli Python paketleri (`requirements.txt`) eksikse otomatik kurulur.
   - Sunucu hazır olduğunda tarayıcı otomatik açılır:
     <http://127.0.0.1:5050/>
4. Giriş ekranından bir köy seçin veya yeni imparatorluk kurun.

**Oyun varlıkları (SWF, görsel, müzik):** ~1,3 GB oldukları için depoda
tutulmaz (yalnızca Türkçe fontlar depodadır). İlk açılışta eksik dosyalar
[AcidCaos/socialemperors](https://github.com/AcidCaos/socialemperors)
deposundan otomatik indirilip `download_assets/` altında saklanır; bu yüzden
ilk açılış için internet gerekir. Hepsini bir kerede indirip internetsiz
oynamak için:

```bat
python varliklari_indir.py
```

**Bot köyleri:** `saves/` altında hiç bot yoksa sunucu ilk açılışta 50 bot
köyü üretir (PvP, ada fetih ve turnuvalar bunlara ihtiyaç duyar). Yeniden
üretmek için: `python araclar\bot_koy_uret.py`.

**Flash desteği:** Oyun sayfası Flash yerine sürümü sabitlenmiş Ruffle 0.7.1
ile tarayıcıda çalışır; Ruffle ilk açılışta bir kez indirilir, sonra internet
gerekmez. Flash eklentili tarayıcılar için eski sayfa: `/flash.html`.
Ayrıntılar: [FLASH.md](FLASH.md). GNU/Linux: [LINUX.md](LINUX.md).

---

## Oynanış

- Sunucu: `http://127.0.0.1:5050/`
- Sağlık kontrolü: `http://127.0.0.1:5050/saglik`
- Oyunu kapatmak için sunucu penceresinde `Ctrl+C` kullanın.

### Ayarlar

`ayarlar.json` dosyasından değiştirilir (sunucuyu yeniden başlatın):

- `zaman_olcegi`: oyun hızı. `3.0` üretim/inşaat sürelerini üçte bire indirir.
  Hız oyun sayfasındaki "Hız" seçicisinden de seçilir. Sayfadan seçilen hız
  `ayarlar.yerel.json`'a yazılır (depoya girmez) ve `ayarlar.json`'dakinin
  önüne geçer. Elle verilen hıza dönmek için o dosyayı silin.
- `magaza_tema_setleri`: tema setlerini mağazaya açar (`config/tema_setleri.json`).
- `dunya`: bot köylerinin simülasyonu (saldırı sıklığı vb.).

### Türkçe

- `ceviri/tr.json`: config'teki oyun metinleri (eşyalar, hedefler, arayüz).
  Oyunun hikâyesine göre elle yazılmıştır.
- `ceviri/arayuz_tr.json`: oyun SWF'sinin içindeki sabit yazılar. Sunucu
  SWF'yi ilk istekte Türkçeleştirip `download_assets/tr/` altında saklar.
- `assets/fonts/tr_*.swf`: Türkçe harfli yazı tipleri.

---

## Geliştirme

```bat
python -m unittest discover -s tests
```

Testler gerçek `saves/` klasörüne dokunmaz; geçici bir klasör kullanır.

- Geliştirme notları ve komut protokolü: [docs/GELISTIRME.md](docs/GELISTIRME.md)
- Katkı rehberi: [CONTRIBUTING.md](CONTRIBUTING.md)
- Güvenlik politikası: [SECURITY.md](SECURITY.md)

### Proje yapısı

| Yol | Açıklama |
| --- | --- |
| `server.py` | Sunucuyu başlatır |
| `oyun/sunucu.py` | Flask uygulaması, giriş ve oyun sayfaları |
| `oyun/istemci.py` | İstemcinin çağırdığı uçlar (config, oyuncu, ada, turnuva) |
| `oyun/komutlar.py` | Oyun komutları (`command.php`) |
| `oyun/varliklar.py` | SWF/görsel/müzik dosyaları ve otomatik indirme |
| `oyun/swf_yama.py`, `oyun/swf_font.py` | Oyun SWF'sinin Türkçeleştirilmesi |
| `oyun/kayit.py`, `oyun/surum.py`, `oyun/yedek.py` | Kayıtlar, sürüm geçişleri, yedekler |
| `oyun/config.py`, `oyun/turkce.py`, `oyun/zaman.py` | Oyun ayarları, çeviri, oyun hızı |
| `oyun/pvp.py`, `oyun/dunya.py`, `oyun/denge.py` | PvP, bot dünyası, denge ayarları |
| `oyun/turnuva.py`, `oyun/ada.py` | Turnuvalar, dünya haritası ve fetih |
| `oyun/pvp_yeni.py`, `oyun/kaynaklar.py` | 1.4.07 PvP uçları, istemcinin kaynağı ve SHA-256 özeti |
| `oyun/bayram_hedefleri.py`, `oyun/takvim.py` | Bayram hedefleri, etkinlik takvimi |
| `oyun/hiz.py`, `oyun/yokken.py` | Sayfadan hız seçimi, "Sen yokken" özeti |
| `oyun/ev_agi.py`, `oyun/tasima.py`, `oyun/kayit_yedek.py` | Ev ağı, Wi-Fi ile taşıma, yedek indir/yükle |
| `oyun/hile.py` | Yerel hile paneli (`/cheat`) |
| `araclar/` | Bot köyü üretimi, çeviri ve birim yaması araçları, Windows ve Android paketleri |
| `android/` | Android uygulaması (Chaquopy + WebView) |
| `config/`, `villages/`, `templates/`, `ceviri/` | Oyun verisi, köyler, sayfalar, çeviriler |
| `tests/` | Testler |

---

## Veri ve gizlilik

- `saves/` altındaki oyun kayıtları **depoya dahil edilmez**.
- Sunucu yalnızca yerel makinede dinler (`127.0.0.1:5050`). `"ev_agi": true` verilirse ev ağına
  açılır; telefon ve tabletler parola sorar. "Wi-Fi ile taşı" 10 dakikalığına 5051 kapısını açar.
- Gizli anahtar `SE_SECRET_KEY` ortam değişkeniyle değiştirilebilir.

---

## Lisans

[GNU GPLv3](LICENSE).

```
Social Empires preservation project.
Copyright (C) 2022  The Social Emperors team
See the GNU General Public License <https://www.gnu.org/licenses/>.
```

Bu proje AcidCaos/socialemperors'tan türetilmiştir ve değiştirilmiştir (GPLv3 madde 5a). Sunucu
0.04a'nın (`f642e0b`) tabanından değiştirildi. `config/patch/0-language_en.json`, `1-mega_patch.json`,
`2-unit_patch.json` ve `config/goals.json`, upstream'in `54df29e` commit'inden olduğu gibi alındı. Bunları
değiştiren kendi yamalarımız ayrı dosyalardadır (`kompu.json`, `turnuva.json`, `yeni_icerik.json`), değişiklik
tarihleri depo geçmişindedir. `villages/`, `config/game_config_*.json`, `araclar/make_se_unit_patch.py`,
`araclar/se_unit_patch.csv`, `araclar/unit_templates.json` ve `templates/img/` altındaki bazı resimler de
0.04a ile aynıdır (`docs/inceleme/2026-10-30-upstream-tarama1.md` §1, `-tarama2.md` §7). Oyunun istemcisi (`SocialEmpires1.4.07sec_fixed.swf`) Social Point'indir, GPL
kapsamında değildir ve depoda tutulmaz.

### Teşekkürler

- [AcidCaos/socialemperors](https://github.com/AcidCaos/socialemperors) —
  orijinal koruma projesi ve sunucu temeli.
- [Ruffle](https://ruffle.rs/) — Flash çalıştırma.
- [BlueMaxima's Flashpoint](https://bluemaxima.org/flashpoint/) ve
  [Internet Archive](https://archive.org/) — dijital koruma çalışmaları.
- Tüm katkıda bulunanlar.
