# Denetim raporu: kayit-goc (kayıt yazma, yedek, sürüm göçü, taşıma)

> İlk dört bulgu bağımsız denetçinindir; denetçi sahibinin isteğiyle (kullanım payı) durdurulmuştu. Rapor 12 Kasım 2026'da
> tamamlandı (DNT-40): KYG-05 ve sonrası `oyun/surum.py`, `oyun/kayit_yedek.py` ve `oyun/tasima.py`'nin denetimidir.

Kod kopyası: `K` (commit `187e84f`). Denemeler `is/kayit-goc/` altında, K'nin kopyasında (`is/kayit-goc/kok`), her biri
ayrı `SE_KAYIT_DIZINI` ve `SE_TABAN_DIZINI` ile yapıldı. Betikler: `is/kayit-goc/t1.py` … `t5.py`, `alanlar.py`, `bak.py`.
Ortak ortam: `SE_KAYIT_DIZINI=<is>/sN SE_TABAN_DIZINI=<is>/taban PYTHONDONTWRITEBYTECODE=1`.

Not: brief'teki `oyun/aktarim.py` kayıt aktarımı değil, HTTP önbellek/sıkıştırma katmanıdır; kayıt içe/dışa aktarma
`oyun/kayit_yedek.py` ve `oyun/tasima.py` içindedir. `tests/test_aktarim.py` buna göre okunmalı.

### KYG-01: Sayı türünde `pid` taşıyan içe aktarılmış kayıt sunucunun bir daha açılmasını engelliyor
- Önem: Yüksek
- İşaret: ✔
- Yer: `oyun/kayit_yedek.py:81-82` (kimlik `str(...)` ile denetleniyor), `oyun/kayit.py:104,110-112`,
  `oyun/kayit.py:288` (`assert isinstance(USERID, str)`)
- Kanıt: `t2.py 777 0.05a`: `playerInfo.pid = 777` (int), `version = "0.05a"`, zarf `kimlik = "777"` olan bir yedek
  `zarfi_ac` denetiminden geçti (`zarf kabul 777`), `geri_yukle` dosyayı yazdı, ardından `load_saved_villages()` içinde
  `_yukleme_duzeltmeleri` göç yaptığı için `save_session(777)` → `session(777)` → `AssertionError`. Yükleme döngüsü
  yarıda kaldı: bellekte 51 kayıttan yalnızca 13'ü (`saves'ta 13 kayit`). Ardından `import oyun.sunucu` (sunucunun
  açılışı) → `SUNUCU ACILAMADI AssertionError AssertionError()`; `saves/777.save.json` 0.05a olarak duruyor, her
  açılışta aynı yerde çöküyor. `zarfi_ac`'taki `kaydi_dogrula` kopyada göç yapıp başarılı sayıyor, `pid`'in türüne
  bakmıyor; `gecerli_uid(str(pid))` de geçiyor.
- Etki: Elle düzenlenmiş/kötü niyetli bir `.seyedek.json` (ya da /tasima ile ev ağındaki bir gönderici) bir kez
  yüklenince sunucu açılmaz; giriş sayfası (`/` her istekte `load_saved_villages` çağırır) da 500 verir. Android'de
  dosyayı silmenin yolu yok (kodun kendi yorumu, `kayit.py:96`), oyuncunun bütün kayıtları erişilemez olur. Aynı yol,
  sürümü güncel olsa bile seviyesi XP'ye uymayan (`_seviyeyi_duzelt` True dönen) her kayıtta da tetiklenir.
- Öneri: İçe aktarmada `pid`'in `str` olmasını şart koş; yükleme döngüsünde kayıt anahtarını `str(USERID)` ile kullan
  ve kayıt başına hatayı yakala (bir kaydın düzeltmesi bütün yüklemeyi düşürmesin). Bu durum için test ekle.

### KYG-02: İçe aktarma/taşımadan önceki kayıt yalnızca `.bak`'ta, o da ilk kayıtta (çoğu zaman hemen) siliniyor
- Önem: Yüksek
- İşaret: ✔
- Yer: `oyun/kayit_yedek.py:89-100` (`geri_yukle`), `oyun/kayit.py:454-457` (`save_session` her yazımda `.bak`'ı
  ezer); `oyun/tasima.py:225` aynı `geri_yukle`'yi kullanır.
- Kanıt: `t4.py`: canlı kayıtta `coins = 999999`, aynı kimlikle `coins = 5` olan yedek yüklendi.
  Güncel sürümlü yedekte: `canli coins: 5 | .bak coins: 999999`, ardından tek bir `save_session` (oyundaki ilk komut,
  bot dünyasının bir turu ya da giriş) → `.bak coins: 5`; `backups/` boş. Eski sürümlü (0.05a) yedekte göç yüklemede
  hemen kaydettiği için daha geri_yukle dönmeden `.bak coins: 5`: önceki hâl hiç kalmıyor.
  Modül belgesi ("eski kayıt otomatik olarak .bak dosyasına alınır") ve tasima'nın yorumu ("eski hâli .bak olarak
  saklanır", `tasima.py:6,217`) bunu güvence olarak sunuyor.
- Etki: Yanlış dosyayı (eski bir yedeği, başka cihazın eski hâlini) kendi imparatorluğunun üzerine yükleyen oyuncu
  ilerlemesini geri alamaz; geriye en iyi ihtimalle günün ilk günlük yedeği (`gunluk_yedek/`) kalır, o da sunucu
  o gün o kaydı görmüşse.
- Öneri: Üzerine yazmadan önce zaman damgalı, budanmayan ya da ayrı adlı bir yedek al (`backup_session` benzeri) ve
  oyuncuya yolunu bildir; geri dönüşü test et.

### KYG-03: Bozuk kayıt `.bak`'tan geri alınınca göç ve düzeltmeler atlanıyor; istemciye göçmemiş kayıt gidiyor
- Önem: Yüksek
- İşaret: ✔
- Yer: `oyun/kayit.py:111` (`save.pop("_bak_kullanildi", False) or _yukleme_duzeltmeleri(save)`: kısa devre)
- Kanıt: `t5.py`: 0.05a kayıt ilk açılışta göçtü (`dosya 0.08a | .bak 0.05a`: göçten sonraki ilk yazımda `.bak`
  göç öncesi hâldir). Canlı dosya yarım yazıldı (`{"yarim`); ikinci açılışta `.bak'tan geri alindi` →
  `2. acilis bellekte: 0.05a | purchasedShields var mi: False | dosya: 0.05a`. `kaydi_dogrula` göçü yalnızca kopyada
  denediği için kayıt "geçerli" sayıldı, ama asıl kayıt göçmedi, dosyaya da 0.05a olarak yazıldı.
- Etki: O oturum boyunca istemci 1.4.07 alanları olmayan, eski görev numaralı kaydı alır; projenin kendi şemasına göre
  (`kayit_semasi.py`, ör. `ShieldManager`, `PopupRecruitment$/canOpen` `undefined.indexOf`) istemci hata verir ya da
  NaN gösterir. Göç öncesi yedek (`goc_oncesi_yedek`) de alınmaz; seviye düzeltmesi yapılmaz. Bir sonraki açılışta göç
  olur, ama 0.06a→0.07a görev çevirisi o arada oynanan oturumun kazandıklarını da "eski" sayabilir.
- Öneri: `.bak` kullanıldığında da `_yukleme_duzeltmeleri` çalışsın (önce düzelt, sonra kaydet); bunun testi yok.

### KYG-04: 0.06a kaydın görev numarası çevirisi makineye bağlı: başka cihaza taşınınca/içe aktarılınca yapılmıyor
- Önem: Orta
- İşaret: ✔
- Yer: `oyun/kayit.py:179-203` (`eski_gorev_numaralari` yalnızca yerel `backups/<uid>.goc-*.save.json`'a bakar),
  `oyun/surum.py:136-141`
- Kanıt: `t3.py`: aynı 0.06a kayıt (`completedMissions = rewardedMissions = [136]`, `tablo[136] = 148`).
  Yerelde `asil.goc-0.05a.save.json` olan makinede → `[148]`; göç öncesi yedeği olmayan makinede (içe aktarma, /tasima,
  yeni kurulum) → `[136]`. Yedek zarfı (`zarf`) göç öncesi yedeği taşımıyor.
- Etki: 0.06a döneminde dışa aktarılmış bir imparatorluk yeni bilgisayarda/tablette açılınca 0926 numaralı görevler
  1.4.07'de başka bir hedefin numarası olarak "bitmiş" kalır (kodun kendi açıklamasına göre oyuncu onları bir daha
  alamaz, asıl karşılığı ise yapılmamış görünür). Göç bir kez yapıldığı için (sürüm 0.08a olur) sonradan düzelmez.
- Öneri: Eski numara kümesini kaydın içine (göç sırasında) yaz ya da zarfa ekle; yedek yoksa davranışı kararlaştırıp
  kayda ve teste bağla.

### KYG-05: Yedek yükleme ve Wi-Fi taşıma, bot dünyasının yazılmamış değişikliklerini siliyor
- Önem: Düşük
- İşaret: ✔ (test ve bozma)
- Yer: `oyun/kayit_yedek.py` `geri_yukle` (yedek yükleme ve `oyun/tasima.py` `tasima_al` bunu kullanır)
- Kanıt: Bot dünyası bot kayıtlarını `BOT_YAZMA_ARALIGI` (5) turda bir yazar (`dunya._bekleyen_botlar`). `geri_yukle`
  yazdıktan sonra `load_saved_villages()` ile bütün kayıtları diskten yeniden okuyordu ama önce bekleyenleri yazmıyordu.
  Giriş sayfası (`oyun/sunucu.py` `login`) bunu yapıyor. Testte bellekteki bot değişikliği (`coins = 123456`) yedek
  yüklemeden sonra kayboldu.
- Etki: Yedek yükleme ya da Wi-Fi taşıma anında botların son turlardaki ekonomisi ve akınları kaybolur. Oyuncunun
  kendi kaydı her komutta yazıldığı için etkilenmez.
- Düzeltme: `geri_yukle` aynı kilit (RLock) altında önce `dunya.etkin.bekleyenleri_yaz()`'ı çağırır, sonra yedeği
  yazar ve kayıtları yeniden okur. Test: `tests/test_kayit_gocu.py`
  `test_geri_yukleme_bot_dunyasinin_bekleyenini_kaybetmez`; çağrı kaldırılınca düşer.

### KYG-06: Taşınan kayıttaki yardımcı ve saldırgan botlar yeni cihazda yok (görünüş)
- Önem: Düşük
- İşaret: ✔ (istemci bayt kodu)
- Yer: bot kimlikleri her cihazda rastgele üretilir (`araclar/bot_koy_uret.py`); taşınan kayıt
  `attrs.si`, `viralOffers[..].friends`, `PVPattacksReceived` içinde gönderen cihazın bot kimliklerini taşır.
- Kanıt:
  - `PopupRecruitment/refreshFotos` @452-472: `friendsInfoMap[kimlik]` yoksa ad atlanır (null denetimi), yuvada "- -" görünür.
  - Resim isteği `graph.facebook.com/<kimlik>/picture` bilinmeyen kimlikte varsayılan portreye yönlenir (`oyun/istemci.py`).
  - Saldırı günlüğündeki intikamda `get_neighbor_info` bilinmeyen kimliğe hata yanıtı verir, 500 değil (`oyun/oyuncu.py`).
- Etki: Çökme yok. Taşıma sonrasında eski yardımcıların adı görünmez, eski saldırganlara intikam alınamaz. Sayılar
  (yardımcı sayısı, ödül) doğru kalır.
- Karar: Düzeltilmedi, tek kişilik kullanımda önemsiz. Gerekirse taşıma bot kayıtlarını da götürür.

### KYG-07: Tanınmayan sürüm etiketi göç adımlarına uymuyor
- Önem: Düşük
- İşaret: ✔ (okuma)
- Yer: `oyun/surum.py` `migrate_loaded_save`
- Kanıt: Sürüm `version_code`'dan farklı ama bilinen adımların hiçbirine uymuyorsa (ör. daha yeni bir uygulamadan gelen
  `0.09a`) işlev hiçbir şeyi değiştirmeden True döner. Kayıt yine `kaydi_dogrula`'nın 1.4.07 alan denetiminden
  (`guvence_hatalari`) geçmek zorundadır. Eksik alanı olan kayıt yüklenmez, kenara alınır.
- Etki: Böyle bir kayıt her açılışta bir kez gereksiz yere yazılır. Veri kaybı yok.
- Karar: Dokunulmadı.

### Denetlenip sorunsuz bulunanlar (✔ okuma)

- **`kayit_yedek.zarfi_ac`:**
  - Biçim ve SHA-256 özeti denetleniyor.
  - Kayıt bir kopyada göç ettirilip `kaydi_dogrula`'dan geçiriliyor.
  - Kimliğin `str` olması, zarfla aynı olması ve `gecerli_uid` şartı var (KYG-01).
  - Başka imparatorluğun üzerine yazma engelleniyor (`cakisma`).
- **`geri_yukle`:**
  - Yol kimlikten `safe_join` ile kuruluyor, kötü kimlik reddediliyor.
  - Önceki hâl hem `.bak`'a hem adlı kalıcı yedeğe alınıyor (KYG-02).
  - Yazım geçici dosya, `fsync` ve `os.replace` ile yapılıyor.
- **`tasima`:**
  - Gönderici ayrı bir sunucu; yalnızca iki uç sunuyor ve 10 dakika açık kalıyor.
  - Kod başlıkta gidiyor, `hmac.compare_digest` ile karşılaştırılıyor.
  - Adres başına 5 ve toplam 30 yanlış denemeden sonra kod geçersiz oluyor.
  - Alan taraf yalnızca özel IPv4 adresine bağlanıyor ve yönlendirmeyi izlemiyor.
  - Okunan veri `EN_BUYUK` ile sınırlı.
  - Botlar listelenmiyor.
  - Alınan kayıt yedek yüklemenin bütün denetimlerinden geçiyor.
  - Not: `_gonderim["gonderilen"]` kilitsiz artıyor; yalnızca ekrandaki sayaç, önemsiz.
- **`surum.migrate_loaded_save`:**
  - Adımlar sırayla ve yalnızca kendi sürümünde çalışıyor.
  - 0.06a→0.07a görev çevirisinin makineye bağlılığı KYG-04'te anlatıldı (KAR-31: olduğu gibi kalır).

