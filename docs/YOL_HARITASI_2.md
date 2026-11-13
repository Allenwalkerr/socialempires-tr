# Yol haritası 2: bundan sonra ne yapılacak (12.11.2026)

Bu belge oyuna bundan sonra neyin ekleneceğini **ölçüme ve kanıta** dayanarak sıralar. Kod yazılmadı; yalnızca
ölçüldü, araştırıldı ve sıralandı.

- Neden ayrı belge: `YOL_HARITASI_1407.md` 1.4.07'ye geçişi (KAR-08) anlatır ve büyük ölçüde bitti.
  `YOL_HARITASI_DURUM.md` 30 Ekim'deki beş fazın kapılarını tutar. Bu belge ikisinin üstüne gelen yeni sıralamadır;
  onları çoğaltmaz, gerektiğinde onlara başvurur.
- Bütün sayılar tek betikten gelir: `python araclar/yol_haritasi_olcum.py` (hiçbir dosya yazmaz; geçici kayıt
  dizininde yeni bir köy açıp uçları çağırır). İstemci: `download_assets/assets/flash/SocialEmpires1.4.07sec_fixed.swf`.
- İşaretler: ✔ ölçüldü ya da çalıştırıldı, ◐ kod okumasına dayanıyor, ? doğrulanmadı.

## 1. Bulgular ve sayılar

### 1.1 Komut kapsamı ✔

İstemcinin `addCommand` ile gönderdiği komutlar (`araclar/komut_imzalari.py`) ile çalışan sunucunun `KOMUTLAR`
sözlüğü karşılaştırıldı. Aynı ad iki kez kaydedilirse sözlükte **sonuncusu** geçer; betik tekrarları ayrıca arar.

| | Sayı |
|---|---|
| İstemcinin gönderdiği komut | 158 (çözülemeyen çağrı 0) |
| Gerçek işleyicisi olan | 141 |
| Boş işleyici (kayda hiçbir şey yazmıyor) | 17 |
| İşleyicisi hiç olmayan | 0 |
| Sunucuda olup istemcinin göndermediği | 1 (`exchange_cash_new`) |
| Aynı adın iki kez kaydı | 0 |

Boş 17 komut: `game_status`, `ping`, `system_set_count_hack`, `perform_city_quest`, `spy_player`,
`reset_position_univers`, `rt_publish_achievement_unit`, `gold_statue_conversion`, `start_quest_new`, geliştirici
paneli komutları (`fast_forward`, `load_map`, `save_map`, `reset`, `clear_tiles_area`, `set_variables`,
`reset_dragon`) ve `end_tournament_match` (sonucu ayrı uç `tournaments/finish_tournament_match.php` işler).
Bunların zararsız olduğu tek tek kanıtlanmadı. `spy_player` boş, ama `buy_spyings_pack` `spyingsPack`'i 50 yapıyor ve istemci bunu `Base/processAttacks`'ta okuyor; casusluk hakkı sunucuda hiç azalmıyor olabilir (?). `gold_statue_conversion` da adından bir değişiklik bekletiyor (?). İkisi A7'de.
Bilinmeyen bir komut gelirse `do_command` yalnızca günlüğe yazar; istemciye hata dönmez.

**Ama** "işleyici var" demek "doğru işliyor" demek değil. Bu oturumda iki örnek bulundu:

- `end_quest` istemcinin gönderdiği `difficulty` alanını yok sayıyor; `privateState.questsRank` hiç yazılmıyor
  (DNT-66, aşağıda).
- 1.4.07 istemcisi kendi adasındaki hikâye görevini hiç kurmuyordu (DNT-65, düzeltmesi bu dalda).

### 1.2 Ayrı HTTP uçları ✔

İstemcinin dize havuzundaki 32 uç, Flask'ın yönlendirme tablosuyla eşleşiyor (32/32). Hepsi yeni bir köyle çağrıldı:

| Cevap türü | Sayı | Not |
|---|---|---|
| Veri | 9 | `get_player_info`, `get_game_config`, `get_continent_ranking`, `pvp/enemy`, `get_tournament_info`... |
| Yalnızca onay (`data: {}`, `OK`, `true/false`) | 19 | `pvp/attack/*`, `pvp/pool/*`, `tournaments/*`, `kompu_*` |
| Boş ya da hata | 4 | `track_game_status`, `sync_error_track` (bilerek boş), `command.php` (gövdesiz istekte 400; komutlar 1.1'de), `get_continent.php` (404) |

`get_continent.php` istemcide yalnızca tanımlı (`Config.SERVICE_LOAD_CONTINENT`); onu kullanan kod yok (✔: ad ve dize yalnızca `Config` sınıf kurucusunda, @119-127), yani 404
gerçek bir eksik değil.

### 1.3 Kapalı sistemler ✔

İstemcinin `Base.Items.globals`'tan okuduğu 92 anahtar istemciye giden config'le karşılaştırıldı.

| Durum | Anahtar | Okuyan sınıf (kod) |
|---|---|---|
| Config'te yok | `PVP_MAX_NUM_DRAGONS`, `PVP_NUM_RANDOM_UNITS` | `Base` (2465 bayt) |
| Config'te yok | `TOWER_LIMIT_EXPANSION` | `BuildingLimits` |
| Config'te yok | `CROSS_PROMOTIONS`, `FONT_EQUIVALENCE` | başka oyunların reklamı ve yazı tipi eşlemesi; oyun için gereksiz |
| 0 ya da boş | `HONOR_POINT_QUEST_LOSE`, `SHOW_GRATS_PACK`, `SPEED_HACK_CONTROL`, `CHAINED_PACK_TRACKING` | görev kaybında onur, paket tebrik penceresi, hile denetimi, izleme |

`Config` sınıfında false olan özellik bayrakları: `ENABLE_FAKE_FRIENDS`, `SHOW_ICON_VIDEOS`, `SHOW_ONLY_ONE_LOCKED`.
Bu sayım yalnızca `getproperty globals` ardından gelen adı yakalar; sabit bir değişkene atanıp sonra okunan anahtarlar
sayılmaz (sınır).

**Sistem envanteri.** Her oyun sistemi için istemci sınıfları, komutlar, config alanı ve arşivdeki varlıklar:

| Sistem | İstemci sınıfı / kod | Komut (gerçek/toplam) | Config | Arşiv varlığı |
|---|---|---|---|---|
| PvP saldırı ve kalkan | 12 / 15052 bayt | 13/14 | `pvp_shields` 3, `honor_levels` 15 | 6 |
| Turnuva | 24 / 24785 | 2/3 | `tournament_type` 8, `tournament_formations` 4 | 6 |
| Görev adaları (seferler) | 76 / 82751 | 3/4 | `map_prices` 4 | haritalar depoda (`villages/quests`) |
| Kendi adasındaki hikâye görevi | 2 / 24913 | 1/1 | — | — |
| Hayatta kalma | 12 / 16214 | 4/4 | — | 9 |
| Ağır kuşatma | 4 / 2401 | 2/2 | — | 1 |
| Ejderha, canavar, binici, tapınak | 21 / 23449 | 17/17 | — | 865 |
| Ruh Kazanı | 9 / 7969 | 0 (istemcide) | — | 6 |
| Mezarlık ve kahraman | 3 / 3765 | 5/5 | — | 2 |
| Birim paketleri | 6 / 8164 | 1/1 | `unit_packs` 8 | 26 |
| Ada etkinliği | 4 / 6009 | 5/5 | `collect_game` 1, `collect_game_items` 6 | 16 |
| Koleksiyonlar | 9 / 9177 | 2/2 | `units_collections_categories` 128 | 0 |
| Dart | 3 / 3643 | 3/3 | `darts_items` 33 | 0 |
| Zaman makinesi | 5 / 2538 | 2/2 | — | 2 |
| Pazar | 2 / 802 | 2/2 | — | 1 |
| Depo | 6 / 2183 | 8/8 | — | 3 |
| Simyacı (kompu) | 10 / 8299 | uç ile | `kompu_offers` 1 | 1 |
| Teklifler | 3 / 2190 | 7/7 | `offer_packs` 67, `viral_offers` 5, `viral_icons` 11 | 6 |
| Günlük, haftalık, dönüş ödülleri | 11 / 6042 | 3/3 | `daily_bonus` 5 | 7 |
| Komşular ve yardım | 6 / 3313 | 10/10 | `neighbor_assists` 5, `social_items` 31, `recruitment_prices` 12 | 14 |
| Büyüler | 18 / 17641 | 3/3 | `magics` 15 | 56 |
| Dünya haritası | 2 / 66 | 3/3 | — | 2 |
| İkinci kasaba | 5 / 1458 | 4/4 | `town_prices` 4 | 0 (pencere resmi eksik, 1.4) |
| Seviye ödülü ve sıralama | 4 / 2457 | 2/2 | `level_ranking_reward` 50, `level_up_tips` 11 | 14 |

Sınıflar ad desenleriyle seçildi (betikte `SISTEMLER`); varlık sayısı da klasör adına göre. İkisi de yaklaşık sayımdır.
Sonuç: **kapalı ya da yarım duran büyük bir sistem yok**; istemcinin istediği her komut ve uç karşılanıyor. Sorunlar
"var ama yanlış ya da eksik işliyor" türünden (1.1).

### 1.4 Varlık tamlığı ✔

İstemci dizelerindeki 66 dosya yolunun 60'ı indirilebilir arşivde (`config/onindirme.tsv`, 4751 satır; istemci yolları
önek olmadan yazıldığı için bir önekin ardı da eşleşme sayıldı). Eksik 6:

| Yol | Etki |
|---|---|
| `PopupNewTown/new_town.png` | İkinci kasaba penceresinin resmi. Pencere resimsiz açılabilir ◐; yerine çizemeyiz (CLAUDE.md). |
| `largeexpansiongfx/expGen.png` | Büyük genişleme görseli ◐ |
| `mobile_storage.png` | Mobil depo simgesi ◐ |
| `buildingsprites/magic_cast_marquee.swf` | Büyü seçim çerçevesi efekti ◐ |
| `PopupDCi/promo_DCi_bg.jpg` | Başka bir oyunun (Dragon City) reklamı: gerekmez |
| `crossdomain.xml` | Flash güvenlik dosyası; sunucu kendisi veriyor |

Birleştirilerek kurulan yollar (ör. `"buildingsprites/" + ad + ".swf"`) düz dize olmadığı için bu sayıma girmez. Ana
penceresi eksik olup "açılamaz" sayılacak bir sistem bulunmadı; ikinci kasaba penceresi oyunda denenmeli.

### 1.5 Döngü ◐

Çekirdek döngü kur, üret, eğit, saldır, savun, ödül. Her adımın sunucu karşılığı var. Tek taraflılık için bakılanlar:

- **Oyuncu gerçekten saldırıya uğruyor mu?** Evet. Botlar oyuncuya akın ediyor (`oyun/dunya.py:681-687`):
  - en çok saatte bir (`oyuncu_saldiri_araligi` 3600, KAR-30);
  - kalkana saygılı (`pvp_yeni.kalkan_bitisi`).

  Ölçülmüş: kalkansız 300 denemede 18 akın, kalkanlıyken 0 (TST-07, ◐: deneme betikleri depoda değil, bu ölçüm betiği üretmiyor). Kalkan gerçek bir tehdide karşı duruyor.
- **Savunma kaybı:** Sahibinin kararıyla oyunun kuralı uygulanıyor (OYN-32): ölenlerin %95'i kurtarılır,
  `protect` birimleri kaybolmaz.
- **Kaynak çıkışı:** inşaat, eğitim, büyü, genişleme ve sefer araması altın ve odun yakıyor; kaynak yetmezse sunucu
  alımı reddediyor (KAR-18).

### 1.6 Ekonomi ✔ (bina başına kuramsal üst sınır)

Mağazadaki 36 üretim binası config'in `collect` ve `activation` (saniye) değerleriyle, 3 kat hızda
(`ayarlar.json` `zaman_olcegi` 3) hesaplandı. Değerler, bina sürekli toplandığında saatte verilen miktardır:

| Seviye | Altın | Yiyecek | Odun | Taş |
|---|---|---|---|---|
| 10 | Altın Ocağı I: 100 | İnek Ağılı I: 18000 | Marangozhane I: 100 | Taş Ocağı I: 87,5 |
| 20 | Altın Ocağı II: 137,5 | İnek Ağılı II: 24000 | Marangozhane II: 175 | Taş Ocağı II: 150 |
| 30 | Altın Ocağı III: 175 | İnek Ağılı III: 30000 | Marangozhane III: 225 | Taş Ocağı III: 200 |
| 50 | Altın Ocağı IV: 250 | Bağ: 33333 | Marangozhane IV: 300 | Taş Ocağı IV: 275 |

Seviye eşikleri (config `levels`, xp): 10. seviye 1504, 20. seviye 16232, 30. seviye 50213, 50. seviye 195760,
70. seviye 581954, 90. seviye 3014199.

Sınırlar:
- Yiyecek değerleri yüksek görünüyor, çünkü tarla ve ağıllar köylüyle kısa döngüde (32,4 ve 90 sn) çalışıyor ve
  tükenme kuralı ayrı (EKF-02).
- Altının asıl kaynağı savaş, görev ve hikâye görevi. Gerçek bir köyün saatlik geliri ve seviye başına süresi
  oyuncu davranışına bağlı; **ölçülmedi** (?). Bunun için sahibinin kaydından bir oturum günlüğü gerekir (Faz 4).

### 1.7 Kendi sistemlerimizin sağlığı ✔

Test sayısı, modülün adının geçtiği test dosyalarındaki test sayısıdır (üst sınır; tam kapsam değil). `ada` sıradan bir sözcük ("ada") olduğu için onun sayısı kesin şişkin.

| Sistem | Satır | Test | Not |
|---|---|---|---|
| dunya | 906 | 196 | |
| pvp | 315 | 222 | |
| ada | 143 | 212 | |
| yokken | 218 | 152 | |
| swf_yama | 646 | 142 | |
| onindirme | 118 | 115 | |
| turnuva | 384 | 92 | |
| bot_koy | 566 | 86 | |
| takvim | 138 | 79 | |
| kayit_yedek | 146 | 58 | |
| elo | 152 | 46 | |
| bayram_hedefleri | 107 | 28 | |
| pvp_yeni | 130 | 25 | |
| ev_agi | 151 | 21 | güvenlik açısından önemli, az test |
| hile | 115 | 20 | |
| tasima | 251 | 16 | ağ ve kodla korunuyor, az test |
| bildirim | 111 | 13 | Android'de |
| bot_yardim | 128 | 13 | |
| gunluk_odul | 57 | 6 | |
| diyar | 136 | 95 | |
| profil | 87 | 65 | |
| denge | 16 | 90 | |
| fx_yama | 115 | 3 | SWF'yi değiştiriyor, en az test |

Kitaptaki durum sayıları:

| Durum | Sayı |
|---|---|
| düzeltildi | 153 |
| karar verildi | 45 |
| çürütüldü | 11 |
| onay bekliyor | 8 |
| doğrulandı | 9 |
| ertelendi | 3 |
| açık | 3 |
| CI bekliyor | 1 |

Onay bekleyenlerin çoğu Android ve tablet maddeleri (DAG-04, DAG-05, DAG-12, OYN-07, OYN-08, DNT-02); sahibi 12.11.2026'da
"tablette şimdilik sorun görmedim" dedi.

## 2. Sıralama

Puan = Etki (1-5) × Güven (0,3-1,0) × 10 / Emek (oturum: 1, 2, 3, 5, 8). Güven, kanıtın ne kadar tam olduğudur
(istemci kodu, varlık, config, yayın kaydı). Sonra bağımlılığa göre düzeltildi.

### 2.1 Oyunun kendi sistemini tamamlamak (önce bunlar)

| # | İş | Etki | Güven | Emek | Puan | Kanıt |
|---|---|---|---|---|---|---|
| A1 | Hikâye görevi kampı (DNT-65): bu daldaki düzeltmeyi birleştirip sürüme koymak | 4 | 0,9 | 1 | 36 | 0926 spawnInit@82-92; Ruffle'da 3 açılışta tek kamp |
| A2 | Seferde zorluk ve yıldız (DNT-66): `end_quest`'in `difficulty`'sini `questsRank`'a yazmak | 4 | 0,9 | 1 | 36 | `Quest$/end`@208 ve QuestIslaEgg, God, Hard, TrollsGeneric, Heroes, QuestBoss*, QuestCollectable* sendResults `difficulty`; PlayerStatus/Init `questsRank`; PopupLoadingQuest |
| A3 | Eksik globals: `PVP_MAX_NUM_DRAGONS`, `PVP_NUM_RANDOM_UNITS`, `TOWER_LIMIT_EXPANSION` | 2 | 0,6 | 1 | 12 | 1.3; değerlerin kaynağı aranacak (eski config'ler, upstream) |
| A4 | Oyunun sistemlerini oyunda tek tek denemek: hayatta kalma, dart, zaman makinesi, simyacı, ada etkinliği, ikinci kasaba | 3 | 0,6 | 2 | 9 | komutları var (1.3), oyunda denenmedi |
| A5 | Eksik 6 varlığın etkisini oyunda görmek (özellikle ikinci kasaba penceresi) | 2 | 0,7 | 1 | 14 | 1.4 |
| A6 | `HONOR_POINT_QUEST_LOSE` 0: görev kaybında onur | 1 | 0,5 | 1 | 5 | 1.3 |
| A7 | Boş `spy_player` ve `gold_statue_conversion`: istemcide ne bekledikleri | 2 | 0,5 | 1 | 10 | 1.1; `buy_spyings_pack` |

### 2.2 Kendi eklememizi iyileştirmek ya da yenisini eklemek

| # | İş | Etki | Güven | Emek | Puan | Kanıt |
|---|---|---|---|---|---|---|
| B1 | Az testli modüllere test: `fx_yama`, `gunluk_odul`, `bildirim`, `tasima`, `ev_agi` | 2 | 0,9 | 1 | 18 | 1.7 |
| B2 | Bot köyleri: profil resmindeki birlik köyde, ona uygun dekorasyon (sahibinin isteği) | 3 | 0,8 | 2 | 12 | oyunun kendi birim ve süsleri; tasarım planı henüz yazılmadı |
| B3 | Tam ekran görünümünü sahibinin eski videosuyla karşılaştırmak | 3 | 0,5 | 2 | 7,5 | sahibinin görseli; video karesi |
| B4 | Ekonomi: sahibinin oturumundan gerçek saatlik gelir ve seviye süresi | 2 | 0,7 | 2 | 7 | 1.6 sınırı |
| B5 | Mutasyon ölçümünün açık uçları (TST-06) | 2 | 0,8 | 2 | 8 | |
| B6 | Açık artırma (KAR-38; sahibi "şimdilik kalsın") | 3 | 0,5 | 5 | 3 | yeni özellik, oyunda yok |

Tablolar iş numarasına göre dizili; sıra puana göre: A1 = A2 (36), A5 (14), A3 (12), A7 (10), A4 (9), A6 (5); B1 (18), B2 (12), B5 (8), B3 (7,5), B4 (7), B6 (3).

Bağımlılık: A1 ve A2 aynı oyun sürümünde çıkmalı (ikisi de görev deneyimi). A4, A1-A2'den sonra; böylece görevler
denenirken yeni bir hata çıkarsa aynı fazda düzeltilir. B2 bot köyü üreticisine dokunur; B3'ten bağımsız. B2 ve B3, puanı B5'ten düşük olsa da sahibinin kendi istekleri olduğu için Faz 3'te; B4 sahibinin oyun günlüğünü beklediği için sonda.

## 3. Fazlar

| Faz | İşler | Kabul kapısı (ölçülebilir) |
|---|---|---|
| 1. Görevler | A1, A2 | Testler: kamp her açılışta tek (kayıtta 41 duvar) ve `end_quest` `difficulty` 2 ile gelince `questsRank[ada]` 2. Ruffle'da 9. seviye köyde kamp görünür; bir ada kazanılınca sonraki açılışta zorluk seçilebilir. Sürüm v0.1.0-deneme4; sahibi oynar. |
| 2. Sistem turu ve testler | A5, A3, A7, A4, B1 | Her sistem için bir Ruffle betiği: pencere açılıyor, komut gidiyor, F5'te sonuç kalıyor (TST-07 gibi). Eksik globals'ın değeri kaynakla yazıldı ya da "kaynak yok" diye ertelendi. Az testli beş modülün her biri en az 10 test (B1 ucuz ve bağımsız olduğu için öne alındı). |
| 3. Bot köyleri ve görünüm | B2, B3 | 50 köyün her birinde profil resmindeki birlik var (test). Dekor yalnızca oyunun kendi süsleri (CLAUDE.md). Tam ekran: sahibinin videosuyla yan yana ekran görüntüsü. |
| 4. Sağlamlık | B5, B4 | Mutasyon oranı ölçülür (`docs/TEST_OLCUMU.md`). Ekonomi: sahibinin bir saatlik günlüğünden gelir tablosu. |
| 5. Sürüm | GEC-09 | v0.1.0 etiketi sahibinin onayıyla. |

## 4. Ertelenenler ve yapılmayacaklar

| İş | Neden |
|---|---|
| Gerçek oyunculara saldırı, çok oyunculu turnuva | KAR-02: sunucu tek kişilik ve çevrimdışı |
| Kurbana kalkan (`end_attack_new` 11. argüman) | Kalkan süresinin kaynağı yok; kurbanlar bot (OYN-31) |
| Eksik pencere resimlerini çizmek | KAR-04 ve CLAUDE.md: yalnızca oyunun kendi görselleri |
| Başka oyun reklamları (`CROSS_PROMOTIONS`, DCi) | Oyunla ilgisi yok |
| Açık artırma | Sahibi "şimdilik kalsın" dedi (KAR-38); biçim yazılı |
| Görev kaybında onur (A6) | Kaynak yok; sahibi isterse |

**Karar gerektirenler:**

- Kalkanın bota uygulanması: OYN-31, çok oyunculuk sınırı.
- Ruh Kazanı'nda iki girdinin harcanıp harcanmaması: topluluk kaynakları çelişiyor (araştırma §5); istemci kendi
  kuralını uyguluyor, değiştirilmedi.

## 5. Her özelliğin kalite kapıları

1. **Tasarım notu:** bayt kodu adresleriyle `docs/inceleme/`'de kısa bir not.
2. **Dikey dilim:** önce tek bir ada ya da tek bir köy uçtan uca; sonra hepsi.
3. **Bayrak:** davranışı değiştiren her şey `ayarlar.json`'dan kapatılabilir olmalı, ya da yama sürümüyle
   (`YAMA_SURUMU`) geri alınabilmeli.
4. **Fail-to-pass test:** önce düşen test yazılır. Bozma denemesi testi düşürmeli; beklenen değerin kaynağı
   istemci, config ya da karar olmalı (`docs/TEST_OLCUMU.md`).
5. **Emülatör senaryosu:** Ruffle'da Playwright betiği; F5 ve sunucu yeniden başlatma dahil.
6. **Bağımsız denetim:** PR incelemesi (CI `inceleme`) ve sonucu görmeyen bir denetçi.
7. **Sahibinin denemesi:** deneme sürümüyle; bildirdiği her şey kitaba yazılır.

## 6. Doğrulanamayanlar

- Oyunun asıl hâlindeki kurallar: zorluğun nasıl açıldığı, kamp süresi (4 ya da 6 saat), kalkan süreleri, onur
  eşikleri. Bunların çoğu yalnızca arama özetinden geldi (§7; birincil siteler ağ engeline takıldı). Oyunun kendi verisi
  geçerlidir: kamp sayacı `TIMER_OGRES_VILLAGE` 14400 sn (4 saat), zorluk `questsRank`.
- Ekonomide gerçek oyuncunun saatlik geliri (1.6).
- Eksik varlıkların oyundaki etkisi (1.4): yalnızca dize sayımı yapıldı.
- Sistem envanterindeki sınıf ve varlık sayıları ad desenine dayanır (1.3).

## 7. Kaynaklar

Araştırma 12.11.2026'da yapıldı. Yalnızca github.com sayfaları açılabildi. Fandom, Wikipedia, SuperCheats, Gamelytic,
Gamezebo, Atarita ve web.archive.org ağ engeline takıldı; bunlara dayanan iddialar **(özetten)** işaretlidir.

- Zorluk 1-3 yıldız; "expert" adı bulunamadı; 3 yıldıza oyuncular "hardcore" diyor (YouTube başlıkları, özetten):
  https://www.youtube.com/watch?v=FrQ3gdfyAgc. Oyunun kendi verisi: `ID_BUILDING_ISLE_HARDCORE_1..7`,
  `DIFFICULTY_MULT_1S..3S_ATCK/LIFE`, `POPUP_QUEST_ELIGE_DIFICULTAD`.
- Bir topluluk sunucusu yıldız seçimini başlangıç penceresinde açık tutuyor ve `end_quest` ile kaydediyor:
  https://github.com/TamalAdebisi/socialemperors/pull/46 (orijinal kanıtı değil).
- Troll Camp görevleri ve ödülleri, iki kamp arası 6 saat (SuperCheats, özetten):
  https://www.supercheats.com/guides/social-empires/troll-camp-tasks-and-rewards. Topluluk sunucusu 4 saat diyor:
  https://github.com/TamalAdebisi/socialemperors/blob/main/DECISIONS.md. Oyunun verisi 4 saat.
- PvP seviye 6'dan, 6 saatte 3 saldırı, Odin Heykeli ile 4 (SuperCheats, özetten):
  https://www.supercheats.com/guides/social-empires/attacking-other-players.
  Bizim istemci verimiz: `MIN_LEVEL_PVP` 8, `ATTACKS_PERIOD_HOURS`.
- Turnuva 15. seviyeden, giriş 30 ve 50 nakit (SuperCheats, özetten): https://www.supercheats.com/guides/social-empires/tournaments
- AcidCaos/socialemperors ve nerroth-rewrite dalı: https://github.com/AcidCaos/socialemperors/commits/nerroth-rewrite;
  sekiz düzeltmesi bizde var (KYN-07).
- Kapanış tarihi kaynaklarda 2016, 2017 ya da 2018; resmî duyuru bulunamadı (Atarita, lostmedia; özetten):
  https://www.atarita.com/social-empires-ve-social-wars-neden-kapatildi/
- Take-Two'nun Social Point'i alması, 1 Şubat 2017: https://www.pocketgamer.biz/take-two-acquires-social-point/
- Yöntem:
  - dikey dilim: https://bugnet.io/blog/what-is-a-vertical-slice
  - MoSCoW: https://www.agilebusiness.org/dsdm-project-framework/moscow-prioririsation.html
  - RICE: https://www.intercom.com/blog/rice-simple-prioritization-for-product-managers/

Bulunamayanlar:

- resmî kapanış tarihi ve son sürüm numarası;
- zorluğun açılma kuralı;
- kalkan süreleri ve fiyatları, onur eşikleri;
- turnuva ve hayatta kalma ödül tabloları;
- dart, zaman makinesi ve ada etkinliğinin orijinal kuralları.
