# Denetim raporu: sunucu-komutlar (SNK)

Kapsam: `oyun/sunucu.py`, `komutlar.py`, `istemci.py`, `ada.py`, `oyuncu.py`; ilgili 5 test dosyası (hepsi geçiyor: 96+22+14+2+20 test).
Araçlar: `is/sunucu-komutlar/` (`g.py` istemci komut listesi, `f1.py` bozuk girdi, `f2.py` yeniden gönderim, `f3.py` eşzamanlılık).
Ekonomi alanında raporlananlar (collect_new çarpanı, negatif çarpan, kaynak yeterliliği) tekrarlanmadı.

### SNK-01: Seviye atlama ödülü sunucuda hiç verilmiyor
- Önem: Orta
- İşaret: ✔ sunucu, ◐ istemci
- Yer: oyun/komutlar.py:1059-1066 (`rt_level_up`)
- Kanıt: İstemci `PlayerStatus/checkForLevelUp` seviyeyi bir artırıp yalnızca `CMD_RT_LEVEL_UP [iLevel]` gönderir. Ödülü ise `PopupLevelUp/<kurucu>` (@420-435) `levels[i].reward_amount/reward_type` ile `Player.adjustStatByType` çağırarak yerelde uygular; bunun için komut yok. Sunucuda `reward_amount` araması boş. Çalıştırdım (`f2.py`): `rt_level_up [2]` sonrası seviye 2, odun 790 -> 790 (config'te seviye 2'nin ödülü 50 odun). Config toplamı: 450 odun, 96 nakit, 50 taş, 50 yemek.
- Etki: Seviye atlayınca ekranda görünen ödül, oyun yeniden yüklenince (kayıt sunucudan okunur) kaybolur; 96 nakit dahil.
- Öneri: `rt_level_up`'ta atlanan seviyelerin ödülünü (istemcinin uyguladığı biçimde) kayda yaz; istemci formülünü kaynak alan test ekle.

### SNK-02: Yeniden gönderilen komut paketi iki kez uygulanıyor (first_number/tries yok sayılıyor)
- Önem: Orta
- İşaret: ✔ sunucu, ◐ istemci davranışı
- Yer: oyun/istemci.py:96-111 (`command_response`), oyun/komutlar.py:184-203
- Kanıt: İstemci `CommandManager/sendPacket` paketle birlikte `first_number`, `tries`, `ts` gönderir; `processCommandsTimeout` / `ioErrorHandlerCommands` aynı paketi `tries` artırarak yeniden yollar. Sunucu yalnızca `commands`'ı okur. `f2.py`: aynı paket (`first_number=5`, `tries=1` ve `2`) iki kez gönderildi -> iki bina eklendi, odun 850 -> 790 (iki kez düştü).
- Etki: İstemci yanıtı alamazsa (kilit uzun sürerse, bağlantı kesilirse) aynı komutlar ikinci kez uygulanır: çift bina, çift bedel, çift ödül.
- Öneri: Kullanıcı başına son işlenen `first_number` + paket uzunluğunu kayıtta tut, işlenmiş paketi tekrar uygulama.

### SNK-03: Bazı komutlar kaynak eşya yokken de depoya/haritaya eşya ekliyor (tekrar koruması tutarsız)
- Önem: Orta
- İşaret: ✔
- Yer: oyun/komutlar.py:303-309 (`store_item`), :934-941 (`add_unit_warehouse`), :943-950 (`place_warehoused_item`), :990-1005 (`buy_cash` ile aynı sınıf değil, yalnızca sunak koşulu)
- Kanıt: `place_gift` depo sayacını denetliyor ama `store_item` eşya bulunmasa da `depo_ekle` çağırıyor; `f2.py`: haritada olmayan koordinatta `store_item` üç kez -> `gifts[1] = 3`. `add_unit_warehouse` birim bulunmasa da listeye ekler; `place_warehoused_item` depoda olmasa da haritaya birim koyar.
- Etki: SNK-02 ya da bozuk bir komut tekrarı eşya/birim çoğaltır (ör. kahraman, nadir birim).
- Öneri: Eşya bulunmadıysa ekleme; depodan yerleştirmede sayaç denetle (`place_gift` gibi).

### SNK-04: Bozuk girdi 500 döndürüyor (çökme yok, ama tutarsız)
- Önem: Düşük
- İşaret: ✔
- Yer: oyun/istemci.py:78 (`map`), :106 (`command_response`: `data.get`), :168/:199 (`veri.get` JSON dizi iken), :230 (`item_id`), :254 (`level_id`); oyun/komutlar.py:187
- Kanıt: `f1.py` ile Flask test istemcisi: komut paketi JSON'u `[1,2]`, `"x"`, `{"commands":"abc"}`, `{"commands":5}`, `{"commands":["buy"]}` -> 500; `get_player_info.php map=abc` -> 500; bilinmeyen `USERID` -> 500 (`'NoneType' object is not subscriptable`); `kompu_try` ve `get_up_data` ve `tournaments/*` `data=[1]` -> 500; `item_id=x`, `level_id=x` -> 500. Hepsi genel hata işleyicisinde yakalanıyor: süreç ayakta, kayıt bozulmadı. `NaN`/`Infinity` argümanı komut içi hatayla geri alınıyor, 200 (`Arg.tam` yalnızca ValueError yakalar, `inf` OverflowError verir; dış `except` kurtarıyor).
- Etki: Yalnızca bozuk/kötü niyetli istek; istemci hatalı yanıtta "senkron hatası" gösterebilir.
- Öneri: Girdi türünü denetle (`isinstance(veri, dict)`), `int()` dönüşümlerini try içine al; bilinmeyen USERID için 404 + JSON.

### SNK-05: Ev ağı kipinde (`ev_agi`) uçlar yetkisiz; kayıt listesi, komut ve yedek yükleme ağdaki herkese açık
- Önem: Orta (yalnızca `ayarlar.json` `ev_agi` açıkken)
- İşaret: ◐
- Yer: oyun/sunucu.py:87-110 (`_koken_denetimi`), :186-196 (`login` GET kayıtları UID'leriyle listeler), oyun/istemci.py:96 (`command.php`), oyun/kayit_yedek.py:117
- Kanıt: `ev_agi` ile sunucu `0.0.0.0` dinler (`sunucu.py:calistir`). Host denetimi yalnızca `remote_addr` loopback iken çalışır; LAN'dan gelen istek için her Host kabul. `command.php`, `get_player_info.php`, `kayit/yukle` oturum ya da parola istemez: kimlik yalnızca istek gövdesindeki `USERID`, ve girişteki sayfa bütün oyuncu UID'lerini gösterir. Hile paneli ise loopback'e bağlı (`hile.py:18`). Çalıştırıp LAN'dan denemedim.
- Etki: Aynı ağdaki başka bir cihaz kaydı değiştirebilir, silebilir ya da yedekle ezebilir.
- Öneri: `ev_agi` kipinde komut ve yedek uçları için oturum çerezi/jeton iste ya da seçeneğin riskini ayarlarda belirt.

### SNK-06: Bina arama `esya_bul(x, y)` kimliksiz; aynı kareyi paylaşan başka eşya yanlış seçilebilir
- Önem: Düşük
- İşaret: ◐
- Yer: oyun/komutlar.py:86-90 (`esya_bul`), kullanımları: `orient` (:278), `push_unit`/`pop_unit` (:500-515), `upgrade` (:355), `accept_collect_help` hariç (kimlikli)
- Kanıt: `orient`, `upgrade`, `push_unit`, `pop_unit` binayı yalnızca (x, y) ile bulur; liste sırasındaki ilk eşya alınır. İstemci bu komutlarda bina kimliğini göndermiyor (`g.py` çıktısı: `orient` 4 argüman). Aynı koordinatta birim ya da başka eşya varsa (birimler bina kapısında doğar) yanlış eşyanın yönü/seviyesi/içeriği değişir.
- Etki: Nadir; yanlış eşya yükselir ya da birim yanlış binaya yazılır.
- Öneri: Birden çok eşya eşleşirse bina türünü (`type == "b"`) tercih et.

### SNK-07: Açık kasaba bellekte; sunucu yeniden başlayınca kasaba numarasız komutlar kasaba 0'a gider
- Önem: Düşük
- İşaret: ◐
- Yer: oyun/oyuncu.py:18-23 (`_acik_kasabalar`), komutlar.py `push_queue_unit`, `pop_queue_unit`, `speed_up_queue`, `buy_first_purchase`
- Kanıt: `acik_kasaba` kayda yazılmayan sözlükten okur, yoksa 0. İstemci `get_player_info`'yu yalnızca açılışta/kasaba değişiminde ister; sunucu oyun sürerken yeniden başlarsa (ya da giriş sayfası `load_saved_villages` ile belleği yeniler, o sözlüğe dokunmaz ama iki sekme aynı USERID'yi paylaşır) ikinci kasabadaki eğitim kuyruğu komutları birinci kasabaya uygulanır. Ayrıca `harita()` (komutlar.py:83) geçersiz kasaba numarasını sessizce 0'a çeviriyor.
- Etki: İkinci kasabada eğitim bedeli/birim birinci kasabadan düşer.
- Öneri: Komutun kasabasını kuyruğun binasından (qid) bul; bilinmeyen kasabada komutu reddet.

### SNK-08: `login()` (GET ve POST "/") her çağrıda bütün kayıtları diskten yeniden yüklüyor
- Önem: Düşük
- İşaret: ◐
- Yer: oyun/sunucu.py:186-196
- Kanıt: `load_saved_villages()` `__saves`'i yeni nesnelerle değiştirir. `kompu_try_response` (istemci.py:161) ve `kompu_hurry_up` kaydı kilit dışında alır, kilitte onu değiştirir ve `save_session(uid)` yeni nesneyi yazar: araya giren bir yeniden yükleme değişikliği sessizce yok eder. Eşzamanlı okuma tarafı sorunsuz: `f3.py` ile dört iş parçacığı 6 sn boyunca `get_player_info` çağırırken beşinci iş parçacığı kilit altında kaydı değiştirdi: 3709 istek, 0 hata.
- Etki: Çok dar yarış; ikinci sekmede giriş sayfasını açmak da bellek durumunu diskten değiştirir.
- Öneri: `kayit_oturumu(uid)`'i kilit içinde al; giriş sayfasında zorunlu yeniden yükleme yapma.

### SNK-09: İstek günlükleri sınırsız büyüyor ve kimliksiz yazıyor
- Önem: Düşük
- İşaret: ◐
- Yer: oyun/komutlar.py:216-228 (`komut_gunlugu.jsonl`), oyun/istemci.py:236-245 (`report_error.php`), :329-341 (`http_gunlugu.jsonl`)
- Kanıt: Üç dosya yalnızca `a` kipinde açılır; boyut sınırı/döndürme yok (`grep` ile yedek/temizlik kodu bulunmadı). `report_error.php` ve bilinmeyen `dynamic` yolu her istek gövdesini (en çok `MAX_CONTENT_LENGTH` = 40 MB) olduğu gibi yazar.
- Etki: Uzun oynayınca ya da döngüde istekle disk dolar; Android'de depolama sorunu.
- Öneri: Boyut sınırı + döndürme; hata raporunu kırp.

## Bakıldı, sorun bulunmadı

- Argüman sırası/arity: istemcinin `addCommand` çağrılarından (158 komut) arity çıkarıldı; sunucu işleyicilerinin okuduğu en büyük indeks hiçbir komutta istemcinin gönderdiği en büyük argüman sayısını aşmıyor. Sunucuda işleyicisi olmayan istemci komutları yalnızca bilinen 8 PvP komutu (`g.py`); istemcinin hiç göndermediği tek işleyici `exchange_cash_new` (zararsız).
- `sell` argümanları (6. = neden dizesi, 5. = kaynak dokunma) ve `buy` (8 argüman) istemciyle uyumlu; `Base/purchaseLand` fiyat indeksi (`ownedGrid.length - 1`) ile `expand` (`len(expansions)-1`) aynı.
- Eşzamanlılık: kilit altında değişen kayıt `get_player_info` çıktısında bozulma üretmedi (yukarıdaki deney); `save_session` atomik (`.tmp` + `os.replace`, `.bak`), kilit RLock.
- Bozuk komutun geri alınması: `command()` her komut öncesi `deepcopy` alıp hatada `save.clear(); save.update(once)` yapıyor; `inf`, `NaN`, sözlük argüman, liste `cmd` denemeleri kaydı bozmadı.
- Çapraz site/DNS yeniden bağlama savunması (`_koken_denetimi`): Host, Origin, Sec-Fetch-Site mantığı okundu; `127.0.0.1.evil.com` gibi adlar `_ad` ile reddediliyor (kod okuması).
- `gecerli_uid` ile dosya yolu güvenliği, turnuva uçlarının `gecerli_uid` denetimi.
- `ada.py`: fetih/kıta mantığı tutarlı; yalnızca rakip botların `(seviye, uid)` sırasına bağlı olması (bot seviyesi değişince yuvalar kayar) not edilir (◐, düşük).
