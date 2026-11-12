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

    def test_depoda_olmayan_esya_yerlestirilip_satilamaz(self):
        # tekrarlanan komut: depo boşken eşya çoğalmamalı, iade verilmemeli
        self.ps["gifts"] = [0, 1]
        self.komut("place_gift", 1, 5, 6, 0, 0)
        self.komut("place_gift", 1, 7, 8, 0, 0)
        self.assertEqual(sum(1 for e in self.harita["items"] if e[0] == 1), 2)  # 1 mevcut + 1 yeni
        self.komut("sell_gift", 1, 0)
        self.assertEqual(self.harita["wood"], 1000)

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
        # [altin, xp, gorev, x, y, kasaba]
        self.komut("collect_treasure", 500, 60, 1, 0, 0, 0)
        self.assertEqual(self.harita["coins"], 50500)
        self.assertEqual(self.harita["xp"], 60)

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
        self.ps["collections"] = [[0] * 6, [0, 2, 1, 0, 1, 1], [0] * 6, [0] * 6, [0, 1, 0, 3, 1, 1]]
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
                self.komut("finish_collection", c, *((1, 5) if c % 2 else ()))
                self.assertEqual(self.ps["gifts"][odul], 1)
                self.assertEqual(sum(self.ps["gifts"]), 1)

    def test_koleksiyon_tekrar_bitirilince_odul_yine_verilir(self):
        # arUniqueCollections = [21, 22] dışındakiler yeniden toplanabilir; getReward her seferinde ödül verir
        self.ps["gifts"] = []
        self.komut("finish_collection", 2)
        self.komut("finish_collection", 2)
        self.assertEqual(self.ps["gifts"][177], 2)
        self.assertEqual(self.ps["collectionsCompleted"], [2])

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
        self.kayit["playerInfo"]["cash"] = 11
        self.komut("buy_unit_pack", 3, 2)  # 11 nakit
        self.assertEqual((self.cash, self.ps["unitPacks"]), (0, {"3": 2}))

    def test_nakitle_toplu_alim_indirimi(self):
        self.kayit["playerInfo"]["cash"] = 1000
        self.komut("buy_unit_pack", 3, 2)  # 6 nakit × 2 = 12, %10 indirim: int(10,8 + 0,5) = 11
        self.assertEqual(self.cash, 1000 - 11)
        self.komut("buy_unit_pack", 3, 8)  # 48, %15 indirim: int(40,8 + 0,5) = 41
        self.assertEqual(self.cash, 1000 - 11 - 41)
        self.assertEqual(self.ps["unitPacks"], {"3": 10})

    def test_kaynak_yetmezse_ve_bilinmeyen_paket_alinmaz(self):
        self.kayit["playerInfo"]["cash"] = 5
        self.komut("buy_unit_pack", 3, 1)
        self.komut("buy_unit_pack", 99, 1)
        self.komut("buy_unit_pack", 2, 4)  # 4 × 20.000 altın > 50.000
        self.assertEqual((self.cash, self.harita["coins"]), (5, 50000))
        self.assertNotIn("unitPacks", self.ps)

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
