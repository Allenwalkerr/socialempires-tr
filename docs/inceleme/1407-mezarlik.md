# 1.4.07 mezarlık (GEC-05, 11.11.2026)

Yardımcı ajanın bayt kodu araştırması. **Doğrulama notu:** kodlanan iddialar (kill@714-894, CommandManager/addCommand@16-99, PopupGraveyard/refreshItems ve get resurrectableUnits, PopupGraveyard/onBuyItem@145-395, PopupResurrectHeroes/onBuyItem@60-302, Constants ve Config değerleri) yeniden okundu ✔. recoverEnemyUnits `protect` notu doğrulanmadı (?).

# 1.4.07 mezarlık: saldıranın ölen birlikleri (bayt kodu araştırması)

İşaret: ✔ bayt kodunda okundu, ◐ çıkarım, ? doğrulanamadı. Depo dosyası değiştirilmedi.

## Kısa cevap
1. EVET, istemci PvP'de (ASSAULT) saldıranın kendi ölen birliğini yerelde `Base.resurrectableUnits`'e ekliyor.
   IsoFightingElement/kill@715-894: PlayerID == PLAYER_SELF ve (inServer || gameModeCurrent == ASSAULT) ise
   checkPutToGraveyard() çağrılır; true ise `Base.Main.addUnitToResurrectableUnits(birim.building.id)` ✔.
2. Sunucuya bunun için AYRI komut GİTMEZ ve ASSAULT'ta kill'in CMD_SELL'i de gitmez:
   kill@808 `Commands.addCommand({cmd:'sell', args:[x,y,id,townID,1,'KILL',mezarliga]})` tek argümanla çağrılır;
   CommandManager/addCommand@0-99 yalnızca `zorla(2. arg, varsayılan false) || mod==NORMAL || (mod==NEIGHBOUR &&
   cmd==ASSIST_NEIGHBOUR)` iken kuyruğa alır ✔ (dallanmalar elle izlendi, dup'lı ham döküm). ASSAULT kuyruğa
   almaz. ASSAULT'ta kuyruğa giren tek şey `sendAssaultResults`'ın `addCommand(..., true)` çağrısıdır (end_attack) ✔.
   Sonuç: yerel mezarlık sunucuya hiç bildirilmez; sunucu end_attack'ın attacker_units'inden çıkarmalıdır.
3. Kalıcılık: yalnızca privateState.resurrectableUnits (Base/loadGraveyardState@51-155, processAttacks@2050) ✔.
   Sunucu şu an bunu hiç yazmıyor (grep: oyun/*.py'de resurrectableUnits yok), yani yeniden yüklemede mezarlık boş.

## Ayrıntılar
### kill (IsoFightingElement/kill) ✔
- Parametreler (killer, dispatchBeingAttacked=true, mezarligaGit=true) (varsayılanlar yöntem bilgisinden: kind 11=true).
  Ana ölüm yolu recibirAtaque@1390 `kill(x, false)`: 3. parametre varsayılan true kalır.
- @175 PlayerID != ENEMY ise @519'a atlar. SELF + ASSAULT (@527-544) + uiAttack>0 + bModeQuest değil + id != EAGLE ise
  `Assault.killed(this)` (@595-599) çağrılır: arPlayerUnits[id].FIELD_KILLED++, numPlayerUnitsNow--, iPlayerKilled++,
  iGoldGainedVictim += ceil(değer*0.1) (Assault$/killed@392-484). Özetle satırlar `summoned` olmayan her SELF
  birimi içerir; summoned en başta çıkar (killed@32-45).
- DÜŞMAN (ENEMY) ölümünde mezarlık yok (@175-249: Assault.killed + PVP.RemoveResource).
- @715-899: SELF ve (inServer || ASSAULT): `mezarliga = checkPutToGraveyard() && 3.parametre`; CMD_SELL gönderilir
  (7 arg: iLastPosSentToServerX, Y, building.id, townID, PARAM_DONT_MODIFY_RESOURCES=1, SELL_REASON_KILL="KILL",
  mezarliga); mezarliga != 0 ise addUnitToResurrectableUnits(building.id).
- @903-967: PlayerID SELF değilse CMD_KILL (5 arg).

### checkPutToGraveyard ✔ (@0-405)
- summoned, ID_UNIT_PEASANT_MALE/FEMALE: false (mezarlık yok, deadUnits yok).
- ID_UNIT_BLUE_PHOENIX ve delegate(PhoenixDelegate).resurrect: false.
- subcat_functional COW, SHEEP, HORSE, BOAR: false.
- Kahramanlar RANGER, XENA, ARTHUR, MERLIN, VALKIRIA, WALLACE, THOR, HIGHELF: `Main.deadHeroes[id]++`, false
  (komutta mezarliga=0; resurrectableUnits'e GİRMEZ).
- Diğerleri: addToDeadUnits(id) -> `Main.deadUnits[id]++` (yerel sayaç), true.
- Anka yumurtası ölümü ayrı: PhoenixEggDelegate/onPhoenixEggDie@132-145 addToDeadUnits + CMD_PUT_GRAVEYARD
  (put_graveyard; başka kullanan yok) ✔.

### Base.addUnitToResurrectableUnits / sortGraveyard ✔
- addUnitToResurrectableUnits@0-36: `resurrectableUnits.push(id); sortGraveyard(); sigResurrectableUnitsListChange`.
  KAPASİTE DENETİMİ YOK. Çağıran tek yer: kill@894.
- sortGraveyard@0-207: id -> StaticData, `sortOn('life', DESCENDING|NUMERIC)`, listeyi id'lerle yeniden kurar. Sıra
  yani can değerine göre; eklenme sırası önemsiz (sunucu hangi sırayla eklese istemci yüklemede sıralar,
  loadGraveyardState@155). Eşit canlarda kararlılık ? (sortOn kararlı garantisi yok).
- loadGraveyardState: privateState.resurrectableUnits'i for-in (dizin->değer, parseInt) ile okur; yoksa boş; sonra
  graveyardCapacity, potionsReceived parseInt.

### Kurtarma (Assault$/recover*) ✔
- assaultEnd@100-134: bir kez (recovered bayrağı) recoverPlayerUnits + recoverEnemyUnits. Yalnızca Assault'un
  arPlayerUnits/arEnemyUnits dizilerinin FIELD_RECOVERED alanını değiştirir (RECOVERED=KILLED, sonra rastgele
  n - ceil(n*yüzde/100) kadarı düşülür, en çok 500 tur). `Base.resurrectableUnits`'e hiç dokunmaz: kurtarılan birim
  yerel mezarlıktan ÇIKMAZ (yerelde hem kurtarılmış hem diriltilebilir görünür; oturum sonunda kayıp).
- recoverEnemyUnits@283-288: protect==1 olan birim düşülmez (hep kurtarılır); protect!=1 düşülebilir (mevcut
  docs/inceleme/1407-pvp.md "yalnızca protect==1 kurtarılabilir" diyor: yön tersi gibi görünüyor ◐, bu sorunun dışı).
- sendAssaultResults gönderdiği `attacker_units` = arPlayerUnits (kurtarma SONRASI) satırları
  [id, başlangıç, ölen, kurtarılan] ✔ (@205-208).

### Kapasite ✔/◐
- İstemci eklerken sınır koymaz. Pencere: PopupGraveyard/init@86-93 maxCapacity = globals.GRAVEYARD_MAX_CAPACITY
  (config/patch/1-mega_patch.json: 10000); GraveYardItemContainer(maxItemQueueLength=capacity): unitIdListToQueue
  sırayla enqueue, uzunluk > sınır ise dequeue (baştakini atar) -> sıralı (can azalan) listede en yüksek canlılar
  gösterilmez, `numberOfDiscartedUnits` sayılır (◐ görüntü sonucu). Main.graveyardCapacity (privateState.
  graveyardCapacity) pencerede OKUNMUYOR (yalnızca loadGraveyardState yazar) ✔. Yani "dolunca ne olur" kural
  sunucuya kalmış; istemcide yalnızca görüntü kırpması var.

### Diriltme ✔
- PopupGraveyard/onBuyItem@350-395: `resurrect_hero` args [staticData.id, tx, ty, townID, '1'] (addCommand tek
  argüman, NORMAL kip). Yerelde: iPotions -= staticData.potion (@149-165), resurrectUnit(id): Main.deadUnits[id]--
  (0 olunca silinir) ve resurrectableUnits'ten ilk eşleşmeyi splice eder (@123-138). Sunucu resurrect_hero
  (oyun/komutlar.py:1565) deadHeroes sayacını düşer, potion'u 1 düşer, birimi ekler; resurrectableUnits'ten
  ÇIKARMAZ. Potion düşümü istemcide staticData.potion, sunucuda sabit 1 (? potion değerleri bakılmadı).
- Kahramanlar ayrı pencere (PopupResurrectHeroes, Main.deadHeroes; aynı komut).

### Saldırı dışı (NORMAL kip, kendi köyünde ölen birim)
- Komut: `sell` [x, y, id, kasaba, 1, "KILL", mezarliga] (kill@808-867) ✔. Sunucu sell (komutlar.py:313-324):
  arg[6] doğruysa mezarliga_ekle -> privateState.deadHeroes[id]++ (tüm birimler için tek sayaç sözlüğü; yüklemede
  processAttacks@1728-2010: kahraman id'leri Main.deadHeroes'a, diğerleri Main.deadUnits'e) ✔.
  Sunucu resurrectableUnits'e YAZMIYOR: yerelde eklenir, yeniden yüklemede kaybolur (kayıp: mezarlık listesi boş).
- Kahramanın ölümü: komutta arg[6]=0 (checkPutToGraveyard false) -> sunucu deadHeroes'a yazmıyor; kahraman
  yeniden yüklemede ölü sayılmaz (sell + neden "KILL" + kahraman id'siyle çıkarılabilir ◐).

## Sunucu önerisi (saldiri_bitir, oyun/pvp.py ~241)
Her attacker_units satırı [id, başlangıç, ölen, kurtarılan] için `net = max(0, ölen - kurtarılan)` (birimleri sildiğiniz
_olenler ile aynı sayı; hem sell dalında hem burada tek kaynak olsun):
1. Atla: tür 'u' olmayanlar; Constants'taki köylü (male/female) kimlikleri; subcat_functional inek/koyun/at/yaban
   domuzu olanlar (SUBCATFUNC_UNIT_COW/SHEEP/HORSE/BOAR); mavi anka (delegate durumu bilinmez, ?). Summoned zaten
   satırda yok (Assault$/killed@32-45).
2. Kahraman kimlikleri (RANGER, XENA, ARTHUR, MERLIN, VALKIRIA, WALLACE, THOR, HIGHELF): yalnızca
   privateState.deadHeroes[id] += net (resurrectableUnits'e değil).
3. Diğerleri: `privateState.deadHeroes[str(id)] += net` (Main.deadUnits sayacı için, resurrect_hero ile uyumlu) ve
   `privateState.resurrectableUnits`'e id'yi `net` kez ekle. Sıra önemsiz (istemci can'a göre sıralar).
4. Sınır: len(liste) <= graveyardCapacity (yoksa/0 ise GRAVEYARD_MAX_CAPACITY=10000). İstemci davranışı yok
   (görüntü kırpması hariç); önerim dolunca fazlayı eklememek (hem liste hem sayaç). ◐ karar.
5. Neden `ölen - kurtarılan`, `ölen` değil: istemci yerelde ölenlerin hepsini ekler ama kurtarılanlar haritada
   kalır (_birimleri_sil yalnızca net kaybı siler); hepsini eklemek aynı birimi hem haritada hem mezarlıkta
   bırakıp diriltmeyle çoğaltırdı. Gerçek sunucunun tercihi ? (görülemez).
6. Aynı iş NORMAL kipte: sell işleyicisi arg[6] doğruysa resurrectableUnits'e de id eklesin; sell + "KILL" + kahraman
   id'si deadHeroes'a işlesin; resurrect_hero ilk eşleşen id'yi resurrectableUnits'ten silsin.
7. Başka komut gerekmiyor. end_attack_new ganimet içindir, mezarlıkla ilgisiz.
