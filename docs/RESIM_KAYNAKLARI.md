# Bot profil resimleri: kaldırıldı

Bu belge eskiden botlara internetten (Wikimedia) alınmış profil resimlerini sayıyordu. O resimler kaldırıldı
(OYN-04): görsel kuralı gereği sayfada ve oyunda yalnızca oyunun kendi resimleri kullanılır (`CLAUDE.md`). Botların
adları ve resimleri artık oyunun kendi birimlerinden gelir (`oyun/bot_kimlik.py`, `SILINEN_PORTRELER`). Eski liste
depo geçmişindedir.

## `templates/img/` dosyalarının kaynağı (DNT-36, TRA-04)

İşaretler: ✔ doğrulandı, ? doğrulanmadı. Denetim 12 Kasım 2026.

### Çatallanılan projeden, olduğu gibi (✔ SHA-1 aynı)

Depo `236916e` ("temiz başlangıç") ile geldi. Her biri AcidCaos/socialemperors'ın
`54df29e1bc5905c72a55a5fd0dda449e7a419019` sürümündeki `templates/img/<ad>` ile bayt bayt aynı:

| Dosya | Kullanıldığı yer |
| --- | --- |
| `Gamebar_byTrevo.png` | `templates/play.html` |
| `cash.png` | `oyun.html`, `play.html`, `cheat.html` |
| `discord.png` | `oyun.html`, `play.html` |
| `github.png` | `play.html` |
| `icon.gif` | `login.html`, `tasima.html`, `gunluk.html` |
| `logo.png` | `login.html`, `oyun.html`, `hazine.html` |

### Oyunun kendi SWF'sinden (✔ araçla)

`templates/img/oyun/` altındaki 11 dosyayı `araclar/swf_resimleri.py` çıkarır (#18). Karakter numaraları aracın
`SECILENLER` listesindedir. 10 dosya istemcinin ana SWF'sinden, `bayrak-tr.png` ise `buildingsprites/flagtr.swf`'den
(Turkey Flag, öğe 174) gelir. Resimler değiştirilmez, yalnızca SWF'nin önceden çarpılmış alfası düz alfaya çevrilir.
Dosyalar şunlardır:

- `pencere.png`
- `gokyuzu.png`
- `altin-kutu.png`
- `kahve-dugme.png`
- `beyaz-hap.png`
- `cubuk-bos.png`
- `cubuk-dolu.png`
- `altin-cerceve.png`
- `bronz-cerceve.png`
- `kirmizi-hap.png`
- `bayrak-tr.png`

### Kaynağı yazılı olmayanlar (?)

| Dosya | Durum |
| --- | --- |
| `profile/1025.png` | `236916e` ile geldi; çatallanılan projenin `templates/img/` altında bu yolda yok. Varsayılan portre (`oyun/bot_kimlik.py` `VARSAYILAN_PORTRE`). |
| `simge-192.png`, `simge-512.png` | #8 ile geldi (uygulama ve web simgesi, `oyun/sunucu.py` manifest, `araclar/android_paketi.py`). Nereden alındığı commit'te yazılı değil. |

Bu üçünün oyunun kendi görseli olduğu bu depodan doğrulanamadı. Sahibi ya da bir sonraki denetim oyun varlıklarında
karşılığını bulursa buraya yazılır. Görsel kuralı (`CLAUDE.md`) gereği yerlerine yeni çizim konmaz.
