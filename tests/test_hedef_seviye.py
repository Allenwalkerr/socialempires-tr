"""Hedeflerin açılış seviyesi ve sırası (DNT-51, KAR-34).

Kaynaklar: 1.4.07 bayt kodu. Config/<sınıf>: MIN_LEVEL_PVP 8, MIN_LEVEL_QUESTS 6. AbstractGoal/<kurucu> @49-60
order = parseInt(orders); GoalsManager/checkAllGoals @50-276 order'a göre sıralayıp ödülsüz ilk 15 hedefi gösterir,
isGoalAvailable her zaman true (min_level'e bakılmaz); GoalsManager/_load @64-70 orders 0'ı atlar. Binaların açılış
seviyesi config'teki eşyanın min_level'i (istemci AbstractEpIsoElement/initBasicButtons onu okur). KAR-34: etkinlik
hedefleri 15. seviyeden önce yok. Sahibinin bildirdiği: seviye 6'da 'bir oyuncuya akın et' çıkıyordu.
"""

import json
import unittest

from ortak import KOK  # noqa: F401

from oyun import hedef_seviye
from oyun.config import get_game_config


def hedef(i):
    return next(h for h in get_game_config()["goals"] if h["id"] == i)


class Seviyeler(unittest.TestCase):
    def test_saldiri_hedefleri_pvp_seviyesinden_once_yok(self):
        saldirilar = [h for h in get_game_config()["goals"] if h["types"] == "attack_player"]
        self.assertTrue(saldirilar)
        self.assertTrue(all(h["min_level"] >= 8 for h in saldirilar), [(h["id"], h["min_level"]) for h in saldirilar])
        self.assertEqual(hedef(242)["min_level"], 8)  # dosyada 1 yazılıydı

    def test_gorev_adasi_hedefleri_altidan_once_yok(self):
        gorevler = [h for h in get_game_config()["goals"] if h["types"] == "complete_quest"]
        self.assertTrue(all(h["min_level"] >= 6 for h in gorevler))

    def test_bina_hedefi_binanin_seviyesinde(self):
        """Hedefin seviyesi, istediği binalardan en erken açılanın min_level'i (config eşyası) kadardır."""
        esyalar = {str(e["id"]): e for e in get_game_config()["items"]}
        for h in get_game_config()["goals"]:
            if h["types"] != "built_id":
                continue
            ids = json.loads(h["params"]).get("ids") or []
            seviyeler = [int(esyalar[str(i)].get("min_level") or 1) for i in ids if str(i) in esyalar]
            if seviyeler:
                self.assertGreaterEqual(h["min_level"], min(seviyeler), h["id"])

    def test_pazar_dost_hedefi_pazarla_birlikte(self):
        self.assertEqual(hedef(51)["min_level"], hedef(50)["min_level"])  # Recruit Friend Market / Build Market
        self.assertGreater(hedef(50)["min_level"], 1)

    def test_sira_dosya_sirasi_ve_tekil(self):
        hedefler = get_game_config()["goals"]
        sira = [h["orders"] for h in hedefler if h["orders"] != 0]
        self.assertEqual(sira, sorted(set(sira)))  # eşit order kalmadı, dosya sırası korunur
        self.assertEqual(hedef(0)["orders"], 0)  # 0 istemcide atlanır, öyle kalır

    def test_seviyeye_gore_suzulur(self):
        hedefler = get_game_config()["goals"]
        alti = {h["id"] for h in hedef_seviye.seviyeye_gore(hedefler, 6)}
        sekiz = {h["id"] for h in hedef_seviye.seviyeye_gore(hedefler, 8)}
        self.assertNotIn(59, alti)
        self.assertIn(59, sekiz)
        self.assertIn(1, alti)


class IstemciyeGiden(unittest.TestCase):
    def test_config_oyuncunun_seviyesine_gore(self):
        from oyun import sunucu
        from oyun.kayit import new_village, session
        istemci = sunucu.app.test_client()
        uid = new_village()
        istemci.post("/", data={"USERID": uid})
        yol = "/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/get_game_config.php"
        session(uid)["maps"][0]["level"] = 6
        ids6 = {h["id"] for h in istemci.get(yol).get_json()["goals"]}
        session(uid)["maps"][0]["level"] = 8
        ids8 = {h["id"] for h in istemci.get(yol).get_json()["goals"]}
        self.assertNotIn(59, ids6)
        self.assertIn(59, ids8)

    def test_etkinlik_hedefi_onbesten_once_gitmez(self):
        from datetime import date
        from oyun import bayram_hedefleri
        hedefler = bayram_hedefleri.aktif_hedefler(date(2026, 3, 20))  # Ramazan Bayramı 2026
        self.assertTrue(hedefler)
        self.assertEqual(hedef_seviye.seviyeye_gore(hedefler, 14), [])
        self.assertEqual(len(hedef_seviye.seviyeye_gore(hedefler, 15)), len(hedefler))


if __name__ == "__main__":
    unittest.main()
