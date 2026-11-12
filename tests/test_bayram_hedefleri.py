"""Bayram hedefleri (GEC-07, oyun/bayram_hedefleri.py).

Beklenen değerlerin kaynağı: Diyanet tablosu (oyun/takvim.py RAMAZAN: 2026 Ramazan Bayramı 20 Mart) ve
config/takvim.json (Ramazan Bayramı no 2, 3 gün, setler Firavunlar ve Mısır; Nevruz no 3, 21 Mart, 7 gün); config/tema_setleri.json;
1.4.07 istemcisinin bayt kodu: GoalsManager/_load@64-70 `orders` 0 olan hedefi atlar, params JSON'dur (ids, ammount),
goalComparison `order` farkıyla sıralar; resim config `images`'ında olmalı (MissionPopup/openInfoPopup).
"""

import json
import os
import unittest
from datetime import date, timedelta
from unittest import mock

from ortak import KOK, KomutTesti

from oyun import bayram_hedefleri, config, takvim

RAMAZAN_2026 = date(2026, 3, 20)
RAMAZAN_KIMLIGI = bayram_hedefleri.hedef_kimligi(2, RAMAZAN_2026)


class Takvim(unittest.TestCase):
    def test_bayram_gunu_var_ertesi_gun_yok(self):
        """Kabul kapısı: bayram günü hedef var, bittikten sonraki gün yok."""
        kimlik = RAMAZAN_KIMLIGI
        gunler = {g: [h["id"] for h in bayram_hedefleri.aktif_hedefler(date(2026, 3, g))] for g in (19, 20, 22, 23)}
        self.assertEqual(gunler[19], [])
        self.assertIn(kimlik, gunler[20])
        self.assertIn(kimlik, gunler[22])
        self.assertNotIn(kimlik, gunler[23])

    def test_magazada_setler_kapaliysa_hedef_yok(self):
        """#56 incelemesi: magaza_tema_setleri false ise set eşyaları mağazada yok, hedef tamamlanamazdı.
        True (hepsi açık) ve "takvim" (etkinlikte açık) kiplerinde hedef gelir."""
        sonuc = {}
        for kip in (False, True, "takvim"):
            with mock.patch.object(config, "tema_seti_kipi", lambda kip=kip: kip):
                sonuc[kip] = len(bayram_hedefleri.aktif_hedefler(RAMAZAN_2026))
        self.assertEqual(sonuc, {False: 0, True: 1, "takvim": 1})

    def test_hedef_istemcinin_okuyacagi_bicimde(self):
        with open(os.path.join(KOK, "config", "tema_setleri.json"), encoding="utf-8") as f:
            setler = json.load(f)["setler"]
        with open(os.path.join(KOK, "config", "goals.json"), encoding="utf-8") as f:
            hedefler = json.load(f)
        h = bayram_hedefleri.aktif_hedefler(RAMAZAN_2026)[0]
        self.assertNotEqual(h["orders"], 0)  # 0 olsa istemci atlar
        self.assertLess(h["orders"], min(x["orders"] for x in hedefler if x["orders"]))  # başa gelir
        self.assertEqual(h["types"], "built_id")
        self.assertEqual(h["min_level"], 15)  # KAR-34: etkinlikler 15. seviyeden önce açılmaz
        params = json.loads(h["params"])
        self.assertEqual(sorted(params["ids"]), sorted(set(setler["Firavunlar"]) | set(setler["Mısır"])))
        self.assertEqual(params["ammount"], 1)
        self.assertNotIn(h["id"], {x["id"] for x in hedefler})
        self.assertIn(h["image"], {x["image"] for x in hedefler})  # oyunun kendi hedef resmi
        self.assertIn(h["characters"], {x["characters"] for x in hedefler})
        self.assertIn("22 Mart", h["description"])  # son gün: 20 + 3 − 1

    def test_her_yil_yeni_kimlik(self):
        """Kimlik gerçekleşmeye özgü: geçen yılın ödülü (rewardedMissions) bu yılın hedefini gizlemez."""
        a = bayram_hedefleri.aktif_hedefler(RAMAZAN_2026)[0]["id"]
        b = bayram_hedefleri.aktif_hedefler(date(2027, 3, 9))[0]["id"]  # Diyanet: 2027 Ramazan Bayramı 9 Mart
        self.assertEqual(a, RAMAZAN_KIMLIGI)
        self.assertNotEqual(a, b)

    def test_bir_yila_iki_bayram(self):
        """#56 incelemesi: 2033'te iki Ramazan Bayramı var (takvim.bayramlar, DNT-22); kimlikleri ayrı, ikisi de ödüllenir."""
        iki = takvim.bayramlar(2033, "ramazan")
        self.assertEqual(len(iki), 2)
        kimlikler = [bayram_hedefleri.aktif_hedefler(g)[0]["id"] for g in iki]
        self.assertEqual(len(set(kimlikler)), 2)
        self.assertEqual([bayram_hedefleri.odul(k, g) for k, g in zip(kimlikler, iki)], [500, 500])

    def test_etkinlik_numaralari_kalici_ve_tekrarsiz(self):
        """#56 incelemesi: kimlik takvim.json'daki sıraya değil kalıcı `no`ya bağlı; sıra değişse de kaymaz."""
        etkinlikler = takvim._yukle()["etkinlikler"]
        numaralar = [e.get("no") for e in etkinlikler]
        self.assertTrue(all(isinstance(n, int) and 0 < n < 100 for n in numaralar), numaralar)
        self.assertEqual(len(set(numaralar)), len(numaralar))
        ters = {"her_zaman": [], "etkinlikler": list(reversed(etkinlikler))}
        with mock.patch.object(takvim, "_yukle", lambda: ters):
            self.assertEqual(bayram_hedefleri.aktif_hedefler(RAMAZAN_2026)[0]["id"], RAMAZAN_KIMLIGI)


class IstemciConfigi(unittest.TestCase):
    def test_config_gune_gore_degisir(self):
        """Mağaza kipi "hepsi açık" (True): önbellek anahtarında güne bağlı tek şey bayram hedefleridir."""
        with mock.patch.object(config, "tema_seti_kipi", lambda: True):
            with mock.patch.object(takvim, "bugun", lambda: RAMAZAN_2026):
                bayramda = config.get_client_game_config("tr")
            with mock.patch.object(takvim, "bugun", lambda: date(2026, 3, 25)):
                sonra = config.get_client_game_config("tr")
        kimlik = RAMAZAN_KIMLIGI
        self.assertIn(kimlik, {h["id"] for h in bayramda["goals"]})
        self.assertNotIn(kimlik, {h["id"] for h in sonra["goals"]})  # önbellek eski günü vermez
        self.assertIn("goal_032.jpg", bayramda["images"])

    def test_ingilizce_configde_yok(self):
        """#56 incelemesi: metinler Türkçe; İngilizce config'e Türkçe metin gitmez."""
        with mock.patch.object(takvim, "bugun", lambda: RAMAZAN_2026):
            en = config.get_client_game_config("en")
        self.assertNotIn(RAMAZAN_KIMLIGI, {h["id"] for h in en["goals"]})

    def test_ascii_kipinde_turkce_harf_yok(self):
        with mock.patch.object(takvim, "bugun", lambda: RAMAZAN_2026):
            c = config.get_client_game_config("tr", ascii_mode=True)
        h = next(h for h in c["goals"] if h["id"] == RAMAZAN_KIMLIGI)
        self.assertFalse(set(h["title"] + h["description"]) & set("çÇğĞıİöÖşŞüÜ"), h["title"])


class Odul(KomutTesti):
    def test_odul_bir_kez_ve_yalniz_acilmis_bayramda(self):
        """reward_mission [kasaba, kimlik]; ödül 500 altın (goals.json'daki en yüksek ödül). Kabul kapısı: bir kez.
        Elle yazılmış paketle gelecek yılın ya da süresi çoktan geçmiş bayramın hedefinden altın alınamaz."""
        with mock.patch.object(takvim, "bugun", lambda: RAMAZAN_2026):
            self.komut("reward_mission", 0, RAMAZAN_KIMLIGI)
            self.komut("reward_mission", 0, RAMAZAN_KIMLIGI)
            self.assertEqual(self.harita["coins"], 50000 + 500)
            self.komut("reward_mission", 0, bayram_hedefleri.hedef_kimligi(2, date(2027, 3, 9)))  # gelecek yıl
            self.komut("reward_mission", 0, bayram_hedefleri.hedef_kimligi(2, date(2026, 3, 19)))  # uydurma gün
        with mock.patch.object(takvim, "bugun", lambda: date(2026, 6, 1)):
            self.komut("reward_mission", 0, bayram_hedefleri.hedef_kimligi(3, date(2026, 3, 21)))  # Nevruz, 30 günden eski
        self.assertEqual(self.harita["coins"], 50000 + 500)

    def test_hedef_gonderilmeyen_kipte_odul_yok(self):
        """#56 incelemesi: magaza_tema_setleri false iken hedef gönderilmez; elle yazılmış paket de ödül almaz."""
        with mock.patch.object(takvim, "bugun", lambda: RAMAZAN_2026), \
                mock.patch.object(config, "tema_seti_kipi", lambda: False):
            self.komut("reward_mission", 0, RAMAZAN_KIMLIGI)
        self.assertEqual(self.harita["coins"], 50000)


class TurkBirimleri(unittest.TestCase):
    """ONR-04, sahibinin kararı (11.11.2026, "Milli bayramlarda"): oyunun Türk birimleri (880 Turkish Swordsman,
    881 Axeman, 882 Archer, 885 Horseman; config'te in_store 0) yalnızca milli bayramda (config/takvim.json bayrak:
    true, ör. Cumhuriyet Bayramı 29 Ekim, 2 gün) mağazada açılır; mağaza kipinden bağımsız."""

    def magazada(self, gun, kip=True):
        with mock.patch.object(takvim, "bugun", lambda: gun), mock.patch.object(config, "tema_seti_kipi", lambda: kip):
            c = config.get_client_game_config("tr")
        return {e["id"]: e.get("in_store") for e in c["items"] if e["id"] in ("880", "881", "882", "885")}

    def test_milli_bayramda_acik_baska_gun_kapali(self):
        acik = {i: "1" for i in ("880", "881", "882", "885")}
        self.assertEqual(self.magazada(date(2026, 10, 29)), acik)
        # kip false: bayram hedefi yok, takvim seti yok; önbellek anahtarında güne bağlı tek şey milli bayram
        self.assertEqual(set(self.magazada(date(2026, 11, 11), kip=False).values()), {"0"})
        self.assertEqual(self.magazada(date(2026, 10, 29), kip=False), acik)
        self.assertEqual(self.magazada(date(2026, 4, 23)), acik)
        self.assertEqual(set(self.magazada(date(2026, 11, 11)).values()), {"0"})
        self.assertEqual(set(self.magazada(RAMAZAN_2026).values()), {"0"})  # dini bayram milli bayram değil
        self.assertEqual({e.get("in_store") for e in config.get_game_config()["items"]
                          if e["id"] in config.TURK_BIRIMLERI}, {"0"})  # sunucunun config'i değişmez

    def test_cizimleri_temel_pakette(self):
        """Bayram günü internetsiz oyunda çizim eksik kalmasın (araclar/onindirme_listesi.py öncelik 1 = temel)."""
        from oyun import onindirme
        oncelik = {y: o for y, _, o in onindirme.liste()}
        for ad in ("880_tk_sword", "881_tk_axe", "882_tk_archer", "885_tk_horseman"):
            self.assertLessEqual(oncelik["buildingsprites/%s.swf" % ad], onindirme.PAKETLER["temel"], ad)


class GununSinirliOgesi(unittest.TestCase):
    """Sahibinin isteği (12.11.2026): "SINIRLI, SON 0 GÜN" öğesi ertesi gün gitsin, rastgele başkası gelsin. İstemci
    bayt kodu: ItemButtonLarge/setItem rozeti subcategory_id == Subcat.LIMITED_EDITION (121) olan öğeye koyar, gün
    Base/getLimitedDaysLeft = max(0, ceil((LIMITED_EDITION_EXPIRATION - lastServerTimestamp) / 86400));
    Utils$/getTimeStampFromString "Y-A-G"yi new Date(Y, A - 1, G), yani yerel gece yarısı okur. Config'te tarih
    2012-09-14, 1299 Cash Wonder in_store 1 (sahibinin gördüğü öğe)."""

    def istemci(self, gun, kip="takvim"):
        with mock.patch.object(config, "yerel_bugun", lambda: gun), \
                mock.patch.object(takvim, "bugun", lambda: gun), \
                mock.patch.object(config, "tema_seti_kipi", lambda: kip):
            c = config.get_client_game_config("tr")
        return c, {e["id"] for e in c["items"] if e.get("subcategory_id") == "121" and e.get("in_store") == "1"}

    def kalan_gun(self, bitis, gun, saat):
        """getLimitedDaysLeft'in kendisi, elle: yerel gece yarısı ile o günün saatindeki an arasındaki gün."""
        import math
        from datetime import datetime
        y, a, g = (int(x) for x in bitis.split("-"))
        fark = (datetime(y, a, g) - datetime(gun.year, gun.month, gun.day, saat)).total_seconds()
        return max(0, math.ceil(fark / 86400))

    def test_config_tarihi_gecmiste(self):
        self.assertEqual(config.get_game_config()["globals"]["LIMITED_EDITION_EXPIRATION"], "2012-09-14")

    def test_her_gun_bir_oge_son_bir_gun(self):
        gun = date(2026, 11, 11)  # takvimde etkinlik yok (milli bayram 29 Ekim'de bitti)
        c, acik = self.istemci(gun)
        self.assertEqual(len(acik), 1)
        bitis = c["globals"]["LIMITED_EDITION_EXPIRATION"]
        for saat in (0, 9, 23):
            self.assertEqual(self.kalan_gun(bitis, gun, saat), 1)
        sinirli = {e["id"] for e in config.get_game_config()["items"] if e.get("subcategory_id") == "121"}
        self.assertLessEqual(acik, sinirli)

    def test_ertesi_gun_baskasi_gelir_ve_tekrar_etmez(self):
        gunler = [date(2026, 11, 5) + timedelta(days=i) for i in range(20)]
        ogeler = [self.istemci(g)[1] for g in gunler]
        ogeler = [next(iter(o)) for o in ogeler]
        self.assertEqual(len(set(ogeler)), len(ogeler))  # 20 gün, 20 ayrı öğe
        self.assertEqual(ogeler[3], next(iter(self.istemci(gunler[3])[1])))  # aynı gün hep aynı öğe

    def test_nakit_harikasi_de_doner_sunucu_configi_degismez(self):
        gunler = [date(2026, 11, 5) + timedelta(days=i) for i in range(60)]
        gorulen = [next(iter(self.istemci(g)[1])) for g in gunler]
        self.assertLess(gorulen.count("1299"), 2)  # dünkü öğe (1299) her gün kalmaz
        self.assertEqual(next(e for e in config.get_game_config()["items"] if e["id"] == "1299")["in_store"], "1")

    def test_takvimde_acik_set_kalir_hepsi_acik_kipte_dokunulmaz(self):
        _, acik = self.istemci(RAMAZAN_2026)  # Firavunlar ve Mısır açık (config/takvim.json)
        setler = config.tema_setleri()
        misir = {str(i) for i in setler["Mısır"] + setler["Firavunlar"]}
        self.assertLessEqual(misir & {e["id"] for e in config.get_game_config()["items"]
                                      if e.get("subcategory_id") == "121"}, acik)
        self.assertEqual(len(acik - misir), 1)  # ve günün öğesi
        # "hepsi açık" kipinde setler sunucu açılırken açılır (tema_setlerini_ac); günlük döngü hiçbirini kapatmaz
        gunler = [date(2026, 11, 5) + timedelta(days=i) for i in range(3)]
        for g in gunler:
            self.assertIn("1299", self.istemci(g, kip=True)[1])


if __name__ == "__main__":
    unittest.main()
