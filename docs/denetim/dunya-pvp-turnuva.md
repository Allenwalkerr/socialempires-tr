# Denetim raporu: dunya-pvp-turnuva (DPT)

Kapsam: `oyun/dunya.py`, `pvp.py`, `elo.py`, `turnuva.py`, `bot_kimlik.py`, `diyar.py`, `gunluk.py`, `profil.py`, `araclar/bot_koy_uret.py`, `templates/js/oyun.js` (haber/sıralama bölümü).
Araçlar: `is/dunya-pvp-turnuva/` (`p1.py` PvP, `p2.py` bot akını, `p3.py` turnuva, `p4.py` süre ölçümü). Ekonomi ve sunucu alanlarındaki bulgular tekrarlanmadı.

### DPT-01: Gönüllü bitirilen saldırı (voluntary_end=1) zafer sayılıp kıta fethi, savunma raporu ve kurban kaybı yazıyor
- Önem: Orta
- İşaret: ✔
- Yer: oyun/pvp.py:90-190 (`saldiri_bitir`), oyun/ada.py:105-115 (`fetih_kaydet`)
- Kanıt: 1.4.07 istemcisinde `end_attack` yalnızca `Assault$/sendAssaultResults` içinde, iki yerde (@343, @379) gönderilir ve yükü sabittir: `win: 1`, `voluntary_end: 1`, `resources {g:0,w:0,s:0,f:0,x:0}`, `honor: 0` (`cagrilar("addCommand")` çıktısı). Gerçek sonuç `end_attack_new` ile gelir (sunucuda yok, bilinen eksik). Sunucu `voluntary_end`'e hiç bakmıyor. Çalıştırdım (`p1.py`): geri çekilme yüküyle `end_attack` -> `Saldiri bitti: ... kazandi`, `universAttackWin == [0]` (fetih kaydedildi), kurbanın `attacksReceived` listesine rapor eklendi, `victim_units` ölenleri kurbandan silindi.
- Etki: Oyuncu saldırıdan geri çekilince bile kıta yuvası fethedilmiş sayılır; 7 geri çekilişle bir sonraki kıtaya geçilir. Kurban botun birimleri silinir.
- Öneri: `voluntary_end == 1` iken `win`'i yok say (zafer, fetih, ganimet yok); gerçek sonuç yolunu `end_attack_new` ile kur.

### DPT-02: Bot akınları oyuncunun köylülerini ve nakitle alınmış birimleri (şifacı, kahraman) öldürüyor
- Önem: Orta
- İşaret: ✔
- Yer: oyun/dunya.py:142-154 (`birim_sil`), :68-83 (`birim_sayilari`), :648-657 (`_savas` kayıp oranları)
- Kanıt: `birim_sayilari` ve `birim_sil` tür `"u"` olan her eşyayı sayar/siler: köylü (alt kategori 71), şifacı (id 502, `cost_unit_cash` 4), Elit Kılıçlı (507) dahil. `p2.py`: oyuncuya 10 köylü + 10 şifacı + 10 Elit Kılıçlı eklendi, güçlü bir bot `_savas` ile saldırdı ve kazandı: üçü de 10 -> 6 (savunan kaybı %45). Mezarlığa girmiyor.
- Etki: Bot akınında üretim yapan köylüler ve nakitle alınmış birimler kalıcı kaybolur; oyuncu kayıp birimi akın sırasında göremez (istemci bellekte eski durumu tutar, yeniden yükleyince görür).
- Öneri: Yalnızca saldırı gücü olan birimleri (`attack > 0`, köylü/kahraman hariç) savaşa ve kayba say.

### DPT-03: Turnuva sonucu istemciden gelen puana güveniyor; 500 altınla 75.000 altın kazanılıyor
- Önem: Orta
- İşaret: ✔
- Yer: oyun/turnuva.py:200-213 (`mac_bitir`), :115-130 (`_bitir`), oyun/elo.py:96-117, oyun/istemci.py:296-303
- Kanıt: `p3.py`: tür 8 turnuvası (config: `cost` 500 altın, ödül 75.000 altın + birim) açıldı, üç maç `mac_baslat` hemen ardından `mac_bitir(..., 100)` ile bitirildi: altın 250 -> 75250, turnuva `date_finished` dolu. Botların maçları 55-90 puan (`_bot_maclarini_oyna`), oyuncunun üç maçı 100'e kadar kabul edilir (3x100 = 300 > en çok 270). Süre alt sınırı, maçın gerçekten oynandığı denetimi yok. Aynı puanlar haftalık Elo tablosuna da girer (`mac_kaydet`), bot puanı haftada ≤ 300, yani ilk 3 maçta 100 puanla haftalık birincilik (Yanardağ Ejderhası, `elo.ODULLER[1]`) de alınır (kod okuması, ◐). Giriş bedeli yalnızca istemcinin ayrı `tournament_substract_resources` komutuna bağlı.
- Etki: Tek kişilik oyunda ekonomiyi bozan açık yol; bozuk/tekrarlanan istek de ödül verir.
- Öneri: Puanı sunucuda savaştan türet ya da bir üst sınır/maç süresi alt sınırı koy; giriş bedelini `katil`de denetle.

### DPT-04: Sunucu kalkanı `shield_until` istemcinin `shieldEndTime`/`shieldCooldown` alanlarıyla ilişkisiz
- Önem: Orta
- İşaret: ◐
- Yer: oyun/kayit.py:252, oyun/dunya.py:434, 618, oyun/pvp.py (`kalkanli`), oyun/hile.py:100, oyun/kayit_semasi.py:18-19
- Kanıt: İstemci `ShieldManager/setPlayerShieldState` kalkanı `privateState.shieldEndTime`/`shieldCooldown`dan okur (kayit_semasi.py bunu kendisi belgeliyor); sunucuda bu alanlar 0 kalır ve hiçbir yerde okunmaz (`grep shieldEndTime` yalnızca şema). Botların akını, seferler ve `end_attack` ise yalnızca uydurma `shield_until`ye bakar. Çalıştırıp doğrulamadım; `buy_shield`/`reset_shield` zaten yok (bilinen eksik).
- Etki: Yeni oyuncuya verilen 24 saatlik koruma oyunda görünmez (oyuncu "kalkan yok" görür). Kalkan yazan bir kayıt (başka sunucudan taşınan ya da ileride yazılacak `buy_shield`) botları durdurmaz.
- Öneri: Tek alan kullan: `shieldEndTime`; botlar onu okusun ve yeni oyuncu kalkanı onu yazsın.

### DPT-05: Turnuva ve haftalık ödül kodu oyuncu kaydını `save_lock` dışında değiştiriyor
- Önem: Düşük
- İşaret: ◐
- Yer: oyun/turnuva.py:115-130 (`_bitir`), :232-238 (`_odul_ver`), oyun/istemci.py `turnuva_ucu`, oyun/diyar.py:92-103 (`hafta_ucu`)
- Kanıt: `_bitir` oyuncunun `coins`, `cash` ve deposunu salt `turnuva.KILIT` ile okuyup yazar; `bilgi()` (salt okuma görünümlü `get_tournament_info`) bunu tetikler. `command.php`, dünya turu ve profil uçları `save_lock` kullanıyor. `dunya` ya da komut aynı anda aynı alanı yazarsa `coins = int(coins) + x` güncellemesi kaybolur. Kilit sırası ters değil (turnuva KILIT -> save_lock; ters yönde çağrı bulunmadı), kilitlenme beklenmez.
- Etki: Çok dar yarış; ödül ya da bir komutun değişikliği kaybolabilir.
- Öneri: Ödül ve reyting yazımlarını `save_lock` içinde yap.

### DPT-06: `end_attack` onur puanı kazanç/kural durumundan bağımsız ve config'ten farklı
- Önem: Düşük
- İşaret: ✔ (sunucu), ◐ (istemci)
- Yer: oyun/pvp.py:134-137
- Kanıt: `p1.py`: `win: 0`, kural dışı saldırı (4 saat içinde aynı hedef), `honor: 15` -> `privateState.honor` ve `honor_points` 10 oldu. Onur `0..10`a kıstırılıyor; config `HONOR_POINT_PVP_WIN_ATTACK` 15, `..._LOSE_ATTACK` 5 (`PopupPVPFinished/<kurucu>` pencereyi bu değerlerle gösterir). Gerçek istemci bu komutta zaten `honor: 0` yolluyor.
- Etki: Pencerede 15 onur görünür, kayda 0 yazılır; elle yollanan istekle kuraldışı saldırıdan onur alınır.
- Öneri: Onuru sunucuda sonuçtan ve config'ten türet.

### DPT-07: Oyuncuya bot akınının sıklığı ve toplam kaybı sınırlı değil
- Önem: Düşük
- İşaret: ◐
- Yer: oyun/dunya.py:240-262, 420-447, ayarlar.json (`oyuncuya_saldiri` 0.25, `oyuncu_saldiri_araligi` 600)
- Kanıt: Oyuncuya akın en çok 10 dakikada bir (`_son_oyuncu_saldiri`) ve intikam seferleri 5 dakikada bir (`yarim`) olabilir; en çok 3 sefer eşzamanlı, her biri 3 akın. Savunmada alınan akın sayısına, saldırı aralığına (oyuncu için 6 saat/3 hak kuralı yok) ya da kaybın toplamına bir üst sınır yok; yenilgiden sonra kalkan verilmiyor. Kayıp: kaynak başına %10 (en çok 50.000) ve birimlerin %45'i. Bu oranları ölçmedim, yalnızca kod okuması.
- Etki: Uzun oturumda oyuncu sürekli soyulur; ilk 24 saat dışında koruma yok.
- Öneri: Oyuncu için akın aralığını/hakkını (6 saatte N) uygula.

### DPT-08: Profil resmi kayıt dosyasının içinde; her komutta ~400 KB yeniden yazılıyor
- Önem: Düşük
- İşaret: ◐
- Yer: oyun/profil.py:55-58
- Kanıt: Resim `kayit["profil_resmi"]` olarak base64 saklanıyor (en çok 300 KB bayt -> ~400 KB metin); `command()` her paketten sonra `save_session` ile bütün kaydı `fsync` ederek yazar. Ölçmedim.
- Etki: Yazım yükü ve yedek boyutu; Android'de pil/depolama.
- Öneri: Resmi ayrı dosyada tut.

### DPT-09: `_lonca` binanın bütün `attrs` sözlüğünü değiştiriyor
- Önem: Düşük
- İşaret: ◐
- Yer: oyun/dunya.py:345-352
- Kanıt: `esya[7] = {"workers", "hired", "guild"}` mevcut `attrs`i (ör. `bq`, `cp`, `hc`) siler. Yalnızca `social_items` listesindeki binalarda ve aynı turda tek bina.
- Etki: Nadir; o binadaki eğitim kuyruğu işareti ya da üretim seçimi kaybolur.
- Öneri: `esya[7].update(...)`.

## Bakıldı, sorun bulunmadı

- Dünya turunun yarışı: `tek_tick` bütün değişiklikleri `save_lock` altında yapıyor; `command.php`, profil ve yedek yazımları da aynı kilidi kullanıyor. Oyuncunun komutunu ezme yolu bulunmadı (yalnızca DPT-05 dışı yazarlar). Süre: 50 bot kaydını `fsync`le yazmak 0,12 sn, bir tur 0,04 sn (bu makinede; Android'de farklı olabilir, ?).
- Haber şeridi ve sıralama XSS: `templates/js/oyun.js` haber metni ve adları `textContent`/`el()` ile yazıyor; `innerHTML` yalnızca sayılar ve repo içindeki `takvim.json` metniyle. Şablonlarda `|safe`/`Markup` yok (Jinja otomatik kaçış). `portre()` adresi yalnızca `/img/`, `/profil/resim/`, oyun varlıkları ile sınırlı.
- Turnuva ödülünün gösterimi: istemci `getTournamentRewardIndex` turnuvadaki `reward_id`'yi kullanıyor, sunucu aynı indeksle (`prize[reward_id % len]`) ödüyor; altın, nakit ve birim alanları `getRewardData` ile aynı.
- Elo: beklenen skor `1/(1+10^((Rb-Ra)/400))`, K 32/16 (bot yarım), puan/100 skoru: formül doğru; hafta sınırı pazartesi 00:00 Türkiye saati, ödül ertesi istekte (`elo.haftayi_kapat`), ödül eşyaları (847, 849, 9101) config'te var.
- Bot kuralları: 6 saatte 3 saldırı (`attacksSent`), aynı hedefe 6 saat (istemcinin 4 saatinden sıkı), kalkan denetimi (kendi anahtarına göre). Bot kaynak büyümesi tavansız ama taşma gerçekçi değil (seviye 50, ölçek 3 için ~2200 gün sonra 2^31).
- Bot adı/portre göçü (`bot_kimlik.adlari_yenile`) yalnızca bot kayıtlarına ve raporlardaki eski adlara dokunuyor; `bot_koy_uret.bot_uret` yalnızca eski botları siliyor.
