> 11.11.2026 bayt kodu araştırması (yardımcı ajan; ana noktalar ana oturumda yeniden okundu: DailyBonusManager/initPlayerData,
> PopupNewDailyBonus/init@754-797). Sahibinin kararı KAR-24: yol B (sunucu verir), 5. günden sonra pencere açılmaz;
> uygulama oyun/gunluk_odul.py.

# 1.4.07 yeni 5 günlük günlük ödül: istemci tanımı ve sunucu için yol

İşaretler: ✔ bayt kodunda okundu (Sınıf/yöntem@ofset), ◐ çıkarım, ? doğrulanmadı.
Araç: `betik/oku.py swf/istemci.swf x '<Sınıf/yöntem>'`; alan türleri için `slot.py` (aynı betik klasörü, sınıfın slot türlerini döker).
Depo dosyalarına dokunulmadı.

## 0. En önemli bulgu (kayıt_semasi.py'nin iddiasını düzeltir)

`oyun/kayit_semasi.py:38` ve KYT-02 "showDailyBonus yokluğu günlük ödülü kapalı tutar" diyor. Bu yalnızca **düğme** için doğru.
**Pencerenin kendisi** (PopupNewDailyBonus) `showDailyBonus` olmadan da açılır:

- ✔ `DailyBonusManager/initPlayerData@56-142`: pencere şu koşulda açılır:
  `(Base.Main.showDailyBonus || _lastDayRewarded == 0) && !Base.Main.tutorialMode` → `showPopup(null)`.
  Eğitim sürüyorsa (`tutorialMode`) `Base.SIG_MAPA_INICIALIZADO`'ya `onMapaInicializado` eklenir (@118-138);
  o da eğitim bitip `gameModeCurrent == GameMode.NORMAL` olunca pencereyi açar (`DailyBonusManager/onMapaInicializado@17-49`).
- ✔ `_lastDayRewarded` `int` türünde (`slot.py DailyBonusManager`: `_numDaysLogged:int, _lastDayRewarded:int, _nextDayReward:int`).
  Kayıtta `lastDayRewarded` yoksa 0 olur (◐: `initproperty` ile int yuvaya `undefined` atanınca 0'a çevrilir; Flash'ın
  bilinen davranışı, bu bayt kodunda ayrıca `convert_i` yok).
- Sonuç ◐: bugünkü sunucuda (`lastDayRewarded` hiç yok) pencere **her girişte** açılıyor olmalı. Bunu `docs/inceleme/2026-10-30-1407-gecis-plani.md:25,48`
  doğruluyor gibi: "Yeni günlük ödül (5 gün) ✔ Açıldı" ve devlog `2026-10-30-2.md:29` "yeni günlük ödül ... çalıştı".
  Yani "kapalı" değil, "kayıtsız ve sınırsız açık". Hesaba göre: gün N (numDayLogged) için `config daily_bonus` kaydında `reward_day == N` olan
  ödül, `lastDayRewarded` hiç ilerlemediği için **her açılışta yeniden verilir** (2-5. günlerde birim 722/714 her girişte
  `store_add_items` ile depoya eklenir: tekrar tekrar alınabilir). Canlı doğrulama yok (?): Ruffle'da 2. gün (numDayLogged=2) kaydıyla bir kez açıp
  `gifts[722]` artışına bakmak yeterli.
- Düğme (DailyBonusButton) ayrı: aşağıda §4.

## 1. Alanlar nereden okunuyor

Hepsi **`get_player_info` yanıtının `privateState` nesnesinden**; başka alandan değil.

- ✔ `Base/loadPlayerInfoSuccess@2123-2135`: `DailyBonusManager.api.initPlayerData(<yanıt>.privateState)` (tüm privateState nesnesi parametre olarak geçiyor; bu yüzden
  `araclar/kayit_alanlari.py` bu alanları bulamamış, dosyanın "Sınır (◐)" notu).
- ✔ `DailyBonusManager/initPlayerData@16-52` (parametre = privateState):
  - `_numDaysLogged  = ps.numDayLogged` (**tekil "Day"**: `numDayLogged`; getter adı `numDaysLogged`). int, "kaç ayrı takvim gününde girildi". Sunucuda var (`oyun/oyuncu.py giris_gunu_say`).
  - `_lastDayRewarded = ps.lastDayRewarded`. int, "en son ödülü alınan giriş günü numarası"; 0 = hiç ödül/giriş tanıtımı yapılmadı.
  - `_nextDayReward = ps.nextDayReward`. **Okunuyor ama kullanılmıyor**: ✔ `DailyBonusManager/get nextDayReward@0-88` alanı değil, hesabı döndürür:
    `rewards` içinde `day > _lastDayRewarded` olan ilk kaydın `id`'si, yoksa 1. Sunucunun bu alanı göndermesi gerekmez (yoksa 0 olur, zararsız).
  - `Base.Main.showDailyBonus` (Boolean) **ayrı yerden** atanır: ✔ `Base/loadPlayerInfoSuccess@1683-1703`: `Main.showDailyBonus = (privateState.showDailyBonus == 1)`.
    Yani sayı `1` gönderilmeli (`true` ya da `"1"` da `==` ile geçer, ◐; `1` en güvenlisi).
- ✔ Eski yol da var: `Base/_parseLoadedInfo@89-144` (`isTimeFF` dalı, yani zaman makinesi `time_ff` sonrası): `Utils.isDailyBonusReady(privateState.timestampLastBonus, lastServerTimestamp, timeZoneModifier)`
  ile `showDailyBonus`/`resetDailyBonus` eski zaman damgası mantığıyla yeniden hesaplanır. Normal girişte kullanılmaz. `DailyBonusManager` bu yolda yeniden başlatılmaz (initPlayerData yalnızca loadPlayerInfoSuccess'te). ◐: time_ff sonrası `Main.showDailyBonus` true kalırsa yalnızca düğmeyi etkiler.
- Kullanıldığı yerler (✔): `PopupNewDailyBonus/init` `DailyBonusManager.api.numDaysLogged`, `.lastDayRewarded`, `.nextDayReward`, `.rewards`; `FirstOfferButton/isActive@129` aynı `numDayLogged`'ı (<3) okur.

## 2. Ödül tablosu

- ✔ Anahtar: oyun config'inin kökünde **`daily_bonus`** (`Base/loadGameConfigSuccess@674-687`: `DailyBonusManager.api.initData(config.daily_bonus)`). `new_daily_bonus` değil.
- ✔ `DailyBonusManager/initData@0-212`: her öğe `{id, reward_day, reward, img}` → `DailyBonus(id, day=reward_day, reward, img)`; `id`'ye göre sıralanır, `_rewards[id-1]`'e konur (id 1'den bitişik olmalı).
  `reward` bir sözlük: anahtar türü, değer miktar/birim no.
- Bizde var ✔: `config/patch/1-mega_patch.json:1333-1397` (`path /daily_bonus`) → `get_game_config()` ve `get_client_game_config('tr')` içinde duruyor (çalıştırıp doğruladım):

  | id/gün | reward | img |
  |---|---|---|
  | 1 | g 250, w 250, f 250, s 250 | day1.png |
  | 2 | u 722 (Fire T-Rex, type u) | day2.png |
  | 3 | c 10 | day3.png |
  | 4 | p 25 (iksir) | day4.png |
  | 5 | u 714 (Two-Headed Dragon, type u) | day5.png |

  Görseller: `download_assets/assets/externalized/DailyBonus/imgs/day1..5.png`, `bg.png`, `bg2.png` (`config/onindirme.tsv:3-9`). Yalnızca 5 resim var.
- Tür anahtarları ✔ `DailyBonusManager/giveReward@135-274` (switch): `u` birim (id), `f g s w c` kaynak (yemek, altın, taş, odun, nakit), `p` iksir; başka anahtar yok sayılır (mana `m` yok). `showReward@185-308` aynı anahtarlar.
- Eski, ayrı tablo: `Items.globals.DAILY_BONUS_CONFIG` (+ `DAILY_BONUS_CONFIG_HEROES`) eski PopupNewDaily içindir (§4); config'te: 250 altın, kahraman, 1 nakit, kahraman, 3 nakit.

## 3. Ödül alınınca istemci ne yapıyor (ÖNEMLİ: kalıcılaştıran komut neredeyse yok)

- ✔ Ödül, **pencere açılırken** (düğmeye basmadan) verilir: `PopupNewDailyBonus/init@1047-1090`: `_currentReward` doluysa `DailyBonusManager.api.giveReward(_currentReward)` çağrılır.
  `_currentReward` = `reward.day == numDaysLogged && numDaysLogged != lastDayRewarded` olan kayıt (@295-797 son kısım).
  "Ödülü Al" (`onGetClicked@16-49`, `btnCLOSE` da aynı) yalnızca `showReward(_currentReward)` (parçacık + birim/resim penceresi) ve `close()` yapar: **komut yok**.
- ✔ `DailyBonusManager/giveReward@0-322`:
  - **`reward.day == 1` ise hemen döner** (@24-34): 1. gün ödülü (250×4) istemcide hiç verilmez, `_lastDayRewarded` da 0 kalır. (Pencere "250" gösterir ama kaynak eklenmez, ◐ asıl niyet: ilk gün başlangıç kaynağı.)
  - `u` → `giveUnitReward(id)`: ✔ `giveUnitReward@0-81`: `StaticDataLibrary.getItem(id)` → `BuildingReference` → `Base.Main.storeItem(ref, false, true, false)` → `Base.Commands.sendCommands()` → `_lastDayRewarded = numDaysLogged`.
    `Base/storeItem@153-197` ile bu şu komutu kuyruğa koyar: **`store_add_items`**, `args = [JSON.encode([birimId])]` (`Constants.CMD_STORE_ADD_ITEMS`). Sunucuda işleyici var ✔ (`oyun/komutlar.py:388`, `depo_ekle`).
  - `f g s w c` → `giveStatsReward(anahtar, miktar)` → ✔ `PlayerStatus.adjustStatByType(miktar, tür)` → `adjustStats`: yalnızca **yerel** sayaçları (`iGold` vb.) değiştirir, **komut yok** (`PlayerStatus/adjustStats` içinde `addCommand` yok).
  - `p` → `givePotions`: `Player.iPotions += miktar`, **komut yok**.
  - Döngüden sonra (@314-319) `_lastDayRewarded = _numDaysLogged` (yalnızca yerel; sunucuya gitmiyor).
- ✔ Sonuç: yeni günlük ödül için **ayrı bir komut yok**. `Constants.CMD_GIVE_BONUS_REWARD = 'give_bonus_reward'` tanımlı ama bayt kodunun hiçbir yerinde kullanılmıyor (`oku.py` yalnızca `Constants/<sınıf>` döndürüyor).
  `win_bonus` yalnızca eski PopupNewDaily'dendir (§4).
- Yerel değişiklikler: `_lastDayRewarded`, `Player.iGold/iWood/iFood/iStone/iCash/iPotions`, depo (birim).
- Sunucuda: `store_add_items` işleyicisi var (birim ödülleri için yeter). Kaynak/nakit/iksir ödülleri ve `lastDayRewarded` **kalıcılaşmaz**: yenileyince geri alınır ve (§0) ödül yeniden verilir. Ödülün kalıcı olması için sunucu kendisi yazmalı.
- Komut kuyruğunun durum fotoğrafı yoktur (✔ `CommandManager/sendCommands`), yani istemcinin yerel kaynak artışını sunucu başka yoldan öğrenemez.

## 4. Eski günlük ödülle ilişki

Eski sistem (0926'dan): `PopupNewDaily` penceresi, `win_bonus` komutu, `privateState.bonusNextId` / `timestampLastBonus`, flashvar `dailyBonus` (`Main.consecutiveDays`).

- ✔ Eski pencereyi **yalnızca `DailyBonusButton` açar**: `DailyBonusButton/clickButton@0-34`: `tutorialMode` değilse `Base.PopUp.openPopupNewDaily()` (→ `PopupManager/openPopupNewDaily@81-114`: `new PopupNewDaily`). 1.4.07'de düğme eski pencereyi açıyor, yeni pencereyi değil.
- ✔ Düğme görünür olması için iki koşul: `IconPanel/populate@91-110`: `viral_icons` kaydında `active == 1` **ve** `DailyBonusButton/isActive` (= `Main.showDailyBonus`) true.
  Bizde `viral_icons` içinde `DailyBonusButton` **`active: 0`** (`config/patch/1-mega_patch.json:1477-1485`, çalıştırıp doğruladım) → `showDailyBonus=1` gönderilse bile düğme oluşmaz. Yeni pencere düğmeye bağlı değil, yöneticiden açılır (§0).
- Yani ikisi aynı anda açılmaz ◐: yeni pencere otomatik (`DailyBonusManager`), eski pencere yalnızca düğmeyle ve düğme kapalı. `showDailyBonus` ortak bayrak: hem düğmeyi (kapalı) hem yeni pencereyi tetikler. Biri ötekini kapatmaz (✔ ortak kod yok), `DailyBonusButton` `active:0` olduğu sürece eski pencere erişilemez.
- Eski pencere kendi başına: `PopupNewDaily/onGetPrize@45-688`: gün = `bonusNextId != 0 ? bonusNextId-1 : consecutiveDays-1` (`resetDailyBonus` ise 0), `% 5`; ödül `DAILY_BONUS_CONFIG[gün]`; yerelde `adjustStatByType`/`storeItem`; sonra komut **`win_bonus`** `args = [altın, townID, kahramanId, gün%5+1, nakit]` (@630-676, `Constants.CMD_WIN_BONUS`). Sunucu: `oyun/komutlar.py:1265` `win_bonus` (altın, nakit, kahraman depoya, `bonusNextId = gün+1`, `timestampLastBonus`) ✔ var. Yeni sistem bunu **kullanmaz**.
- Önerim: `viral_icons.DailyBonusButton.active` 0 kalsın (düğme eski pencereyi açıyor; sahibinin "yalnızca oyunun kendi ödülü" kuralıyla çelişmez ama iki ödül penceresi olur). Gerekirse düğme sonradan düşünülür.

## 5. Sunucunun yapması gerekenler

Önkoşul ✔: `numDayLogged` her yeni takvim gününde ilk `get_player_info`'da artıyor (`oyun/oyuncu.py:28-35`); aynı gün ikinci çağrıda (kasaba değişimi) artmıyor (`last_logged_in` her çağrıda güncellenir).

Sunucu tarafında yeni kayıt alanı: `privateState.lastDayRewarded` (int, boş değer 0). Şemaya `ALANLAR`'a eklenebilir (boş değer 0; göç eksik kayıtlara ekler). `showDailyBonus` **kayda yazılmaz**, yalnızca yanıta konur
(`tests/test_kayit_semasi.py:84` "showDailyBonus kayıtta yok" ile uyumlu kalır).

İki yol (sahibine seçtirilir):

**A. İstemci gösterir ve verir; sunucu yalnızca kalıcılaştırır (pencerede ödül canlanır, "Ödülü Al" çalışır).** ◐ tasarım:
`get_player_info` içinde, `giris_gunu_say`'dan sonra, `N = numDayLogged`, `L = lastDayRewarded` (yoksa 0), `T = config daily_bonus`:
1. `N > L` ve `T`'de `reward_day == N` kaydı varsa (gün 2..5): yanıt için `privateState` kopyasında `showDailyBonus = 1` ve `lastDayRewarded = L` (eski değer; istemci `currentReward`'u bulsun diye).
   Kayıtta `lastDayRewarded = N`. Birim ödülü (`u`): istemci `store_add_items` yollar (işleyici var), sunucu eklemez.
   Kaynak/nakit/iksir (`g w f s c p`): istemci yalnızca yerelde ekler, kalıcılaştırmaz. Bu yüzden sunucu bunları **kayda ekler** (map `coins/wood/food/stone`,
   `playerInfo.cash`, `privateState.potion`; `oyun/komutlar.py kaynak_ekle/cash_ekle`) ve **yanıtta aynı miktarı düşük gösterir** (yanıtın `map`/`playerInfo`/`privateState` kopyasında eksiltilmiş), istemci yerelde ekleyince toplam kayıtla eşleşir. ◐ (hile; pencere açılmazsa değer sonraki yüklemede görünür). Yanıt kopyası derin kopya olmalı.
2. `N == 1` ve `L == 0` (yeni hesap, tanıtım penceresi): istemci 1. günü vermiyor (§3). Sunucu 1. gün ödülünü (250×4) **kendisi** kayda ekleyebilir (yanıtta zaten dahil) ya da vermez; `lastDayRewarded = 1` yazar, yanıtta `showDailyBonus` yok ama `L==0` yeterli (pencere açılır, "bugün" 1. gün). Karar sahibinin: pencere "250" gösteriyor, istemci vermiyor.
3. Diğer durumda (`N <= L`, ya da `N > 5`): `showDailyBonus` yok, `lastDayRewarded >= 1` (pencere açılmaz).
- Tek çağrıda yalnızca ilk `get_player_info` (kayıtta `L < N`) bu işi yapar; aynı günün kasaba değişimi çağrılarında `L == N` olur, pencere açılmaz.

**B. Sunucu verir, pencere yalnızca gösterir (basit, güvenli).**
`N > L` ise ödülü kayda sunucu ekler (kaynak, nakit, iksir, birim → `depo_ekle`), `lastDayRewarded = N` yazar ve yanıtta `lastDayRewarded = N` gönderir: `_currentReward` boş kalır, pencere
"Kapat" düğmesiyle yalnızca takvimi gösterir (@1094-1127), `giveReward` hiç çalışmaz, çift verme yok. Dezavantaj ◐: "Ödülü Al" canlandırması yok; `showDailyBonus` göndermeye bile gerek yok (pencereyi `showDailyBonus=1` açar;
`L==N` iken açılması için `showDailyBonus: 1` gönder). Eksik: pencereyi açmak için o gün `showDailyBonus=1` şart (L>0 olduğundan).

**5. günden sonra** ✔: istemcide döngü **yok**. Ödül `reward.day == numDaysLogged` ile bulunur, 5 kayıtlı tabloda N>5 için ödül yok. Üstelik `lastDayRewarded >= NUM_FIRST_PAGE (=5)`
(✔ `DailyBonusManager/<sınıf>@18-20`) olunca pencere 2. çerçeveye ve `nextDayReward-2` başlangıcına kayar (`PopupNewDailyBonus/init@121-190`); 5 kayıtlı tabloda `nextDayReward` getter'ı 1 döner, başlangıç −1 olur
ve `rewards[-1]` ◐ RangeError (hesap; ? çalıştırılmadı). **5. günden sonra pencere hiç açılmamalı:** `showDailyBonus` göndermeyin, `lastDayRewarded ≥ 1` tutun.
Döngü istenirse `daily_bonus` tablosunu uzatmak gerekir (resim yalnızca `day1..5.png`, `img` serbest dize; mevcut resimler yeniden kullanılabilir) ve ödüller sahibinin kararı (?). `numDayLogged`'ı döngüye çevirmeyin: `FirstOfferButton` (<3) onu da okuyor.
Gün sayısı ardışık değil, "ayrı giriş günü" sayısı (✔ `POPUP_NEW_DAILY_BONUS_DAY` = "Login"; istemcide sıfırlama kodu yok; sunucu da sıfırlamıyor). Yardım metni "art arda günlerde oynarsan" diyor (yalnızca metin).

Kontrol listesi (test): (1) `lastDayRewarded` yokken bile tekrar tekrar verme olmaması; (2) 2-5. gün birer kez; (3) kasaba değişiminde ikinci kez açılmama; (4) N>5'te açılmama; (5) yanıttaki `showDailyBonus` kayda sızmama. Beklenen değerin kaynağı: bu rapordaki `DailyBonusManager/giveReward` anahtar eşlemesi, `config daily_bonus`.

## 6. OYN-11: hangi pencere, başlık nereden

- Belirtiler "başlık boş" ve "'250 altın' sığmıyor, 2. ve 4. gün yalnızca '1'" **eski PopupNewDaily**'ye uyuyor (◐ güçlü): ✔ `PopupNewDaily/<kurucu>@565-660` her kutuya `tx_N` etiketini `Language.POPUP_NUEVO_DIARIO_CASH/ORO` ("#0# nakit/altın", `qty` ile) ve kahramanda `POPUP_NUEVO_DIARIO_HEROE` ile kurar; yeni pencerede altın/nakit etiketi **yok** (ödül resimlerle, `img`).
  OYN-03 notu 0926 döneminde (eski pencere tek günlük ödüldü) yazıldı; `config/DAILY_BONUS_CONFIG`: gün 2 ve 4 kahraman (`type: hero`) → "1 Kahraman!" etiketi.
- Eski pencerenin başlığı ✔ `PopupNewDaily/<kurucu>@2006-2021`: `txTitle.setHTML(Language.POPUP_DAILYBONUS_TITLE)`; alt başlık `txSubtitle` = `POPUP_DAILYBONUS_DESC`; `mcToday.lbl` = `POPUP_DAILYBONUS_TODAY`; `mcTomorrow.lbl` = `POPUP_DAILYBONUS_TOMORROW`.
  Yerelleştirme kimlikleri ✔ (sunucu config'i): 1550 `POPUP_DAILYBONUS_TITLE` "Daily Bonus", 1551 TODAY, 1552 TOMORROW, 1553 DESC; 503 `..._ORO` "#0# gold"; 504 `..._HEROE` "1 Hero!"; 1246 `..._CASH`; 1310 `GET_PRIZE`.
  `ceviri/tr.json` karşılıkları **var** ✔ (`loc:POPUP_DAILYBONUS_TITLE` = "Günlük Hediye", DESC = "Her gün oyna, hediyeni al!", TODAY "Bugün", TOMORROW "Yarın", ORO "#0# altın", HEROE "1 Kahraman!", CASH "#0# nakit", GET_PRIZE "Ödülü al").
  `ceviri/arayuz_tr.json` içinde `metin_alanlari`: "Daily Bonus" → "Günlük Bonus", "Day 1..5" → "1. Gün..5. Gün", "DAY" → "GÜN" (SWF içi sabit metinler).
  Başlığın **boş** görünmesinin nedeni bu veriden çıkmıyor: metin var. ? Olası nedenler (◐): başlık alanının gömülü yazı tipinin "ü, ğ, ş, ı" glyphlerini içermemesi ("Günlük" → boş), ya da `setHTML`'in alan genişliğine göre kesmesi. Doğrulamak için Ruffle'da bir kez `POPUP_DAILYBONUS_TITLE`'ı ASCII ("Gunluk Hediye") yapıp bakmak yeterli. Aynı kaygı "250 altın" (`#0# altın`, kutu dar) için de geçerli (? kısaltma "250 altın" → "250 Altın" ya da etiketi kısaltmak).
- Önemli (✔): 1.4.07'de eski pencereyi açan tek yol `DailyBonusButton` ve o `active:0` (§4); yani OYN-11'in eski pencere belirtileri **şu an ekranda görünmüyor**. Yeni pencerenin başlığı: `bg.png`/`bg2.png`
  (`externalized/DailyBonus/`) resim; üstünde kutu başlıkları kod ile `Language.POPUP_NEW_DAILY_BONUS_DAY` ("Giriş N"), `POPUP_DAILYBONUS_TODAY`, `POPUP_DAILYBONUS_TOMORROW`, `AUX_DAY` ("Gün N") ile kuruluyor
  (✔ `PopupNewDailyBonus/init@357-640`). Yeni pencerede "boş başlık" olabilecek tek metin yok; olası boşluk ◐ `lblTitle` kutuları.
- Yeni pencerenin metin kimlikleri (✔ `Language/<sınıf>`): 1760 `POPUP_NEW_DAILY_BONUS_GET` "Get Reward!" (TR "Ödülü Al!"), 1761 `..._DAY` "Login" (TR "Giriş"), 1762 `..._HELP` (TR "Art arda günlerde oynarsan hediyeler büyür!"), 1763 `..._GET_TEXT` (EN metin yok: `[1763]-...` yer tutucu; TR "Al"), 1756 `..._LOGINS_REMAINING` (EN yer tutucu; TR "Kalan giriş"), 1766 `..._LOGINS_REMAINING_NUM` (EN yer tutucu; TR "Kalan giriş sayısı"), 1764 `AUX_CLOSE`.
  Dikkat ◐: `lblLoginsRemainingJust` = 1766, `lblLoginsRemaining` = 1756, `lblLoginsRemainingNum` = (sonraki ödül günü − N) (@887-952). Düzen "[1766] [sayı] [1756]" gibi okunuyor (ör. "Sadece 3 giriş kaldı"); mevcut Türkçe "Kalan giriş sayısı 3 Kalan giriş" bunu bozuyor olabilir. Önerilen: 1766 "Sadece", 1756 "giriş kaldı" (? orijinal İngilizce hiç yok; ekranda görmeden kesinleştirilmez).

## Özet kararlar (sahibine)
1. `lastDayRewarded` kaydı şart (şimdiki durumda yinelenen ödül riski ◐).
2. A mı B mi.
3. 1. gün 250×4'ü sunucu mu verecek (istemci vermiyor).
4. 5. günden sonra: pencere kapalı (önerilen) ya da tablo uzatma.
5. `DailyBonusButton` `active:0` kalsın (eski pencere).
