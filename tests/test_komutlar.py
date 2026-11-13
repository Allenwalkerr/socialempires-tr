"""Komut işleyicileri: argüman sıraları istemci bytecode'undan alınmıştır.

Çalıştırma: python tests/test_komutlar.py
"""

import json
import math
import unittest
from unittest import mock

from ortak import KomutTesti, bos_kayit


class EsyaKomutlari(KomutTesti):
    def test_buy_maliyet_xp_ve_yon(self):
        # [id, x, y, yon, kasaba, bedava, carpan, tur] - Ev I: 30 odun
        self.komut("buy", 1, 30, 31, 1, 0, 0, 1, "b")
        self.assertEqual(self.harita["wood"], 1000 - 30)
        self.assertEqual(self.harita["items"][-1][:4], [1, 30, 31, 1])
        self.assertEqual(self.harita["xp"], 3)  # Ev I'in xp'si

    def test_buy_indirim_carpani_uygulanir(self):
        self.komut("buy", 1, 30, 31, 0, 0, 0, "0.9", "u")
        self.assertEqual(self.harita["wood"], 1000 - 27)

    def test_buy_bedava(self):
        self.komut("buy", 1, 30, 31, 0, 0, 1, 1, "b")
        self.assertEqual(self.harita["wood"], 1000)
        self.assertEqual(self.harita["xp"], 0)

    def test_move_ve_orient(self):
        self.komut("move", 10, 10, 1, 40, 41, 2, 0, "MouseUsed")
        self.assertEqual(self.harita["items"][0][:4], [1, 40, 41, 2])
        self.komut("orient", 40, 41, 3, 0)
        self.assertEqual(self.harita["items"][0][3], 3)

    def test_sell_yuzde_bes_iade(self):
        self.komut("sell", 10, 10, 1, 0, 0, "")
        self.assertEqual(len(self.harita["items"]), 1)
        self.assertEqual(self.harita["wood"], 1000 + 1)  # 30 * 0.05

    def test_yukseltmede_satis_iadesi_yok(self):
        """DNT-27 (denetim EKF-08). 1.4.07 bayt kodu: IsoBuilding/upgrade eski binayı Base/removeElement(..., "UPGR")
        ile kaldırır ve sell [x, y, id, kasaba, 0, "UPGR"] yollar; ekranda iade vermez, yalnızca yeni binanın tam
        bedelini düşer (IsoEngine/getDifferenceCost = [yeni.cost, yeni.cost_type]) ve yeni binanın xp'sini ekler; ardından
        buy [id, x, y, 1, kasaba, 0, 1, tür]. Ev I: 30 odun, 3 xp (config)."""
        self.komut("sell", 10, 10, 1, 0, 0, "UPGR")
        self.komut("buy", 1, 10, 10, 1, 0, 0, 1, "b")
        self.assertEqual(self.harita["wood"], 1000 - 30)  # iade yok: istemcinin gösterdiğiyle aynı
        self.assertEqual(self.harita["xp"], 3)
        self.assertEqual([e[:3] for e in self.harita["items"]].count([1, 10, 10]), 1)

    def test_olmayan_esya_satilinca_iade_yok(self):
        self.komut("sell", 99, 99, 1, 0, 0, "")
        self.assertEqual(self.harita["wood"], 1000)

    def test_depoya_kaldir_ve_yerlestir(self):
        self.komut("store_item", 10, 10, 0, 1)
        self.assertEqual(self.ps["gifts"][1], 1)
        # place_gift: [id, x, y, yon, kasaba]
        self.komut("place_gift", 1, 5, 6, 1, 0)
        self.assertEqual(self.ps["gifts"], [])
        self.assertEqual(self.harita["items"][-1][:4], [1, 5, 6, 1])

    def test_hediye_yerlestirme_xp_verir_depodan_yerlestirme_vermez(self):
        """TST-02, DNT-43. 1.4.07 Base/sendPlaceItemCmd: giftId yolunda (@40-262, place_gift) istemci xp verir: seviye
        heykelinde (Constants.ID_BUILDING_LEVELUP_STATUE 1478) uiExpMax − iExperience (@59-84; uiExpMax =
        levels[seviye].exp_required, PlayerStatus/checkForLevelUp), öteki eşyada selectedBuilding.xp (@131-145);
        place_stored_item yolu (@352-405) xp vermez. Config: Ev I xp 3; levels[10].exp_required 1993."""
        from oyun.config import get_item_from_id, seviye_araligi
        self.assertEqual((get_item_from_id(1)["xp"], seviye_araligi(10)[1], get_item_from_id(1478)["name"]),
                         ("3", 1993, "Level Up Statue"))
        self.ps["gifts"] = [0, 2]
        self.harita["xp"] = 1600
        self.komut("place_gift", 1, 5, 6, 0, 0)
        self.assertEqual(self.harita["xp"], 1603)
        self.komut("place_stored_item", 1, 7, 8, 0, 0)
        self.assertEqual(self.harita["xp"], 1603)
        self.ps["gifts"] = [0] * 1478 + [1]
        self.komut("place_gift", 1478, 9, 9, 0, 0)
        self.assertEqual(self.harita["xp"], 1993)  # bir sonraki seviyenin eşiği
        self.komut("place_gift", 1478, 9, 9, 0, 0)  # depoda yok: xp de yok
        self.assertEqual(self.harita["xp"], 1993)

    def test_nufus_artisi_haritaya(self):
        """TST-02. PopupRecruitmentPopulation/onRecruitComplete: Player.increasedPopulation + 1 ve increase_population
        [townID]; PlayerStatus/Init @61-81 değeri _mapInfo.increasedPopulation'dan okur (yoksa 0)."""
        self.komut("increase_population", 0)
        self.komut("increase_population", 0)
        self.assertEqual(self.harita["increasedPopulation"], 2)

    def test_yuva_ve_tapinak_adimi_nakitle(self):
        """TST-02. 1.4.07: PopupDragons/clickGetnow, PopupMonstersNest/clickGetnow, PopupDragonRiderTraining/clickGetNow ve
        PopupBahamutSupremeInvocationTemple$/clickGetnow nakdi ekranda düşer ve bedeli tek argümanla yollar; zaman damgası
        sıfırlanır (tapınakta privateState.timeStampTemple = 0). Yuvada istemci 0 yazar; NestsManager/check ve
        getDragonTimeLeft'e göre damga ≤ 0 iken adım hazırdır (kalan süre = adım − (şimdi − damga) < 0)."""
        for komut, alan, bedel in (("buy_step_cash", "timeStampTakeCare", 7), ("buy_monster_step_cash", "timeStampTakeCareMonster", 5),
                                   ("rider_buy_step_cash", "riderTimeStamp", 3)):
            self.ps[alan] = 2_000_000_000
            once = self.cash
            self.komut(komut, bedel)
            self.assertEqual(self.cash, once - bedel, komut)
            self.assertLessEqual(self.ps[alan], 0, komut)
        self.ps["timeStampTemple"] = 2_000_000_000
        once = self.cash
        self.komut("buy_temple_step_cash", 4)
        self.assertEqual((self.cash, self.ps["timeStampTemple"]), (once - 4, 0))

    def test_dart_atisi(self):
        """TST-02. PopupDarts/onClickPlay: dartsHasFree değilse globals.DART_COST_CASH kadar nakit düşer; hitBalloon
        darts_shoot_balloon [balon, dartsHasFree ? 0 : 1, gotExtraInThisThrow ? 1 : 0] yollar ve balonu dartsBalloonsShot'a
        ekler; ödül storeItem(..., true) ile ayrı komutla gelir. Config: DART_COST_CASH."""
        from oyun.config import get_game_config
        bedel = int(get_game_config()["globals"]["DART_COST_CASH"])
        once = self.cash
        self.komut("darts_shoot_balloon", 3, 0, 0)  # bedava atış
        self.assertEqual((self.cash, self.ps["dartsBalloonsShot"], self.ps["dartsHasFree"]), (once, [3], False))
        self.komut("darts_shoot_balloon", 5, 1, 1)  # ücretli, ekstra
        self.assertEqual((self.cash, self.ps["dartsBalloonsShot"], self.ps["dartsGotExtra"]), (once - bedel, [3, 5], True))

    def test_gorev_sonu_ada_sirasi_ve_odul(self):
        """DNT-44, TST-02. 1.4.07: Quest*/sendResults end_quest [JSON {map, resources {g, x}, win, quest_id, item_rewards,
        set_unlocked_index, ...}] yollar; QuestBossGolem: quest_id QUEST_BOSS_GOLEM (100000003), item_rewards {"537": 1}
        (ödülü storeItem(.., false, false) ile komutsuz depoya koyar), set_unlocked_index 1; QuestCollectable1-5: 0.
        unlockedQuestIndex globals.ISLE_ORDER'da açık son adanın sırasıdır: PopupQuestsManager/<kurucu> @1207-1232 ada
        kilitli = isLevelLocked || sıra > unlockedQuestIndex. Config ISLE_ORDER: 100000003 8. sırada (indeks 7)."""
        from oyun.config import get_game_config
        sira = [str(g) for g in get_game_config()["globals"]["ISLE_ORDER"]]
        self.assertEqual(sira.index("100000003"), 7)
        self.ps["unlockedQuestIndex"] = 2
        altin, xp = self.harita["coins"], self.harita["xp"]
        self.ps["gifts"] = []
        self.komut("end_quest", json.dumps({"map": 0, "resources": {"g": 150, "x": 30}, "win": True, "quest_id": 100000003,
                                            "item_rewards": {"537": 1}, "set_unlocked_index": 1}))
        self.assertEqual(self.ps["unlockedQuestIndex"], 8)
        self.assertEqual((self.harita["coins"] - altin, self.harita["xp"] - xp, self.ps["gifts"][537]), (150, 30, 1))
        self.komut("end_quest", json.dumps({"map": 0, "resources": {"g": 0, "x": 0}, "win": True, "quest_id": 100000006,
                                            "item_rewards": {}, "set_unlocked_index": 1}))  # sıra 0: geri düşmez
        self.assertEqual(self.ps["unlockedQuestIndex"], 8)
        self.komut("end_quest", json.dumps({"map": 0, "resources": {"g": 0, "x": 0}, "win": True, "quest_id": 100000055,
                                            "item_rewards": {}, "set_unlocked_index": 0}))  # koleksiyon görevi
        self.komut("end_quest", json.dumps({"map": 0, "resources": {"g": 0, "x": 0}, "win": True, "quest_id": 100000092,
                                            "item_rewards": {}, "set_unlocked_index": 0}))  # listedeki ada, bayrak 0
        self.komut("end_quest", json.dumps({"map": 0, "resources": {"g": 0, "x": 0}, "win": False, "quest_id": 100000092,
                                            "item_rewards": {}, "set_unlocked_index": 1}))  # yenilgi
        self.assertEqual(self.ps["unlockedQuestIndex"], 8)
        # QuestBossDragon2/sendResults anahtarı iki noktalı yazar ('set_unlocked_index:', 1); QUEST_BOSS_DRAGON_2 100000033,
        # ISLE_ORDER'da indeks 17
        self.komut("end_quest", json.dumps({"map": 0, "resources": {"g": 0, "x": 0}, "win": True, "quest_id": 100000033,
                                            "item_rewards": {}, "set_unlocked_index:": 1}))
        self.assertEqual(self.ps["unlockedQuestIndex"], 18)

    def test_gorev_zaferi_zorlugu_kaydeder(self):
        """DNT-66. Sahibi: 'adayı bitirdim, zorluk seçemiyorum, yıldız kazanılmıyor'. Quest*/sendResults end_quest'e
        'difficulty' (Quest.difficulty, 1-3) ve 'quest_id' koyar (QuestIslaTrollsGeneric/sendResults @147-156).
        İstemci questsRank'i hiç yazmaz, yalnızca okur: PlayerStatus/Init privateState.questsRank'ten alır;
        PopupLoadingQuest/<kurucu> @1674-1755 rank 1 ya da 2 ise rank + 1'i açar, 3 yıldız tavandır. Değer, adada
        kazanılmış en yüksek zorluktur (PopupQuestFinished: ilk onur rank yoksa ya da rank < difficulty)."""
        self.ps["questsRank"] = {}
        sonuc = {"map": 0, "resources": {"g": 0, "x": 0}, "quest_id": 100000003, "item_rewards": {}, "set_unlocked_index": 0}
        self.komut("end_quest", json.dumps(dict(sonuc, win=True, difficulty=1)))
        self.assertEqual(self.ps["questsRank"], {"100000003": 1})
        self.komut("end_quest", json.dumps(dict(sonuc, win=False, difficulty=2)))  # yenilgi açmaz
        self.assertEqual(self.ps["questsRank"], {"100000003": 1})
        self.komut("end_quest", json.dumps(dict(sonuc, win=True, difficulty=3)))
        self.assertEqual(self.ps["questsRank"], {"100000003": 3})
        self.komut("end_quest", json.dumps(dict(sonuc, win=True, difficulty=1)))  # kolay zafer düşürmez
        self.assertEqual(self.ps["questsRank"], {"100000003": 3})
        self.komut("end_quest", json.dumps(dict(sonuc, win=True, difficulty=7, quest_id=100000006)))  # 1-3 dışı
        self.assertNotIn("100000006", self.ps["questsRank"])

    def test_depoda_olmayan_esya_yerlestirilip_satilamaz(self):
        # tekrarlanan komut: depo boşken eşya çoğalmamalı, iade verilmemeli
        self.ps["gifts"] = [0, 1]
        self.komut("place_gift", 1, 5, 6, 0, 0)
        self.komut("place_gift", 1, 7, 8, 0, 0)
        self.assertEqual(sum(1 for e in self.harita["items"] if e[0] == 1), 2)  # 1 mevcut + 1 yeni
        self.komut("sell_gift", 1, 0)
        self.assertEqual(self.harita["wood"], 1000)

    def test_mobil_kutudan_yerlestirme_ve_satis_bir_kez(self):
        """DNT-45, TST-02. 1.4.07 GiftButtonLarge/sellGiftReally: iphoneId olan eşya sell_iphone_item [id, townID] ile satılır,
        Base/sendPlaceItemCmd @270-345 place_iphone [id, x, y, frame, townID] ile yerleştirilir; istemci eşyayı kutudan bir kez
        çıkarır. Kutuda olmayan eşya için tekrarlanan komut eşyayı ya da iadeyi çoğaltmamalı (sell_gift ve DNT-20 gibi).
        Ev I: 30 odun, iade %5 (satis_iadesi)."""
        self.ps["iphoneBox"] = [1, 1]
        self.komut("place_iphone", 1, 5, 6, 0, 0)
        self.komut("sell_iphone_item", 1, 0)
        self.assertEqual((self.ps["iphoneBox"], self.harita["wood"]), ([], 1000 + 1))
        adet = sum(1 for e in self.harita["items"] if e[0] == 1)
        self.komut("place_iphone", 1, 7, 8, 0, 0)  # kutu boş
        self.komut("sell_iphone_item", 1, 0)
        self.assertEqual((sum(1 for e in self.harita["items"] if e[0] == 1), self.harita["wood"]), (adet, 1000 + 1))

    def test_komsu_yardimi_ve_ejderha_adimi(self):
        """TST-02. 1.4.07: FauxBar2/update ekranda globals.ASSIST_REWARD_GOLD altın ve ASSIST_REWARD_XP xp verir, assist_neighbor
        [komşu_pid, lastIdAssist, townID] yollar. PopupDragons/goNextStep _stepCash kadar nakit düşer, next_step [_stepCash ya da 0]
        yollar, dragonStepNumber + 1 (PlayerStatus/Init privateState.stepNumber'dan okur) ve timeStampTakeCare = şimdi."""
        from unittest import mock
        from oyun.config import get_game_config
        g = get_game_config()["globals"]
        altin, xp = self.harita["coins"], self.harita["xp"]
        self.komut("assist_neighbor", "komsu1", 3, 0)
        self.assertEqual((self.harita["coins"] - altin, self.harita["xp"] - xp),
                         (int(g["ASSIST_REWARD_GOLD"]), int(g["ASSIST_REWARD_XP"])))
        self.assertIn("ukomsu1", self.ps["neighborAssists"])
        self.ps["stepNumber"] = 2
        with mock.patch.object(self.komutlar, "timestamp_now", return_value=2_000_000_000):
            self.komut("next_step", 6)
        self.assertEqual((self.cash, self.ps["stepNumber"], self.ps["timeStampTakeCare"]), (94, 3, 2_000_000_000))

    def test_yuva_acma_kapama_ve_sonraki(self):
        """TST-02. 1.4.07 PopupInactiveNest/goBuy: bedel globals.ACTIVATE_DRAGON_NEST_CASH/GOLD ya da
        ACTIVATE_MONSTER_NEST_CASH/GOLD (ekranda düşer); activate_dragon/activate_monster [CostType] yollar ve
        privateState.dragonNestActive / monsterNestActive = 1 yapar. Yuva kapanınca ve sonraki ejderhaya geçilince adım
        sayacı sıfırlanır, damga ≤ 0 (NestsManager/check: adım hazır). Config: 50 nakit, 100000 altın."""
        from oyun.config import get_game_config
        g = get_game_config()["globals"]
        self.harita["coins"] = 300000
        self.komut("activate_dragon", "c")
        self.komut("activate_monster", "g")
        self.assertEqual((self.cash, self.harita["coins"]),
                         (100 - int(g["ACTIVATE_DRAGON_NEST_CASH"]), 300000 - int(g["ACTIVATE_MONSTER_NEST_GOLD"])))
        self.assertEqual((self.ps["dragonNestActive"], self.ps["monsterNestActive"]), (1, 1))
        self.ps.update(stepNumber=4, dragonNumber=1)
        self.komut("next_dragon")
        self.assertEqual((self.ps["stepNumber"], self.ps["dragonNumber"]), (0, 2))
        self.assertLessEqual(self.ps["timeStampTakeCare"], 0)
        self.komut("desactivate_dragon")
        self.assertEqual((self.ps["dragonNestActive"], self.ps["stepNumber"], self.ps["dragonNumber"]), (0, 0, 0))
        # bedel her yuvanın kendi anahtarından okunur (config değişirse istemciyle birlikte değişir)
        from unittest import mock
        sahte = dict(g, ACTIVATE_DRAGON_NEST_CASH=7, ACTIVATE_MONSTER_NEST_CASH=9,
                     ACTIVATE_DRAGON_NEST_GOLD=11, ACTIVATE_MONSTER_NEST_GOLD=13)
        with mock.patch.object(self.komutlar, "globals_", lambda: sahte):
            once = self.cash
            self.komut("activate_dragon", "c")
            self.assertEqual(once - self.cash, 7)
            self.komut("activate_monster", "c")
            self.assertEqual(once - self.cash, 16)
            altin = self.harita["coins"]
            self.komut("activate_dragon", "g")
            self.assertEqual(altin - self.harita["coins"], 11)
            self.komut("activate_monster", "g")
            self.assertEqual(altin - self.harita["coins"], 24)

    def test_tapinak_adimi(self):
        """TST-02. 1.4.07 PopupBahamutSupremeInvocationTemple/doAction: next_temple_step [JSON veri, adım]. RESOURCES_SUBSTRACT
        adımında veri _configTemple[adım].data'dır ({tür: miktar}, mana dahil) ve istemci ekranda düşer (@598-744);
        SACRIFICE_UNIT'te {"u": birim} gider, birimi MapInitializer$/removeFromMapNoResources ayrı bir sell
        [.., PARAM_DONT_MODIFY_RESOURCES] ile kaldırır; COMPLETE_COLLECTION'da {"collection": c} gider, parça harcanmaz.
        privateState.templeStep'e adım eklenir."""
        from unittest import mock
        self.ps["mana"] = 10
        altin = self.harita["coins"]
        with mock.patch.object(self.komutlar, "timestamp_now", return_value=2_000_000_000):
            self.komut("next_temple_step", json.dumps({"g": 5000, "m": 3}), 2)
        self.assertEqual((altin - self.harita["coins"], self.ps["mana"], self.ps["templeStep"], self.ps["timeStampTemple"]),
                         (5000, 7, [2], 2_000_000_000))
        self.komut("next_temple_step", json.dumps({"u": 512}), 3)  # kurban: kaynak değişmez (birim sell ile gider)
        self.komut("next_temple_step", json.dumps({"collection": 4}), 4)
        self.assertEqual((altin - self.harita["coins"], self.ps["mana"], self.ps["templeStep"]), (5000, 7, [2, 3, 4]))

    def test_depoya_gecersiz_adet_eklenmez(self):
        self.komut("end_survival", 1, 30, json.dumps({"523": -1, "-2": 1}))
        self.assertEqual(self.ps["gifts"], [])

    def test_depoda_sifir_olan_esya_satilmaz(self):
        self.ps["gifts"] = [0, 0, 3]  # Ev I (1) sıfır, arkasında başka eşya var
        self.komut("sell_stored_item", 1, 0)
        self.assertEqual((self.ps["gifts"], self.harita["wood"]), ([0, 0, 3], 1000))

    def test_depodaki_esyayi_sat(self):
        self.ps["gifts"] = [0, 2]
        self.komut("sell_stored_item", 1, 0)
        self.assertEqual(self.ps["gifts"], [0, 1])
        self.assertEqual(self.harita["wood"], 1000 + 1)  # Ev I: 30 odunun %5'i, aşağı yuvarlanır

    def test_depoya_cash_ile_esya(self):
        # [kasaba, id, cash]
        self.komut("buy_stored_item_cash", 0, 5, 7)
        self.assertEqual(self.ps["gifts"][5], 1)
        self.assertEqual(self.cash, 93)

    def test_upgrade_seviye_artirir(self):
        self.komut("upgrade", 10, 10, 0)
        self.assertEqual(self.harita["items"][0][5], 1)
        self.assertEqual(self.harita["items"][0][0], 1)

    def test_bina_kilidi_ve_tema(self):
        self.komut("unlock_building", "9001")  # min_level 20 -> 7 cash
        self.assertEqual(self.ps["unlockedEarlyBuildings"], {"9001": True})
        self.assertEqual(self.cash, 93)
        self.komut("unlock_skin", "3")
        self.komut("set_skin", 0, "3")
        self.assertEqual(self.ps["unlockedSkins"], {"3": True})
        self.assertEqual(self.harita["skin"], 3)

    def test_arazi_genisletme_sirali_fiyat(self):
        # ilk açılan arazi 4000 altın, ikincisi 40.000 altın ya da 25 cash
        self.komut("expand", 14, "gold", 0)
        self.komut("expand", 14, "gold", 0)  # aynı arazi: yeniden alınmaz
        self.assertEqual(self.harita["coins"], 50000 - 4000)
        self.komut("expand", 15, "cash", 0)
        self.assertEqual((self.cash, self.harita["expansions"]), (100 - 25, [13, 14, 15]))

    def test_nakit_altina_ve_iksire(self):
        self.komut("exchange_cash_new", 0)  # 5 cash -> 2500 altın
        self.assertEqual((self.cash, self.harita["coins"]), (95, 52500))
        self.komut("graveyard_buy_potions")  # 5 cash -> 25 iksir (boş kayıtta 1 vardı)
        self.assertEqual((self.cash, self.ps["potion"]), (90, 1 + 25))

    def test_ikinci_kasaba_acilir(self):
        self.kayit["playerInfo"]["cash"] = 50
        self.komut("buy_map", 1, 1, "t", 0)
        self.komut("buy_map", 1, 1, "t", 0)  # tekrar: yeniden ücret alınmaz
        self.assertEqual(len(self.kayit["maps"]), 2)
        self.assertEqual(self.kayit["maps"][1]["race"], "t")
        self.assertEqual(self.cash, 50 - 22)
        self.assertEqual(len(self.kayit["playerInfo"]["map_names"]), 2)


class DepoCogaltmaz(KomutTesti):
    """DNT-20 (denetim SNK-03). İstemci Base/storeItem store_item'ı (ve _frombug'ı) haritadaki öğenin tx, ty'siyle
    yollar; haritada olmayanı depoya eklemek için ayrı komut (store_add_items) vardır. Tekrarlanan ya da bozuk komut
    eşya/birim çoğaltmamalı. bos_kayit haritası: (10, 10)'da 1 (House I)."""

    def test_store_item_yalnizca_haritadakini_depolar(self):
        for _ in range(3):
            self.komut("store_item", 10, 10, 0, 1)
        self.assertEqual(self.ps["gifts"][1], 1)
        self.assertNotIn(1, [e[0] for e in self.harita["items"]])
        self.komut("store_item_frombug", 50, 50, 0, 19)  # orada 19 yok
        self.assertEqual(sum(self.ps["gifts"]), 1)

    def test_birim_deposu_cogaltmaz(self):
        self.harita["items"].append([512, 30, 30, 0, 0, 0])
        for _ in range(2):
            self.komut("add_unit_warehouse", 30, 30, 0, 512)
        self.assertEqual(self.harita["warehousedUnits"], [512])
        for _ in range(2):
            self.komut("place_warehoused_item", 512, 31, 31, 0, 0)
        self.assertEqual(([e[0] for e in self.harita["items"]].count(512), self.harita["warehousedUnits"]), (1, []))


class Kaynaklar(KomutTesti):
    def test_kaynak_ve_nakit_eksiye_dusmez(self):
        """Eksiye düşmez; sahibinin kararı KAR-18 (11.11.2026): bedel bakiyeyi aşarsa reddedilir (önce 0'a
        kıskaçlanıyordu, bu bedava alım demekti)."""
        from oyun.ekonomi import Yetersiz
        self.kayit["playerInfo"]["cash"] = 5
        self.ps["mana"] = 2
        for yap in (lambda: self.komutlar.cash_ekle(self.kayit, -8),
                    lambda: self.komutlar.kaynak_ekle(self.kayit, self.harita, "w", -5000),
                    lambda: self.komutlar.kaynak_ekle(self.kayit, self.harita, "m", -3)):
            with self.assertRaises(Yetersiz):
                yap()
        self.assertEqual((self.cash, self.harita["wood"], self.ps["mana"]), (5, 1000, 2))
        self.komutlar.cash_ekle(self.kayit, -5)  # tam bakiye yeter
        self.komutlar.kaynak_ekle(self.kayit, self.harita, "c", 7)
        self.assertEqual(self.cash, 7)

    def test_yetersiz_alim_uygulanmaz(self):
        """KAR-18: bedeli karşılanamayan buy kayda girmez; paketteki öteki komutlar uygulanır. Eksi fiyat çarpanı
        (denetim EKF-03: kaynak yaratıyordu) da reddedilir. Config: 1 (House I) 30 odun."""
        from oyun.config import get_item_from_id
        ev = get_item_from_id(1)
        self.assertEqual((ev["cost_type"], int(ev["cost"])), ("w", 30))
        self.harita["wood"] = 20
        esya = len(self.harita["items"])
        self.komutlar.command("test", {"commands": [
            {"cmd": "buy", "args": [1, 30, 30, 0, 0, 0, 1, 0]},  # 30 odun, 20 var
            {"cmd": "buy", "args": [1, 31, 31, 0, 0, 0, -5, 0]},  # eksi çarpan
            {"cmd": "buy", "args": [1, 32, 32, 0, 0, 0, -0.05, 0]},  # satış iadesinin çarpanı (#46 incelemesi)
            {"cmd": "rt_publish_score", "args": [7]}]})
        self.assertEqual((self.harita["wood"], len(self.harita["items"]), self.harita["xp"]), (20, esya, 7))
        self.harita["wood"] = 30
        self.komutlar.command("test", {"commands": [{"cmd": "buy", "args": [1, 30, 30, 0, 0, 0, 1, 0]}]})
        self.assertEqual((self.harita["wood"], len(self.harita["items"])), (0, esya + 1))


class UretimKomutlari(KomutTesti):
    def test_collect_kaynak_ve_sayac(self):
        # [x, y, kasaba, id, birimler, carpan, cash] - 19: ağaç, 20 odun, 1 xp
        simdi = self.komutlar.timestamp_now()
        self.komut("collect_new", 20, 20, 0, 19, 1, 1, 0)
        self.assertEqual((self.harita["wood"], self.harita["xp"]), (1000 + 20, 1))
        self.assertGreaterEqual(self.harita["items"][1][4], simdi)

    def test_collect_carpan_ve_cash(self):
        # çarpan 3: 60 odun; hızlandırma için 2 cash
        self.komut("collect_new", 20, 20, 0, 19, 1, 3, 2)
        self.assertEqual((self.harita["wood"], self.cash), (1000 + 60, 98))
        self.komut("collect_new", 20, 20, 0, 19, 1, 50, 0)  # çarpan en çok 10
        self.assertEqual(self.harita["wood"], 1000 + 60 + 200)

    def test_collect_kisa_bicim(self):
        self.komut("collect_new", 20, 20, 0, 19)
        self.assertEqual((self.harita["wood"], self.harita["xp"]), (1000 + 20, 1))

    def test_pazar_alim_istemci_formulu(self):
        # [kasaba, kaynak, satis, miktar]: odun tabanı 100 -> 100 odun = 100 altın
        self.komut("trade_resource_b", 0, "w", 0, 100)
        self.assertEqual(self.harita["coins"], 50000 - 100)
        self.assertEqual(self.harita["wood"], 1100)
        self.assertEqual(self.harita["resourcesTraded"]["w"], 1)
        # İkinci alım %2 pahalı
        self.komut("trade_resource_b", 0, "w", 0, 100)
        self.assertEqual(self.harita["coins"], 50000 - 100 - 102)

    def test_pazar_sayaci_sinirda_kalir(self):
        # MARKET_MAX_INCREMENTS 200, MARKET_MAX_DECREMENTS 25
        self.harita["resourcesTraded"] = {"w": 200, "s": -25}
        self.komut("trade_resource_b", 0, "w", 0, 100)
        self.komut("trade_resource_b", 0, "s", 1, 100)
        self.assertEqual(self.harita["resourcesTraded"], {"w": 200, "s": -25})

    def test_pazar_satis(self):
        self.komut("trade_resource_b", 0, "w", 1, 100)
        self.assertEqual(self.harita["coins"], 50000 + 75)
        self.assertEqual(self.harita["wood"], 900)
        self.assertEqual(self.harita["resourcesTraded"]["w"], -1)

    def test_birim_binaya_girer_cikar(self):
        self.harita["items"].append([512, 3, 3, 0, 0, 0])
        self.komut("push_unit", 3, 3, 512, 20, 20, 0)
        self.assertEqual(self.harita["items"][1][6], [512])
        self.komut("pop_unit", 20, 20, 0, 512, 4, 4, 2)
        self.assertEqual(self.harita["items"][1][6], [])
        self.assertEqual(self.harita["items"][-1][:4], [512, 4, 4, 2])

    def test_kimliksiz_bina_komutlari_karedeki_birimi_degil_binayi_bulur(self):
        """DNT-29 (denetim SNK-06): orient/upgrade/push_unit/pop_unit'te istemci bina kimliği yollamaz (bayt kodu
        argümanları, bu dosyanın öteki testleri). Birimler bina kapısında doğar: aynı karede önce birim olsa da komut
        binaya (config type "b") gider."""
        from oyun.config import get_item_from_id
        self.assertEqual((get_item_from_id(512)["type"], get_item_from_id(19)["type"]), ("u", "b"))
        birim = [512, 20, 20, 0, 0, 0]
        self.harita["items"].insert(1, birim)  # liste sırasında binadan önce
        bina = self.harita["items"][2]
        self.komut("orient", 20, 20, 3, 0)
        self.komut("upgrade", 20, 20, 0)
        self.komut("push_unit", 3, 3, 513, 20, 20, 0)
        self.assertEqual((bina[3], bina[5], bina[6]), (3, 1, [513]))
        self.assertEqual(birim, [512, 20, 20, 0, 0, 0])
        self.komut("pop_unit", 20, 20, 0, 513, 4, 4, 2)
        self.assertEqual(bina[6], [])
        self.harita["items"].remove(bina)
        self.komut("orient", 20, 20, 2, 0)  # karede bina yoksa eskisi gibi ilk eşya
        self.assertEqual(birim[3], 2)

    def test_kurban_binasindan_birim_satisi(self):
        """TST-02: pop_sell [bina_x, bina_y, kasaba, bina_id, birim_id]. 1.4.07 bayt kodu: IsoBuilding/PopSell birimi
        vUnitsContained'den çıkarır, komutu yollar, bina boşalınca activation ve collected_at'i 0 yapar (üretim yeniden
        başlar); altın iadesini IsoElement/collect @2762-2830 verir: birimin bedeli altınsa Token(TOKEN_GOLD,
        floor(cost / Config.DIVISOR_SELL)), DIVISOR_SELL 20. Light Knight (512): 75 altın → 3."""
        from unittest import mock
        bina = [7, 20, 20, 0, 1000, 0, [512, 512], {}]
        self.harita["items"].append(bina)
        altin = self.harita["coins"]
        with mock.patch.object(self.komutlar, "timestamp_now", return_value=2_000_000_000):
            self.komut("pop_sell", 20, 20, 0, 7, 512)
            self.assertEqual((bina[6], bina[4], self.harita["coins"] - altin), ([512], 1000, 3))
            self.komut("pop_sell", 20, 20, 0, 7, 512)
            self.assertEqual((bina[6], bina[4], self.harita["coins"] - altin), ([], 2_000_000_000, 6))

    def test_tukenen_ciftligin_kill_i_xp_vermez(self):
        """TST-02: 1.4.07 IsoElement/collect @3438-3675: çiftlikte (SUBCATFUNC_BUILDING_FARM) Math.round(collect / 3) odun
        yetmezse çiftlik SELL_REASON_FARM_DEPLETED ile kaldırılır ve kill [x, y, id, kasaba, tür] gider; collect_xp'yi
        veren @3805-3831 local12 false olduğu için atlanır. Pumpkin Crop (8): config collect_xp 2. (Ölen birimin ve yıkılan
        düşman binasının kill'indeki xp ayrı bir soru, TST-02 notu.)"""
        from oyun.config import get_item_from_id
        self.assertEqual((get_item_from_id(8)["subcat_functional"], get_item_from_id(8)["collect_xp"]), ("122", "2"))
        self.harita["items"].append([8, 30, 30, 0, 0, 0])
        xp = self.harita["xp"]
        self.komut("kill", 30, 30, 8, 0, "b")
        self.assertEqual(self.harita["xp"], xp)
        self.assertNotIn([8, 30, 30], [e[:3] for e in self.harita["items"]])

    def test_birim_deposu_kapasitesi_ve_pvp_arazisi_nakitle(self):
        """TST-02. 1.4.07 bayt kodu:
        - PopupUnitWarehouse/onBuyMoreSlots: upgradePrice (kurucu: globals.WAREHOUSE_CAPACITY_INCREASE_PRICE_SINGLE)
          kadar nakit; buy_warehouse_capacity_single [kasaba]. Base/loadPlayerInfoSuccess @1838-1854 kapasiteyi
          map.warehouseAditionalCapacitySingle'dan okur.
        - PopupBuyTerritoryPvp/onBuy: costCash (kurucu: globals.PVP_BUY_TERRITORY_CASH) kadar nakit;
          buy_pvp_territory [position]; mapInfo.universAttackWin'e eklenir.
        Config globals: WAREHOUSE_CAPACITY_INCREASE_PRICE_SINGLE 2, PVP_BUY_TERRITORY_CASH 5."""
        from oyun.config import get_game_config
        g = get_game_config()["globals"]
        self.assertEqual((g["WAREHOUSE_CAPACITY_INCREASE_PRICE_SINGLE"], g["PVP_BUY_TERRITORY_CASH"]), (2, 5))
        self.komut("buy_warehouse_capacity_single", 0)
        self.komut("buy_warehouse_capacity_single", 0)
        self.assertEqual((self.cash, self.harita["warehouseAditionalCapacitySingle"]), (96, 2))
        self.komut("buy_pvp_territory", 3)
        self.assertEqual((self.cash, self.harita["universAttackWin"]), (91, [3]))

    def test_birim_deposu(self):
        self.harita["items"].append([512, 3, 3, 0, 0, 0])
        self.komut("add_unit_warehouse", 3, 3, 0, 512)
        self.assertEqual(self.harita["warehousedUnits"], [512])
        self.komut("reset_warehouse", 0)
        self.assertEqual(self.harita["warehousedUnits"], [])
        self.assertEqual(self.ps["gifts"][512], 1)

    def test_uretim_secimi_ve_yardim(self):
        self.komut("activate", 20, 20, 0, 19, 2)
        self.assertEqual(self.harita["items"][1][7]["cp"], 2)
        once = self.harita["items"][1][4]
        self.komut("accept_collect_help", 20, 20, 0, 19, "arkadas")
        self.assertEqual(self.harita["items"][1][4], once - 3600)


class GorevVeBonusKomutlari(KomutTesti):
    def test_gorev_tamamla_ve_odul_bir_kez(self):
        self.komut("complete_mission", 2, 0)
        self.komut("complete_mission", 2, 0)
        self.assertEqual(self.ps["completedMissions"], [2])
        self.komut("reward_mission", 0, 2)
        self.komut("reward_mission", 0, 2)
        self.assertEqual(self.harita["coins"], 50000 + 10)

    def test_odul_1407_hedeflerinden(self):
        # 113: eski görev listesinde "Get Treasure Chest!" (226), 1.4.07 hedeflerinde başka hedef (224)
        from oyun.config import get_game_config
        hedef = next(g for g in get_game_config()["goals"] if g["id"] == 113)
        self.komut("reward_mission", 0, 113)
        self.assertEqual(self.harita["coins"], 50000 + hedef["reward"])
        self.assertEqual(hedef["reward"], 224)

    def test_gorev_atlama_bedeli(self):
        self.komut("complete_mission", 2, 1)
        self.assertEqual(self.cash, 98)

    def test_gunluk_bonus_istemcinin_odulu(self):
        # [altin, kasaba, kahraman, gun, cash]
        self.komut("win_bonus", 250, 0, 0, 1, 3)
        self.assertEqual((self.harita["coins"], self.cash), (50250, 103))
        self.assertEqual(self.ps["bonusNextId"], 2)
        self.komut("win_bonus", 0, 0, 555, 2, 0)
        self.assertEqual(self.ps["gifts"][555], 1)

    def test_pazartesi_ve_geri_donus(self):
        self.komut("weekly_reward", "g", 2500)
        self.assertEqual(self.harita["coins"], 52500)
        # Base/loadPlayerInfoSuccess@1730: istemci alındığını privateState.timeStampMondayBonus'tan okur (KMT-07)
        self.assertAlmostEqual(self.ps["timeStampMondayBonus"], self.komutlar.timestamp_now(), delta=5)
        self.komut("comeback_reward", "u", 512, 3)
        self.assertEqual(self.ps["gifts"][512], 1)
        self.assertEqual(self.ps["comebackBonusCollected"], [3])

    def test_hazine_dogru_kasabaya(self):
        """DNT-50. QuestsInMap$/finalizeQuest @442-465: [altın, xp, sıradaki görev, yiyecek (yerel1), taş (yerel2), townID];
        istemci dördünü de ekler (@356-400) ve timestampLastTreasure = sunucu zamanı (@91-120). Açılışta
        map.idCurrentTreasure ve map.timestampLastTreasure'ı okur (TownManager$/onEndLoadTown @65-105).
        Config.NUM_QUESTS 30: görev 0..29."""
        with mock.patch.object(self.komutlar, "timestamp_now", return_value=2_000_000_000):
            self.komut("collect_treasure", 500, 60, 1, 70, 80, 0)
        h = self.harita
        self.assertEqual((h["coins"], h["xp"], h["food"], h["stone"]), (50500, 60, 1070, 1080))
        self.assertEqual((h["idCurrentTreasure"], h["timestampLastTreasure"]), (1, 2_000_000_000))
        self.komut("collect_treasure", 0, 0, 30, 0, 0, 0)  # NUM_QUESTS dışı: görev değişmez
        self.assertEqual(h["idCurrentTreasure"], 1)
        # MapInitializer$/setCorrectQuest @227-274: ödülsüz [0, 0, görev, 0, 0, townID] yalnızca görevi düzeltir; istemci
        # timestampLastTreasure'a dokunmaz, bekleme süresi sıfırlanmamalı
        with mock.patch.object(self.komutlar, "timestamp_now", return_value=2_000_000_999):
            self.komut("collect_treasure", 0, 0, 5, 0, 0, 0)
        self.assertEqual((h["idCurrentTreasure"], h["timestampLastTreasure"]), (5, 2_000_000_000))

    def test_teklif_paketi(self):
        self.kayit["playerInfo"]["cash"] = 100
        self.komut("buy_offer_pack", 0, 66)  # 40 cash; her kaynaktan 10.000, 500 xp, 9101-9103 birer
        self.assertEqual(self.cash, 60)
        h = self.harita
        self.assertEqual((h["coins"], h["wood"], h["stone"], h["food"], h["xp"]), (60000, 11000, 11000, 11000, 500))
        self.assertEqual(self.ps["gifts"][9101:9104], [1, 1, 1])

    def test_birim_koleksiyonu_bir_kez(self):
        self.komut("unit_collections_completed", 4)
        self.komut("unit_collections_completed", 4)
        self.assertEqual(self.ps["unitCollectionsCompleted"], ["4"])
        self.assertEqual(self.cash, 101)

    def test_yardim_listesi_buyur(self):
        self.komut("set_help_map", "pvp")
        self.komut("set_help_map", "quest")
        self.assertEqual(self.ps["helpMap"], ["pvp", "quest"])

    def test_takimlar_moda_gore(self):
        self.komut("set_attack_team", "tournament", json.dumps([512, 516]))
        self.komut("set_attack_team", "quest", json.dumps([1]))
        self.assertEqual(self.ps["teams"], {"tournament": [512, 516], "quest": [1]})


class SeviyeKomutlari(KomutTesti):
    def test_bozuk_xp_yok_sayilir(self):
        self.komut("rt_publish_score", 10 ** 12)
        self.assertEqual(self.harita["xp"], 0)

    def test_seviye_siniri_asilirsa_son_seviye(self):
        from oyun.config import get_level_from_xp
        self.assertEqual(get_level_from_xp(10 ** 12), 99)  # 1.4.07'de 100 seviye

    def test_seviye_esigi_tam_xp(self):
        from oyun.config import get_level_from_xp
        # eşikler 0, 29, 60, ...: 29 xp ile 2. seviye
        self.assertEqual([get_level_from_xp(x) for x in (0, 28, 29, 59, 60)], [1, 1, 2, 2, 3])


class BuyuVeMezarlik(KomutTesti):
    def test_mana_altin_veya_cash(self):
        self.komut("buy_mana_new", 0, 0)
        self.assertEqual(self.harita["coins"], 50000 - 20000)
        self.komut("buy_mana_new", 0, 1)
        self.assertEqual(self.cash, 99)
        self.assertEqual(self.ps["mana"], 10)

    def test_buyu_al_ve_kullan(self):
        self.komut("buy_magic", 2, 0, 0)  # Fire Havoc: 1000 altın, 5 mana
        self.assertEqual(self.harita["coins"], 49000)
        self.assertIn("2", self.ps["magics"])
        self.ps["mana"] = 7
        self.komut("use_magic", 2)
        self.assertEqual(self.ps["mana"], 2)

    def test_mezarlik_ve_diriltme(self):
        self.komut("put_graveyard", 512)
        self.assertEqual(self.ps["deadHeroes"], {"512": 1})
        self.komut("resurrect_hero", 512, 5, 5, 0, "1")
        self.assertEqual(self.ps["deadHeroes"], {})
        self.assertEqual(self.ps["potion"], 0)
        self.assertEqual(self.harita["items"][-1][:3], [512, 5, 5])


    def test_olen_birlik_mezarlik_listesine(self):
        """Mezarlık penceresi Base.resurrectableUnits'i gösterir (PopupGraveyard/refreshItems); kalıcılığı
        privateState.resurrectableUnits (Base/loadGraveyardState). sell [x, y, id, kasaba, 1, "KILL", mezarliga]
        (IsoFightingElement/kill@799-867). Kahraman (Constants.ID_UNIT_RANGER 535) mezarliga=0 ile gelir ve yalnızca
        deadHeroes'a girer (checkPutToGraveyard@295-390). Anka yumurtası (put_graveyard) listeye girmez."""
        self.harita["items"] += [[668, 3, 3, 0], [535, 4, 4, 0]]
        self.komut("sell", 3, 3, 668, 0, 1, "KILL", 1)
        self.komut("sell", 4, 4, 535, 0, 1, "KILL", 0)
        self.komut("put_graveyard", 777)
        self.assertEqual(self.ps["resurrectableUnits"], [668])
        self.assertEqual(self.ps["deadHeroes"], {"668": 1, "535": 1, "777": 1})

    def test_diriltme_bedeli_istemcininki(self):
        """PopupGraveyard/onBuyItem@149-165: iPotions -= config 'potion' (668: 5); resurrectUnit@123-138 listeden
        çıkarır. PopupResurrectHeroes/onBuyItem@90-176: cost_unit_cash (535: 3) × RESURRECT_MULTIPLIER (500) altın.
        Yetmezse uygulanmaz (KAR-18)."""
        self.ps.update(potion=7, resurrectableUnits=[668, 668], deadHeroes={"668": 2, "535": 1})
        self.komut("resurrect_hero", 668, 5, 5, 0, "1")
        self.assertEqual((self.ps["potion"], self.ps["resurrectableUnits"], self.ps["deadHeroes"]["668"]), (2, [668], 1))
        self.komutlar.command("test", {"commands": [{"cmd": "resurrect_hero", "args": [668, 6, 6, 0, "1"]}]})
        self.assertEqual((self.ps["potion"], self.ps["resurrectableUnits"]), (2, [668]))  # 2 < 5
        self.komut("resurrect_hero", 535, 7, 7, 0)
        self.assertEqual((self.harita["coins"], self.ps["deadHeroes"].get("535")), (50000 - 1500, None))

    def test_kahraman_diriltme_kasabanin_altiniyla(self):
        """#51 incelemesi: altın kasaba başınadır (her haritanın coins'i); bedel komuttaki kasabadan (4. argüman)
        düşer, kahraman da oraya konur. Yetmezse komut uygulanmaz (KAR-18)."""
        import copy
        ikinci = copy.deepcopy(self.harita)
        ikinci.update(coins=2000, items=[])
        self.kayit["maps"].append(ikinci)
        self.ps["deadHeroes"] = {"535": 2}
        self.komut("resurrect_hero", 535, 7, 7, 1)
        self.assertEqual((ikinci["coins"], self.harita["coins"], ikinci["items"][-1][:3]), (500, 50000, [535, 7, 7]))
        self.komutlar.command("test", {"commands": [{"cmd": "resurrect_hero", "args": [535, 8, 8, 1]}]})
        self.assertEqual((ikinci["coins"], len(ikinci["items"]), self.ps["deadHeroes"]["535"]), (500, 1, 1))


class GenelDavranis(KomutTesti):
    def test_bozuk_komut_digerlerini_dusurmez(self):
        veri = {"commands": [
            {"cmd": "name_map", "args": [99, "x"]},  # gerçekten hata verir (IndexError)
            {"cmd": "complete_mission", "args": [2, 0]},
        ]}
        with self.assertRaises(IndexError):
            self.komut("name_map", 99, "x")
        self.komutlar.command("test", veri)
        self.assertEqual(self.ps["completedMissions"], [2])

    def test_bilinmeyen_komut_hata_vermez(self):
        once = json.dumps(self.kayit, sort_keys=True)
        self.komut("boyle_bir_komut_yok", 1, 2)
        self.assertEqual(json.dumps(self.kayit, sort_keys=True), once)


class KomsuKomutlari(KomutTesti):
    def setUp(self):
        super().setUp()
        self.komsu = bos_kayit("komsu")
        self.kayitlar["komsu"] = self.komsu

    def test_komsuya_yardim_en_cok_bes_bina(self):
        binalar = [[i, i, 1] for i in range(7)]
        self.komut("assist_neighbor_new", "komsu", 0, json.dumps(binalar))
        self.assertEqual((self.harita["coins"], self.harita["xp"]), (50000 + 5 * 10, 5 * 3))
        self.assertEqual(self.komsu["maps"][0]["receivedAssists"], {"utest": binalar[:5]})

    def test_komsuya_yardim(self):
        self.komut("assist_neighbor_new", "komsu", 0, json.dumps([[5, 5, 1], [6, 6, 19]]))
        self.assertEqual(self.harita["coins"], 50020)
        self.assertEqual(self.harita["xp"], 6)
        self.assertIn("ukomsu", self.ps["neighborAssists"])
        self.assertEqual(self.komsu["maps"][0]["receivedAssists"], {"utest": [[5, 5, 1], [6, 6, 19]]})

    def test_yardim_arabasi_ve_temizleme(self):
        self.harita["receivedAssists"] = {"ukomsu": [[5, 5, 19]]}
        self.komut("assist_receive", 0, 19)
        self.assertEqual((self.harita["xp"], self.harita["wood"]), (10, 1000 + 20 // 4))
        self.komut("clean_received_assists", "komsu", 0)
        self.assertEqual(self.harita["receivedAssists"], {})

    def test_sosyal_bina_iscisi(self):
        self.harita["items"].append([6, 40, 40, 0, 0, 0])
        self.komut("buy_si_help", 40, 40, 0, 6)
        self.assertEqual(self.cash, 98)
        self.assertEqual(self.harita["items"][-1][7]["si"], [0])
        self.komut("finish_si", 40, 40, 0, 6)
        self.assertNotIn("si", self.harita["items"][-1][7])

    def test_koleksiyon_parcasi(self):
        self.komut("add_collectable", 2, 3)
        self.assertEqual(self.ps["collections"][2], [0, 0, 0, 1, 0, 0])

    def test_koleksiyon_parcasi_birikir(self):
        # CollectableManager$/addCollectible: her çağrıda o parçanın sayısı bir artar (mutasyon ölçümünde kalan:
        # tam uzunluktaki liste her seferinde sıfırlansa da önceki test geçiyordu)
        self.komut("add_collectable", 2, 3)
        self.komut("add_collectable", 2, 3)
        self.komut("add_collectable", 2, 5)
        self.assertEqual(self.ps["collections"][2], [0, 0, 0, 2, 0, 1])

    def test_koleksiyonu_parcalarla_ve_nakitle_bitirme(self):
        # popupCollections/onExchange [c] ve onBuy [c, 1, bedel] (bedel nakit düşer) ikisi de
        # CollectableManager$/getReward'ı çağırır: her parça (1-5) sıfırdan büyükse bir azalır,
        # arCollected[c][0] = true (Base/processAttacks yüklemede bunu collections[c][0] == 1'den kurar);
        # ikisinde de collectionsCompleted'a c eklenir
        # Takas yalnızca beş parçanın her biri varken (checkCollectionComplete); nakitle alım eksik parçayla da olur.
        self.ps["collections"] = [[0] * 6, [0, 2, 1, 1, 1, 1], [0] * 6, [0] * 6, [0, 1, 0, 3, 1, 1]]
        self.komut("finish_collection", 1)
        self.assertEqual(self.ps["collections"][1], [1, 1, 0, 0, 0, 0])
        self.komut("finish_collection", 4, 1, 12)
        self.assertEqual(self.cash, 88)
        self.assertEqual(self.ps["collections"][4], [1, 0, 0, 2, 0, 0])  # nakitle de parçalar düşer
        self.assertEqual(self.ps["collectionsCompleted"], [1, 4])

    # CollectableManager sınıf kurucusu: arCollections[c][0] (c = 1..23) ödülün Constants adı; sayısal değer
    # Constants sınıfının derlenmiş sabiti (1.4.07, araclar/abc_okur.py Abc.sabitler("Constants")).
    KOLEKSIYON_ODULLERI = [
        ("ID_DECO_PYRAMID", 176), ("ID_DECO_TREASURE", 177), ("ID_DECO_GARDEN", 178),
        ("ID_DECO_FOUNTAIN", 179), ("ID_DECO_MAMMOTH", 180), ("ID_UNIT_AXETHROWER_PLAYER", 551),
        ("ID_UNIT_PENGUIN", 546), ("ID_UNIT_YETI", 544), ("ID_UNIT_WARTROLL_PLAYER", 552),
        ("ID_UNIT_MERLIN_CASTLE3", 553), ("ID_DECO_FOSO", 206), ("ID_DECO_ARBOL_AVATAR", 207),
        ("ID_DECO_GUILLOTINA", 208), ("ID_DECO_JAULA", 209), ("ID_DECO_STATUE_SOLDIER", 124),
        ("ID_UNIT_PET_DOG", 561), ("ID_UNIT_PET_CAT", 562), ("ID_UNIT_SKELETON_PLAYER", 563),
        ("ID_UNIT_RAVAGER_PLAYER", 564), ("ID_UNIT_HIGHELF_COLEC", 565), ("ID_UNIT_GOLDEN_BAHAMUT_DRAGON", 875),
        ("ID_UNIT_RED_BAHAMUT_DRAGON", 853), ("ID_BUILDING_BAHAMUT_HEART", 1410),
    ]

    def test_koleksiyon_odulu_depoya(self):
        # KMT-05: getReward ödülü Base.storeItem(ref, false, false) ile depoya koyar; üçüncü argüman false olunca
        # storeItem hiçbir komut göndermez (Base/storeItem@149 iffalse → 308). Sunucu eklemezse yenilemede kaybolur.
        for c, (ad, odul) in enumerate(self.KOLEKSIYON_ODULLERI, 1):
            with self.subTest(koleksiyon=c, odul=ad):
                self.ps["gifts"] = []
                self.ps["collections"] = [[0, 1, 1, 1, 1, 1] for _ in range(24)]  # takas için beş parça
                self.komut("finish_collection", c, *((1, 5) if c % 2 else ()))
                self.assertEqual(self.ps["gifts"][odul], 1)
                self.assertEqual(sum(self.ps["gifts"]), 1)

    def test_koleksiyon_tekrar_bitirilince_odul_yine_verilir(self):
        # arUniqueCollections = [21, 22] dışındakiler yeniden toplanabilir; getReward her seferinde ödül verir
        self.ps["gifts"] = []
        self.ps["collections"] = [[0] * 6, [0] * 6, [0, 2, 2, 2, 2, 2]]  # iki takaslık parça
        self.komut("finish_collection", 2)
        self.komut("finish_collection", 2)
        self.assertEqual(self.ps["gifts"][177], 2)
        self.assertEqual(self.ps["collectionsCompleted"], [2])

    def test_takas_istemcinin_kosulu_yoksa_uygulanmaz(self):
        """1.4.07 bayt kodu. popupCollections/onExchange finish_collection [c]'yi yalnızca iki denetim geçerse yollar:
        CollectableManager$/checkCollectionComplete (p1..p5'in her biri > 0; arUniqueCollections = [21, 22]
        ödülü depodaysa olmaz) ve checkCanComplete (ödül süs, SUBCATFUNC_BUILDING_DECO 411, ise olur; birim ya da
        binaysa depoda, birimse kasabada ya da bir binanın içinde (IsoEngine/countPlayerElementsById, vUnitsContained) bir
        tanesi bile varsa olmaz, AVISO_UNIDAD_UNICA; tekil koleksiyonda yalnızca depoya bakılır, @59-106). onBuy (nakit) yalnızca
        canAfford'a bakar. Önce sunucu bunları denetlemiyordu: eksik parçayla ikinci takas ödülü yeniden veriyordu."""
        def dene(c, parcalar=(0, 1, 1, 1, 1, 1), gifts=(), harita=(), nakit=False):
            self.ps["gifts"] = []
            for i in gifts:
                komutlar_mod.depo_ekle(self.kayit, i)
            self.ps["collections"] = [list(parcalar) for _ in range(24)]
            self.harita["items"] = [[1, 10, 10, 0, 0, 0]] + [[i, 30, 30, 0, 0, 0] for i in harita]
            self.komut("finish_collection", c, *((1, 5) if nakit else ()))
            return self.ps["gifts"][KOLEKSIYON[c]] if len(self.ps["gifts"]) > KOLEKSIYON[c] else 0
        KOLEKSIYON = {1: 176, 8: 544, 21: 875, 23: 1410}
        komutlar_mod = self.komutlar
        self.assertEqual(dene(1, parcalar=(0, 1, 1, 0, 1, 1)), 0)        # 3. parça yok
        self.assertEqual(self.ps["collections"][1], [0, 1, 1, 0, 1, 1])  # parçalar da düşmez
        self.assertEqual(dene(1, parcalar=(0, 1, 1, 0, 1, 1), nakit=True), 1)  # nakitle olur
        self.assertEqual(dene(1, gifts=(176,)), 2)                        # süs: depoda olsa da olur
        self.assertEqual(dene(8, gifts=(544,)), 1)                        # birim depoda: olmaz (zaten 1)
        self.assertEqual(dene(8, harita=(544,)), 0)                       # birim kasabada: olmaz
        self.assertEqual(dene(8), 1)                                      # birim yok: olur
        self.assertEqual(dene(23, gifts=(1410,)), 1)                     # süs olmayan bina depoda: olmaz (zaten 1)
        # Kasabadaki bina: istemcinin sayıp saymadığı doğrulanmadı (arPlayerIsoFightingElements); sunucu katı olmaz,
        # yoksa ekranda verilen ödül kayda yazılmazdı.
        self.assertEqual(dene(23, harita=(1410,)), 1)
        self.harita["items"] = [[1, 10, 10, 0, 0, 0]]
        self.ps["collections"] = [[0, 1, 1, 1, 1, 1] for _ in range(24)]
        self.ps["gifts"] = []
        self.harita["items"].append([7, 20, 20, 0, 0, 0, [544], {}])  # Yeti bir binanın içinde (vUnitsContained)
        self.komut("finish_collection", 8)
        self.assertEqual(len(self.ps["gifts"]) > 544 and self.ps["gifts"][544], 0)
        self.assertEqual(dene(21, gifts=(875,)), 1)                       # tekil koleksiyon, ödül depoda: olmaz
        self.assertEqual(dene(21, harita=(875,)), 1)                      # tekil: kasabadaki ejderha engel değil

    def test_koleksiyon_disi_numara_odul_vermez(self):
        # arCollections[0] adlar listesidir, NUM_COLLECTIONS = 23: 0 ve 24 koleksiyon değildir
        self.ps["gifts"] = []
        self.komut("finish_collection", 0)
        self.komut("finish_collection", 24)
        self.assertEqual(self.ps["gifts"], [])


class PvpKomutlari(KomutTesti):
    """end_attack: istemcinin Assault.sendAssaultResults biçimi."""

    def setUp(self):
        super().setUp()
        self.kurban = bos_kayit("rakip")
        self.kurban["playerInfo"]["name"] = "Rakip"
        self.kurban["maps"][0]["level"] = 5
        self.kayitlar["rakip"] = self.kurban

    def saldir(self, *ek_arg, **ek):
        veri = {"attacker": {"user_id": "test", "map": 0}, "victim": {"user_id": "rakip", "level": 5},
                "resources": {"g": 500, "x": 30}, "resources_victim": {"g": 0},
                "attacker_units": [[512, 4, 2, 1]], "victim_units": [[512, 3, 2, 0]],
                "win": 1, "duration": 30, "voluntary_end": 0, "townhall_gold": 500, "honor": 4}
        veri.update(ek)
        self.komut("end_attack", json.dumps(veri), *ek_arg)

    def yeni(self, g=600, f=100, w=400, s=50, kazanan="test", xp=40, hedef="rakip"):
        """end_attack_new, PVPManager/sendEnd@328-458: [g, f, w, s, attacked_id, ad, seviye, zaman, winnerId
        (bPlayerWinner ? sessionID : attacked_id), gönüllü, intikam, kalkan, yüzde*100, iXPGained]."""
        self.komut("end_attack_new", g, f, w, s, hedef, "Test", 10, 2_000_000_000, kazanan, 0, 0, 0, 30, xp)

    def test_yeni_sonuc_ganimeti_verir(self):
        """1.4.07'de end_attack'ın resources ve honor'u literal 0'dır (Assault$/sendAssaultResults @137-164,
        @284-287); ganimet ve XP end_attack_new ile gelir. Hedefin elindekinden fazlası verilmez. Onur: config
        globals HONOR_POINT_PVP_WIN_ATTACK 15 / HONOR_POINT_PVP_LOSE_ATTACK 5."""
        self.kurban["maps"][0].update(coins=1000, food=500, wood=300, stone=0)
        self.saldir(resources={"g": 0, "x": 0, "w": 0, "s": 0, "f": 0}, honor=0)
        once = {k: self.harita[k] for k in ("coins", "food", "wood", "stone", "xp")}
        kaydedilen = []
        self.pvp.save_session = kaydedilen.append
        self.yeni()
        self.assertEqual({k: self.harita[k] - once[k] for k in once},
                         {"coins": 600, "food": 100, "wood": 300, "stone": 0, "xp": 40})
        self.assertEqual((self.ps["attacksWon"], self.ps.get("attacksLost", 0), self.ps["honor"]), (1, 0, 15))
        self.assertEqual(self.ps["attacksSent"][-1]["description"]["resources"],
                         {"g": 600, "f": 100, "w": 300, "s": 0, "x": 40})
        # KAR-20 (sahibinin kararı, 11.11.2026): ganimet kurbandan düşülür; 300 isteyen odunun hepsi gider
        self.assertEqual({k: self.kurban["maps"][0][k] for k in ("coins", "food", "wood", "stone")},
                         {"coins": 400, "food": 400, "wood": 0, "stone": 0})
        self.assertEqual(kaydedilen, ["rakip"])
        self.yeni()  # aynı savaşın ikinci sonucu: verilmez
        self.assertEqual(self.harita["coins"] - once["coins"], 600)

    def test_yeni_sonuc_kayitsiz_hedefte_sinirli(self):
        """#50 incelemesi: statik komşu (kayıtlı değil) değişmez ama ganimet yine onun kaynağıyla ve eski
        end_attack'ın altın tavanıyla (200 × 2 yıkılan + 5 × 100 + 25 = 925) sınırlı; XP de o altından
        (ceil(925 × 0,05) + 2 + 150). Okunamayan hedeften hiçbir şey alınmaz."""
        self.kurban["maps"][0].update(coins=50000, food=500, wood=0, stone=0)
        self.pvp.all_saves_userid = lambda: ["test"]
        kaydedilen = []
        self.pvp.save_session = kaydedilen.append
        self.saldir(resources={"g": 0, "x": 0}, honor=0)
        once = {k: self.harita[k] for k in ("coins", "food", "wood", "stone", "xp")}
        self.yeni(g=999999, f=999999, w=999999, s=999999, xp=999999)
        self.assertEqual({k: self.harita[k] - once[k] for k in once},
                         {"coins": 925, "food": 500, "wood": 0, "stone": 0, "xp": 47 + 2 + 150})
        self.assertEqual((self.kurban["maps"][0]["coins"], self.kurban["maps"][0]["food"], kaydedilen),
                         (50000, 500, []))
        del self.kayitlar["rakip"]
        self.ps["attacksSent"] = []
        self.saldir(resources={"g": 0, "x": 0}, honor=0)
        once = {k: self.harita[k] for k in ("coins", "food", "wood", "stone")}
        self.yeni(g=999999, f=999999, w=999999, s=999999)
        self.assertEqual({k: self.harita[k] - once[k] for k in once}, {"coins": 0, "food": 0, "wood": 0, "stone": 0})

    def test_yeni_sonuc_bozuk_sayi_kurbani_bozmaz(self):
        """#50 incelemesi: "inf" (float'a çevrilir, int'e çevrilemez: OverflowError) gelince kurbandan düşülüp komutun
        çökmesi olmamalı; bozuk değer 0 sayılır, geçerli olanlar uygulanır."""
        self.kurban["maps"][0].update(coins=1000, food=500, wood=0, stone=0)
        self.saldir(resources={"g": 0, "x": 0}, honor=0)
        once = self.harita["coins"]
        self.yeni(g=100, f="inf", w=0, s=0, xp="inf")
        self.assertEqual((self.kurban["maps"][0]["coins"], self.kurban["maps"][0]["food"], self.harita["coins"] - once),
                         (900, 500, 100))

    def test_yeni_sonuc_eski_ganimetin_ustune_vermez(self):
        """#50 incelemesi: end_attack resources.g > 0 ile (eski istemci biçimi) ganimet verdiyse aynı savaşın
        end_attack_new'i ikinci kez altın, XP ya da kaynak vermez; kurbandan da ikinci kez düşülmez."""
        self.kurban["maps"][0].update(coins=50000, food=500)
        self.saldir()  # resources g 500, x 30
        once = {k: self.harita[k] for k in ("coins", "food", "xp")}
        self.yeni(g=999999, f=500, w=0, s=0, xp=999999)
        self.assertEqual({k: self.harita[k] for k in once}, once)
        self.assertEqual((self.kurban["maps"][0]["coins"], self.kurban["maps"][0]["food"], self.ps["attacksWon"]),
                         (49500, 500, 1))

    def test_yeni_sonuc_eski_onurun_ustune_vermez(self):
        """#50 incelemesinin notu (OYN-24): end_attack ganimetsiz ama honor > 0 ile geldiyse (eski biçim) aynı savaşın
        end_attack_new'i onuru ikinci kez vermez. Onur tavanı eski yolda 10 (saldiri_bitir)."""
        self.saldir(resources={"g": 0, "x": 0}, honor=4)
        self.yeni()
        self.assertEqual((self.ps["honor"], self.saldiran_onur()), (4, 4))

    def saldiran_onur(self):
        return self.kayit["playerInfo"].get("honor_points", 0)

    def test_saldirida_olen_birlik_mezarliga(self):
        """1.4.07: ASSAULT'ta ölen kendi birliği istemcide yalnızca yerelde mezarlığa girer, komut gitmez
        (IsoFightingElement/kill@714-894, CommandManager/addCommand@16-99). Sunucu attacker_units'ten net kaybı
        (ölen − kurtarılan) ve yalnızca haritadan gerçekten silineni ekler; köylü (500) girmez; kahraman (535)
        yalnızca deadHeroes'a (checkPutToGraveyard@295-390)."""
        self.harita["items"] += [[668, 1, 1, 0], [668, 2, 2, 0], [500, 3, 3, 0], [535, 4, 4, 0]]
        self.saldir(attacker_units=[[668, 5, 4, 1], [500, 1, 1, 0], [535, 1, 1, 0]])  # 668: net 3, haritada 2
        self.assertEqual(self.ps["resurrectableUnits"], [668, 668])
        self.assertEqual(self.ps["deadHeroes"], {"668": 2, "535": 1})

    def test_saldiridan_sonra_sag_kalanlar_yerinde(self):
        """Sahibinin F5 sorusu (savaştan sonra askerler eski yere dönüyor mu): kendi adasına dönüş bir harita
        yüklemesidir (Base/realLoadMap → get_player_info); istemci sağ kalanları kayıttaki yerleriyle kurar. Sunucu
        yalnızca net kaybı siler; sağ kalanın koordinatı, başka türden birlik ve bina değişmez."""
        self.harita["items"] += [[668, 10, 11, 0], [668, 12, 13, 0], [668, 14, 15, 0], [512, 20, 21, 0]]
        once = [list(e) for e in self.harita["items"]]
        self.saldir(attacker_units=[[668, 3, 1, 0], [512, 1, 0, 0]])
        sonra = self.harita["items"]
        self.assertEqual(len(sonra), len(once) - 1)
        self.assertTrue(all(e in once for e in sonra))  # hiçbir öğenin yeri ya da yönü değişmedi
        self.assertEqual(sum(e[0] == 668 for e in sonra), 2)
        self.assertIn([512, 20, 21, 0], sonra)

    def test_yeni_sonuc_saldirinin_kasabasina(self):
        """#50 incelemesi: end_attack attacker.map'in kasabasına yazar; end_attack_new'in ganimeti de oraya."""
        import copy
        ikinci = copy.deepcopy(self.harita)
        ikinci.update(coins=0, xp=0)
        self.kayit["maps"].append(ikinci)
        self.kurban["maps"][0].update(coins=1000)
        self.saldir(resources={"g": 0, "x": 0}, honor=0, attacker={"user_id": "test", "map": 1})
        ana = self.harita["coins"]
        self.yeni(g=300, f=0, w=0, s=0, xp=10)
        self.assertEqual((ikinci["coins"], ikinci["xp"], self.harita["coins"]), (300, 10, ana))

    def test_yeni_sonuc_yenilgi_ve_eslesmeyen(self):
        self.yeni()  # önce end_attack gelmedi: hiçbir şey verilmez
        self.assertEqual((self.harita["coins"], self.ps.get("attacksWon", 0)), (50000, 0))
        self.saldir(resources={"g": 0, "x": 0}, honor=0, win=0)
        self.yeni(kazanan="rakip", g=0, f=0, w=0, s=0, xp=0)
        self.assertEqual((self.ps.get("attacksWon", 0), self.ps["attacksLost"], self.ps["honor"]), (0, 1, 5))

    def test_kural_disi_saldiri_ganimetsiz_ama_sayilir(self):
        self.kurban["privateState"]["shieldEndTime"] = 4_000_000_000  # kalkanlı hedef (KYT-03)
        self.saldir(resources={"g": 0, "x": 0}, honor=0)
        self.yeni()
        self.assertEqual((self.harita["coins"], self.ps["attacksWon"], self.ps.get("honor", 0)), (50000, 1, 0))

    def test_ganimet_kurbandan_saldirana_gecer(self):
        """KAR-20 (sahibinin kararı, 11.11.2026): PvP ganimeti kurbandan düşülür; elinde olmayan verilmez."""
        self.saldir()
        self.assertEqual(self.harita["coins"], 50500)
        self.assertEqual(self.harita["xp"], 30)
        self.assertEqual(self.kurban["maps"][0]["coins"], 49500)
        self.assertEqual(self.ps["honor"], 4)
        rapor = self.kurban["privateState"]["attacksReceived"][0]
        self.assertEqual(rapor["attacker_id"], "test")
        self.assertEqual(rapor["viewPending"], 1)
        self.assertEqual(rapor["description"]["oponent"]["name"], "Test")
        self.assertEqual(self.ps["attacksSent"][0]["description"]["oponent"]["name"], "Rakip")
        self.kurban["maps"][0]["coins"] = 120
        self.ps["attacksSent"] = []
        self.saldir()  # kurbanda 120 altın var: 500 değil 120 alınır
        self.assertEqual((self.harita["coins"], self.kurban["maps"][0]["coins"]), (50620, 0))

    def test_ganimet_istemci_formuluyle_sinirli(self):
        # 2 birim yıkıldı, kurban seviye 5: en çok 200*2 + 500 + 25 = 925
        self.saldir(resources={"g": 999999, "x": 999999})
        self.assertEqual(self.harita["coins"], 50000 + 925)
        self.assertEqual(self.harita["xp"], 47 + 2 + 150)  # ganimetin %5'i yukarı yuvarlanır: 46,25 → 47

    def test_belediye_binasi_yoksa_ganimet_yok(self):
        self.saldir(True)
        self.assertEqual(self.harita["coins"], 50000)

    def test_ayni_hedefe_dort_saatte_ikinci_saldiri_ganimetsiz(self):
        self.saldir()
        self.saldir()
        self.assertEqual(self.harita["coins"], 50500)
        self.assertEqual(len(self.ps["attacksSent"]), 2)

    def test_dorduncu_saldiri_ganimetsiz_paket_varsa_serbest(self):
        from oyun.ekonomi import timestamp_now
        simdi = timestamp_now()
        self.ps["attacksSent"] = [{"time": simdi - 60, "victim_id": f"x{i}"} for i in range(3)]
        self.saldir()
        self.assertEqual(self.harita["coins"], 50000)
        self.ps["attacksPack"] = 5
        self.kurban["privateState"]["attacksReceived"] = []
        self.ps["attacksSent"] = [{"time": simdi - 60, "victim_id": f"x{i}"} for i in range(3)]
        self.saldir()
        self.assertEqual(self.harita["coins"], 50500)
        self.assertEqual(self.ps["attacksPack"], 4)

    def test_kaybedince_savunan_odullenir(self):
        self.saldir(win=0, resources={"g": 0, "x": 0}, resources_victim={"g": 9999})
        # saldıranın satırı [512, 4, 2, 1]: 2 birim öldü (1'i sonra kurtarıldı). İstemci ödülü her ölen için ekler
        # (Assault$/killed@393-435; recoverPlayerUnits yalnızca FIELD_RECOVERED'ı ayarlar, OYN-17): en çok 2 × 20
        self.assertEqual(self.kurban["maps"][0]["coins"], 50040)

    def test_kalici_kayiplar_haritadan_silinir(self):
        self.harita["items"] += [[512, 1, 1, 0, 0, 0], [512, 2, 2, 0, 0, 0]]
        self.saldir()
        self.assertEqual(sum(1 for e in self.harita["items"] if e[0] == 512), 1)

    def test_kalkanli_hedef_ganimetsiz_ve_dokunulmaz(self):
        self.kurban["privateState"]["shield_until"] = 2 ** 40
        self.kurban["maps"][0]["items"].append([512, 1, 1, 0, 0, 0])
        self.saldir()
        self.assertEqual(self.harita["coins"], 50000)
        self.assertNotIn("attacksReceived", self.kurban["privateState"])
        self.assertIn([512, 1, 1, 0, 0, 0], self.kurban["maps"][0]["items"])

    def test_statik_komsu_degismez(self):
        # villages/ köyleri kayıtlı oyuncu değildir (all_saves_userid'de yok)
        self.komutlar.all_saves_userid = lambda: ["test"]
        self.pvp.all_saves_userid, eski = (lambda: ["test"]), self.pvp.all_saves_userid
        try:
            self.saldir()
        finally:
            self.pvp.all_saves_userid = eski
        self.assertNotIn("attacksReceived", self.kurban["privateState"])
        self.assertEqual(self.harita["coins"], 50500)

    def test_kendine_saldiri_yok(self):
        self.saldir(victim={"user_id": "test"})
        self.assertNotIn("attacksSent", self.ps)

    def test_raporlar_gorulunce_gecmis_kalir(self):
        self.ps["attacksReceived"] = [{"time": 1, "viewPending": 1}, {"time": 2}]
        self.komut("clean_attacks")
        self.assertEqual(self.ps["attacksReceived"], [{"time": 1}, {"time": 2}])


class IlkAlimTeklifi(KomutTesti):
    """KAR-10: ilk alım teklifi 1.4.07'nin kendi bedeli ve ödülüyle, bir kez (PopupFirstBuy/onBuy)."""

    def setUp(self):
        super().setUp()
        from oyun.config import get_game_config
        self.g = get_game_config()["globals"]
        self.kayit["playerInfo"]["cash"] = 100
        self.ps.update(firstPurchaseTimestamp=0, numDayLogged=1)

    def test_pencere_acilinca_damga_konur_bir_kez(self):
        self.komut("set_first_purchase_timestamp")
        damga = self.ps["firstPurchaseTimestamp"]
        self.assertGreater(damga, 1)
        self.komut("set_first_purchase_timestamp")  # yeniden açmak süreyi uzatmaz
        self.assertEqual(self.ps["firstPurchaseTimestamp"], damga)
        self.komut("set_first_purchase_timestamp", 0)  # geliştirici paneli sıfırlar
        self.assertEqual(self.ps["firstPurchaseTimestamp"], 0)

    def test_alim_bedel_ve_odul_bir_kez(self):
        odul = self.g["POPUP_FIRST_PURCHASE_OFFER_REWARD"]
        bedel = self.g["POPUP_FIRST_PURCHASE_OFFER_COST"]
        # beklenen değerler config'ten okunuyor; config'in 1.4.07 değerleri de sabitlenir
        self.assertEqual((bedel, odul), (28, {"units": [2245, 2248, 2242], "g": 20000, "f": 40000}))
        self.komut("set_first_purchase_timestamp")
        altin, yemek = self.harita["coins"], self.harita["food"]
        self.komut("buy_first_purchase")
        self.assertEqual(self.kayit["playerInfo"]["cash"], 100 - bedel)
        self.assertEqual(self.harita["coins"], altin + odul["g"])
        self.assertEqual(self.harita["food"], yemek + odul["f"])
        for birim in odul["units"]:
            self.assertEqual(self.ps["gifts"][birim], 1)
        self.assertEqual(self.ps["firstPurchaseTimestamp"], self.komutlar.ILK_ALIM_ALINDI)
        self.komut("buy_first_purchase")  # ikinci kez alınmaz
        self.assertEqual(self.kayit["playerInfo"]["cash"], 100 - bedel)

    def test_pencere_acilmadan_sure_gecince_nakit_yetmezse_alinmaz(self):
        self.komut("buy_first_purchase")  # damga 0: pencere açılmadı
        self.ps["firstPurchaseTimestamp"] = self.komutlar.timestamp_now() - self.g["POPUP_FIRST_PURCHASE_OFFER_TIME"] - 3600
        self.komut("buy_first_purchase")  # süre geçti
        self.komut("set_first_purchase_timestamp", self.komutlar.timestamp_now())
        self.kayit["playerInfo"]["cash"] = self.g["POPUP_FIRST_PURCHASE_OFFER_COST"] - 1
        self.komut("buy_first_purchase")  # nakit yetmiyor
        self.assertEqual(self.ps["gifts"], [])
        self.assertEqual(self.kayit["playerInfo"]["cash"], self.g["POPUP_FIRST_PURCHASE_OFFER_COST"] - 1)

    def test_odul_acik_kasabaya_gider(self):
        from oyun import oyuncu
        ikinci = dict(self.harita, id=1, coins=0, food=0)
        self.kayit["maps"].append(ikinci)
        oyuncu._acik_kasabalar["test"] = 1
        self.addCleanup(oyuncu._acik_kasabalar.pop, "test", None)
        self.komut("set_first_purchase_timestamp")
        self.komut("buy_first_purchase")
        self.assertEqual(ikinci["coins"], self.g["POPUP_FIRST_PURCHASE_OFFER_REWARD"]["g"])

    def test_acik_kasaba_sunucu_yeniden_baslayinca_kayittan(self):
        """DNT-30 (SNK-07): istemci açık kasabayı yalnızca açılışta ve kasaba değişiminde bildirir (get_player_info
        map); sunucu oyun sürerken yeniden başlarsa bellek boşalır. Kasaba kayıtta da durur, ödül yine o kasabaya."""
        from oyun import oyuncu
        ikinci = dict(self.harita, id=1, coins=0, food=0)
        self.kayit["maps"].append(ikinci)
        yazilan = []
        self.ps.update(numDayLogged=9, lastDayRewarded=9)  # günlük ödül yok: kayıt yalnızca kasaba için yazılmalı
        self.kayit["playerInfo"]["last_logged_in"] = self.komutlar.timestamp_now()  # aynı gün
        with mock.patch.object(oyuncu, "session", lambda u: self.kayit), \
                mock.patch.object(oyuncu, "neighbors", lambda u: []), \
                mock.patch.object(oyuncu, "save_session", yazilan.append):
            oyuncu.get_player_info("test", 1)
            self.assertEqual(yazilan, ["test"])  # #66 incelemesi: hemen diske (komuttan önce yeniden başlayabilir)
            oyuncu.get_player_info("test", 1)
            self.assertEqual(yazilan, ["test"])  # değişmediyse yeniden yazılmaz
        self.assertEqual(self.kayit["playerInfo"]["acik_kasaba"], 1)
        oyuncu._acik_kasabalar.pop("test", None)  # sunucu yeniden başladı
        self.komut("set_first_purchase_timestamp")
        self.komut("buy_first_purchase")
        self.assertEqual(ikinci["coins"], self.g["POPUP_FIRST_PURCHASE_OFFER_REWARD"]["g"])
        self.kayit["playerInfo"]["acik_kasaba"] = "bozuk"
        self.assertEqual(oyuncu.acik_kasaba("test", self.kayit), 0)

    def test_giris_gunu_yeni_gunde_artar(self):
        from oyun.oyuncu import giris_gunu_say
        pi = self.kayit["playerInfo"]
        bugun = 1_760_000_000
        pi["last_logged_in"] = bugun - 60
        giris_gunu_say(self.kayit, bugun)
        self.assertEqual(self.ps["numDayLogged"], 1)  # aynı gün
        pi["last_logged_in"] = bugun - 2 * 86400
        giris_gunu_say(self.kayit, bugun)
        self.assertEqual(self.ps["numDayLogged"], 2)
        pi["last_logged_in"] = -1  # yeni köy şablonu
        giris_gunu_say(self.kayit, bugun)
        self.assertEqual(self.ps["numDayLogged"], 2)


class EgitimKuyrugu(KomutTesti):
    """GEC-03: 1.4.07'nin eğitim kuyruğu (BuildingQueueManager); formüller docs/inceleme/1407-formuller.md."""

    KISLA, MIZRAKCI, OKCU, KOC, KOYLU = 38, 509, 515, 519, 500

    def setUp(self):
        super().setUp()
        self.harita["items"].append([self.KISLA, 30, 30, 0, 0, 0])
        yama = mock.patch.object(self.komutlar, "zaman_olcegi", return_value=1.0)
        yama.start()
        self.addCleanup(yama.stop)

    def it(self, *args):
        self.komut("push_queue_unit", 30, 30, self.KISLA, *args)

    def test_kuyruga_ekleme_bedel_yemek_ve_bq(self):
        self.it(self.MIZRAKCI, 7, 1)
        self.it(self.MIZRAKCI, 7, 1)
        q = self.ps["barracksQueues"]["7"]
        self.assertEqual((q["amount"], q["unit"]), (2, self.MIZRAKCI))
        self.assertEqual(self.harita["items"][-1][7], {"bq": "7"})
        self.assertEqual(self.harita["coins"], 50000 - 2 * 30)
        self.assertEqual(self.harita["food"], 1000 - 2 * 60)  # bedelin iki katı yemek

    def test_koylunun_yemegi_yok_kuyruk_besle_sinirli(self):
        for _ in range(6):
            self.it(self.KOYLU, 3, 1)
        self.assertEqual(self.ps["barracksQueues"]["3"]["amount"], 5)
        self.assertEqual(self.harita["food"], 1000 - 5 * 50)  # yalnızca kendi bedeli (yemek)

    def test_demirci_ve_universite_indirimi(self):
        self.harita["items"] += [[22, 50, 50, 0, 0, 0], [25, 60, 60, 0, 0, 0]]
        self.it(self.OKCU, 1, 1)
        self.assertEqual(self.harita["coins"], 50000 - 270)
        self.assertEqual(self.harita["food"], 1000 - 540)
        self.it(self.KOC, 2, 1)
        self.assertEqual(self.harita["coins"], 50000 - 270 - 90)
        # Hafif Şövalye (512) 75 altın: 75 × 0,9 = 67,5 yukarı yuvarlanır → 68; yemek 136
        self.it(512, 3, 1)
        self.assertEqual((self.harita["coins"], self.harita["food"]), (50000 - 270 - 90 - 68, 1000 - 540 - 180 - 136))

    def test_ruh_karistiricida_bedel_yok(self):
        self.harita["items"].append([1529, 40, 40, 0, 0, 0])
        self.komut("push_queue_unit", 40, 40, 1529, self.MIZRAKCI, 4, 0)
        self.assertEqual((self.harita["coins"], self.harita["food"]), (50000, 1000))
        self.assertEqual(self.ps["barracksQueues"]["4"]["amount"], 1)

    def test_cikan_birim_haritaya_xp_ve_zincir(self):
        self.it(self.MIZRAKCI, 7, 1)
        self.it(self.MIZRAKCI, 7, 1)
        q = self.ps["barracksQueues"]["7"]
        q["ts"] = baslangic = q["ts"] - 100
        self.komut("pop_queue_unit", 7, 33, 34, self.KISLA)
        self.assertEqual(self.harita["items"][-1][:3], [self.MIZRAKCI, 33, 34])
        self.assertEqual(self.harita["xp"], 3)
        self.assertEqual((q["amount"], q["ts"]), (1, baslangic + 5))  # sıradaki, öncekinin bitişinde başlar
        self.komut("pop_queue_unit", 7, 35, 34, self.KISLA)
        self.assertNotIn("7", self.ps["barracksQueues"])
        self.assertNotIn("bq", self.harita["items"][2][7])
        self.komut("pop_queue_unit", 7, 36, 34, self.KISLA)  # tekrarlanan komut: birim çıkmaz
        self.assertEqual(sum(1 for e in self.harita["items"] if e[0] == self.MIZRAKCI), 2)

    def test_kuyruktan_cikarma_iade(self):
        self.it(self.MIZRAKCI, 7, 1)
        self.it(self.MIZRAKCI, 7, 1)
        self.komut("unqueue_unit", 7, self.KISLA)
        self.assertEqual(self.ps["barracksQueues"]["7"]["amount"], 1)
        self.assertEqual((self.harita["coins"], self.harita["food"]), (50000 - 30, 1000 - 60))
        self.komut("unqueue_unit", 7, self.KISLA)
        self.assertNotIn("7", self.ps["barracksQueues"])
        self.assertEqual((self.harita["coins"], self.harita["food"]), (50000, 1000))

    def test_iade_yalnizca_alinan_kadar(self):
        # KAR-11: istemcinin returnCost'u köylüde yemek, Ruh Karıştırıcı'da bedel de verir; sunucu vermez
        self.it(self.KOYLU, 3, 1)
        self.komut("unqueue_unit", 3, self.KISLA)
        self.assertEqual(self.harita["food"], 1000)
        self.harita["items"].append([1529, 40, 40, 0, 0, 0])
        self.komut("push_queue_unit", 40, 40, 1529, self.MIZRAKCI, 4, 0)
        self.komut("unqueue_unit", 4, 1529)
        self.assertEqual((self.harita["coins"], self.harita["food"]), (50000, 1000))
        self.assertNotIn("4", self.ps["barracksQueues"])

    def test_hizlandirma_kalan_her_saat_bir_nakit(self):
        self.kayit["playerInfo"]["cash"] = 2  # tam yetiyor
        self.it(self.MIZRAKCI, 7, 1)
        self.it(self.MIZRAKCI, 7, 1)
        q = self.ps["barracksQueues"]["7"]
        with mock.patch.object(self.komutlar, "egitim_suresi", return_value=3000):
            self.komut("speed_up_queue", 7)  # kalan 3000 + 3000 sn: 2 saat
        self.assertEqual(self.cash, 0)
        self.assertLessEqual(q["ts"] + 2 * 3000, self.komutlar.timestamp_now())  # ikisi de bitmiş görünür
        self.kayit["playerInfo"]["cash"] = 0
        self.it(self.MIZRAKCI, 8, 1)
        with mock.patch.object(self.komutlar, "egitim_suresi", return_value=3000):
            self.komut("speed_up_queue", 8)  # nakit yetmez
        self.assertGreater(self.ps["barracksQueues"]["8"]["ts"] + 3000, self.komutlar.timestamp_now())

    def test_sure_istemcinin_gordugu_gibi_olceklenir(self):
        with mock.patch.object(self.komutlar, "zaman_olcegi", return_value=3.0):
            self.assertEqual(self.komutlar.egitim_suresi({"training_time": "10"}), 3)
            self.assertEqual(self.komutlar.egitim_suresi({"sm_training_time": "10000"}, True), 3333)
        self.assertEqual(self.komutlar.egitim_suresi({}), 0)


class BirlikPaketleri(KomutTesti):
    """GEC-03, KAR-12: oyunun kendi birlik paketleri (UnitPacksManager/buyPack)."""

    def test_altinla_ilk_paket_bir_kez(self):
        self.komut("buy_unit_pack", 1, 1)  # The Guardian: 50 altın, en çok 1
        self.assertEqual(self.harita["coins"], 50000 - 50)
        self.assertEqual(self.ps["unitPacks"], {"1": 1})
        self.komut("buy_unit_pack", 1, 1)
        self.assertEqual(self.harita["coins"], 50000 - 50)

    def test_nakit_tam_yetince_alinir(self):
        self.kayit["playerInfo"]["cash"] = 14
        self.komut("buy_unit_pack", 3, 2)  # 14 nakit (Gladyatör Paketi 8 nakit, KAR-36)
        self.assertEqual((self.cash, self.ps["unitPacks"]), (0, {"3": 2}))

    def test_nakitle_toplu_alim_indirimi(self):
        self.kayit["playerInfo"]["cash"] = 1000
        self.komut("buy_unit_pack", 3, 2)  # 8 nakit × 2 = 16, %10 indirim: int(14,4 + 0,5) = 14
        self.assertEqual(self.cash, 1000 - 14)
        self.komut("buy_unit_pack", 3, 8)  # 64, %15 indirim: int(54,4 + 0,5) = 54
        self.assertEqual(self.cash, 1000 - 14 - 54)
        self.assertEqual(self.ps["unitPacks"], {"3": 10})

    def test_kaynak_yetmezse_ve_bilinmeyen_paket_alinmaz(self):
        self.kayit["playerInfo"]["cash"] = 7
        self.harita["coins"] = 28799
        self.komut("buy_unit_pack", 3, 1)  # 8 nakit > 7
        self.komut("buy_unit_pack", 99, 1)
        self.komut("buy_unit_pack", 2, 4)  # 4 × 8.000 altın, %10 indirim: 28.800 > 28.799
        self.assertEqual((self.cash, self.harita["coins"]), (7, 28799))
        self.assertNotIn("unitPacks", self.ps)

    def test_paket_dengesi_sahibinin_karari(self):
        """KAR-36 (sahibi, 12.11.2026, 'Önerimi uygula'): kopya Öfkeli Ejderha paketi (id 5) altınla alınan Kraliyet
        Paketi olur (silinince mağaza ızgarasında boş yuva kalıyordu); ayarsız paketler adlarına uygun birlik verir;
        fiyat güce göre artar (nakit: Gladyatör 8 < Öfkeli 20 < Destansı 38 < Vahşi ve Kadim 45 < Kadim 60; altın:
        Kraliyet 5.000, Zorlu 8.000); oyuncuya 'DO NOT BUY' gibi yarım kalmış İngilizce metin gitmez."""
        from oyun.config import get_game_config, get_item_from_id
        paketler = {int(p["id"]): p for p in get_game_config()["unit_packs"]}
        self.assertEqual(sorted(paketler), list(range(1, 9)))
        self.assertEqual({no: p["price"] for no, p in paketler.items()},
                         {1: {"g": 50}, 2: {"g": 8000}, 3: {"c": 8}, 4: {"c": 20}, 5: {"g": 5000}, 6: {"c": 38},
                          7: {"c": 45}, 8: {"c": 60}})
        # Mağaza yuvaları store_order'a göre dizilir: 1..8 boşluksuz
        self.assertEqual(sorted(int(p["store_order"]) for p in paketler.values()), list(range(1, 9)))
        adlar = [p["name"] for p in paketler.values()]
        self.assertEqual(len(adlar), len(set(adlar)))
        for p in paketler.values():
            metin = " ".join(str(p.get(k, "")) for k in ("name", "banner", "tooltip", "description", "data"))
            for kotu in ("NOT SET UP", "DO NOT BUY", "Do not buy", "ripped off", "Overpowered", "refund"):
                self.assertNotIn(kotu, metin, p["id"])
        for no, kelime in ((3, "Gladiator"), (4, "Dragon"), (5, "")):  # yeniden kurulan paketler; çark içerikle aynı
            self.assertEqual([b["id"] for b in paketler[no]["carrusel"]], [b["id"] for b in paketler[no]["custom"]])
            for b in paketler[no]["custom"]:
                birlik = get_item_from_id(str(b["id"]))
                self.assertEqual(birlik["type"], "u")
                self.assertIn(kelime, birlik["name"], (no, b["id"]))
        self.assertEqual({b["id"] for b in paketler[5]["custom"]}, {608, 609, 610, 611, 539, 540, 541, 574})  # Kraliyet, Güçlü
        # Birliğin kategorisini pack_category ağırlıkları seçer (docs/inceleme/1407-formuller.md, "Birliklerin seçimi");
        # yeniden kurulan paketlerde bütün ağırlık custom'da olmalı, yoksa birlik çoğu zaman genel havuzdan çıkar
        for no in (3, 4, 5):
            agirlik = {k: float(v) for k, v in paketler[no]["pack_category"].items()}
            self.assertEqual(sum(agirlik.values()), agirlik["custom"], no)

    def test_paketten_cikan_birlik_depoya(self):
        # istemci seçtiği birliği Base/storeItem ile store_add_items [JSON] olarak bildirir
        self.komut("store_add_items", "[880]")
        self.assertEqual(self.ps["gifts"][880], 1)


class MezarlikVeViralTeklifler(KomutTesti):
    """GEC-03: mezarlık kapasitesi ve iksir bildirimi; viral teklifler (SpecialDayOfferManager)."""

    def test_mezarlik_kapasitesi_bedel_ve_tavan(self):
        from oyun.config import get_game_config
        g = get_game_config()["globals"]
        bedel, artis = g["GRAVEYARD_CAPACITY"]["price"]["c"], g["GRAVEYARD_CAPACITY"]["amount"]
        self.kayit["playerInfo"]["cash"] = bedel - 1
        self.komut("buy_graveyard_capacity")  # nakit yetmiyor
        self.assertNotIn("graveyardCapacity", self.ps)
        self.kayit["playerInfo"]["cash"] = 2 * bedel
        self.komut("buy_graveyard_capacity")
        self.komut("buy_graveyard_capacity")
        self.assertEqual(self.cash, 0)
        # 1.4.07: artış 10.000, tavan 10.000; ikinci alım tavanı geçmez
        self.assertEqual((bedel, artis, g["GRAVEYARD_MAX_CAPACITY"]), (10000, 10000, 10000))
        self.assertEqual(self.ps["graveyardCapacity"], 10000)

    def test_gelen_iksir_bildirimi_sifirlanir(self):
        self.ps["potionsReceived"] = 4
        self.komut("reset_potions_received")
        self.assertEqual(self.ps["potionsReceived"], 0)

    def test_viral_yardimci_tek_tek_ve_hepsi(self):
        # teklif 1: 3 yardımcı, tek tek 40, hepsi [100, 70, 40]
        self.kayit["playerInfo"]["cash"] = 200
        self.komut("buy_viral_offer_friend", 1)
        self.assertEqual(self.cash, 160)
        self.komut("buy_viral_offer_all", 1)  # 1 alınmış: kalan ikisi 70
        self.assertEqual(self.cash, 90)
        self.assertEqual(self.ps["viralOffers"]["1"]["friends"], [-1, -1, -1])
        self.komut("buy_viral_offer_all", 1)  # hepsi alınmış: fiyat yok
        self.assertEqual(self.cash, 90)
        self.komut("reward_viral_offer", 1, 50, 50, 0, 0)
        self.assertEqual(self.ps["viralOffers"]["1"]["rewarded"], 1)
        self.assertEqual(self.harita["items"], bos_kayit()["maps"][0]["items"])  # birim store_add_items'la gelir

    def test_viral_eksik_yardimcida_odul_yok_nakit_yetmezse_alinmaz(self):
        self.kayit["playerInfo"]["cash"] = 39
        self.komut("buy_viral_offer_friend", 1)
        self.komut("reward_viral_offer", 1, 50, 50, 0, 0)
        self.komut("buy_viral_offer_friend", 999)
        self.assertEqual(self.cash, 39)
        self.assertEqual(self.ps["viralOffers"]["1"], {"id": 1, "friends": [], "rewarded": 0})


class AdaOcagi(KomutTesti):
    """GEC-03: Ada Ocağı (CollectGameManager). Malzemeler 1.4.07'nin collect_game_items'ından."""

    def test_odenen_malzeme_bedeli_ve_sinir(self):
        # bakır (1): 15 gerekli, tek bedel 8, son bedel 8
        self.kayit["playerInfo"]["cash"] = 100
        self.ps["collectGame"] = {"1": {"id": 1, "counter": 13, "timestamp": 7}}
        self.komut("collect_game_add_item", 1, 1)
        self.komut("collect_game_add_item", 1, 1)
        self.komut("collect_game_add_item", 1, 1)  # dolu: nakit yetse de bedel alınmaz, sayaç artmaz
        self.assertEqual(self.cash, 84)
        self.assertEqual(self.ps["collectGame"]["1"], {"id": 1, "counter": 15, "timestamp": 7})
        self.kayit["playerInfo"]["cash"] = 4
        self.komut("collect_game_add_item", 2, 1)  # diş: 5 nakit, 4 kaldı
        self.komut("collect_game_add_item", 99, 0)
        self.assertEqual((self.cash, self.ps["collectGame"]["2"]["counter"]), (4, 0))
        # çekiç (6): cost ve last_cost 0; istemcinin currentCost'u speedup_cost'a (3) düşmez, bedel 0
        self.komut("collect_game_add_item", 6, 1)
        self.assertEqual((self.cash, self.ps["collectGame"]["6"]["counter"]), (4, 1))

    def test_son_birim_son_bedelle(self):
        # 1.4.07'de her malzemede cost == last_cost; ayrımı denemek için ikisi farklı bir malzeme
        malzeme = {"9": {"id": 9, "required": 3, "cost": 4, "last_cost": 10, "speedup_cost": 1, "cooldown": 0}}
        self.kayit["playerInfo"]["cash"] = 100
        with mock.patch.object(self.komutlar, "_ada_malzemeleri", return_value=malzeme):
            for _ in range(4):  # 4, 4, 10; dördüncüsü dolu
                self.komut("collect_game_add_item", 9, 1)
        self.assertEqual((self.cash, self.ps["collectGame"]["9"]["counter"]), (100 - 4 - 4 - 10, 3))

    def test_toplama_ani_ve_hizlandirma(self):
        simdi = self.komutlar.timestamp_now()
        self.komut("collect_game_add_item", 3, 0)  # ödenmeyen: nakit yok, toplama anı yazılır
        self.assertEqual(self.ps["collectGame"]["3"]["counter"], 1)
        self.assertGreaterEqual(self.ps["collectGame"]["3"]["timestamp"], simdi)
        self.komut("collect_game_update_timestamp", 1)
        self.assertGreaterEqual(self.ps["collectGame"]["1"]["timestamp"], simdi)
        # diş (2): hızlandırma 1 nakit, bekleme 300 sn
        self.kayit["playerInfo"]["cash"] = 1
        self.komut("collect_game_speed_up", 2)
        self.komut("collect_game_speed_up", 2)  # nakit bitti
        self.assertEqual(self.cash, 0)
        self.assertLessEqual(self.ps["collectGame"]["2"]["timestamp"], self.komutlar.timestamp_now() - 300)
        self.assertGreaterEqual(self.ps["collectGame"]["2"]["timestamp"], simdi - 300)

    def test_boru_viral_teklif_2nin_yardimcisidir(self):
        # boru (5): 5 gerekli, bedel 10; istemci ayrıca buy_viral_offer_friend [2] gönderir
        self.kayit["playerInfo"]["cash"] = 25
        self.komut("collect_game_add_item", 5, 1)
        self.komut("buy_viral_offer_friend", 2)
        self.assertEqual(self.cash, 15)
        self.assertEqual(self.ps["viralOffers"]["2"]["friends"], [-1])
        self.assertEqual(self.ps["collectGame"]["5"]["counter"], 0)

    def test_hepsini_al_bedeli_ve_tamamlanma(self):
        # boş adada (gerekli - 1) × tek + son: 120 + 125 + 125 + 160 + 50 + 60 (çekiçte bedel 0, hızlandırma 3)
        # = 640; %21 indirim, ilerleme 0: ceil(640 - 640 × 0,21) = 506
        self.assertEqual(self.komutlar.ada_paket_bedeli(self.kayit), 506)
        self.kayit["playerInfo"]["cash"] = 505
        self.komut("collect_game_buy_all", 1)
        self.assertNotIn("collectGame", self.ps)
        self.kayit["playerInfo"]["cash"] = 506
        self.komut("collect_game_buy_all", 1)
        self.assertEqual(self.cash, 0)
        sayaclar = {no: m["counter"] for no, m in self.ps["collectGame"].items()}
        self.assertEqual(sayaclar, {"1": 15, "2": 25, "3": 25, "4": 20, "5": 0, "6": 20})
        self.assertEqual(len(self.ps["viralOffers"]["2"]["friends"]), 5)
        self.assertEqual(self.komutlar.ada_paket_bedeli(self.kayit), 0)
        self.komut("reward_viral_offer", 2, 0, 0, 0, 0)  # bütün ödüller verilince istemci gönderir
        self.assertEqual(self.ps["viralOffers"]["2"]["rewarded"], 1)

    def test_ilerledikce_indirim_azalir(self):
        self.ps["collectGame"] = {"1": {"id": 1, "counter": 14, "timestamp": 0}}
        # bakırda 8 kaldı: 640 - 14 × 8 = 528; ilerleme 14/110: ceil(528 - 528 × 0,21 × 96/110)
        self.assertEqual(self.komutlar.ada_paket_bedeli(self.kayit), math.ceil(528 - 528 * 0.21 * 96 / 110))

    def test_odul_bir_kez_yazilir(self):
        self.komut("collect_game_reward_given", 2272)
        self.komut("collect_game_reward_given", 2272)
        self.komut("collect_game_reward_given", 9999)  # adanın ödülü değil
        self.assertEqual(self.ps["collectGameGivenPrizes"], [2272])
        self.assertEqual(self.harita["items"], bos_kayit()["maps"][0]["items"])  # birim store_add_items'la gelir


class KalanKomutlar(KomutTesti):
    """TST-02 son grup. Beklenen değerler 1.4.07 istemcisinin bayt kodundan (yöntem/@konum)."""

    SIMDI = 2_000_000_000

    def zamanla(self, ad, *args):
        with mock.patch.object(self.komutlar, "timestamp_now", return_value=self.SIMDI):
            self.komut(ad, *args)

    def test_egitim_adimi_kaydedilir_ve_sonda_biter(self):
        """DNT-46. TutorialMain/nextStep @457 her adımda completarTutorial(currentStep), endTutorial @97 sonda 15 yollar;
        Base/completarTutorial @105 adımı playerInfo.completed_tutorial'a yazar. Base/tutorialCheck @36: açılışta
        parseInt(completed_tutorial) 0 ise eğitim baştan başlar. 1.4.07 eğitiminde 15 adım var (TutorialMain/init)."""
        self.kayit["playerInfo"]["completed_tutorial"] = 0
        self.komut("complete_tutorial", 3)
        self.assertEqual(self.kayit["playerInfo"]["completed_tutorial"], 3)
        self.komut("complete_tutorial", 15)
        self.assertEqual(self.kayit["playerInfo"]["completed_tutorial"], 15)

    def test_binici_secimi_adimi_sifirlar(self):
        """DNT-47. PopupDragonRiders/onRiderFieldClick @38-85: tür = seçilen, adım = 0, zaman = 0, sonra select_rider [tür].
        PopupDragonRiderTraining/onTrainClick @89-139: select_rider ['0'] ve üçü de 0. PlayerStatus/Init bunları
        riderNumber, riderStepNumber, riderTimeStamp'ten okur."""
        self.ps.update(riderNumber=1, riderStepNumber=5, riderTimeStamp=123)
        self.komut("rider_select", 2)
        self.assertEqual((self.ps["riderNumber"], self.ps["riderStepNumber"], self.ps["riderTimeStamp"]), (2, 0, 0))
        self.ps.update(riderStepNumber=5, riderTimeStamp=123)
        self.komut("rider_select", "0")
        self.assertEqual((self.ps["riderNumber"], self.ps["riderStepNumber"], self.ps["riderTimeStamp"]), (0, 0, 0))

    def test_binici_sonraki_adim(self):
        """PopupDragonRiderTraining/onGameSuccess @36-149: rider_next_step ['1'], adım + 1, zaman = sunucu zamanı."""
        self.ps.update(riderStepNumber=2, riderTimeStamp=0)
        self.zamanla("rider_next_step", "1")
        self.assertEqual((self.ps["riderStepNumber"], self.ps["riderTimeStamp"]), (3, self.SIMDI))

    def test_dunya_yuvasi_ikinci_argumandan(self):
        """DNT-48. ExplorationsManager/evalUserPositionNotConquered @286-376: oyuncunun yuvası (yerel6) fethedilmemiş
        rakibin yuvasıyla (yerel5) yer değiştirir; komut [yerel6, yerel5]: oyuncunun yeni yuvası ikinci argüman."""
        from oyun import ada
        self.komut("modify_position_univers", 7, 3)
        self.assertEqual(ada.kendi_konumu(self.kayit), 3)

    def test_strateji(self):
        """PopUpBattleOptions/closeWindow @67-90: set_strategy [defensiveStrategy]; Base/processAttacks @1700-1713
        privateState.strategy'yi defensiveStrategy'ye okur."""
        self.komut("set_strategy", 4)
        self.assertEqual(self.ps["strategy"], 4)

    def test_bilgi_gosterildi(self):
        """PlayerStatus/setInfoShowed @28-58: set_info_showed [indeks, değer] ve infoShowed[indeks] = değer."""
        self.ps["infoShowed"] = [0, 0]
        self.komut("set_info_showed", 3, 1)
        self.komut("set_info_showed", 0, 1)
        self.assertEqual((self.ps["infoShowed"][3], self.ps["infoShowed"][0], self.ps["infoShowed"][1]), (1, 1, 0))

    def test_mesaj_ve_dunya_degisimi_temizlenir(self):
        """clear_message argümansız (PopupManager/checkStartPopup'ın kapanışı ?1486); ExplorationsManager/
        onContinentLoaded @390-447: worldChange 1 ise reset_world_change ve istemci worldChange = 0 yazar."""
        self.ps.update(message={"m": "x"}, worldChange=1)
        self.komut("clear_message")
        self.komut("reset_world_change")
        self.assertEqual((self.ps["message"], self.ps["worldChange"]), (None, 0))

    def test_sahte_komsular(self):
        """Base/testABFakeNeighbours @186-268: üç kimlik, eksik olan '0'."""
        self.komut("set_fake_neighbors", "5", "0", "0")
        self.assertEqual(self.ps["fakeNeighbors"], ["5"])

    def test_capraz_tanitim(self):
        """PopupCrossPromotion/_onGetReward @20-147: kimlik düğme adının son iki harfi, ödül bir kez."""
        self.komut("cross_promotion_finished", "ab")
        self.komut("cross_promotion_finished", "ab")
        self.assertEqual(self.ps["crossPromotionsFinished"], ["ab"])

    def test_gorev_degiskeni(self):
        """CustomQuestNew/saveQuestStatus @17-58: [townID, anahtar, JSON.encode(questStatus[anahtar])]."""
        self.komut("set_quest_var", 0, "kesilen", json.dumps({"agac": 3}))
        self.assertEqual(self.harita["currentQuestVars"], {"kesilen": {"agac": 3}})

    def test_hayatta_kalma_cani(self):
        """PopupSurvival/refreshLifes: 3 can; survivalVidaTimeStamp'teki damga + SURVIVAL_HOURS_LIVE_REGENERATE saat
        geçmemişse can harcanmış; üstüne survivalVidasExtra. start_survival argümansız
        (PopupLoadingSurvival/startSurvival)."""
        self.ps.update(survivalVidaTimeStamp=[], survivalVidasExtra=2)
        self.zamanla("start_survival")
        self.assertEqual(self.ps["survivalVidaTimeStamp"], [self.SIMDI])
        dort_saat = self.SIMDI - 4 * 3600
        self.ps["survivalVidaTimeStamp"] = [dort_saat, dort_saat, self.SIMDI - 3600]
        sahte = dict(self.komutlar.globals_(), SURVIVAL_HOURS_LIVE_REGENERATE=5)
        with mock.patch.object(self.komutlar, "globals_", lambda: sahte):
            self.zamanla("start_survival")  # 5 saatte üç can da harcanmış: ek can gider
        self.assertEqual((len(self.ps["survivalVidaTimeStamp"]), self.ps["survivalVidasExtra"]), (3, 1))

    def test_agir_kusatma_baslar(self):
        """MapInitializer$/attacksInit @96-149: heavySiegeAttackTimestamp 0 ise = istemci zamanı, start_heavy_siege [].
        PlayerStatus/Init bunu timeStampHeavySiegeAttack'tan okur."""
        self.zamanla("start_heavy_siege")
        self.assertEqual(self.ps["timeStampHeavySiegeAttack"], self.SIMDI)

    def test_canavar_yuvasi(self):
        """PopupMonstersNest/clickAction @46-220: next_monster_step [_stepCash], nakit düşer, adım + 1, damga = şimdi.
        nextMonster @16-84: adım 0, canavar + 1 (next_monster ['0']). desactivateNest @17-111: monsterNumber, adım ve
        damga 0, monsterNestActive 0."""
        self.ps.update(stepMonsterNumber=1, monsterNumber=0, monsterNestActive=1)
        once = self.cash
        self.zamanla("next_monster_step", 4)
        self.assertEqual((once - self.cash, self.ps["stepMonsterNumber"], self.ps["timeStampTakeCareMonster"]),
                         (4, 2, self.SIMDI))
        self.komut("next_monster", "0")
        self.assertEqual((self.ps["stepMonsterNumber"], self.ps["monsterNumber"]), (0, 1))
        self.komut("desactivate_monster")
        self.assertEqual((self.ps["monsterNestActive"], self.ps["monsterNumber"], self.ps["stepMonsterNumber"]),
                         (0, 0, 0))
        self.assertLessEqual(self.ps["timeStampTakeCareMonster"], 0)

    def test_ejderha_yardimi_temizlenir(self):
        """PopupDragons/closeHireResults @168-224: finish_dragon_help [JSON] ve dragonSocialHelp = []."""
        self.ps["dragonSocialHelp"] = ["a", "b"]
        self.komut("finish_dragon_help", json.dumps(["a", "b"]))
        self.assertEqual(self.ps["dragonSocialHelp"], [])

    def test_tapinak_sifirlanir(self):
        """PopupBahamutSupremeInvocationTemple/resetTempleProgress @181-229: timeStampTemple 0, templeStep []."""
        self.ps.update(timeStampTemple=55, templeStep=[1, 2])
        self.komut("reset_temple")
        self.assertEqual((self.ps["timeStampTemple"], self.ps["templeStep"]), (0, []))

    def test_dart_sifirlama_ve_bedava_atis(self):
        """PopupDarts$/resetDartGame @2-137: iki damga = sunucu zamanı, balonlar [], tohum = gönderilen, bedava atış
        var, ek yok. PopupDarts$/newFree @2-56: timeStampDartsNewFree = şimdi, dartsHasFree true."""
        self.ps.update(dartsBalloonsShot=[1, 2], dartsHasFree=False, dartsGotExtra=True)
        self.zamanla("darts_reset", 777)
        self.assertEqual({k: self.ps[k] for k in ("timeStampDartsReset", "timeStampDartsNewFree", "dartsBalloonsShot",
                                                   "dartsRandomSeed", "dartsHasFree", "dartsGotExtra")},
                         {"timeStampDartsReset": self.SIMDI, "timeStampDartsNewFree": self.SIMDI,
                          "dartsBalloonsShot": [], "dartsRandomSeed": 777, "dartsHasFree": True,
                          "dartsGotExtra": False})
        self.ps.update(dartsHasFree=False, timeStampDartsNewFree=0)
        self.zamanla("darts_new_free")
        self.assertEqual((self.ps["timeStampDartsNewFree"], self.ps["dartsHasFree"]), (self.SIMDI, True))

    def test_yardim_paylasimi_binaya_yazilir(self):
        """PopupSocialFeeds/onPost @185-236: [tx, ty, townID, bina id, arkadaş]; PopupSocialFeeds/<kurucu> @558-596
        binanın attrs.sif'ini okur."""
        self.komut("assist_send_feed", 20, 20, 0, 19, "arkadas")
        self.assertEqual(self.harita["items"][1][7], {"sif": {"arkadas": True}})
        self.assertEqual(len(self.harita["items"][0]), 6)  # öteki bina değişmez

    def test_muttefik_pazari_kaynagi(self):
        """PopupSelectResource/onSelect @47-178: set_resource_allies [kaynak, tx, ty, townID, iID]; seçimde bina üretime
        baştan başlar (collected_at 0). IsoElement/collect @506-563: toplanınca 'n' yollanır, sayaç değişmez."""
        self.harita["items"][1][4] = 5
        self.zamanla("set_resource_allies", "w", 20, 20, 0, 19)
        self.assertEqual((self.harita["resourceAlliesMarket"], self.harita["items"][1][4]), ("w", self.SIMDI))
        self.harita["items"][1][4] = 5
        self.zamanla("set_resource_allies", "n", 20, 20, 0, 19)
        self.assertEqual((self.harita["resourceAlliesMarket"], self.harita["items"][1][4]), ("n", 5))

    def test_hayvan_eklenir(self):
        """MapInitializer$/spawnAnimals @215-314: admin_add_animal [alt kategori, adet], arrayAnimals[alt] += adet."""
        self.ps["arrayAnimals"] = {"7": 2}
        self.komut("admin_add_animal", "7", 3)
        self.komut("admin_add_animal", "9", 1)
        self.assertEqual(self.ps["arrayAnimals"], {"7": 5, "9": 1})

    def test_hedefler_sifirlanir(self):
        """GoalsManager/resetGoals @106-123: reset_completed_missions []."""
        self.ps.update(completedMissions=[1, 2], rewardedMissions=[1])
        self.komut("reset_completed_missions")
        self.assertEqual((self.ps["completedMissions"], self.ps["rewardedMissions"]), ([], []))

    def test_oyuncuya_saldiri_kaydi_degistirmez(self):
        """Assault$/assaultEnemy @103-121 ve ExplorationsManager/doAttack @69-112: attack_player [kurban]; sonucu
        end_attack taşır, başlangıç bir şey değiştirmez."""
        import copy
        once = copy.deepcopy(self.kayit)
        self.komut("attack_player", "rakip")
        self.assertEqual(self.kayit, once)

    def test_kendi_adasinda_oldurulen_dusmanin_jetonu(self):
        """DNT-49. IsoFightingElement/kill @168-511: PLAYER_ENEMY öğe NORMAL kipte ölünce jeton bırakır; Token/onComplete2
        @20-51 NORMAL kipte değeri komut yollamadan ekler. Birim: Token(TOKEN_GOLD, 5) ve Token(TOKEN_XP, collect_xp)
        (@438-475). Bina: uiAttack > 0 ise 5 altın ve ceil(Number(floor(cost / 4)) × 0,02) xp, taş bedelli değilse 0
        (@303-425); uiAttack 0 ise jeton yok. Kuşatma düşmanını istemci doğurur, kayıtta yoktur. Koyun
        (SUBCATFUNC_UNIT_SHEEP 75) PLAYER_NEUTRAL'dır, jetonu yok. Config: Healer (502) collect_xp 4, Tower II (30)
        attack 10, 250 taş: ceil(62 × 0,02) = 2; 27 attack 22, 15 nakit: 0 xp."""
        from oyun.config import get_item_from_id
        self.komutlar.yer_bildir("test", True)
        altin, xp = self.harita["coins"], self.harita["xp"]
        self.komut("kill", 40, 40, 502, 0, "u")
        self.assertEqual((self.harita["coins"] - altin, self.harita["xp"] - xp),
                         (5, int(get_item_from_id(502)["collect_xp"])))
        altin, xp = self.harita["coins"], self.harita["xp"]
        self.komut("kill", 41, 41, 30, 0, "b")
        self.assertEqual((self.harita["coins"] - altin, self.harita["xp"] - xp), (5, 2))
        altin, xp = self.harita["coins"], self.harita["xp"]
        self.komut("kill", 44, 44, 27, 0, "b")  # saldıran ama taş bedelli değil
        self.assertEqual((self.harita["coins"] - altin, self.harita["xp"] - xp), (5, 0))
        altin, xp = self.harita["coins"], self.harita["xp"]
        self.komut("kill", 42, 42, 505, 0, "u")  # koyun
        self.komut("kill", 43, 43, 1, 0, "b")  # saldırmayan bina
        self.assertEqual((self.harita["coins"], self.harita["xp"]), (altin, xp))
        self.assertEqual(self.harita["items"], bos_kayit()["maps"][0]["items"])

    def test_savasta_ya_da_bilinmeyen_yerde_oldurme(self):
        """DNT-49. Görevde, saldırıda, survival'da öldürülen öğenin koordinatı o haritanındır (kill @903-967 kipten
        bağımsız gider); istemci orada jeton vermez (@186-291). start_quest ile başlayan görevde kendi adasının aynı
        koordinatlı öğesi silinmez; end_quest'ten sonra yine kendi adası. Yer bilinmiyorsa (sunucu yeni açıldı) eski
        davranış: kayıttaki öğe silinir, kayıtta olmayana ödül verilmez."""
        self.komut("start_quest", "Q1", 0)
        once = json.dumps(self.kayit, sort_keys=True)
        self.komut("kill", 20, 20, 19, 0, "b")
        self.komut("kill", 40, 40, 502, 0, "u")
        self.assertEqual(json.dumps(self.kayit, sort_keys=True), once)
        self.komut("end_quest", json.dumps({"map": 0, "resources": {}}))
        self.assertTrue(self.komutlar._EVDE["test"])
        for baslat, bitir in (("attack_player", ("end_attack", "{}")), ("start_survival", ("end_survival", 1, 0, "{}"))):
            self.komut(baslat, "rakip") if baslat == "attack_player" else self.komut(baslat)
            self.assertIs(self.komutlar._EVDE["test"], False)
            self.komut(*bitir)
            self.assertIs(self.komutlar._EVDE["test"], True)
        self.komutlar._EVDE.clear()
        altin = self.harita["coins"]
        self.komut("kill", 40, 40, 502, 0, "u")
        self.komut("kill", 20, 20, 19, 0, "b")
        self.assertEqual((self.harita["coins"], len(self.harita["items"])), (altin, 1))

    def test_oyun_durumu_kaydi_degistirmez(self):
        """game_status istemcinin izleme bildirimidir: Base/init @1351-1382 ['MapLoaded', 'INIT', spRefCat],
        Base/_drawMap @99-130 ['LOAD_MAP', çıkılan, girilen]. Kayıtta karşılığı yok."""
        import copy
        once = copy.deepcopy(self.kayit)
        self.komut("game_status", "MapLoaded", "INIT", "")
        self.assertEqual(self.kayit, once)


if __name__ == "__main__":
    unittest.main(verbosity=2)
