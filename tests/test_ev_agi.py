"""Ev ağı kipinin parolası (oyun/ev_agi.py).

Beklenen davranışın kaynağı sahibinin kararı KAR-17 (11.11.2026: "parola istensin") ve bağımsız denetimin
DGV-01/SNK-05 bulgusu (docs/denetim/dagitim-guvenlik.md): ev ağı açıkken ağdaki bir cihaz parolasız girip kaydı
indirip ezebiliyordu. Bu bilgisayar (127.0.0.1) parola sormaz; ev ağı kapalıyken hiçbir şey değişmez.
"""

import json
import os
import stat
import tempfile
import unittest
from unittest import mock

from ortak import KOK  # noqa: F401

from oyun import ev_agi
from oyun import sunucu as server

ADRES = "http://192.168.1.20:5050"
TABLET = {"REMOTE_ADDR": "192.168.1.30"}
KOMUT = "/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires/command.php"


class EvAgiParolasi(unittest.TestCase):
    def setUp(self):
        self.ayar = {"ev_agi": True, "ev_agi_parolasi": "dogru-parola-1"}
        for hedef, deger in ((ev_agi.ayarlar, "oku"),):
            yama = mock.patch.object(hedef, deger, lambda: dict(self.ayar))
            yama.start()
            self.addCleanup(yama.stop)
        ev_agi._yanlislar.clear()
        self.uid = server.new_village()

    def tablet(self):
        return server.app.test_client()

    def get(self, istemci, yol, **kw):
        return istemci.get(yol, base_url=ADRES, environ_base=TABLET, **kw)

    def post(self, istemci, yol, **kw):
        return istemci.post(yol, base_url=ADRES, environ_base=TABLET, **kw)

    def komut(self, istemci):
        return self.post(istemci, KOMUT, data={"USERID": self.uid, "data": "0" * 64 + ';{"commands": []}'})

    def test_girissiz_tablet_hicbir_seye_ulasamaz(self):
        t = self.tablet()
        sayfa = self.get(t, "/", headers={"Accept": "text/html"})
        self.assertEqual((sayfa.status_code, sayfa.headers["Location"]), (302, "/ev-agi-giris"))
        self.assertEqual(self.komut(t).status_code, 401)
        self.assertEqual(self.get(t, "/kayit/indir").status_code, 401)
        self.assertEqual(self.post(t, "/", data={"USERID": self.uid}).status_code, 401)
        self.assertNotIn(self.uid, self.get(t, "/ev-agi-giris").get_data(as_text=True))  # giriş listesi yok
        self.assertEqual(self.get(t, "/css/oyun.css").status_code, 200)  # sayfanın durağan dosyası açık

    def test_dogru_parola_ile_oyun_acilir(self):
        t = self.tablet()
        self.assertEqual(self.post(t, "/ev-agi-giris", data={"parola": "dogru-parola-1"}).status_code, 302)
        self.assertEqual(self.komut(t).status_code, 200)
        self.assertEqual(self.get(t, "/", headers={"Accept": "text/html"}).status_code, 200)

    def test_yanlis_parola_ve_deneme_siniri(self):
        t = self.tablet()
        for _ in range(ev_agi.DENEME_SINIRI):
            self.assertEqual(self.post(t, "/ev-agi-giris", data={"parola": "yanlis"}).status_code, 403)
        # sınır dolunca doğru parola da beklemeden kabul edilmez
        self.assertEqual(self.post(t, "/ev-agi-giris", data={"parola": "dogru-parola-1"}).status_code, 429)
        self.assertEqual(self.komut(t).status_code, 401)

    def test_parola_degisince_eski_giris_gecersiz(self):
        t = self.tablet()
        self.post(t, "/ev-agi-giris", data={"parola": "dogru-parola-1"})
        self.ayar["ev_agi_parolasi"] = "yeni-parola-22"
        self.assertEqual(self.komut(t).status_code, 401)

    def test_bu_bilgisayar_parola_sormaz(self):
        yerel = server.app.test_client()
        cevap = yerel.post(KOMUT, data={"USERID": self.uid, "data": "0" * 64 + ';{"commands": []}'})
        self.assertEqual(cevap.status_code, 200)

    def test_ev_agi_kapaliyken_degisiklik_yok(self):
        self.ayar["ev_agi"] = False
        self.assertEqual(self.komut(self.tablet()).status_code, 200)

    def test_parola_uretilir_ve_yalnizca_sahibine_okunur(self):
        self.ayar.pop("ev_agi_parolasi")
        klasor = tempfile.mkdtemp()
        with mock.patch.object(ev_agi, "DOSYA", os.path.join(klasor, ".ev_agi_parolasi")), \
                mock.patch.object(ev_agi, "_uretilen", None):
            parola = ev_agi.parola()
            self.assertRegex(parola, r"^[a-z2-9]{4}-[a-z2-9]{4}-[a-z2-9]{4}$")
            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(os.stat(ev_agi.DOSYA).st_mode), 0o600)
            with mock.patch.object(ev_agi, "_uretilen", None):
                self.assertEqual(ev_agi.parola(), parola)  # yeniden açılışta aynı parola dosyadan
        self.ayar["ev_agi_parolasi"] = "kisa"  # 8'den kısa ayar yok sayılır
        with mock.patch.object(ev_agi, "_uretilen", "uretilen-parola"):
            self.assertEqual(ev_agi.parola(), "uretilen-parola")


if __name__ == "__main__":
    unittest.main()
