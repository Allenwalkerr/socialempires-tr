# Denetim raporu: ekonomi-formuller (EKF)

Kapsam: `oyun/ekonomi.py`, `config.py`, `zaman.py`, `takvim.py`, `denge.py`, `config/`, `mods/`, `komutlar.py`'nin ekonomi komutları.
İstemci: `SocialEmpires1.4.07sec_fixed.swf`. Sunucu denemeleri `is/ekonomi-formuller/` altındaki kopyada yapıldı
(`demo1.py`, `d.py`, `f.py`).

### EKF-01: `collect_new` üretim seçimini (COLLECT_MULTIPLIER) ve içerideki birim sayısını yok sayıyor
- Önem: Orta
- İşaret: ✔ sunucu tarafı, ◐ istemci formülü
- Yer: oyun/ekonomi.py:19-31 (`apply_collect`); oyun/komutlar.py:36 (`COLLECT_MINUTES` tanımlı, hiçbir yerde kullanılmıyor), :428-438 (`collect_new`), :441-450 (`activate`, `cp` kaydı)
- Kanıt: İstemci `IsoElement/collect` @3208-3246: `Config.COLLECT_MULTIPLIER[cp-1]` okunur, kazanç `floor(building.collect) × Base.Iso.getResourceMultiplier(...)` ile çarpılır; @3300-3346 `iUnitsContainedWhenHarvested > 1` ise `(birim-1) × MULTIPLIER_PEASANTS (0,2)` eklenir. `Config/<sınıf>` sabitleri: `COLLECT_MINUTES=[5,60,240,480]`, `COLLECT_MULTIPLIER=[0.5,1,2,3]` (diziyi iki `initproperty` arasındaki `pushbyte/pushdouble` değerlerinden okudum, ◐). Komut argümanları (`IsoElement/collect`@3999): `[x, y, kasaba, id, iUnitsContainedWhenHarvested, getResourceMultiplier, cash]`; sunucu 4. argümanı hiç okumuyor. Çalıştırdım (`python -I demo1.py`): `activate ... 19 4` (8 saatlik seçim) sonra `collect_new ... 19 1 1 0` -> odun artışı **20**; `activate ... 1` (5 dk) sonrası yine **20** (ağacın `collect`'i 20). Beklenen: 60 ve 10.
- Etki: Üretim seçimi olan binalarda (`PopupCollect$/doShit`, `arIdsCollect`) istemci 8 saatlik seçimde x3 gösterir, sunucu x1 kaydeder; yeniden yüklenince oyuncunun gördüğü kaynak düşer. 5 dakikalık seçimde tersi: fazladan kaynak. Çok birimli (köylü) toplamada da fark çıkar. Testler (`tests/test_komutlar.py:136-150`) yalnızca `çarpan × collect`'i sınıyor; `cp`'yi hiç sınamıyor.
- Öneri: `collect_new`'da kayıtlı `cp`'yi ve 5. argümanı istemci formülüne göre uygula; bunu istemci formülünü kaynak alan bir testle koru.

### EKF-02: Çiftlik hasadında odun düşümü ve çiftliğin tükenmesi sunucuda yok
- Önem: Orta
- İşaret: ◐
- Yer: oyun/komutlar.py:428-438
- Kanıt: `IsoElement/collect` @3450-3505: bina alt kategorisi `SUBCATFUNC_BUILDING_FARM` ise `round(collect/3)` odun `canAfford` ise `adjustStatByType(-odun, WOOD)` ile düşülür; yetmezse çiftlik `removeElement(..., SELL_REASON_FARM_DEPLETED)` + `CMD_KILL` ile kaldırılır. Odun düşümü için ayrı komut yok; sunucuda `FARM`/`round(collect/3)` araması boş (`grep -in farm oyun/*.py` yalnızca ekonomi.py'deki ilgisiz satırlar).
- Etki: İstemci ekranda odunu düşürür, yeniden yüklemede sunucunun kaydı geri gelir: çiftlik hasadı oyunda bedava odun yolu.
- Öneri: Çiftlikte `collect_new` odun düşümünü sunucuda da uygula (istemci kararı `canAfford` ise).

### EKF-03: Sunucu hiçbir yerde "yeterli kaynak var mı" denetlemiyor; eksiye düşme yerine 0'a kıskaçlama bedava üretim veriyor
- Önem: Düşük
- İşaret: ✔
- Yer: oyun/ekonomi.py:5-16 (`apply_cost`: `max(x - cost, 0)`), oyun/komutlar.py:120-135 (`cash_ekle`, `kaynak_ekle`), :255-259 (`buy`), :425-428 (`collect_new` `cash_ekle(-a.tam(6))`), :640-643 (`push_queue_unit`)
- Kanıt: `python -I demo1.py` -> `collect_new ... cash=-1000` ile nakit 100 -> 1100; `buy ... fiyat_carpani=-5` ile odun 1020 -> 1170 (negatif çarpan `apply_cost`'ta kaynak ekliyor). Kaynak yetmezken `buy`/`push_queue_unit` eşyayı/birimi yine verir, bedeli 0'a kıskaçlar (kod okuması ◐).
- Etki: Tek kişilik ve çevrimdışı olduğundan düşük; ama bozuk/eski kayıt tekrarı (aynı komutun iki kez gelmesi) ya da bozuk istemci komutu kaynak yaratır.
- Öneri: Negatif çarpan/cash argümanını reddet; bedeli karşılanamayan `buy`/`push_queue_unit` komutunu uygulama (bazı komutlar `buy_time_packet` gibi zaten böyle).

### EKF-04: Zaman ölçeği yalnızca eşyanın 4 alanını ölçekliyor; kalan süreler ölçeklenmiyor, çok yüksek/düşük ölçekte bozuk değer çıkıyor
- Önem: Düşük
- İşaret: ✔ (değerler), ◐ (istemci etkisi)
- Yer: oyun/config.py:146 (`SURE_ALANLARI`), :196-207; oyun/zaman.py (belge "üretim/inşaat")
- Kanıt: `TIME_SCALE` 1,5/3/7/100/0,1 ile `get_client_game_config` çalıştırıldı: ölçek 100'de 457 süre alanı 1'den küçük (ör. eşya 8 `activation` "32.4" -> "0.324"), ölçek 0,1'de `.6g` üstel biçim üretiyor (eşya 229 `activation` 172800 -> "1.728e+06"). Ölçeklenmeyenler: istemci sabitleri `COLLECT_MINUTES` ([5,60,240,480], üretim seçimi süreleri), config `globals`: `COLLECT_HELP_SECONDS` (sunucu `accept_collect_help` 3600 sn çeker), `ATTACKS_PERIOD_HOURS`, `TIME_MACHINE`. `egitim_suresi` ile config aynı `.6g` formülünü kullandığı için eğitim süresi tutarlı (EKF dışı, ✔).
- Etki: Ölçek 3'te binalar 3 kat hızlı biter ama üretim seçimi süreleri, arkadaş yardımı ve PvP hakkı normal hızda kalır; ölçek büyükse süre "0"a yuvarlanıp anında olur (istemcinin `convert_i`/`parseInt` kullanımı doğrulanmadı ?). Taban config'te 1 saniyeden kısa süreler zaten var (eşya 144 `activation` "0,36").
- Öneri: Ölçeklenen/ölçeklenmeyen süreleri belgele; ölçekli değeri en az 1 sn'ye ve üstel biçimsiz yaz.

### EKF-05: 2030 sonrası bayramlar sessizce yok; bir miladi yıla iki bayram düşebilir
- Önem: Düşük
- İşaret: ✔
- Yer: oyun/takvim.py:34-44 (`_hijridate_ile`), :47-55 (`bayram`); requirements*.txt (`hijridate` yok)
- Kanıt: `python -I`: `takvim.bayram(2031,'ramazan')`, `(2032,..)`, `(2033,..)`, `(2035,'kurban')` hepsi `None`; `grep hijri requirements*.txt` boş. Ayrıca `_hijridate_ile` yılı için tek tarih döner, oysa 2033'te Ramazan Bayramı iki kez (Ocak ve Aralık) gelir; ikincisi hiç bulunmaz. 2026-2030 tablo tarihleri (3/20, 5/27, 3/9, 5/16, 2/4, 4/13) Diyanet takvimiyle uyumlu görünüyor (tablo dış kaynak, ?).
- Etki: Kurulumda kitaplık yoksa 2031'den sonra bayram etkinlikleri ve mağaza setleri hiç açılmaz, hata da görünmez.
- Öneri: Kitaplığı gereksinime ekle ya da tabloyu uzat; `None` olduğunda uyarı yaz.

### EKF-06: `mods.txt` satırındaki `.json` soneki ayıklanmıyor (etkisiz satır)
- Önem: Düşük
- İşaret: ◐
- Yer: oyun/config.py:62 (`mod.replace(".json", "")` sonucu atılıyor)
- Kanıt: Satır `mod_x.json` yazılırsa yol `mods/mod_x.json.json` olur, `os.path.exists` yanlış, mod sessizce atlanır (dosya başlığı "uzantı yazmana gerek yok" diyor, ama yazılırsa uyarı yok). Ayrıca mod yok/hatalıysa `jsonpatch` istisnası modül içe aktarılırken (`config.py:112`) bütün sunucuyu düşürür.
- Etki: Mod yazarı etkisiz mod görür.
- Öneri: Sonucu değişkene ata; bulunamayan modu uyar.

### EKF-07: `docs/inceleme/1407-config-hatti.md` depodaki yama durumuyla uyuşmuyor
- Önem: Düşük
- İşaret: ◐
- Yer: docs/inceleme/1407-config-hatti.md tablosu; config/patch/
- Kanıt: Belge `graveyard`, `level_up_tips`, `mission_goals`, `missions_0_1`, `new_daily_bonus`, `soulmixer_temp`, `unit_collections`, `viral_*` yamalarını ölçüyor; `config/patch/` içinde yalnızca `0-language_en`, `1-mega_patch`, `2-unit_patch`, `kompu`, `turnuva`, `yeni_icerik` var. `kompu` belgede "çatışır" (28 işlemin 27'si farklı) ama hâlâ uygulanıyor. Ölçümü yeniden üretemedim: `araclar/config_hatti.py` upstream yama klasörü ve ikinci SWF istiyor, kopyada yok (?).
- Etki: Belge, kimin kazandığı konusunda yanıltır; `kompu` istemcinin kendi 1.4.07 değerlerinin üstüne yazıyor olabilir.
- Öneri: Belgeyi yeniden üret; `kompu` için "çatışır" kararını kapat.

### EKF-08: Yükseltmede XP ve fark maliyeti kayda farklı yansıyor olabilir
- Önem: Düşük
- İşaret: ?
- Yer: oyun/komutlar.py:255-259 (`buy`), :296-302 (`sell`), :352-358 (`upgrade`)
- Kanıt: `IsoBuilding/upgrade` @525-619: istemci eski binayı `removeElement(..., SELL_REASON_UPGRADE)` (`sell`, 5. arg 0 -> sunucu `satis_iadesi` ile %5 verir) ardından `buy` (arg5=0, çarpan 1: sunucu yeni binanın tam bedelini düşer ve yeni xp'yi ekler) gönderir. @259-263 ve @394'te istemci `Player.adjustStatByType` ile `xp`yi negatif girdiyle çağırıyor; eski binanın xp'sinin geri alındığını düşünüyorum ama hangi değerin düşüldüğünü doğrulamadım. Sunucu `sell`de xp geri almıyor.
- Etki: Doğruysa her yükseltmede sunucu xp'si istemcininkinden eski binanın xp'si kadar fazla olur (yeniden yüklemede seviye atlama).
- Öneri: İstemcinin yükseltme xp'sini bayt kodundan netleştir; `sell` sebebi `UPGR` ise xp'yi geri al.

### EKF-09: PvP/denge sabitleri üç yerde elle kopyalanmış, config'e bağlı değil
- Önem: Düşük
- İşaret: ✔ (karşılaştırma)
- Yer: oyun/denge.py:11-12, oyun/pvp.py:27-28, config `globals`
- Kanıt: `denge.SALDIRI_HAKKI=3`, `SALDIRI_PERIYODU=6*3600` ve `pvp.SALDIRI_HAKKI=3`, `SALDIRI_PERIYODU=6*3600` aynı; config `ATTACKS_PERIOD_MAX=3`, `ATTACKS_PERIOD_HOURS=6` ile bugün eşit, ama hiçbiri config'ten okunmuyor (`grep` ile doğrulandı).
- Etki: Config yaması bu değerleri değiştirirse istemci ve bot dünyası ayrışır.
- Öneri: Tek kaynak: config `globals`.

## Bakıldı, sorun bulunmadı

- Satış iadesi: istemci `Base/bulldozeBuilding` `floor(parseInt(cost) / Config.DIVISOR_SELL(20))`; sunucu `int(-0.05 × cost)`. Config'in bütün eşyalarında karşılaştırdım: 0 fark (✔).
- `unlock_building`: `Config.MULTIPLIER_UNLOCK = 0,3333…`, sunucuda `1/3`; n=1..199 için `ceil` sonucu aynı (✔).
- Eğitim bedeli (`BuildingQueueManager/addUnit`): kuyruk sınırı `remainingUnits < 5`, `ceil(cost × 0,9)`, yemek `ceil(bedel × FOOD_PER_GOLD_INTRAINING=2)`, köylüde yemek yok, Ruh Karıştırıcı'da `sm_training_time`: sunucu uyumlu (◐; indirimin alt kategoriye göre koşulu `lookupswitch`te, doğrusal okumada kesinleştiremedim).
- `buy_unit_pack`: `UnitPacksManager/buyPack` (`int(fiyat × adet)`, `ifnge` ile 8 ve 2 eşikleri, `int(x × oran + 0,5)`) sunucuyla aynı (◐).
- Hızlandırma bedeli `ceil(kalan/3600) × COST_SPEED_UP_UNIT_QUEUE(1)`, eğitim süresinin ölçekli değerle hesabı (config ve `egitim_suresi` aynı `.6g`).
- Seviye çevirileri (`get_level_from_xp`, `get_xp_from_level`, `seviye_araligi`): `>=` sınırı istemcideki `checkForLevelUp` ile tutarlı (kod okuması).
- Takvim: UTC+3 sabit saat dilimi, gün sınırı `baslangic <= gun < bitis`, yıl geçişi (31 Aralık 2026'da Yılbaşı 29 Aralık-4 Ocak), `milli_bayram` 29-30 Ekim; çalıştırıldı (✔). 2026-2030 bayram tablosu Diyanet'e uyuyor görünüyor (dış kaynak, ?).
- `remove_duplicate_items` (sonradan gelen kalır), `kompu_teklifi` 30 günlük dönem, config önbellek anahtarı (ölçek, dil, takvim setleri).
- `time_ff`/`zamani_ilerlet`: paket sayacı denetimi var, `< 1e9` işaret değerleri kaydırılmıyor.
