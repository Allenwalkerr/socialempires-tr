# Geliştirme Notları

> İşlerin kaydı ve denetimi için görev kitabı: `docs/gorev/00-CEKIRDEK.md` (bulgular `docs/gorev/BULGULAR.json`,
> kapılar `docs/gorev/KAPILAR.md`, oturum notları `docs/devlog/`).

Bu depo, [AcidCaos/socialemperors](https://github.com/AcidCaos/socialemperors)
koruma projesinin (GPLv3) Türkçeleştirilmiş ve geliştirilmiş bir çatalıdır.

## Temel ilke: istemci yönetir, sunucu kaydeder

Oyun mantığı Flash istemcisinde çalışır. İstemci her değişikliği (bina alma,
toplama, satma...) `command.php` ile bir komut olarak bildirir; sunucu aynı
değişikliği oyuncunun kaydına uygular. Kayıt yeniden yüklendiğinde istemcinin
gördüğü durumla birebir aynı olmalıdır.

Bu yüzden `oyun/komutlar.py` içindeki işleyiciler **kendi kurallarını
uygulamaz**, istemcinin yaptığını taklit eder. Sunucunun bir komutu
reddetmesi ya da farklı bir ödül vermesi, oyuncunun kaynaklarının bir sonraki
açılışta "geri gitmesine" yol açar. Kaynaklar yalnızca eksiye düşmemesi için
sınırlanır.

## Komut protokolü nereden geliyor?

Komut adları ve argüman sıraları oyun SWF'sinin (`SocialEmpires1.4.07sec_fixed.swf`)
AVM2 bytecode'undan çıkarılmıştır: `araclar/abc_okur.py` bayt kodunu okur, `araclar/komut_imzalari.py`
istemcinin gönderdiği komutları (G = 158) sunucunun işledikleriyle (H) karşılaştırır ve
`docs/inceleme/1407-komutlar.md` tablosunu üretir. İstemcide her komut şu kalıpla kurulur:

```
Base.Commands.addCommand({cmd: Constants.CMD_X, args: [a0, a1, ...]})
```

Her işleyicinin belge dizesinde argüman sırası yazılıdır, örneğin:

```python
@komut("buy")
def buy(save, a):
    """[id, x, y, yon, kasaba, kaynak_dusme(1=bedava), fiyat_carpani, tur]"""
```

`tests/test_komut_imzalari.py` (`test_1407_*`) istemcinin gönderdiği bütün komutların bir işleyicisi
olduğunu (`EKSIK_1407` boş) ve argüman sayılarının uyduğunu denetler.

### Yeni komut eklemek

```python
@komut("komut_adi")
def komut_adi(save, a):
    """[arg0, arg1, ...] - istemcideki karşılığı"""
    h = harita(save, a.tam(2))      # kasaba numarası
    kaynak_ekle(save, h, "g", -100)  # g/w/f/s, c (cash), m (mana)
```

`a.tam(i)`, `a.metin(i)`, `a.ondalik(i)`, `a.json(i)` eksik ya da bozuk
argümanda varsayılan değer döndürür.

### Kayıttaki eşya biçimi

```
[id, x, y, yon, toplama_zamani, seviye, [icindeki_birimler], {ozellikler}]
```

`toplama_zamani` mutlak bir zaman damgasıdır; istemci geçen süreyi
`sunucu_zamani - toplama_zamani` olarak hesaplar.

### İstemcinin okuduğu bazı kayıt alanları

| Alan | Biçim |
| --- | --- |
| `privateState.deadHeroes` | `{"birim_id": adet}` (mezarlık) |
| `privateState.unlockedEarlyBuildings`, `unlockedSkins` | `{"id": true}` |
| `privateState.neighborAssists` | `{"u<pid>": zaman}`: komşuya 24 saatte bir yardım |
| `privateState.collections` | `[[tamam, p1, p2, p3, p4, p5], ...]` |
| `privateState.teams` | `{"tournament": [...], "quest": [...]}` |
| `privateState.helpMap` | görülen yardım pencereleri listesi |
| `maps[n].receivedAssists` | `{"u<pid>": [[x, y, id], ...]}` |
| `maps[n].resourcesTraded` | pazar sayaçları `{"w": n, ...}` |
| `maps[n].warehousedUnits` | birim deposundaki birimler |

## Türkçeleştirme

1. **Config metinleri**: `ceviri/tr.json` (`oyun/turkce.py` uygular).
   Eksik metinleri bulmak için `araclar/sozluk_cikar.py`. Üslup:
   oyuncuya "sen" diye hitap edilir, noktalı virgül ve tire kullanılmaz,
   terimler tutarlıdır (Konak, Okçu Ocağı, Bıçkıhane, Nakit, Sefer, Hedef).
2. **SWF içindeki sabit yazılar**: `ceviri/arayuz_tr.json`.
   - `metin_alanlari`: DefineEditText başlangıç metinleri (HTML etiketleri
     çıkarılmış hâli anahtardır).
   - `statik_yazilar`: DefineText yazıları; satırlar `|` ile ayrılır ve
     satır sayısı korunmalıdır.
   `oyun/swf_yama.py` SWF'yi ilk istekte yamalar ve
   `download_assets/tr/` altında saklar. Sözlük ya da yama kodu değişince
   önbellek kendiliğinden yenilenir (`YAMA_SURUMU`).
3. **Yazı tipleri**: SWF'ye gömülü Arial Rounded / Eras Bold yazı
   tiplerinde `ğ Ğ İ ş Ş` yoktur. `oyun/swf_font.py` bu harfleri
   `assets/fonts/tr_*.swf` içinden ekler ve statik yazıların glif
   numaralarını yeniden eşler.

Resim olarak çizilmiş yazılar ("BUILD", "ADD ALLY", "Add Cash") bu yolla
çevrilemez.

## Ayarlar ve veriler

- `ayarlar.json`: `zaman_olcegi` (oyun hızı) ve `dunya` (bot simülasyonu). Sunucu bu dosyaya yazmaz.
- `ayarlar.yerel.json`: sunucunun yazdığı ayarlar (sayfadan seçilen hız, `oyun/ayarlar.py`). Depoya girmez,
  `ayarlar.json`'un üstüne biner.
- `oyun/denge.py`: PvP ganimet oranı, kupa ve saldırı hakkı.
- `saves/`: oyuncu ve bot kayıtları (depoya girmez). Hiç bot yoksa sunucu
  ilk açılışta 50 bot üretir (`araclar/bot_koy_uret.py`).
- `download_assets/`: indirilen oyun varlıkları ve Türkçe SWF önbelleği.

## Testler

```bat
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests
```

`tests/ortak.py`, `SE_KAYIT_DIZINI` ortam değişkeniyle testlerin geçici bir
kayıt klasörü kullanmasını sağlar. `requirements-test.txt` yalnızca testlere
gerekenleri (Hypothesis) ekler; oyuna ve paketlere girmez.

Testlerin hata yakalama gücü ölçülür, tahmin edilmez: yöntem, kaynaklar ve son
ölçüm `docs/TEST_OLCUMU.md`'de; ölçüm aracı `araclar/mutasyon_olc.py`.

## Windows programı (.exe) ve zip

Sürümde iki Windows biçimi çıkar (`.github/workflows/windows.yml`):

- **Tek dosyalık program:** `araclar/exe_paketi.py` PyInstaller `--onefile` ile üretir; giriş
  `araclar/exe_giris.py`. Oyun dosyaları ve Ruffle (SHA-512 denetlenmiş) `.exe`'nin içindedir. Kayıtlar,
  ayarlar ve modlar `.exe`'nin yanında durur (`oyun/yollar.py` BASE_DIR); ilk açılışta `ayarlar.json` ve
  `mods/` yanına kopyalanır, var olanlara dokunulmaz. Sunucu hazır olunca tarayıcı açılır (`SE_TARAYICI_ACMA=1`
  açmaz). PyInstaller yalnızca kendi sisteminin programını üretir: `.exe` CI'da `windows-latest`'te derlenir
  ve boş klasörden açılıp sınanır. Yerelde aynı betik o sistemin tek dosyalık programını üretir:
  ```bat
  python -m pip install -r requirements-exe.txt
  python araclar\exe_paketi.py --cikti dist
  ```
- **Zip:** `araclar/windows_paketi.py` (gömülü Python + `Social Empires.bat`); antivirüs `.exe`'yi engellerse
  yedek yol.

## Servis istekleri ve imza

Komutlar dışındaki bazı istekler (büyücü iksirleri, turnuvalar, hata
bildirimi) `data` alanında `<imza>;<json>` gönderir ve yanıtı da aynı biçimde
bekler. İmza, istemcideki `Config.SERVER_KEY` ile HMAC-SHA256'dır
(`oyun/istemci.py` içinde `imzali()`). Yanıtın JSON'u `{"result": ..., "data": ...}`
biçimindedir; istemci yalnızca `data`'yı okur.

## İçerik

- `config/tema_setleri.json`: eski etkinliklerin mağazaya açılan setleri.
  Yalnızca sprite ve küçük resmi arşivde eksiksiz olan eşyalar listelenir.
- `config/patch/kompu.json`: Büyücünün İksirleri teklifi (ödüller, büyücü
  bedelleri, metinler). Teklifin kimliği ve başlangıcı 30 günlük döneme göre
  `oyun/config.py` içinde hesaplanır.

## Bilinen eksikler

- Açık işlerin tam listesi `docs/gorev/BULGULAR.json`'dadır (durumu `acik` ya da `onay_bekliyor`).
  Eskiden burada yazan "Ruffle'da yere tıklanmıyor" (F0-01, çürütüldü), "oyuncu fotoğrafları boş"
  (OYN-05: oyuncu kendi resmini koyar, botlarda oyunun birim resmi) ve "haftalık turnuva kapalı"
  (KNF-04: açık) artık geçerli değil.
- 1.4.07'nin 5 günlük günlük ödül penceresi kapalı (KYT-02, OYN-11).
- `fx/p.miniFireball2.swf` orijinal arşivde de yok; `oyun/fx_yama.py` onu oyunun
  kendi `p.fireBall` efektinden türetir (VAR-01).

## Görseller

Sayfaya ya da oyuna kendi üretilmiş görsel (çizim, SVG illüstrasyon, yapay
zekâ resmi, emoji, CSS ile çizilmiş figür) eklenmez; oyunun ruhunu bozar.
Gerekirse yalnızca oyunun kendi görselleri olduğu gibi kullanılır (oyun
varlıkları ve `templates/img/`).
