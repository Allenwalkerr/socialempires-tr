"""Seviye ile XP arasındaki çeviri: sunucunun her yolu istemcinin eşik okumasını kullanır (OYN-14).

Beklenen değerin kaynağı istemcinin (SocialEmpires1.4.07sec_fixed.swf) bayt kodudur, `araclar/abc_okur.py` ile
okundu (5 Kasım 2026):

  - PlayerStatus/checkForLevelUp: `iLevel < arLevelList.length && iExperience >=
    parseInt(arLevelList[iLevel].exp_required)` ise `iLevel += 1`, `uiExpMin = uiExpMax`,
    `uiExpMax = parseInt(arLevelList[iLevel].exp_required)`, sonra `addCommand(rt_level_up, [iLevel])`.
  - PlayerStatus/Init: `iLevel >= arLevelList.length` ise `iLevel = length - 1`;
    `uiExpMin = arLevelList[iLevel - 1].exp_required`, `uiExpMax = arLevelList[iLevel].exp_required`.

Yani `levels[i].exp_required`, (i+1). seviyenin eşiğidir. Eşik sayıları oyun config'inden
(config/game_config_20120826.json `levels`: 0, 29, 60, 100, ...; 100 seviye) gelir.
"""

import unittest

from ortak import KomutTesti, KOK  # noqa: F401

from oyun import config
from oyun import sunucu as server
from oyun.kayit import _seviyeyi_duzelt

ESIK = [int(s["exp_required"]) for s in config.get_game_config()["levels"]]
ESIK_ODUL = [(s["reward_type"], int(s["reward_amount"])) for s in config.get_game_config()["levels"]]


def istemci_seviyesi(xp, seviye=1):
    """İstemcinin kuralı, yukarıdaki iki yöntemden aktarıldı (uygulamanın kodu değil)."""
    while seviye < len(ESIK) and xp >= ESIK[seviye]:
        seviye += 1
    return min(seviye, len(ESIK) - 1)


class EsikOkumasi(unittest.TestCase):
    def test_config_esikleri(self):
        # config/game_config_20120826.json levels[0..3] ve uzunluk
        self.assertEqual(ESIK[:4], [0, 29, 60, 100])
        self.assertEqual(len(ESIK), 100)
        self.assertEqual(config.en_yuksek_seviye(), 99)  # PlayerStatus/Init: length - 1

    def test_xpden_seviye_istemciyle_ayni(self):
        for xp in sorted({x for e in ESIK for x in (e - 1, e, e + 1) if x >= 0} | {10 ** 12}):
            self.assertEqual(config.get_level_from_xp(xp), istemci_seviyesi(xp), xp)

    def test_seviyenin_alt_esigi(self):
        """get_xp_from_level(L): istemcinin L. seviyede saydığı en küçük XP."""
        self.assertEqual([config.get_xp_from_level(s) for s in (1, 2, 3, 4)], [0, 29, 60, 100])
        for s in range(2, config.en_yuksek_seviye() + 1):
            alt = config.get_xp_from_level(s)
            self.assertEqual((istemci_seviyesi(alt), istemci_seviyesi(alt - 1)), (s, s - 1), s)

    def test_xp_cubugu_istemcinin_araligi(self):
        """Oyun sayfasındaki XP çubuğu istemcininkiyle aynı aralığı çizer (uiExpMin, uiExpMax)."""
        # oran: şablonun önceki formülü (seviye içindeki ilerleme %, en az 3, en çok 100); OYN-12'den beri sunucuda
        self.assertEqual(server._xp_araligi({"level": 2, "xp": 40}),
                         {"simdi": 40, "bas": 29, "son": 60, "oran": (40 - 29) / (60 - 29) * 100})
        self.assertEqual(server._xp_araligi({"level": 99, "xp": 0}),
                         {"simdi": 0, "bas": ESIK[98], "son": ESIK[99], "oran": 3})
        self.assertEqual(server._xp_araligi({"level": 500, "xp": 0})["bas"], ESIK[98])  # Init: length - 1


class BaslikYenilenir(unittest.TestCase):
    """OYN-12: oyun sayfasının başlığı (seviye, XP, rütbe) yalnızca sayfa açılırken yazılıyordu; oyunda seviye
    atlayınca eski kalıyordu. /oyuncu/baslik kaydın şimdiki hâlini verir, oyun.js onu yoklar."""

    def test_seviye_atlayinca_uc_yeni_degeri_verir(self):
        import os
        from ortak import KOK
        uid = server.new_village()
        istemci = server.app.test_client()
        self.assertEqual(istemci.get("/oyuncu/baslik").status_code, 404)  # oturum yok
        istemci.post("/", data={"USERID": uid, "GAMEVERSION": "SocialEmpires1.4.07sec_fixed.swf"})
        sayfa = istemci.get("/play.html").get_data(as_text=True)
        harita = server.kayit_oturumu(uid)["maps"][0]
        harita["level"], harita["xp"] = 2, 40  # oyunda seviye atlandı (rt_level_up)
        v = istemci.get("/oyuncu/baslik").get_json()
        self.assertEqual(v["seviye"], 2)
        self.assertEqual(v["xp"], {"simdi": 40, "bas": 29, "son": 60, "oran": (40 - 29) / (60 - 29) * 100})
        self.assertEqual(v["rutbe"], server.rutbe(2))
        # oyun.js'in güncellediği öğeler sayfada var
        with open(os.path.join(KOK, "templates", "js", "oyun.js"), encoding="utf-8") as f:
            js = f.read()
        for kimlik in ("baslik-seviye", "baslik-xp-simdi", "baslik-xp-son", "baslik-xp", "baslik-rutbe"):
            self.assertIn('id="%s"' % kimlik, sayfa)
            self.assertIn('getElementById("%s")' % kimlik, js)
        self.assertIn('fetch("/oyuncu/baslik"', js)
        # #65 incelemesi: oyun modundan çıkınca ve sekme öne gelince (panelleriTazele) başlık da hemen yenilenir;
        # yalnızca 30 sn'lik aralıkla olsaydı tam ekranda atlanan seviye bir süre eski görünürdü
        import re
        tazele = re.search(r"function panelleriTazele\(\) \{([^}]*)\}", js).group(1)
        self.assertIn("baslikYenile()", tazele)


class RtLevelUp(KomutTesti):
    def test_esikteki_atlama_yeniden_acilista_seviye_kaydirmaz(self):
        """İstemci 29 XP'de 2. seviyeye geçip rt_level_up [2] gönderir; kayıt yeniden açılınca hâlâ 2. seviye."""
        self.harita.update(level=1, xp=29)
        self.komut("rt_level_up", 2)
        self.assertEqual((self.harita["level"], self.harita["xp"]), (2, 29))
        _seviyeyi_duzelt(self.kayit)
        self.assertEqual(self.harita["level"], 2)

    def test_xp_alt_esige_cekilir(self):
        self.harita.update(level=1, xp=0)
        self.komut("rt_level_up", 3)
        self.assertEqual((self.harita["level"], self.harita["xp"]), (3, 60))
        _seviyeyi_duzelt(self.kayit)
        self.assertEqual(self.harita["level"], 3)

    def test_seviye_odulu_kayda_yazilir(self):
        """SNK-01 (bağımsız denetim). İstemci PopupLevel/<kurucu>: arLevelList[iLevel - 1] ödülünü
        Player.adjustStatByType(reward_amount, reward_type) ile kendisi ekler, komut göndermez. Config levels[1] =
        50 odun (w), levels[2] = 50 yemek (f), levels[3] = 400 odun, levels[4] = nakit (c)."""
        self.assertEqual([(ESIK_ODUL[i]) for i in (1, 2, 3)], [("w", 50), ("f", 50), ("w", 400)])
        self.harita.update(level=1, xp=29)
        odun, yemek = self.harita["wood"], self.harita["food"]
        self.komut("rt_level_up", 2)
        self.assertEqual((self.harita["wood"], self.harita["food"]), (odun + 50, yemek))
        self.komut("rt_level_up", 2)  # aynı komut yeniden: ödül bir kez
        self.assertEqual(self.harita["wood"], odun + 50)
        self.komut("rt_level_up", 4)  # 2 → 4: 3. ve 4. seviyenin ödülleri
        self.assertEqual((self.harita["wood"], self.harita["food"]), (odun + 450, yemek + 50))
        nakit = self.cash
        self.komut("rt_level_up", 5)
        self.assertEqual(self.cash, nakit + ESIK_ODUL[4][1])
        self.assertEqual(ESIK_ODUL[4][0], "c")

    def test_odul_baska_yol_seviyeyi_yukseltse_de_bir_kez(self):
        """#45 incelemesi: rt_publish_score eşiği geçirip seviyeyi önce yükseltirse ödül kaybolmamalı; seviye
        düşüp yeniden çıkınca ödül yinelenmemeli. Ödüller config levels[1..3]: 50 odun, 50 yemek, 400 odun."""
        self.harita.update(level=1, xp=0)
        odun, yemek = self.harita["wood"], self.harita["food"]
        self.komut("rt_publish_score", 60)  # 60 XP: istemcide 3. seviye; seviye sunucuda 3 olur
        self.assertEqual(self.harita["level"], 3)
        self.komut("rt_level_up", 2)
        self.komut("rt_level_up", 3)
        self.assertEqual((self.harita["wood"], self.harita["food"]), (odun + 50, yemek + 50))
        self.komut("rt_level_up", 1)
        self.komut("rt_level_up", 4)
        self.assertEqual((self.harita["wood"], self.harita["food"]), (odun + 450, yemek + 50))

    def test_xp_bildirimi_seviyeyi_dusurmez(self):
        """KYT-05 ile aynı kural: istemci seviyeyi yalnızca yukarı taşır (PlayerStatus/checkForLevelUp)."""
        self.harita.update(level=53, xp=69467)
        self.komut("rt_publish_score", 69467)
        self.assertEqual(self.harita["level"], 53)


class HilePaneliSeviye(unittest.TestCase):
    def uygula(self, islem):
        istemci = server.app.test_client()
        istemci.post("/", data={"USERID": server.new_village(), "GAMEVERSION": "SocialEmpires1.4.07sec_fixed.swf"})
        return [istemci.post("/cheat/uygula", json=i).get_json()["ozet"] for i in islem]

    def test_seviye_ekleme_istemcinin_esiginde(self):
        once, sonra = self.uygula([{"islem": "kaynak", "tur": "wood", "miktar": 1}, {"islem": "seviye", "delta": 1}])
        self.assertEqual(sonra["seviye"], once["seviye"] + 1)
        self.assertEqual(sonra["xp"], ESIK[sonra["seviye"] - 1])
        self.assertEqual(istemci_seviyesi(sonra["xp"]), sonra["seviye"])

    def test_en_yuksek_seviye(self):
        (ozet,) = self.uygula([{"islem": "max_seviye"}])
        self.assertEqual((ozet["seviye"], ozet["xp"]), (99, ESIK[98]))
        self.assertEqual(istemci_seviyesi(ozet["xp"]), 99)


if __name__ == "__main__":
    unittest.main()
