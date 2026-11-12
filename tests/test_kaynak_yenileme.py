"""Ağaç, taş ve altın günde bir yenilenir (sahibinin kararı, 12.11.2026: "Günde bir yenilensin").

Yamalı istemci (oyun/swf_yama.py kaynaklari_gunde_bir) kendi köyünde kaynakları yalnızca config'in
globals.NUM_TREE_CLUSTERS[Base.Main.townID]'si doğruysa yeniler; bayrak yoksa yenilemez. İstemci config'i sayfa açılışında
bir kez ister (Base/loadGameConfigSuccess), kasaba değişince istemez (TownManager$/loadTown). Beklenen: o kasabanın
haritası o gün yüklenmediyse 1, yüklendiyse 0, ertesi gün yine 1.
"""

import datetime
import unittest

from ortak import KOK  # noqa: F401

from oyun import config, istemci
from oyun import sunucu as server
from oyun.kayit import session

DIN = "/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires"
CONFIG = DIN + "/get_game_config.php"
INFO = DIN + "/get_player_info.php"


class KaynakBayragi(unittest.TestCase):
    def test_bayrak_istemcinin_okudugu_ad(self):
        # MapInitializer'ın sabiti (çok adlı 12596, genel ad alanı); yama globals'tan bu adı okur
        self.assertEqual(config.KAYNAK_BAYRAGI, "NUM_TREE_CLUSTERS")

    def test_her_config_kasaba_basina_bayrak_tasir(self):
        # Yama globals.NUM_TREE_CLUSTERS[Base.Main.townID] okur; verilmezse hepsi 1 (bayrağı olmayan istemci yenilemez)
        self.assertEqual(config.get_client_game_config("tr")["globals"]["NUM_TREE_CLUSTERS"], [1] * 5)
        self.assertEqual(config.get_client_game_config("tr", kaynak_yenile=(0, 1))["globals"]["NUM_TREE_CLUSTERS"], [0, 1])
        self.assertEqual(config.get_client_game_config("en", kaynak_yenile=(1, 0))["globals"]["NUM_TREE_CLUSTERS"], [1, 0])


class GundeBir(unittest.TestCase):
    def setUp(self):
        self.uid = server.new_village()
        self.kayit = session(self.uid)
        self.kayit["maps"].append(dict(self.kayit["maps"][0], id=1))  # ikinci kasaba

    def test_kasaba_basina_gunde_bir(self):
        gun = datetime.date(2026, 11, 12)
        self.assertEqual(istemci.kaynak_bayraklari(self.kayit, gun), (1, 1, 1))  # iki kasaba + yeni alınacak
        istemci.kaynak_yenilendi(self.kayit, 0, gun)
        self.assertEqual(istemci.kaynak_bayraklari(self.kayit, gun), (0, 1, 1))  # 1. kasaba o gün açılmadı: yenilenir
        istemci.kaynak_yenilendi(self.kayit, 1, gun)
        self.assertEqual(istemci.kaynak_bayraklari(self.kayit, gun), (0, 0, 1))
        self.assertEqual(istemci.kaynak_bayraklari(self.kayit, gun + datetime.timedelta(days=1)), (1, 1, 1))

    def test_kayit_yoksa_yeniler(self):
        self.assertEqual(istemci.kaynak_bayraklari(None), (1,))

    def test_gun_harita_yuklenince_yazilir_config_istenince_degil(self):
        tarayici = server.app.test_client()
        tarayici.post("/", data={"USERID": self.uid, "GAMEVERSION": "SocialEmpires1.4.07sec_fixed.swf"})
        session(self.uid)["maps"].append(dict(session(self.uid)["maps"][0], id=1))
        bayrak = lambda: tarayici.get(CONFIG).get_json()["globals"]["NUM_TREE_CLUSTERS"]  # noqa: E731
        self.assertEqual(bayrak(), [1, 1, 1])
        self.assertEqual(bayrak(), [1, 1, 1])  # harita yüklenmeden (yarıda kalan açılış) gün harcanmaz
        tarayici.post(INFO, data={"USERID": self.uid, "map": 0})
        self.assertEqual(bayrak(), [0, 1, 1])  # aynı gün F5: 0. kasaba yenilenmez, 1. kasaba yenilenir
        tarayici.post(INFO, data={"USERID": self.uid, "map": 1})
        self.assertEqual(bayrak(), [0, 0, 1])
        session(self.uid)["privateState"]["kaynakYenilemeGunu"] = {"0": "2000-01-01", "1": "2000-01-01"}  # ertesi gün
        self.assertEqual(bayrak(), [1, 1, 1])

    def test_aralik_disi_kasaba_numarasi_yuklenen_kasabaya_yazilir(self):
        # get_player_info aralık dışı map'i 0. kasabaya indirir (oyun/oyuncu.py); gün de 0. kasabanın olmalı
        tarayici = server.app.test_client()
        tarayici.post("/", data={"USERID": self.uid, "GAMEVERSION": "SocialEmpires1.4.07sec_fixed.swf"})
        for numara in (7, -1):
            tarayici.post(INFO, data={"USERID": self.uid, "map": numara})
        self.assertEqual(set(session(self.uid)["privateState"]["kaynakYenilemeGunu"]), {"0"})
        self.assertEqual(tarayici.get(CONFIG).get_json()["globals"]["NUM_TREE_CLUSTERS"][0], 0)


if __name__ == "__main__":
    unittest.main()
