"""Bot yardımı, Ada Ocağı ve viral teklifler (KMT-09, OYN-29; KAR-26, KAR-27, KAR-29).

Beklenen değerlerin kaynağı: 1.4.07 bayt kodu (docs/inceleme/1407-asker-ada.md):
- PopupRecruitment/onFindFriend: ExternalInterface.call("showPopupSEHelpSocialItem", tx, ty, kasaba, bina, si, ad);
  yardım edenler binanın attrs.si'si, istemci en çok 4 sayar (onOpenBuilding@248-250); parseInt(kimlik) 0 ise "Köylü".
- Viral teklif ve Ada'nın boru malzemesi: showPopupSEHelpOffer(no); privateState.viralOffers[no].friends, num_workers
  (config: teklif 2 = 5, teklif 1 = 3).
- CollectGameManager/get active: şimdi > starts_at ve şimdi < starts_at + duration; SpecialDayOfferManager/timeLeft
  int(starts_at + duration - şimdi) > 0 (int32). ImageManager/getUserPhoto: serverUrl + "graph.facebook.com/<id>/picture".
Sahibinin kararları: botlar yardım eder; her yer için günde bir bot; kayan 30 günlük pencere; ada ve ödül çizimleri
temel pakette.
"""

import os
import re
import unittest
from datetime import date, timedelta
from unittest import mock

from ortak import KOK

from oyun import config, istemci, takvim
from oyun import sunucu as server
from oyun.kayit import all_saves_userid, neighbor_session

GUN = date(2026, 11, 12)


def bot_mu(kimlik):
    k = neighbor_session(str(kimlik))
    return bool(k and k["playerInfo"].get("bot"))


class Yardim(unittest.TestCase):
    def setUp(self):
        self.uid = server.new_village()
        self.istemci = server.app.test_client()
        self.istemci.post("/", data={"USERID": self.uid, "GAMEVERSION": "SocialEmpires1.4.07sec_fixed.swf"})
        self.kayit = server.kayit_oturumu(self.uid)
        self.kayit["maps"][0]["items"].append([387, 40, 41, 0, 0, 0, [], {}])
        self.gun = GUN
        yama = mock.patch.object(takvim, "bugun", lambda: self.gun)
        yama.start()
        self.addCleanup(yama.stop)

    def iste(self, **veri):
        return self.istemci.post("/yardim/bot", json=veri)

    def asker(self):
        return self.iste(tur="sosyal", tx=40, ty=41, town=0, id=387)

    def test_asker_toplama_gunde_bir_bot_en_cok_dort(self):
        from oyun import bot_yardim
        si = lambda: self.kayit["maps"][0]["items"][-1][7].get("si", [])  # noqa: E731
        yazilan = []
        for yama in (mock.patch.object(bot_yardim.random, "choice", lambda l: l[0]),  # hep ilk aday: tekrar görünür
                     mock.patch.object(bot_yardim, "save_session", yazilan.append)):
            yama.start()
            self.addCleanup(yama.stop)
        r = self.asker()
        self.assertEqual(yazilan, [self.uid])  # yardım kalıcı
        self.assertEqual((r.status_code, r.get_json()["yardimci"], r.get_json()["gerekli"]), (200, 1, 4))
        self.assertEqual(self.asker().status_code, 409)  # aynı gün ikinci kez yok
        self.assertTrue(self.asker().get_json()["yarin"])
        for i in range(3):
            self.gun += timedelta(days=1)
            self.assertEqual(self.asker().status_code, 200, i)
        self.gun += timedelta(days=1)
        self.assertEqual(self.asker().status_code, 409)  # 4 dolu
        self.assertEqual(len(si()), 4)
        self.assertEqual(len(set(si())), 4)  # aynı bot iki kez yok
        for kimlik in si():
            self.assertTrue(bot_mu(kimlik), kimlik)
            self.assertNotEqual(kimlik[0], "0")  # istemci parseInt'te 0 = Köylü

    def test_aday_botlar(self):
        """Yalnızca botlar; zaten yardım edenler ve parseInt'te 0 sayılacak (0 ile başlayan) kimlikler hariç."""
        from oyun import bot_yardim
        kayitlar = {"0ab": {"playerInfo": {"pid": "0ab", "bot": True}}, "5ab": {"playerInfo": {"pid": "5ab", "bot": True}},
                    "cd": {"playerInfo": {"pid": "cd", "bot": True}}, "oyuncu": {"playerInfo": {"pid": "oyuncu"}}}
        with mock.patch.object(bot_yardim, "all_saves_userid", lambda: list(kayitlar)), \
                mock.patch("oyun.kayit.neighbor_session", kayitlar.get):
            self.assertEqual(sorted(bot_yardim._botlar({"cd"})), ["5ab"])

    def test_pazar_calisan_sayisi_kadar_dost_alir(self):
        """PopupSocialBuilding/onFindFriend @18-70: si.length < arWorkerNames.length iken yardım istenir; işçiler
        config social_items[23].workers 'Butcher,Fishmonger,Greengrocer' (3). Günde bir bot (KAR-29)."""
        from oyun import bot_yardim
        self.kayit["maps"][0]["items"].append([23, 12, 14, 0, 0, 0, [], {}])
        self.assertEqual(bot_yardim._calisan_sayisi(23), 3)
        self.assertEqual(bot_yardim._calisan_sayisi(387), 4)
        self.assertIsNone(bot_yardim._calisan_sayisi(1))  # sosyal olmayan bina (Ev I)
        self.assertEqual(self.iste(tur="sosyal", tx=12, ty=14, town=0, id=23).status_code, 200)
        pazar = next(e for e in self.kayit["maps"][0]["items"] if e[0] == 23)
        self.assertEqual(len(pazar[7]["si"]), 1)
        self.assertEqual(self.iste(tur="sosyal", tx=12, ty=14, town=0, id=23).status_code, 409)  # aynı gün ikinci (KAR-29)

    def test_sosyal_olmayan_ya_da_olmayan_bina_reddedilir(self):
        self.assertEqual(self.iste(tur="sosyal", tx=40, ty=41, town=0, id=234).status_code, 400)
        self.kayit["maps"][0]["items"].append([1, 44, 45, 0, 0, 0, [], {}])  # Ev I: haritada var ama sosyal bina değil
        self.assertEqual(self.iste(tur="sosyal", tx=44, ty=45, town=0, id=1).status_code, 400)
        self.assertEqual(self.iste(tur="sosyal", tx=1, ty=1, town=0, id=387).status_code, 400)
        self.assertEqual(self.iste(tur="sosyal", tx="x", ty=41, town=0, id=387).status_code, 400)
        r = self.istemci.post("/yardim/bot", data='{"tur": "sosyal", "tx": 1e400, "ty": 41, "town": 0, "id": 387}',
                              content_type="application/json")  # JSON 1e400 -> inf; int(inf) OverflowError
        self.assertEqual(r.status_code, 400)
        for govde in ([1], "x"):  # JSON nesnesi olmayan gövde
            self.assertEqual(self.istemci.post("/yardim/bot", json=govde).status_code, 400, govde)
        cikis = server.app.test_client()
        self.assertEqual(cikis.post("/yardim/bot", json={"tur": "teklif", "no": 2}).status_code, 404)  # oturum yok

    def test_teklif_yardimcilari_num_workers_kadar(self):
        for i in range(5):  # teklif 2 (Ada'nın boru malzemesi): num_workers 5
            self.assertEqual(self.iste(tur="teklif", no=2).status_code, 200, i)
            self.gun += timedelta(days=1)
        self.assertEqual(self.iste(tur="teklif", no=2).status_code, 409)
        self.assertEqual(len(self.kayit["privateState"]["viralOffers"]["2"]["friends"]), 5)
        self.assertEqual(self.iste(tur="teklif", no=1).status_code, 200)  # ayrı hedef, ayrı günlük hak
        self.assertEqual(self.iste(tur="teklif", no=99).status_code, 400)

    def test_arkadas_bilgisinde_ad_ve_resim_yonlendirmesi(self):
        from oyun.kayit import fb_friends_str
        arkadaslar = fb_friends_str(self.uid)
        self.assertTrue(all("first_name" in f for f in arkadaslar))  # sabit köyler de (Arthur dışındakiler)
        botlar = [f for f in arkadaslar if bot_mu(f["uid"])]
        self.assertTrue(botlar)
        for f in botlar:
            self.assertEqual(f["first_name"], neighbor_session(f["uid"])["playerInfo"]["name"])
        bot = botlar[0]["uid"]
        r = self.istemci.get(istemci.DINAMIK + "/graph.facebook.com/%s/picture?type=square" % bot)
        self.assertEqual((r.status_code, r.headers["Location"]), (302, neighbor_session(bot)["playerInfo"]["pic"]))
        r = self.istemci.get(istemci.DINAMIK + "/graph.facebook.com/kimse/picture")
        self.assertEqual(r.headers["Location"], "/img/profile/1025.png")
        # Açık yönlendirme yok: tam adres, protokolsüz "//" ve tarayıcıların "//" okuduğu "/\\"; dizge olmayan değer 500 vermez.
        for pic in ("https://kotu.site/x.png", "//kotu.site/x.png", "/\\kotu.site/x.png", 5):
            kotu = {"playerInfo": {"pic": pic}}
            with mock.patch.object(istemci, "neighbor_session", lambda u: kotu):
                r = self.istemci.get(istemci.DINAMIK + "/graph.facebook.com/%s/picture" % bot)
            self.assertEqual((r.status_code, r.headers["Location"]), (302, "/img/profile/1025.png"), pic)


class Pencere(unittest.TestCase):
    def test_ada_ve_teklifler_istemcide_acik_sunucuda_degismez(self):
        simdi = 1_794_500_000
        bas, sure = config.etkinlik_penceresi(simdi)
        self.assertTrue(bas < simdi < bas + sure)  # CollectGameManager/get active
        self.assertTrue(29 * 86400 < bas + sure - simdi <= 30 * 86400)  # pencerede 29-30 gün
        self.assertLess(bas + sure - simdi, 2 ** 31)  # timeLeft convert_i
        self.assertGreater(config.etkinlik_penceresi(simdi + 86400)[0], bas)  # her gün kayar
        c = config.get_client_game_config("tr")
        bugun = config.etkinlik_penceresi()
        self.assertEqual((c["collect_game"]["1"]["starts_at"], c["collect_game"]["1"]["duration"]), bugun)
        for no, t in c["viral_offers"].items():
            self.assertEqual((t["starts_at"], t["duration"]), bugun, no)
        g = config.get_game_config()
        self.assertEqual(g["collect_game"]["1"]["starts_at"], 0)  # sunucunun config'i değişmez
        self.assertEqual({t["active"] for t in c["viral_icons"]} if isinstance(c["viral_icons"], list)
                         else None, {t["active"] for t in g["viral_icons"]} if isinstance(g["viral_icons"], list)
                         else None)  # viral_icons (gerçek para, Facebook) değişmez

    def test_ada_ve_odul_cizimleri_temel_pakette(self):
        from oyun import onindirme
        oncelik = {y: o for y, _, o in onindirme.liste()}
        for ad in ("1530_forgeIsland", "2267_easterDragon", "2269_forgeDragon", "2272_demonDragon",
                   "2324_ivoryDinastyDragon", "2363_nightForgeDragon"):
            self.assertLessEqual(oncelik["buildingsprites/%s.swf" % ad], onindirme.PAKETLER["temel"], ad)


class Sayfa(unittest.TestCase):
    def test_oyunun_cagirdigi_islevler_sayfada(self):
        with open(os.path.join(KOK, "templates", "js", "oyun.js"), encoding="utf-8") as f:
            js = f.read()
        self.assertIn("window.showPopupSEHelpSocialItem = function", js)
        self.assertIn("window.showPopupSEHelpOffer = function", js)
        self.assertIn("forceReloadInfo()", js)
        self.assertIn("id: Number(bina)", js)
        self.assertIn('fetch("/yardim/bot"', js)


if __name__ == "__main__":
    unittest.main()
