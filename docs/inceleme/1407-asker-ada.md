> 12.11.2026 bayt kodu araştırması (yardımcı ajan). Sahibinin kararları KAR-26, KAR-27, KAR-29: botlar yardım eder (her yer
> için günde bir), teklif düğmelerinde de bot, Ada Ocağı ve beş teklif kayan 30 günlük pencereyle açık, ada ve ödül
> çizimleri temel pakette. Uygulama: oyun/bot_yardim.py, config.etkinlik_penceresi, templates/js/oyun.js.

# A) KMT-09 Asker Toplama ve B) OYN-29 Ada Ocağı + viral teklifler: uygulama araştırması

İşaretler: ✔ bayt kodunda / kodda okundu, ◐ çıkarım, ? doğrulanmadı. Bayt kodu yerleri `Sınıf/yöntem@ofset`.
Hiçbir depo dosyasına dokunulmadı. SWF: 1.4.07 (`swf/istemci.swf`).

---------------------------------------------------------------------------------------------------

## A) Asker Toplama: "botlar yardım etsin"

### A.1 İstemci sayfa JS'inden ne bekliyor? Geri çağrı var mı?

- ✔ Üç açılır pencere aynı ExternalInterface çağrısını yapar: `PopupRecruitment/onFindFriend@89-133`,
  `PopupSocialBuilding/onFindFriend@89-133`, `PopupRecruitmentPopulation/onFindFriend@214-258`.
  Çağrı: `ExternalInterface.call("showPopupSEHelpSocialItem", tx, ty, townID, iID, siCsv, sName)` (yedi bağımsız
  değişken: ad + altı değer; `callpropvoid call (7)`).
  - `tx, ty`: `eBuilding.buildingReference.tx/ty` (binanın karesi)
  - `townID`: `Base.Main.townID`
  - `iID`: bina kimliği (Asker Toplama için 387 = `ID_BUILDING_ALLIES_RECRUITMENT`)
  - `siCsv`: şu ana kadar yardım edenlerin `si.join(",")` dizgisi
  - `sName`: `eBuilding.sName`
  - Çağrı yalnızca `si.length < arWorkerNames.length` iken (Recruitment'ta `si.length < arWorkerNames.length`,
    `@22-71`) yapılır, yani boş yuva varken.
- ✔ **Dönüş değeri kullanılmaz** (`callpropvoid`): çağrı yangın-unut. İstemcide `showPopupSEHelpSocialItem` için
  `addCallback` yok. `Base/init@1036-1194` yalnızca şunları kaydeder: `zoomMap, hideBookmarkButton, hideLikeButton,
  hideGiftsButton, hideNeighborButton, exitFullScreen, openStore, openTrolls, enableFlashAdVideoButton,
  forceReloadInfo (-> Base.reloadPlayerInfo), showLikeButton`. Başka `addCallback` yok (`CrossManager/initialize@53`
  ayrı: çapraz tanıtım).
- ✔ Yani asıl oyundaki akış: sayfa JS'i Facebook arkadaş seçtirirdi, arkadaş kabul edince **sunucu** binanın
  `attrs.si` dizisine arkadaşı yazardı; istemci yeni durumu ya açılışta ya da `forceReloadInfo` ile okurdu.
  Sayfa JS'i `si`'yi doğrudan istemciye vermez. (◐: "arkadaş kabul edince sunucu yazar" kısmı istemcide görünmez,
  yalnızca `si`'nin sunucudan geldiği ✔ görülür: aşağıda.)
- ✔ Ruffle 0.7.1 tarafı (indirilmiş `download_assets/ruffle/0.7.1/`):
  - AS3 -> JS: çekirdek `new Function("return (" + ad + ")(...arguments)")` ile çağırır (`core.ruffle.*.js`,
    `function r(e,_)`). Yani `window.showPopupSEHelpSocialItem` adlı **genel (global) işlev** gerekir. Tanımlı
    değilse ReferenceError olur; Ruffle bunu yutup günlüğe yazar (◐, hata ayıklama konsolunda doğrulanmadı: ?).
  - JS -> AS3: `addCallback` ile kaydedilen adlar oyuncu öğesinin (`ruffle-player`) özelliği olur
    (`ruffle.js`: `Object.defineProperty(this, e, {value: (...n) => callExternalInterface(e, n)})`). Yani
    `oyuncu.forceReloadInfo()` çağrılabilir (templates/js/oyun.js'te `oyuncu` değişkeni `oyunuBaslat`ta var).
  - `allowScriptAccess: true` zaten ayarlı (oyun.js:252) ve `ExternalInterface.available` bu yüzden true olur (◐).
- ✔ `templates/js/oyun.js`'te bugün hiç `ExternalInterface` karşılığı yok (grep: yalnızca ayar yorumu, satır 252).
  Oyunun çağırdığı ama sayfada olmayan diğer işlevler: `gotoBuy`, `gotoBuyWithOfferBuilding`, `gotoNeighbors`,
  `askForAchievementPermission`, `showPopupSEHelpOffer` (viral teklifler, B bölümü) vb.

### A.2 `si` dizisi, dolunca ne olur, sunucu komutu

- ✔ `PopupRecruitment` kurucusu `si`'yi **canlı referans** olarak `eBuilding.buildingReference.loaded.attrs.si`'ye
  bağlar (`<kurucu>@186-224`); yoksa boş dizi açar (`@231-314`). Yani liste binanın kaydındaki `attrs.si`'dir
  (sunucuda `privateState` değil, harita eşyasının `ozellikler(esya)["si"]`).
- ✔ Öğe biçimi (`PopupRecruitment/refreshFotos@230-705`):
  - `parseInt(si[i]) == 0` ise yuva "Köylü" (`POPUP_RECLUTAMIENTO_ALDEANO`) gösterilir, ad/foto aramaz.
    `AdminPanel/addRecruitmenFriend@148-161` hata ayıklamada tam böyle `si.push(0)` yapar ✔; sunucudaki
    `buy_si_help` da `0` ekler (komutlar.py:2054) ✔.
  - Sıfırdan farklıysa öğe bir arkadaş kimliğidir: `Main.friendsInfoMap[si[i]]` bakılır; `first_name` yoksa ya da
    kayıt yoksa ad `- -` / `- - -` olur (`@448-503`), foto `ImageManager.getUserPhoto(si[i])` ile yüklenir
    (`PopupRecruitment/loadPhoto@44`).
- ✔ `friendsInfoMap`, oyun.html'deki `friendsInfo` bayrağından gelir: `Base/<kurucu>@4886-4925`
  `friendsInfoMap[item.uid] = item`. Sunucunun `fb_friends_str` (oyun/kayit.py:337) bütün botları ve oyuncuları
  `{uid: pid, pic_square: ...}` olarak verir ✔; **`first_name` yok**, yani bot adı "- -" görünür.
- ? `getUserPhoto(id)`: tek bağımsız değişkenle çağrılınca ikinci parametrenin varsayılanı `true`
  (`ImageManager/getUserPhoto` seçenek (11,11); `@39-71`): `Commands.serverUrl + "graph.facebook.com/" + id +
  "/picture?type=" + tip` istenir. Depoda `graph.facebook.com` karşılığı yok (grep); istek
  `istemci.py:368 bilinmeyen_dinamik_uc`'a düşer ve 404 verir (◐). Bu yüzden bot kimliğiyle fotoğraf **büyük
  olasılıkla gelmez** (? Ruffle'da ölçülmedi). FotoNeighbour de aynı `getUserPhoto`yu kullanıyor ve komşu
  fotoları çalışıyorsa başka bir yol vardır; bu çıkarım denetlenmedi (?).
- ✔ İşe al düğmesi: `createFotos@138-228`: `si.length >= arPrices[currentPosition].num_recruitments` ise
  `btnHire` -> `onOpenBuilding`, değilse `onFindFriend` (kancayı çağıran). `refreshFotos` yuvaları `num_recruitments`
  kadar gösterir (`mcFotos.gotoAndStop(num_recruitments)`, `@370-377`). `btBuy` yalnızca hep gizli (`@460-474`).
- ✔ Dolunca (`PopupRecruitment/onOpenBuilding@56-372`): komut
  `finish_si_recruitment` args `[tx, ty, townID, iID, price.id]` (hepsi tam sayı); sonra birimler
  `storeItem(ref, false, false, false)` ile komutsuz depoya, `attrs.si = si.slice(0, min(si.length, 4) - num_recruitments)`
  (`@228-318`), `playerRecruitmentPrices.push(price.id)` (`@340`), ödül penceresi.
- ✔ Sunucu işleyicisi `finish_si_recruitment` (komutlar.py:2069-2101) bunlarla uyumlu: `a.tam(0..4)` sırası aynı;
  `si[:min(len,4) - gerekli]` istemcininkiyle aynı; ödül tekrarı ve yetersiz `si` reddedilir; ödül
  `recruitment_prices[id]` (config: 12 kademe; `num_recruitments` 1,1,1,2,2,3,3,4,4,4,4,4; `unlock_level`
  4,8,10,12,14,18,20,24,28,32,38,46). Test: `tests/test_istemci_kaynakli.py:200 AskerToplama` (✔ var, çalıştırmadım).
- ✔ Başka sosyal binalar (`PopupSocialBuilding`, 31 `social_items`): `worker_cost > 0` ise `btBuy` görünür ve nakit
  yolu (`buy_si_help`) çalışır (`PopupSocialBuilding/refreshFotos@178-189`, `createFotos@83`). Yalnızca Asker
  Toplama (387, `worker_cost: 0`) nakitle de doldurulamaz. Yani sorun yalnız 387'de.

### A.3 En sade yol: önerilen tasarım

**Önerilen (A1): sayfa JS kancası + küçük sunucu uç noktası + `forceReloadInfo`.**

1. `templates/js/oyun.js`: `window.showPopupSEHelpSocialItem = function (tx, ty, town, iID, siCsv, ad) {...}`.
   Yalnızca `iID === 387` için: `fetch("/asker-toplama/yardim", {POST, JSON {tx, ty, town, id: iID}})`, başarılıysa
   `oyuncu.forceReloadInfo()` (oyuncu değişkeni `oyunuBaslat` içinde; kancayı orada ya da dışarıda
   `let oyuncu` ile tanımla). Diğer binalar için işlev hiçbir şey yapmaz (aşağıya bak: denge).
2. Sunucu: yeni yol (hile.py'deki kalıp: `session["USERID"]`, `kayit_oturumu(uid)`, `save_lock`):
   `esya_bul(harita(save, town), tx, ty, 387)` -> `ozellikler(esya)["si"]` listesine yardım eden botları ekler
   (`buy_si_help` ile aynı yazım yeri). Bot seçimi: `playerInfo.bot` olan kayıtlar (bot_kimlik.py: 50 bot, Türkçe
   birim adları, portre = oyunun kendi birim resmi, ✔ kural uyumlu), `siCsv`'deki ve `si`'deki kimlikler hariç.
   `min(4, ...)` sınırı: istemci `Math.min(si.length, 4)` sayar (`@248-250`).
3. Sunucu `friendsInfo` kayıtlarına (oyun/kayit.py `fb_friends_str`) `first_name`: botun adı eklenir; istemci
   `friendsInfoMap[id].first_name`'i okur (✔ `@466-503`). Böylece yuvada "Keşiş", "Thor" vb. görünür. Başka
   okuyanlar (FriendsWindow, GuiManager/setNeighborStats, Base/getRandomFriend, PopupSpecialDayOffer/update) da
   `first_name`'e bakıyor; ek alanın zararı olması beklenmez (◐, çalıştırılmadı).
4. Fotoğraf: ya `DINAMIK/graph.facebook.com/<pid>/picture` yolunu botun `pic`'ine yönlendir (bot pic'i oyunun kendi
   `buildingthumbs/<resim>.jpg` yolu ✔) ya da `si`'ye bot kimliği yerine `0` yaz (köylü yuvası, ad/foto aramaz,
   ✔ hata ayıklama yolu). **En düşük riskli ilk sürüm: `0` (Köylü) ya da kimlik + `first_name`; fotoğraf için yol
   eklemek ayrı adım.** (Köylü yuvası "botlar yardım etti" duygusunu vermez; ad+foto vermek için kimlik gerek.)

**Seçenekler**
- A2 (sayfa JS'siz): sunucu `get_player_info`'da 387'nin `attrs.si`'sini kendiliğinden doldurur. Çok sade ama
  "yardım iste" adımı kalkar, tüm kademeler seviyeye bağlı anında alınır (Thor 4. seviyede!). Önermem.
- A3: yardımcı başına bekleme (ör. her bot bir saatte bir yardım eder). Daha oyun gibi; sunucuda zaman damgası
  saklamayı gerektirir. Sahibine sorulacak.

**`forceReloadInfo` maliyeti:** `Base/reloadPlayerInfo@1-159` `canReloadPlayerInfo()` ise `Gui.returnHome()` yapar ve
oyuncu bilgisini yeniden yükler (✔). Açık pencere kapanır, kısa yükleme olur (? süresi ölçülmedi). Alternatif:
yeniden yüklemeden, yalnızca sunucuya yazıp oyuncuya "pencereyi kapatıp açın" demek (kötü). Önerilen: yeniden yükle.
Ruffle'da denenmeli (bir kayıtla popup aç, boş yuvaya tıkla, `forceReloadInfo` sonrası `si` dolu mu?).

**Yarış durumu:** istemci komutları anında gönderiyor; sayfa POST'u komut akışının dışında. Aynı kayıt nesnesi
(`kayit_oturumu`) ve `save_lock` kullanılırsa ek risk görünmüyor (◐). Test: komut öncesi/sonrası `si` ve
`finish_si_recruitment` sonrası kalan.

**Yapılacaklar listesi (A)**
1. `oyun/` içinde yeni işlev + yol (ör. `oyun/asker_toplama.py`, `/asker-toplama/yardim`): doğrulama (yalnız 387,
   bina var, `siCsv` ile sunucudaki `si` tutarlı), bot seçimi, yazım, `save_session`.
2. `oyun/kayit.py fb_friends_str`: `first_name`.
3. `templates/js/oyun.js`: kanca + `oyuncu.forceReloadInfo()`.
4. (İsteğe bağlı) fotoğraf yolu ya da `0` sürümü.
5. Testler: sunucu yolu (bot seçimi, 4 sınırı, tekrar yok, 387 dışı reddi), `fb_friends_str` `first_name`,
   JS testi (`tests/js/`: kancanın yalnız 387'de `fetch` yapması), mevcut `AskerToplama` testi değişmez.
6. `docs/gorev/BULGULAR.json` KMT-09 ve KAR-26 ✔ işaretle; devir notu.

**Riskler (A)**: foto 404 (?), `first_name` yan etkisi (◐), yeniden yükleme sırasında açık komut kuyruğu
(`canReloadPlayerInfo` reddederse hiçbir şey olmaz; yeniden denemek gerekir ◐), denge (Thor 4. seviyede; bot
yardımı sınırsız ve bedelsiz).

---------------------------------------------------------------------------------------------------

## B) OYN-29: Ada Ocağı (collect_game) ve viral teklifler

### B.1 İstemci neye göre gösteriyor, bizde değerler ne?

**Ada Ocağı (`CollectGameManager`)**
- ✔ Yükleme: `Base/loadGameConfigSuccess@606-652`: `CollectGameManager.api.initIsland(config.collect_game)`,
  `initItems(config.collect_game_items)`; oyuncu verisi `Base/loadPlayerInfoSuccess@2054-2098`
  `initIslandPlayerData(privateState.collectGame, privateState.collectGameGivenPrizes)`; her kare
  `Base/UpdateGame@527` (yalnız `GameMode.NORMAL`'de) `update()`.
- ✔ `initIsland@48-440`: yalnızca `collect_game["1"]` okunur; `startCollectDate = startBuyDate = starts_at`,
  `endCollectDate = endBuyDate = starts_at + duration`, `islandId = building_id (1530)`, `discountPrice`, `minLevel =
  min_level`, `gameType`, `game_data.{retry_price, speedup_price(!), trolls_cooldown, pvp_cooldown,
  pvp_killed_life_multiplier}`, `rewards`.
  `game_data` bizde tam: `retry_price 1, speedup_price 1, trolls_cooldown 300, pvp_cooldown 300, pvp_killed_life_multiplier 0.5` (eksik alan yok).
- ✔ **Aktiflik** (`get active@18-101`): `clientTimestamp > startCollectDate && clientTimestamp < endBuyDate &&
  _prizes.length >= 1`. `canCollect`: `startCollect < şimdi < endCollect` (aynı değerler). Şimdi ile config'in
  `starts_at`'ı **aynı birimde, saniye ve sunucu zamanı** (`Base/clientTimestamp`: sunucu zamanı + geçen süre,
  getTimer/1000).
- ✔ Bizde (config/patch/1-mega_patch.json ops 16, 17; get_game_config çıktısı): `collect_game["1"]`:
  `starts_at: 0, duration: 0, building_id: 1530, discount_price: 21, min_level: 1, game_type: 2,
  minimum_pack_value: 0, rewards {"90": [2272], "110": [2269]}, game_data {retry_price 1, speedup_price 1,
  trolls_cooldown 300, pvp_cooldown 300, pvp_killed_life_multiplier 0.5}`. Yani `endBuyDate = 0` -> `active`
  hiçbir zaman true olmaz.
- ✔ Ada nasıl çıkar: `initIslandPlayerData@321-331` `SIG_MAPA_INICIALIZADO`'na `spawnIsland`'ı bağlar; `spawnIsland`
  (`@38-157`) `active && gameModeCurrent == NORMAL && prizesRemaining` ise 1530 numaralı `IsoBuilding`'i
  (PLAYER_NEUTRAL) `encontrarZonaProximaLibre` ile kasabada boş bir yere koyar. Yani **haritada kendiliğinden
  çıkan** nötr bir bina (Hell's Forge Island), mağazadan alınmaz. Tıklanınca `PopupIslandForge`. İlerleme ödül
  eşiğini geçmişse ve ödül verilmemişse pencere kendiliğinden açılır (`checkPrizes@47-131`).
- ✔ Malzeme düşürme (istemcide `Math.random`, `generate@92-100`): `active`, `canCollect` ve oyuncu seviyesi >= 2
  (`@109-144`). Bekleme süreleri istemcide.
- ✔ Süre dolunca: `update` `active` false ise adayı kaldırır; `PopupIslandForge/onEnterFrame@66-93` `collectTimeLeft
  <= 0` ise adayı kaldırıp pencereyi kapatır; pencere `lblRemainingTimeValue`'da kalan süreyi gösterir
  (`GameStatic.dhms(collectTimeLeft)`, `@98-112`).
- ✔ Ödüller bitince (`giveReward@75-144`): `reward_viral_offer [2, 0, 0, yön, kasaba]` gönderir, viral teklif 2'yi
  `rewarded` yapar, adayı kaldırır (ada tek seferliktir; promosyon kimliği sabit `1`, yeni dönem açmak ek
  kayıt gerektirir: sunucu/istemci `collectGame` sayaçları `promoId` ile ayrılmıyor ✔ görülmedi).

**Viral teklifler (`SpecialDayOfferManager`)**
- ✔ `init(config.viral_offers)` (`SpecialDayOfferManager/init@46-94`) her teklifi `_offers[id]`'ye koyar,
  `friends = []`. `setPlayerInfo(privateState.viralOffers)` her teklif için `friends` ve `rewarded` alır, sonra
  `checkViralButton()` çağırır (`@23-103`).
- ✔ **Simge görünürlüğü** (`checkViralButton@24-366`, `getViralButtons@22-317`): her teklif için `icon` boş değil,
  `rewarded != 1`, `timeLeft(id) > 0` ve `şimdi > starts_at` ise simge yapılır ve `Gui.viralButtonPanel`'e
  `openPopupSpecialDayOffer` ile eklenir. `timeLeft@47-87` = `int(starts_at + duration - şimdi)`, 0'dan büyükse.
  **`convert_i` (int32) yüzünden `starts_at + duration - şimdi` 2^31-1 (≈68 yıl) altında kalmalı**; taşarsa negatif
  olur ve simge/ada gizlenir. Ada için de aynı (`PopupIslandForge/onEnterFrame@74` `collectTimeLeft convert_i`).
- ✔ Bizde (`viral_offers`, mega_patch op 26): 1 `easterDragon` (birim 2267, buy_cost [40,40,40], buy_all [100,70,40],
  3 yardımcı), 2 `easterDragon` (**Ada'nın boru malzemesi; `_popups[2]` = PopupIslandForge**, buy_cost [] , 5 yardımcı),
  3 ve 4 `viralDynasty` (birim 2324, 4 yardımcı, 90'ar, 330/250/170/90), 5 `easterDragon` (birim 2363 NightForge, 4
  yardımcı). Hepsinin `starts_at` ve `duration` 0 -> `timeLeft = 0` -> hiçbiri görünmez.
  Popup eşlemesi (✔ `SpecialDayOfferManager/<kurucu>@47-104`): 1 PopupSpecialDayOffer, 2 PopupIslandForge,
  3-4 PopupIvoryOffer, 5 PopupNightForgeOffer.
- ✔ `viral_icons` (mega_patch op 31): 11 giriş; yalnızca `FirstOfferButton` `active: 1`, ötekiler 0. `asclass` listesi: FirstOfferButton (active 1), CrossDCiViralIcon, RecruitmentTavernButton,
  DailyBonusButton, MobileGuiGiftButton, comebackButtonViral, MondayBonusButton, askForAchievementsButton,
  specialDayOffer, CrossViralIcon, FBLikeButton (hepsi active 0). `IconPanel/populate@49-451`: `active == 1` olan her giriş için sınıfın `isActive()`'i true ise
  simge ekler; `asclass == "specialDayOffer"` ise `SpecialDayOfferManager.getViralButtons()` ile teklif simgelerini
  ekler. **Viral teklif simgeleri `checkViralButton` yolundan `viral_icons` bayrağından bağımsız eklenir** (✔
  `checkViralButton` `viral_icons` okumaz), yani `specialDayOffer.active` açmak şart değil. Açılırsa iki yoldan eklenme
  riski (◐, `addIcon` yinelemeyi önlüyor mu ?); upstream 1.4.07 config'inde de 0, onunla gerçek oyun çalışıyordu.
  Bu yüzden `specialDayOffer` 0 kalsın.
- ✔ Diğer `viral_icons` (hepsi 0, **bunlar "viral teklif" kapsamında açılmasın**):
  - `FirstOfferButton`: ilk alım teklifi (gerçek para satın alma; `privateState.firstPurchaseTimestamp` ve
    `POPUP_FIRST_PURCHASE_OFFER_TIME`; `active: 1` ama kayıtta alan yoksa pasif, KYT-02) ✔ zaten KYT-02'de ayrı karar.
  - `FBLikeButton` (`isActive` hep false), `askForAchievementsButton` (`ExternalInterface askForAchievementPermission`,
    Facebook), `MobileGuiGiftButton` (iPhone deposu), `CrossViralIcon`/`CrossDCiViralIcon` (başka oyun reklamı),
    `comebackButtonViral`, `MondayBonusButton`, `DailyBonusButton` (OYN-11 ayrı), `RecruitmentTavernButton` (Asker
    Toplama kısayolu; A'ya bağlı, `Main.addRecruitment` kaynağı bulunamadı ?).

### B.2 Açmak için hangi değerler?

- Ada: `collect_game["1"].starts_at` geçmiş bir an, `starts_at + duration` ileri bir an. Viral teklifler: her
  teklif için aynı. **Sürekli açık** önerilir: Ada'nın ilerleme/ödül kaydı (`collectGame`, `collectGameGivenPrizes`)
  dönem kimliği taşımıyor, dönemsel yenilemek ek göç ister.
- ✔ Sınır: `starts_at + duration - şimdi < 2147483647` olmalı (yukarıya bak). Örnek: `starts_at = 1` (ya da
  1577836800), bitiş `2145916800` (2038-01-01) -> `duration = 2145916800 - starts_at`. Ek: `admireTimeLeft` getter'ı
  `endBuyDate`'e 7 gün ekliyor (`@3-20`, yan etki; yalnızca bu getter çağrılınca) ◐ zararsız.
- Bunlar `SURE_ALANLARI` (config.py:~192) içinde değil, oyun hızı ölçeği onları ölçeklemez ✔ (yalnız
  `activation, expiration, training_time, sm_training_time`).
- Nasıl yazılır: yeni yama dosyası `config/patch/etkinlik.json` (adı sıralamada `2-unit_patch`'ten sonra, `kompu`'dan
  önce; yama sırası alfabetik, kayıtlı çıktıda `0-language_en, 1-mega_patch, 2-unit_patch, kompu, turnuva,
  yeni_icerik` ✔), `replace` işlemleri: `/collect_game/1/starts_at`, `/collect_game/1/duration`,
  `/viral_offers/1..5/starts_at`, `.../duration`. Gerekçe: mega_patch upstream'in kopyası (KNF-01: "upstream ile birebir"),
  doğrudan düzenlenmez; `turnuva` yaması aynı yolla mega_patch'in değerini ezer (tests/test_sistemler.py:410).
  Alternatif: `kompu_teklifi()` gibi (config.py:165-180) `get_client_game_config`te dinamik pencere (bugün + N gün);
  geri sayımı gerçekçi gösterir ama oturum N günden uzun açık kalırsa ada kaybolur. Önerilen: sabit 2038 sonu.
- Yan etki: Ada penceresinde "kalan süre" ≈ 4000 gün görünür (◐ görsel; kabul edilebilir mi, sahibine sorulabilir).
  Her simge/pencerede kalan süre yazısı: `PopupSpecialDayOffer/refreshTimer` (kontrol edilmedi ?).

### B.3 Açılınca istemcinin göndereceği komutlar, sunucu karşılıyor mu?

✔ (docs/inceleme/1407-komutlar.md satır 71-83 ve komutlar.py 870-1065 ile elle karşılaştırıldı)
- `collect_game_add_item [id, ödendi]` (`CollectGameManager/addItem@109`), `collect_game_update_timestamp [id]`
  (`collectItem@66`), `collect_game_speed_up [id]` (`buySpeedup@88`), `collect_game_buy_all [1]` (`buyAll@67`),
  `collect_game_reward_given [ödül_id]` (`giveReward@48`), `buy_viral_offer_friend [no]` (`SpecialDayOfferManager/
  buyFriend@48`, ayrıca `CollectGameManager/buyItem@89-101` boru için `[2]`), `buy_viral_offer_all [no]` (`buyAll@38`),
  `reward_viral_offer [no, x, y, yön, kasaba]` (`giveReward@223`; ada bitince `[2,0,0,yön,kasaba]`,
  `CollectGameManager/giveReward@96-121`). Sunucuda hepsinin işleyicisi var ve imzaları uyuyor (kapı:
  tests/test_komut_imzalari.py `EKSIK_1407 = set()`). Birim testleri: tests/test_komutlar.py:984-1082.
- Ödül birimi komutla değil istemci `storeItem` + `store_add_items` ile gider; `reward_viral_offer` yalnızca işaret
  koyar (✔ belgelenmiş, `SpecialDayOfferManager/giveReward@78-87`).
- ◐ Gürültü: boru satın alınca `buy_viral_offer_friend [2]` gelir, teklif 2'nin `buy_cost`'u boş olduğundan
  `_viral_ode` `" ! viral teklif alinamadi"` yazar; zararsız (komutlar.py:1049 yorumunda biliniyor).
- ◐ Eksik/ek iş yok (komut tarafında). Sunucu `collect_game_add_item` bekleme süresini denetlemiyor (belgelenmiş,
  istemcide şans/bekleme; sahibi olmayan tek kişilik oyunda sorun değil).
- Kayıt şeması: `privateState.collectGame` ve `collectGameGivenPrizes`, `viralOffers` zaten `kayit_semasi.py`'de.
  Bunlar yokken istemci boş geçiyor (KYT-02 ✔).

### B.4 Çevrimdışı oyunda çalışmayacak / çok oyunculu kurala aykırı parçalar (SAHİBİNE YENİDEN SORULABİLİR)

1. ✔ **Davet düğmesi = Facebook.** `PopupSpecialDayOffer/onInvite`, `PopupNightForgeOffer/onInvite`,
   `PopupIvoryOffer/onInvite` ve **Ada Ocağı'nın "boru" malzemesi** (`PopupIslandForge/actionClick@218-237`)
   `ExternalInterface.call("showPopupSEHelpOffer", teklifNo)` çağırır. Sayfada karşılığı yok; çağrı sessizce
   başarısız olur (◐). Bu, A'daki Asker Toplama kancasının aynısı: gerçek arkadaş daveti = çok oyunculu özellik, yani
   **yasak**. Çözüm A'daki gibi: sayfada `window.showPopupSEHelpOffer = (no) => ...` bot yardımcı ekler
   (`viralOffers[no].friends` listesine bot kimliği, bunu istemci `friendsInfoMap` ile ad/foto çözer,
   `PopupSpecialDayOffer/update@294-387`, `0`/`-1` ise "Köylü" ✔) ve `forceReloadInfo` çağırır. Sınır: o teklifin
   `num_workers` değeri. **Sahibine sor:** bot yardımı bedelsiz mi, bekleme süreli mi? Teklif ödüllerinde Easter,
   Ivory, NightForge ejderhaları var (birim 2267, 2324, 2363); bedelsiz bot yardımı ile ödüller hemen alınır
   (Ada'nın boru malzemesi 5 gerekli = beş bot).
   Alternatif (bot yardımı olmadan): yalnızca oyun içi nakitle satın alma (`buy_cost`/`buy_all_cost`) bırakmak ve
   davet düğmesini ölü bırakmak; bu "ikisini de aç" kararıyla uyumlu ama davet düğmesi çalışmaz görünür.
2. ✔ **Nakit.** `buyFriend`/`buyAll`, Ada `buyItem` vb. oyun içi `cash` düşer. Gerçek para yok; nakit yetmezse
   pencere `Base.gotoCash` -> `ExternalInterface.call("gotoBuy", false)` çağırır (Base/gotoCash@31-49), sayfada
   yok -> sessiz başarısız. Oyuncu nakiti başka yoldan (günlük ödül, hile paneli, ödüller) edinir. Sorun değil
   ama "nakit yetmedi" tıklamasında hiçbir şey olmaz (◐).
3. ✔ `FirstOfferButton` (gerçek para) ve Facebook/çapraz tanıtım simgeleri kapsam dışı bırakılmalı (yukarıda).
   Yalnızca `viral_offers` + Ada açılır; `viral_icons` değişmez.
4. ◐ Ada'nın "PvP" malzemesi `Gui.openPvp` (botlara karşı mevcut PvP, tek kişilik uyumlu), "görev" malzemesi
   `PopupIslandQuestsManager.loadWorldForgeIsland` (mevcut ada görevleri). Çok oyunculu parça yok.
   `pvp_killed_life_multiplier` yalnızca istemci şansı.
5. ◐ Popuplarda İngilizce kod dizgeleri var: `PopupIvoryOffer`/`PopupNightForgeOffer` `update`: `'BUY '`,
   `'BUY ALL FOR '` (bayt kodunda sabit; çeviri yolu `swf_yama.py` ile; görsellerdeki yazılara dokunulmaz kuralı bu
   kod dizgelerine uygulanmaz ama sahibine sorulur ?).

### B.5 Görseller (yalnızca oyunun kendi resimleri) ve çevrimdışı paket

✔ Kullanılanlar oyun varlıklarıdır; yeni görsel gerekmez.
- Ada penceresi (`PopupIslandForge/init`): `externalized/IslandForge/{bg.jpg, dragonBG.png, 1..6.jpg/png,
  forge_hammer.swf, island_progressbar.swf}` -> `config/onindirme.tsv` satır 10-25, **öncelik 0 (temel)** ✔.
  Malzeme jetonları `images_new/collect_*`: tsv'de öncelik 0 ✔ (satır 422-437).
  Ada binasının küçük resmi `buildingthumbs/1530_forgeIsland.jpg` öncelik 1 (temel) ✔; **bina animasyonu
  `buildingsprites/1530_forgeIsland.swf` (763 KB) öncelik 2 = yalnızca "tam" pakette** (satır 3656) -> temel
  çevrimdışı pakette **eksik**.
- Viral simgeler: `externalized/viral_buttons/easterDragon.swf` ve `viralDynasty.swf` tsv'de öncelik 0 ✔ (satır
  127, 129). Pencere arka planları `PopupEasterDragon/popup_easter_bg.png`, `popup_ivory.png` öncelik 0 ✔ (31-32).
  NightForge penceresi bir arka plan dizgesi belirtmiyor (`PopupNightForgeOffer` kurucusunda yalnızca metin;
  görünüşte PopupEasterDragon arka planlarını yeniden kullanıyor ? doğrulanmadı).
- Ödül birimleri (2267 Easter, 2269 Forge, 2272 Demon, 2324 Ivory, 2363 NightForge, 2271 Rider): küçük resimler
  `buildingthumbs/*` öncelik 1 ✔; **birim animasyonları `buildingsprites/{2267,2269,2271,2272,2324,2363}_*.swf`
  (1,4-2,9 MB, öncelik 2) yalnızca tam pakette** (satır 3897-3989) -> temel pakette eksik.
- Öneri: `araclar/onindirme_listesi.py` içinde 1530 ve bu altı birimin sprite'larını öncelik 1'e çek (toplam ≈ 14,5 MB:
  0,76 + 1,60 + 1,69 + 1,88 + 1,51 + 2,93 + 1,43). Aksi halde çevrimdışı paketle kurulumda ada/ödül ilk kez görününce
  ağ gerekir. Ayrıca `tests` içindeki paket testleri (öncelik sınırları) güncellenmeli ?

### Yapılacaklar listesi (B)

1. `config/patch/etkinlik.json`: `collect_game/1` ve `viral_offers/1..5` için `starts_at`, `duration` (sürekli açık,
   bitiş < now + 68 yıl; öneri 2038-01-01). `viral_icons` değişmez.
2. Sayfa kancası `window.showPopupSEHelpOffer(no)` + sunucu yolu (A'daki aynı yol, `viralOffers[no].friends` listesine
   bot ekler; `num_workers` sınırı; tekrar yok) + `forceReloadInfo`. Bot yardımı kararı sahibine sorulana kadar
   yalnızca nakit yolu bırakılabilir.
3. (İsteğe bağlı) `gotoBuy` için sayfada işlev yok: tıklayınca ne olacağına karar.
4. `araclar/onindirme_listesi.py`: ada ve ödül birimi sprite'ları öncelik 1.
5. Testler: yama sonrası `get_client_game_config` çıktısında `collect_game["1"]` aktiflik koşulu (`starts_at < şimdi <
   starts_at+duration < şimdi + 2^31`), beş viral teklif için aynısı, `viral_icons` değişmediği; kanca için JS testi;
   mevcut komut testleri değişmez.
6. Tarayıcı (Ruffle) doğrulaması: ada haritada çıkıyor mu, pencere açılıyor mu, boru için `showPopupSEHelpOffer`
   çağrısı ve ödül alma uçtan uca. Bunlar çalıştırılmadı (?).
7. `docs/inceleme/1407-formuller.md` "açılması ayrı karar" satırları (152 ve viral bölümü) güncellensin; BULGULAR
   OYN-29, KAR-27 ✔; devir notu.

### Riskler (B)

- Davet düğmesi Facebook'a gidiyor: kanca yazılmazsa tıklamak hiçbir şey yapmaz (ölü düğme).
- Sınırsız bedelsiz bot yardımı ile ejderha ödülleri (2267, 2324, 2363, ada 2269/2272) hemen alınır; denge kararı.
- int32 taşması: süre alanları yanlış seçilirse ada/simge sessizce kaybolur.
- Temel pakette ada ve ödül birimi sprite'ları yok (çevrimdışı paketle ilk görüşte ağ gerekir).
- Çalışma zamanında uçtan uca denenmedi (Ruffle'da ada yerleşimi `encontrarZonaProximaLibre` ile boş yer arıyor; harita
  doluysa yerleşmeyebilir ?).

---------------------------------------------------------------------------------------------------

## Sahibine sorulması gerekenler

1. (A ve B) Bot yardımı: anında ve bedelsiz mi (Thor 4. seviyede, ejderhalar hemen), yoksa her yardımcı için bekleme
   süreli mi?
2. (A) Bot yardımı yalnız Asker Toplama (387) binasında mı, tüm sosyal binalarda mı? (Diğerlerinde nakit yolu var;
   bedava bot yardımı onların nakit bedelini anlamsız kılar.)
3. (B) Viral tekliflerin Facebook "davet" düğmesi çalışmayacak: bot yardımı mı, yalnız nakit satın alma mı? Beş teklifin
   hepsi mi (1-5), yoksa Ada'ya bağlı 2 ve ejderha teklifleri ayrı mı?
4. (B) Ada penceresinde ~4000 günlük geri sayım görünmesi kabul mü, yoksa "her açılışta 30 gün" gibi kayan pencere mi?
5. (B) `PopupIvoryOffer` ve `PopupNightForgeOffer` içindeki İngilizce kod dizgeleri (`BUY`, `BUY ALL FOR`) çevrilsin mi?
6. (B) Çevrimdışı temel pakete ada ve ejderha sprite'ları (≈ 14,5 MB) eklensin mi?
