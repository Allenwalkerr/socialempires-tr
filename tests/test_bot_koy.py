"""Bot köyleri (oyun/bot_koy.py; plan docs/inceleme/bot-koyleri-plani.md §3.3).

Beklenen değerlerin kaynağı: config items (min_level, trains, width, height, type, attack, life, in_store);
1.4.07 bayt kodu: Base/setOccupiedGrid binayı tx-genişlik+1..tx, ty-yükseklik+1..ty karolarına yazar; Config
EI_TILES_IN_BIGTILE 20, MAX_TOWERS_PER_BIGTILE 10; genişleme kimliği satır·5 + sütun + 1. Üreticinin kendi çıktısı
beklenen değer yapılmaz: doluluk, sınır ve güç burada config'ten ayrıca hesaplanır.
"""

import unittest
import uuid

from ortak import KOK  # noqa: F401

from oyun import bot_koy
from oyun.config import get_game_config

ESYA = {int(e["id"]): e for e in get_game_config()["items"]}
SEVIYELER = (1, 3, 8, 14, 15, 21, 29, 30, 42, 46, 60)
KRALIYET = {608, 609, 610}  # Kışla V, Okçu Ocağı V, Ahır V birimleri


def karolar(e):
    w, h = int(ESYA[int(e[0])]["width"]), int(ESYA[int(e[0])]["height"])
    return {(i, j) for i in range(int(e[1]) - w + 1, int(e[1]) + 1) for j in range(int(e[2]) - h + 1, int(e[2]) + 1)}


def acik_karolar(genislemeler):
    sonuc = set()
    for g in genislemeler:
        satir, sutun = divmod(g - 1, 5)
        sonuc |= {(sutun * 20 + i, satir * 20 + j) for i in range(20) for j in range(20)}
        sonuc |= {(satir * 20 + i, sutun * 20 + j) for i in range(20) for j in range(20)}
    return sonuc


def guc(items):
    return sum(float(ESYA[int(e[0])].get("attack") or 0) + float(ESYA[int(e[0])].get("life") or 0) * 0.35
               for e in items if ESYA[int(e[0])].get("type") == "u")


class Kademeler(unittest.TestCase):
    def test_kollar_configdeki_bina_ve_birimle(self):
        for kol, tablo in bot_koy.KOLLAR.items():
            for seviye, bina, birim in tablo:
                e = ESYA[bina]
                self.assertEqual((int(e["min_level"]), int(e["trains"]), e["in_store"]), (seviye, birim, "1"), bina)
                self.assertEqual(ESYA[birim]["type"], "u")
            self.assertEqual([s for s, _, _ in tablo], sorted(s for s, _, _ in tablo), kol)

    def test_bina_ve_sus_tablolari_configdeki_acilis_seviyesiyle(self):
        for ad in ("BELEDIYE", "EV", "KULE", "SUR", "KALE", "DEGIRMEN", "TARLA", "ALTIN", "MARANGOZ", "TAS", "KOYUN",
                   "INEK", "PAZAR", "INANC", "AGAC", "CICEK", "HEYKEL", "BAYRAK"):
            for seviye, kimlik in getattr(bot_koy, ad):
                self.assertEqual(int(ESYA[kimlik].get("min_level") or 0), seviye, (ad, kimlik))
        for seviye, kimlik in (bot_koy.SUR_KAPISI, bot_koy.CESME, bot_koy.ATES):
            self.assertEqual(int(ESYA[kimlik].get("min_level") or 0), seviye, kimlik)


class Yerlesim(unittest.TestCase):
    def setUp(self):
        self.koyler = {(sv, k): bot_koy.koy_kur(sv, k, "test-%d-%s" % (sv, k), 1000)
                       for sv in SEVIYELER for k in bot_koy.KISILIK}

    def test_ust_uste_binmez_ve_acik_alanda_kalir(self):
        for (sv, k), (items, genislemeler) in self.koyler.items():
            alan, dolu = acik_karolar(genislemeler), {}
            for e in items:
                for t in karolar(e):
                    self.assertNotIn(t, dolu, (sv, k, e, dolu.get(t)))
                    dolu[t] = e
                    self.assertIn(t, alan, (sv, k, e))

    def test_seviyesinde_acilmamis_oge_yok_ve_kule_siniri(self):
        for (sv, k), (items, _) in self.koyler.items():
            kuleler = {}
            for e in items:
                self.assertLessEqual(int(ESYA[int(e[0])].get("min_level") or 0), sv, (sv, k, e[0]))
                if ESYA[int(e[0])].get("subcategory_id") == "21":  # kule
                    bk = (int(e[1]) // 20, int(e[2]) // 20)
                    kuleler[bk] = kuleler.get(bk, 0) + 1
            self.assertLessEqual(max(kuleler.values(), default=0), 10, (sv, k))  # MAX_TOWERS_PER_BIGTILE

    def test_sur_kapi_ve_belediye(self):
        for (sv, k), (items, _) in self.koyler.items():
            ids = [int(e[0]) for e in items]
            self.assertEqual(sum(1 for i in ids if ESYA[i].get("subcategory_id") == "13"
                                 and i in (26, 139, 140, 141)), 1, (sv, k))  # tek belediye
            self.assertEqual(ids.count(37), 1 if sv >= 21 else 0, (sv, k))  # Sur Kapısı 21'de açılır
            surlar = sum(1 for i in ids if i in (34, 35, 36, 195, 196))
            self.assertTrue(surlar > 40 if sv >= 3 else surlar == 0, (sv, k, surlar))

    def test_ordu_seviyeyle_guclenir(self):
        for k in bot_koy.KISILIK:
            g = [guc(self.koyler[(sv, k)][0]) for sv in (3, 14, 30, 60)]
            self.assertEqual(g, sorted(g), k)
            self.assertGreater(g[-1], 4 * g[0], k)
            birimler = {int(e[0]) for e in self.koyler[(60, k)][0] if ESYA[int(e[0])]["type"] == "u"}
            self.assertTrue(birimler & KRALIYET, (k, birimler))  # 60. seviyede 5. kademe birim
            dusuk = {int(e[0]) for e in self.koyler[(3, k)][0] if ESYA[int(e[0])]["type"] == "u"}
            self.assertFalse(dusuk & KRALIYET, k)

    def test_elli_koy_birbirinden_farkli(self):
        desenler = set()
        for i in range(50):
            k = list(bot_koy.KISILIK)[i % 4]
            items, _ = bot_koy.koy_kur(3 + int(i * 1.15), k, str(uuid.UUID(int=i + 1)), 0)
            desenler.add(frozenset((int(e[0]), int(e[1]), int(e[2])) for e in items
                                   if ESYA[int(e[0])]["type"] == "b"))
        self.assertEqual(len(desenler), 50)
        self.assertEqual({v["duzen"] for v in bot_koy.KISILIK.values()}, {"kale", "carsi", "ordugah", "ciftlik"})

    def test_koyler_farkli_yonlere_bakar(self):
        """Kapı (Sur Kapısı) belediyeye göre dört yönden birinde; köyler aynı yöne dizilmez."""
        yonler = set()
        for i in range(24):
            items, _ = bot_koy.koy_kur(30, list(bot_koy.KISILIK)[i % 4], "yon-%d" % i, 0)
            bel = next(e for e in items if int(e[0]) in (26, 139, 140, 141))
            kapi = next(e for e in items if int(e[0]) == 37)
            dx, dy = int(kapi[1]) - int(bel[1]), int(kapi[2]) - int(bel[2])
            yonler.add(("x" if abs(dx) > abs(dy) else "y", (dx if abs(dx) > abs(dy) else dy) > 0))
        self.assertGreaterEqual(len(yonler), 3, yonler)

    def test_ordu_kalabaligi_seviyeyle_artar(self):
        """Plan §3.1: ordu 8 + seviye (en çok 60), kişilik oranıyla."""
        for k in bot_koy.KISILIK:
            say = [sum(1 for e in self.koyler[(sv, k)][0] if ESYA[int(e[0])]["type"] == "u") for sv in (3, 30, 60)]
            self.assertLess(say[0], say[1], k)
            self.assertLess(say[1], say[2], k)
            self.assertGreaterEqual(say[2], 3 * say[0], k)

    def test_ayni_tohum_ayni_koy(self):
        self.assertEqual(bot_koy.koy_kur(20, "tuccar", "abc", 5), bot_koy.koy_kur(20, "tuccar", "abc", 5))


class YenidenKur(unittest.TestCase):
    def kayit(self, **pi):
        return {"playerInfo": dict({"pid": "p1", "name": "Balrog", "bot": True, "bot_kisi": "agresif"}, **pi),
                "maps": [{"level": 25, "coins": 777, "items": [[512, 41, 41, 0, 0, 0, [], {}]], "expansions": [13]}],
                "privateState": {"attacksReceived": [{"time": 5}]}}

    def test_eski_bot_yenilenir_gecmis_kalir(self):
        k = self.kayit()
        self.assertTrue(bot_koy.yeniden_kur(k, 100))
        self.assertEqual((k["playerInfo"]["pid"], k["playerInfo"]["name"], k["maps"][0]["coins"],
                          k["maps"][0]["level"], k["privateState"]["attacksReceived"]),
                         ("p1", "Balrog", 777, 25, [{"time": 5}]))
        self.assertEqual(k["maps"][0]["expansions"], [13, 14, 18, 19])  # 15-29: 40..79
        self.assertGreater(len(k["maps"][0]["items"]), 50)
        self.assertFalse(bot_koy.yeniden_kur(k, 200))  # bir kez

    def test_oyuncu_kaydina_dokunmaz(self):
        k = self.kayit(bot=False)
        self.assertFalse(bot_koy.yeniden_kur(k, 100))
        self.assertEqual(k["maps"][0]["items"], [[512, 41, 41, 0, 0, 0, [], {}]])


if __name__ == "__main__":
    unittest.main()
