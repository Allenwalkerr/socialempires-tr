"""Bayram hedefleri (GEC-07, oyun/bayram_hedefleri.py).

Beklenen değerlerin kaynağı: Diyanet tablosu (oyun/takvim.py RAMAZAN: 2026 Ramazan Bayramı 20 Mart) ve
config/takvim.json (Ramazan Bayramı 3 gün, setler Firavunlar ve Mısır; ikinci etkinlik); config/tema_setleri.json;
1.4.07 istemcisinin bayt kodu: GoalsManager/_load@64-70 `orders` 0 olan hedefi atlar, params JSON'dur (ids, ammount),
goalComparison `order` farkıyla sıralar; resim config `images`'ında olmalı (MissionPopup/openInfoPopup).
"""

import json
import os
import unittest
from datetime import date
from unittest import mock

from ortak import KOK, KomutTesti

from oyun import bayram_hedefleri, config, takvim

RAMAZAN_2026 = date(2026, 3, 20)


class Takvim(unittest.TestCase):
    def test_bayram_gunu_var_ertesi_gun_yok(self):
        """Kabul kapısı: bayram günü hedef var, bittikten sonraki gün yok."""
        kimlik = bayram_hedefleri.hedef_kimligi(2026, 2)
        gunler = {g: [h["id"] for h in bayram_hedefleri.aktif_hedefler(date(2026, 3, g))] for g in (19, 20, 22, 23)}
        self.assertEqual(gunler[19], [])
        self.assertIn(kimlik, gunler[20])
        self.assertIn(kimlik, gunler[22])
        self.assertNotIn(kimlik, gunler[23])

    def test_hedef_istemcinin_okuyacagi_bicimde(self):
        with open(os.path.join(KOK, "config", "tema_setleri.json"), encoding="utf-8") as f:
            setler = json.load(f)["setler"]
        with open(os.path.join(KOK, "config", "goals.json"), encoding="utf-8") as f:
            hedefler = json.load(f)
        h = bayram_hedefleri.aktif_hedefler(RAMAZAN_2026)[0]
        self.assertNotEqual(h["orders"], 0)  # 0 olsa istemci atlar
        self.assertLess(h["orders"], min(x["orders"] for x in hedefler if x["orders"]))  # başa gelir
        self.assertEqual(h["types"], "built_id")
        params = json.loads(h["params"])
        self.assertEqual(sorted(params["ids"]), sorted(set(setler["Firavunlar"]) | set(setler["Mısır"])))
        self.assertEqual(params["ammount"], 1)
        self.assertNotIn(h["id"], {x["id"] for x in hedefler})
        self.assertIn(h["image"], {x["image"] for x in hedefler})  # oyunun kendi hedef resmi
        self.assertIn(h["characters"], {x["characters"] for x in hedefler})
        self.assertIn("22 Mart", h["description"])  # son gün: 20 + 3 − 1

    def test_her_yil_yeni_kimlik(self):
        """Kimlik yılı taşır: geçen yılın ödülü (rewardedMissions) bu yılın hedefini gizlemez."""
        a = bayram_hedefleri.aktif_hedefler(RAMAZAN_2026)[0]["id"]
        b = bayram_hedefleri.aktif_hedefler(date(2027, 3, 9))[0]["id"]  # Diyanet: 2027 Ramazan Bayramı 9 Mart
        self.assertNotEqual(a, b)


class IstemciConfigi(unittest.TestCase):
    def test_config_gune_gore_degisir(self):
        """Mağaza kipi "hepsi açık" (True): önbellek anahtarında güne bağlı tek şey bayram hedefleridir."""
        with mock.patch.object(config, "tema_seti_kipi", lambda: True):
            with mock.patch.object(takvim, "bugun", lambda: RAMAZAN_2026):
                bayramda = config.get_client_game_config("tr")
            with mock.patch.object(takvim, "bugun", lambda: date(2026, 3, 25)):
                sonra = config.get_client_game_config("tr")
        kimlik = bayram_hedefleri.hedef_kimligi(2026, 2)
        self.assertIn(kimlik, {h["id"] for h in bayramda["goals"]})
        self.assertNotIn(kimlik, {h["id"] for h in sonra["goals"]})  # önbellek eski günü vermez
        self.assertIn("goal_032.jpg", bayramda["images"])

    def test_ascii_kipinde_turkce_harf_yok(self):
        with mock.patch.object(takvim, "bugun", lambda: RAMAZAN_2026):
            c = config.get_client_game_config("tr", ascii_mode=True)
        h = next(h for h in c["goals"] if h["id"] == bayram_hedefleri.hedef_kimligi(2026, 2))
        self.assertFalse(set(h["title"] + h["description"]) & set("çÇğĞıİöÖşŞüÜ"), h["title"])


class Odul(KomutTesti):
    def test_odul_bir_kez_ve_yalniz_acilmis_bayramda(self):
        """reward_mission [kasaba, kimlik]; ödül 500 altın (goals.json'daki en yüksek ödül). Kabul kapısı: bir kez.
        Elle yazılmış paketle gelecek yılın ya da süresi çoktan geçmiş bayramın hedefinden altın alınamaz."""
        kimlik = bayram_hedefleri.hedef_kimligi(2026, 2)
        with mock.patch.object(takvim, "bugun", lambda: RAMAZAN_2026):
            self.komut("reward_mission", 0, kimlik)
            self.komut("reward_mission", 0, kimlik)
            self.assertEqual(self.harita["coins"], 50000 + 500)
            self.komut("reward_mission", 0, bayram_hedefleri.hedef_kimligi(2027, 2))  # gelecek yıl
        with mock.patch.object(takvim, "bugun", lambda: date(2026, 6, 1)):
            self.komut("reward_mission", 0, bayram_hedefleri.hedef_kimligi(2026, 3))  # Nevruz 2026, 30 günden eski
        self.assertEqual(self.harita["coins"], 50000 + 500)


if __name__ == "__main__":
    unittest.main()
