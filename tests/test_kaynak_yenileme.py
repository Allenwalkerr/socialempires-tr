"""Ağaç, taş ve altın günde bir yenilenir (sahibinin kararı, 12.11.2026: "Günde bir yenilensin").

Yamalı istemci (oyun/swf_yama.py kaynaklari_gunde_bir) kendi köyünde kaynakları yalnızca config'in
globals.NUM_TREE_CLUSTERS'ı doğruysa yeniler; bayrak yoksa yenilemez. İstemci config'i her sayfa açılışında bir kez
ister (Base/loadGameConfigSuccess). Beklenen: günün ilk config'i 1, aynı gün sonrakiler 0, ertesi gün yine 1.
"""

import datetime
import unittest

from ortak import KOK  # noqa: F401

from oyun import config, istemci
from oyun import sunucu as server
from oyun.kayit import session

CONFIG = "/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/get_game_config.php"


class KaynakBayragi(unittest.TestCase):
    def test_bayrak_istemcinin_okudugu_ad(self):
        # MapInitializer'ın sabiti (çok adlı 12596, genel ad alanı); yama globals'tan bu adı okur
        self.assertEqual(config.KAYNAK_BAYRAGI, "NUM_TREE_CLUSTERS")

    def test_her_config_bayragi_tasir(self):
        self.assertEqual(config.get_client_game_config("tr")["globals"]["NUM_TREE_CLUSTERS"], 1)
        self.assertEqual(config.get_client_game_config("tr", kaynak_yenile=False)["globals"]["NUM_TREE_CLUSTERS"], 0)
        self.assertEqual(config.get_client_game_config("tr", kaynak_yenile=True)["globals"]["NUM_TREE_CLUSTERS"], 1)
        self.assertEqual(config.get_client_game_config("en", kaynak_yenile=False)["globals"]["NUM_TREE_CLUSTERS"], 0)


class GundeBir(unittest.TestCase):
    def setUp(self):
        self.uid = server.new_village()
        self.kayit = session(self.uid)

    def test_gunun_ilki_yeniler_sonrakiler_yenilemez(self):
        gun = datetime.date(2026, 11, 12)
        self.assertTrue(istemci.kaynak_yenilenir_mi(self.uid, self.kayit, gun))
        self.assertEqual(self.kayit["privateState"]["kaynakYenilemeGunu"], "2026-11-12")
        self.assertFalse(istemci.kaynak_yenilenir_mi(self.uid, self.kayit, gun))
        self.assertFalse(istemci.kaynak_yenilenir_mi(self.uid, self.kayit, gun))
        self.assertTrue(istemci.kaynak_yenilenir_mi(self.uid, self.kayit, gun + datetime.timedelta(days=1)))
        self.assertFalse(istemci.kaynak_yenilenir_mi(self.uid, self.kayit, gun + datetime.timedelta(days=1)))

    def test_kayit_yoksa_yeniler(self):
        self.assertTrue(istemci.kaynak_yenilenir_mi("", None))

    def test_config_ucu_gunun_ilk_acilisinda_bir_kez_yeniler(self):
        tarayici = server.app.test_client()
        tarayici.post("/", data={"USERID": self.uid, "GAMEVERSION": "SocialEmpires1.4.07sec_fixed.swf"})
        bayraklar = [tarayici.get(CONFIG).get_json()["globals"]["NUM_TREE_CLUSTERS"] for _ in range(3)]
        self.assertEqual(bayraklar, [1, 0, 0])
        # ertesi gün (kayıttaki gün dün olur); sayfa açılışı kaydı yeniden yüklediği için oturumdaki kayıt
        session(self.uid)["privateState"]["kaynakYenilemeGunu"] = "2000-01-01"
        self.assertEqual(tarayici.get(CONFIG).get_json()["globals"]["NUM_TREE_CLUSTERS"], 1)


if __name__ == "__main__":
    unittest.main()
