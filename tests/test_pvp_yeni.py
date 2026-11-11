"""1.4.07'nin yeni PvP'si, ilk parça (GEC-05; oyun/pvp_yeni.py).

Beklenen değerlerin kaynağı istemcinin bayt kodu (yöntem adları oyun/pvp_yeni.py'nin belge dizesinde) ve oyun
config'i: globals.PVP_SEARCH_ENEMY_COST {"0": 0, "11": 25, "21": 50, ..., "81": 5000 altın}; pvp_shields id 1:
10 nakit, 86400 sn koruma, 86400 sn bekleme; id 2: 20 nakit, 172800/172800.
"""

import json
import unittest
from unittest import mock

from ortak import KomutTesti, bos_kayit

from oyun import pvp_yeni
from oyun import sunucu as server

DINAMIK = "/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires"
SIMDI = 2_000_000_000


def bot(pid, seviye, **ps):
    k = bos_kayit(pid)
    k["playerInfo"]["bot"] = True
    k["maps"][0]["level"] = seviye
    k["privateState"].update(ps)
    return k


class Kayitlar(KomutTesti):
    """Botlar KomutTesti'nin bellekteki kayıtlarına eklenir; pvp_yeni onları oyun.kayit'tan okur."""

    def setUp(self):
        super().setUp()
        for ad, deger in (("all_saves_userid", lambda: list(self.kayitlar)), ("neighbor_session", self.kayitlar.get),
                          ("timestamp_now", lambda: SIMDI)):
            yama = mock.patch.object(pvp_yeni, ad, deger)
            yama.start()
            self.addCleanup(yama.stop)


class AramaBedeli(Kayitlar):
    def test_seviyeden_buyuk_ilk_anahtarin_bedeli(self):
        """PVPManager/getSearchEnemyCost: seviye < anahtar olan ilk satırda durur (seviye 15 → "21" → 50)."""
        self.assertEqual([pvp_yeni.arama_bedeli(s) for s in (1, 10, 11, 15, 21, 80, 81, 99)],
                         [25, 25, 50, 50, 100, 5000, 5000, 5000])

    def test_get_enemy_new_bedeli_duser_yetmezse_uygulanmaz(self):
        self.harita.update(level=15, coins=60)
        self.komut("get_enemy_new", 50, 0)
        self.assertEqual(self.harita["coins"], 10)
        self.komutlar.command("test", {"commands": [{"cmd": "get_enemy_new", "args": [50, 1]}]})  # KAR-18
        self.assertEqual(self.harita["coins"], 10)
        self.harita["coins"] = 60
        self.komut("get_enemy_new", 0, 2)  # istemcinin bildirdiği değil, istemcinin formülüyle hesaplanan bedel
        self.assertEqual(self.harita["coins"], 10)


class Kalkan(Kayitlar):
    def test_kalkan_alimi(self):
        """ShieldManager/buyShield: -1 ise şimdi + koruma, değilse eski + koruma; bekleme şimdi + cooldown."""
        with mock.patch.object(pvp_yeni, "timestamp_now", lambda: SIMDI):
            self.komut("buy_shield", 1)
            self.assertEqual((self.ps["shieldEndTime"], self.ps["shieldCooldown"], self.ps["purchasedShields"],
                              self.cash), (SIMDI + 86400, SIMDI + 86400, [1], 90))
            self.komut("buy_shield", 1)  # ShieldManager.isShieldAvailable: alınan yeniden alınamaz
            self.assertEqual((self.ps["purchasedShields"], self.cash), ([1], 90))
            self.komut("buy_shield", 2)  # üst üste biner
            self.assertEqual((self.ps["shieldEndTime"], self.ps["shieldCooldown"], self.ps["purchasedShields"],
                              self.cash), (SIMDI + 86400 + 172800, SIMDI + 172800, [1, 2], 70))

    def test_saldiri_baslayinca_kalkan_kalkar(self):
        self.ps.update(shieldEndTime=SIMDI + 500, shield_until=SIMDI + 500, shieldCooldown=SIMDI + 900,
                       purchasedShields=[1])
        self.komut("begin_attack_new", SIMDI)
        self.assertEqual((self.ps["shieldEndTime"], self.ps["shield_until"], self.ps["shieldCooldown"],
                          self.ps["purchasedShields"]), (0, 0, SIMDI + 900, [1]))  # removeShields bekleme dokunmaz

    def test_reset_shield_yalnizca_suresi_dolani_temizler(self):
        self.ps.update(shieldEndTime=SIMDI - 1, shieldCooldown=SIMDI + 900, purchasedShields=[1])
        self.komut("reset_shield")
        self.assertEqual((self.ps["shieldEndTime"], self.ps["shieldCooldown"], self.ps["purchasedShields"]),
                         (0, SIMDI + 900, [1]))
        self.ps.update(shieldEndTime=SIMDI + 5, shieldCooldown=SIMDI - 1)
        self.komut("reset_shield")  # _checkCoolDown: bekleme bitti → purchasedShields = []
        self.assertEqual((self.ps["shieldEndTime"], self.ps["shieldCooldown"], self.ps["purchasedShields"]),
                         (SIMDI + 5, 0, []))


class RakipSecimi(Kayitlar):
    def test_kalkanli_yakin_saldirilan_ve_oyuncu_secilmez(self):
        self.harita["level"] = 20
        self.kayitlar.update(kalkanli=bot("kalkanli", 20, shieldEndTime=SIMDI + 60),
                             yeni=bot("yeni", 20, shield_until=SIMDI + 60), dovulen=bot("dovulen", 20),
                             uygun=bot("uygun", 40), oyuncu=bos_kayit("oyuncu"))
        self.ps["attacksSent"] = [{"time": SIMDI - 3600, "victim_id": "dovulen"}]  # 4 saat dolmadı
        self.assertEqual({pvp_yeni.rakip_sec(self.kayit) for _ in range(20)}, {"uygun"})
        self.ps["attacksSent"][0]["time"] = SIMDI - 4 * 3600
        self.assertIn("dovulen", {pvp_yeni.rakip_sec(self.kayit) for _ in range(40)})

    def test_bot_yoksa_rakip_yok(self):
        self.assertIsNone(pvp_yeni.rakip_sec(self.kayit))


class Gunluk(Kayitlar):
    def test_intikam_ve_temizleme(self):
        self.ps["PVPattacksReceived"] = {"123": {"id": "b", "attackTime": 123}, "456": {"id": "c"}}
        self.komut("reply_attack", 123)  # AttackLogItem kaydın 'reply' alanını okur
        self.assertEqual(self.ps["PVPattacksReceived"]["123"]["reply"], 1)
        self.assertNotIn("reply", self.ps["PVPattacksReceived"]["456"])
        self.komut("reply_attack", 999)  # olmayan kayıt: hata yok
        self.komut("clean_attack_log")
        self.assertEqual(self.ps["PVPattacksReceived"], {})

    def test_turnuva_maci_komutu_kayda_yazmaz(self):
        once = json.dumps(self.kayit, sort_keys=True)
        self.komut("end_tournament_match", 1)
        self.assertEqual(json.dumps(self.kayit, sort_keys=True), once)


class PvpUclari(unittest.TestCase):
    """Önce bu uçlar bilinmeyen-uç yakalayıcısında 404 alıyordu (rakip aranamıyor, başta/sonda senkron hatası)."""

    def setUp(self):
        self.uid = server.new_village()
        self.istemci = server.app.test_client()
        self.kayitlar = {"b1": bot("b1", 10)}
        for ad, deger in (("all_saves_userid", lambda: [self.uid, *self.kayitlar]),
                          ("neighbor_session", lambda u: self.kayitlar.get(u) or server.kayit_oturumu(u))):
            yama = mock.patch.object(pvp_yeni, ad, deger)
            yama.start()
            self.addCleanup(yama.stop)

    def cagir(self, ad, govde):
        cevap = self.istemci.post(f"{DINAMIK}/pvp/web/app.php/pvp/{ad}?USERID={self.uid}",
                                  data={"data": "0" * 64 + ";" + json.dumps(govde)})
        self.assertEqual(cevap.status_code, 200, ad)
        return json.loads(cevap.get_data(as_text=True).split(";", 1)[1])

    def test_rakip_bulunur(self):
        self.assertEqual(self.cagir("enemy", {"user_id": self.uid, "level": 5}), {"result": "success",
                                                                                 "data": {"id": "b1"}})
        self.kayitlar.clear()
        self.assertEqual(self.cagir("enemy", {"user_id": self.uid, "level": 5})["result"], "error")

    def test_havuz_ve_saldiri_uclari(self):
        self.assertEqual(self.cagir("pool/check", {"user_id": "b1"}), {"result": "success", "data": 1})
        self.kayitlar["b1"]["privateState"]["shieldEndTime"] = 4_000_000_000
        self.assertEqual(self.cagir("pool/check", {"user_id": "b1"})["data"], 0)
        for ad in ("attack/begin", "attack/end", "pool/add", "pool/del"):
            self.assertEqual(self.cagir(ad, {"user_id": self.uid})["result"], "success", ad)
        self.assertEqual(self.istemci.post(f"{DINAMIK}/pvp/web/app.php/pvp/bilinmeyen").status_code, 404)


if __name__ == "__main__":
    unittest.main()
