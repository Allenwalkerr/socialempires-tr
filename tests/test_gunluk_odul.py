"""1.4.07'nin 5 günlük günlük ödülü (OYN-11, KYT-02, KAR-24; oyun/gunluk_odul.py).

Beklenen değerlerin kaynağı: config `daily_bonus` (1-mega_patch): gün 1 g/w/f/s 250, gün 2 birim 722, gün 3 nakit 10,
gün 4 iksir 25, gün 5 birim 714. İstemci: DailyBonusManager/initPlayerData pencereyi (showDailyBonus ||
lastDayRewarded == 0) && !tutorial iken açar; PopupNewDailyBonus/init@754-797 ödülü yalnızca day == numDaysLogged ve
numDaysLogged != lastDayRewarded iken verir. Sahibinin kararı (KAR-24): ödülü sunucu verir, 5. günden sonra pencere
açılmaz.
"""

import unittest
from unittest import mock

from ortak import bos_kayit

from oyun import gunluk_odul, oyuncu


def kayit(gun, son=None):
    k = bos_kayit()
    k["privateState"]["numDayLogged"] = gun
    if son is not None:
        k["privateState"]["lastDayRewarded"] = son
    return k


def istemci_acar_mi(ps):
    """initPlayerData@56-142 kuralı."""
    return ps.get("showDailyBonus") == 1 or int(ps.get("lastDayRewarded", 0) or 0) == 0


def istemci_odul_verir_mi(ps):
    """PopupNewDailyBonus/init@754-797: _currentReward = day == numDaysLogged && numDaysLogged != lastDayRewarded."""
    gun = ps["numDayLogged"]
    return any(t["reward_day"] == gun for t in gunluk_odul.tablo()) and gun != ps.get("lastDayRewarded", 0)


class Isle(unittest.TestCase):
    def test_bes_gunun_odulleri_bir_kez(self):
        k = kayit(1)
        h, ps = k["maps"][0], k["privateState"]
        once = (h["coins"], h["wood"], h["food"], h["stone"])
        self.assertTrue(gunluk_odul.isle(k))
        self.assertEqual((h["coins"], h["wood"], h["food"], h["stone"]), tuple(x + 250 for x in once))
        self.assertFalse(gunluk_odul.isle(k))  # aynı gün ikinci kez: yok
        self.assertEqual(h["coins"], once[0] + 250)
        ps["numDayLogged"] = 2
        self.assertTrue(gunluk_odul.isle(k))
        self.assertEqual(ps["gifts"][722], 1)
        ps["numDayLogged"] = 3
        nakit = k["playerInfo"]["cash"]
        gunluk_odul.isle(k)
        self.assertEqual(k["playerInfo"]["cash"], nakit + 10)
        ps["numDayLogged"] = 4
        iksir = ps["potion"]
        gunluk_odul.isle(k)
        self.assertEqual(ps["potion"], iksir + 25)
        ps["numDayLogged"] = 5
        gunluk_odul.isle(k)
        self.assertEqual((ps["gifts"][714], ps["gifts"][722]), (1, 1))
        self.assertEqual(ps["lastDayRewarded"], 5)

    def test_bes_gunden_sonra_pencere_acilmaz(self):
        k = kayit(6, son=5)
        once = json_kopya(k)
        self.assertFalse(gunluk_odul.isle(k))
        self.assertEqual(k["privateState"]["lastDayRewarded"], 6)
        once["privateState"]["lastDayRewarded"] = 6
        self.assertEqual(k, once)  # ödül yok
        self.assertFalse(istemci_acar_mi(k["privateState"]))

    def test_eski_kayit_atlanan_gun_icin_bugunun_odulu(self):
        """numDayLogged ayrı giriş günü sayısıdır (raporda ✔); 3. gündeyken lastDayRewarded yoksa yalnızca 3. gün."""
        k = kayit(3)
        nakit = k["playerInfo"]["cash"]
        self.assertTrue(gunluk_odul.isle(k))
        self.assertEqual((k["playerInfo"]["cash"], k["privateState"].get("gifts")), (nakit + 10, []))


def json_kopya(k):
    import json
    return json.loads(json.dumps(k))


class Yanit(unittest.TestCase):
    def setUp(self):
        self.kayitlar, self.yazilan = {}, []
        for ad, deger in (("session", lambda u: self.kayitlar.get(u)), ("save_session", self.yazilan.append),
                          ("neighbors", lambda u: [])):
            yama = mock.patch.object(oyuncu, ad, deger)
            yama.start()
            self.addCleanup(yama.stop)

    def bilgi(self, uid="t"):
        k = self.kayitlar[uid]
        k["playerInfo"]["last_logged_in"] = oyuncu.timestamp_now()  # aynı gün: giris_gunu_say artırmaz
        return oyuncu.get_player_info(uid)

    def test_odul_gunu_pencere_acilir_istemci_ikinci_kez_vermez(self):
        self.kayitlar["t"] = kayit(2)
        y = self.bilgi()
        ps = y["privateState"]
        self.assertEqual(ps["showDailyBonus"], 1)
        self.assertTrue(istemci_acar_mi(ps))
        self.assertFalse(istemci_odul_verir_mi(ps))  # sunucu verdi; istemci store_add_items yollamaz
        self.assertNotIn("showDailyBonus", self.kayitlar["t"]["privateState"])  # yalnızca yanıtta
        self.assertEqual(self.yazilan, ["t"])  # ödül hemen kalıcı
        ikinci = self.bilgi()["privateState"]  # aynı gün yeniden açılış (kasaba değişimi, sayfa yenileme)
        self.assertFalse(istemci_acar_mi(ikinci))
        self.assertEqual(self.kayitlar["t"]["privateState"]["gifts"][722], 1)

    def test_eski_hata_lastDayRewarded_yokken_her_giriste_birim(self):
        """Düzeltmeden önceki durum: lastDayRewarded yok → istemci pencereyi açar ve 2. günün birimini verir. Artık
        sunucu ilk yanıtta lastDayRewarded'ı yazar; ikinci yanıtta pencere açılmaz."""
        self.kayitlar["t"] = kayit(2)
        self.assertTrue(istemci_acar_mi(self.kayitlar["t"]["privateState"]))  # sunucudan önce
        self.bilgi()
        self.assertEqual(self.kayitlar["t"]["privateState"]["lastDayRewarded"], 2)


if __name__ == "__main__":
    unittest.main()
