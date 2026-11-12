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
        tarayici.get(CONFIG)
        for numara in (7, -1):
            tarayici.post(INFO, data={"USERID": self.uid, "map": numara})
        self.assertEqual(set(session(self.uid)["privateState"]["kaynakYenilemeGunu"]), {"0"})
        self.assertEqual(tarayici.get(CONFIG).get_json()["globals"]["NUM_TREE_CLUSTERS"][0], 0)

    def test_izin_gitmeyen_yukleme_gunu_harcamaz(self):
        """Sayfa gece yarısını geçerek açık kalır: 12.11'in ikinci açılışında bayrak 0 gitti; 13.11'de komşudan dönüşte
        istemci yenilemez (bayrak 0), gün de yazılmamalı; yoksa 13.11'de hiç yenileme olmaz."""
        uid, gun = self.uid, datetime.date(2026, 11, 12)
        istemci.kaynak_yenilendi(self.kayit, 0, gun)  # 12.11'in ilk açılışı
        istemci.kaynak_bayraklari_gitti(uid, istemci.kaynak_bayraklari(self.kayit, gun))  # ikinci açılış: [0, 1, 1]
        ertesi = gun + datetime.timedelta(days=1)
        self.assertFalse(istemci.kaynak_yenilendi(self.kayit, 0, ertesi, uid=uid))
        self.assertEqual(istemci.kaynak_bayraklari(self.kayit, ertesi)[0], 1)

    def test_izin_oturumda_bir_kez_kullanilir(self):
        """İstemci her kasabayı oturumda bir kez yeniler: ikinci yükleme (komşudan dönüş) günü yeniden yazmaz."""
        uid, gun = self.uid, datetime.date(2026, 11, 12)
        istemci.kaynak_bayraklari_gitti(uid, istemci.kaynak_bayraklari(self.kayit, gun))  # [1, 1, 1]
        self.assertTrue(istemci.kaynak_yenilendi(self.kayit, 0, gun, uid=uid))
        ertesi = gun + datetime.timedelta(days=1)  # aynı oturum gece yarısını geçti
        self.assertFalse(istemci.kaynak_yenilendi(self.kayit, 0, ertesi, uid=uid))
        self.assertTrue(istemci.kaynak_yenilendi(self.kayit, 1, gun, uid=uid))  # öteki kasabanın izni ayrı

    def test_config_gitmeden_gelen_yukleme_gunu_yazmaz(self):
        istemci._GIDEN_BAYRAKLAR.pop(self.uid, None)
        self.assertFalse(istemci.kaynak_yenilendi(self.kayit, 0, datetime.date(2026, 11, 12), uid=self.uid))



class HalkaTemizligi(unittest.TestCase):
    """Kaynak yenilemesi olmayan açılışta istemci MapInitializer$/cleanBorderTiles'ı atlar; hikâye görevi kampı ise her
    açılışta yeniden kurulur. safeAreaClean@240-507: halkadaki (orta 3×3 dışı) binalar satılır, oyuncunun ırkından
    birlikler geri çekilir, hayvanlar (inek 504, koyun 505) kalır. Ağaç (19), taş (69), altın (73) yenilenmez, kalır.
    Kimlikler config'ten: 305 Troll Wall II (b, t), 526 Devious Troll (u, t), 512 Light Knight (u, h)."""

    def harita(self):
        return {"race": "h", "expansions": [13, 1], "items": [
            [305, 5, 30, 0], [526, 90, 90, 0], [19, 5, 30, 0], [69, 85, 85, 0], [73, 2, 95, 0],
            [505, 3, 50, 0], [512, 95, 3, 0], [305, 5, 5, 0], [305, 50, 50, 0], [526, 40, 40, 0]]}

    def test_kamp_silinir_kaynak_hayvan_kendi_birligi_kalir(self):
        h = self.harita()
        self.assertEqual(istemci.halkadaki_kampi_temizle(h), 2)
        self.assertEqual(h["items"], [[19, 5, 30, 0], [69, 85, 85, 0], [73, 2, 95, 0], [505, 3, 50, 0], [512, 95, 3, 0],
                                      [305, 5, 5, 0],     # genişleme 1 (0..19, 0..19) oyuncunun
                                      [305, 50, 50, 0], [526, 40, 40, 0]])  # orta 3×3 halkada değil

    def test_izinsiz_acilista_sunucu_temizler(self):
        tarayici = server.app.test_client()
        tarayici.post("/", data={"USERID": self.uid, "GAMEVERSION": "SocialEmpires1.4.07sec_fixed.swf"})
        tarayici.get(CONFIG)
        tarayici.post(INFO, data={"USERID": self.uid, "map": 0})  # izinli açılış: istemci kendisi temizler
        h = session(self.uid)["maps"][0]
        h["items"] += [[305, 5, 30, 0], [526, 90, 90, 0]]  # istemcinin kurduğu kamp
        tarayici.post(INFO, data={"USERID": self.uid, "map": 0})  # aynı oturumda dönüş: izin kullanıldı
        self.assertNotIn([305, 5, 30, 0], h["items"])
        self.assertNotIn([526, 90, 90, 0], h["items"])

    def setUp(self):
        self.uid = server.new_village()


if __name__ == "__main__":
    unittest.main()
