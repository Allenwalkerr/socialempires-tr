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
    """x = ((g - 1) mod 5)·20, y = ((g - 1) div 5)·20 (Arthur30 dosyası: [18, 13] → x 40..59, y 40..79; test aşağıda)."""
    sonuc = set()
    for g in genislemeler:
        satir, sutun = divmod(g - 1, 5)
        sonuc |= {(sutun * 20 + i, satir * 20 + j) for i in range(20) for j in range(20)}
    return sonuc


def buyuk_karolar(genislemeler):
    return {((g - 1) % 5, (g - 1) // 5) for g in genislemeler}


def bagli_mi(bks):
    bks = set(bks)
    gorulen, yigin = set(), [next(iter(bks))]
    while yigin:
        c, r = yigin.pop()
        if (c, r) in gorulen:
            continue
        gorulen.add((c, r))
        yigin += [(c + dc, r + dr) for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (c + dc, r + dr) in bks]
    return gorulen == bks


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
        # Kişilik köyün ilk iki şeridini belirler: dört kişiliğin başı birbirinden farklı (plan §3.1)
        self.assertEqual(len({tuple(v[:2]) for v in bot_koy.SERIT_SIRASI.values()}), 4)

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

    def test_serit_sirasi_kisiligin_basi_sabit_kalani_karisir(self):
        import random
        for k, asil in bot_koy.SERIT_SIRASI.items():
            siralar = [bot_koy.serit_sirasi(k, random.Random("t%d" % i)) for i in range(20)]
            self.assertTrue(all(s[:2] == asil[:2] and sorted(s) == sorted(asil) for s in siralar), k)
            self.assertGreater(len({tuple(s[2:]) for s in siralar}), 1, k)

    def test_ayni_tohum_ayni_koy(self):
        self.assertEqual(bot_koy.koy_kur(20, "tuccar", "abc", 5), bot_koy.koy_kur(20, "tuccar", "abc", 5))


class ArthurDuzeni(unittest.TestCase):
    """Sahibi (12.11.2026): 'Arthur'un köyüne bak, hakikaten güzel; birebir yapma'. Oyunun kendi Arthur köyleri
    (villages/Arthur30, 31, 32.json; FriendButton/mouseUsed oyuncu seviyesi <= 10 → 30, <= 20 → 31, sonra 32):
    30 iki büyük karoluk dikdörtgen, 31 L, 32 40×40; sur köyün kenarında; köşelerde kule; askerler küme küme."""

    def test_genisleme_eksenleri_arthur30_dosyasindan(self):
        import json
        import os
        with open(os.path.join(KOK, "villages", "Arthur30.json"), encoding="utf-8") as f:
            harita = json.load(f)["maps"][0]
        alan = acik_karolar(harita["expansions"])
        self.assertEqual(sorted(harita["expansions"]), [13, 18])
        for e in harita["items"]:
            self.assertLessEqual(karolar(e), alan, e)
        self.assertEqual(bot_koy.karolari([13, 18]), alan)

    def test_koy_seviyeyle_asama_asama_buyur(self):
        beklenen = {1: 1, 9: 1, 10: 2, 19: 2, 20: 3, 29: 3, 30: 4, 60: 4}
        for sv, adet in beklenen.items():
            for i in range(6):
                _, acik = bot_koy.koy_kur(sv, list(bot_koy.KISILIK)[i % 4], "b%d-%d" % (sv, i), 0)
                bks = buyuk_karolar(acik)
                self.assertEqual(len(bks), adet, (sv, acik))
                self.assertIn((2, 2), bks)
                self.assertTrue(bagli_mi(bks), acik)
                if adet == 3:  # L: hepsi aynı satırda ya da sütunda değil
                    self.assertTrue(len({c for c, _ in bks}) == 2 and len({r for _, r in bks}) == 2, acik)
                if adet == 4:  # 2×2
                    self.assertTrue(len({c for c, _ in bks}) == 2 and len({r for _, r in bks}) == 2, acik)

    def test_sur_kenarda_ve_koselerde_kule(self):
        for sv in (5, 15, 25, 45):
            for k in bot_koy.KISILIK:
                items, acik = bot_koy.koy_kur(sv, k, "s%d%s" % (sv, k), 0)
                alan = acik_karolar(acik)
                kenar = {(x, y) for x, y in alan
                         if any((x + dx, y + dy) not in alan for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
                savunma = set()
                kule = set()
                for e in items:
                    if ESYA[int(e[0])].get("subcategory_id") in ("21", "22"):
                        savunma |= karolar(e)
                    if ESYA[int(e[0])].get("subcategory_id") == "21":
                        kule |= karolar(e)
                self.assertGreaterEqual(len(kenar & savunma) / len(kenar), 0.9, (sv, k))  # yalnızca kapı boşlukları
                koseler = {(x, y) for x, y in kenar
                           if sum((x + dx, y + dy) not in alan for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))) >= 2}
                self.assertLessEqual(koseler, kule, (sv, k))

    def test_askerler_kume_kume(self):
        for sv in (10, 30, 55):
            for k in bot_koy.KISILIK:
                items, _ = bot_koy.koy_kur(sv, k, "a%d%s" % (sv, k), 0)
                birimler = {(int(e[1]), int(e[2])) for e in items if ESYA[int(e[0])]["type"] == "u"}
                # Ya mangada (8 komşudan biri asker) ya geçitte (sırada iki karo ötesi asker)
                yalniz = [t for t in birimler
                          if not any((t[0] + dx, t[1] + dy) in birimler for dx in (-2, -1, 0, 1, 2)
                                     for dy in (-2, -1, 0, 1, 2) if (dx or dy) and (abs(dx) < 2 or dy == 0)
                                     and (abs(dy) < 2 or dx == 0))]
                self.assertLessEqual(len(yalniz), len(birimler) * 0.2, (sv, k, len(yalniz), len(birimler)))


class BirimEkle(unittest.TestCase):
    def test_kayittaki_genisleme_icinde_kalir(self):
        """Seviye atlayan bot (20) ama kayıtta yalnızca [13] açık: yeni birim 40..59'da kalır (genişleme kuralı,
        acik_karolar; #81 incelemesi)."""
        import random
        kayit = {"playerInfo": {"bot": True, "bot_kisi": "agresif"},
                 "maps": [{"level": 20, "expansions": [13], "items": []}]}
        rng = random.Random(3)
        for _ in range(25):
            bot_koy.birim_ekle(kayit, 509, 0, rng)
        items = kayit["maps"][0]["items"]
        self.assertEqual(len(items), 25)
        for e in items:
            self.assertIn((e[1], e[2]), acik_karolar([13]), e)


class AskerGecidi(unittest.TestCase):
    """DNT-60 (internet taraması: 55. seviye oyuncu köyünde avluda sıralı ordu; sahibi 'bir kısmını yap'): 15. seviyeden
    ordusu en az 12 olan köyde askerlerin bir bölümü 4 sütunlu, bir karo aralı düzgün sıralar hâlinde."""

    def test_gecit_dort_sutun_bir_karo_ara(self):
        for sv in (15, 25, 35, 55):
            for k in bot_koy.KISILIK:
                items, _ = bot_koy.koy_kur(sv, k, "g%d%s" % (sv, k), 0)
                birimler = {(int(e[1]), int(e[2])) for e in items if ESYA[int(e[0])]["type"] == "u"}
                if len(birimler) < 12:
                    continue
                en_iyi = max(sum(1 for i in range(4) for j in range(4) if (x + 2 * i, y + 2 * j) in birimler)
                             for x, y in birimler)
                self.assertGreaterEqual(en_iyi, 8, (sv, k))  # en az iki tam sıra

    def test_on_bes_ten_once_gecit_yok(self):
        for k in bot_koy.KISILIK:
            items, _ = bot_koy.koy_kur(14, k, "y%s" % k, 0)
            birimler = {(int(e[1]), int(e[2])) for e in items if ESYA[int(e[0])]["type"] == "u"}
            self.assertFalse(any(all((x + 2 * i, y) in birimler for i in range(4)) and
                                 all((x + 2 * i, y + 2) in birimler for i in range(4)) and
                                 not any((x + 1 + 2 * i, y) in birimler for i in range(3)) for x, y in birimler), k)


class IcSur(unittest.TestCase):
    """DNT-60 (internet taraması: oyuncu köylerinde iç surlarla bölünmüş avlular): 3 ve daha çok büyük karolu köyde
    bitişik büyük karoların arasında sur var, ortasında geçilecek kapı boşluğu bırakılır."""

    def test_bitisik_karolar_arasinda_kapili_sur(self):
        for sv in (25, 35, 55):
            for k in bot_koy.KISILIK:
                items, acik = bot_koy.koy_kur(sv, k, "i%d%s" % (sv, k), 0)
                bks = buyuk_karolar(acik)
                surlar = set()
                for e in items:
                    if ESYA[int(e[0])].get("subcategory_id") in ("21", "22"):
                        surlar |= karolar(e)
                for c, r in bks:
                    if (c + 1, r) in bks:
                        cizgi = [((c + 1) * 20, r * 20 + j) for j in range(1, 19)]
                    elif (c, r + 1) in bks:
                        cizgi = [(c * 20 + j, (r + 1) * 20) for j in range(1, 19)]
                    else:
                        continue
                    dolu = sum(t in surlar for t in cizgi)
                    self.assertGreaterEqual(dolu, 10, (sv, k, c, r))
                    self.assertLess(dolu, len(cizgi), (sv, k, c, r))  # kapı boşluğu
        _, acik = bot_koy.koy_kur(12, "dengeli", "iki", 0)
        self.assertEqual(len(acik), 2)  # iki karoluk köyde iç sur yok (Arthur30 gibi tek avlu)


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
        acik = k["maps"][0]["expansions"]  # 20-29: üç büyük karo, L (Arthur31 gibi)
        self.assertEqual(len(acik), 3)
        self.assertIn(13, acik)
        self.assertGreater(len(k["maps"][0]["items"]), 50)
        self.assertFalse(bot_koy.yeniden_kur(k, 200))  # bir kez

    def test_oyuncu_kaydina_dokunmaz(self):
        k = self.kayit(bot=False)
        self.assertFalse(bot_koy.yeniden_kur(k, 100))
        self.assertEqual(k["maps"][0]["items"], [[512, 41, 41, 0, 0, 0, [], {}]])


if __name__ == "__main__":
    unittest.main()
