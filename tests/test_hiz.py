"""Oyun hızı seçici (ONR-01, KAR-21; oyun/hiz.py).

Beklenen değerlerin kaynağı: oyun/zaman.py'nin kuralı (süreler ölçeğe bölünür; ortam değişkeni TIME_SCALE ayar
dosyasından önce gelir; sayfadan seçilen hız depoda izlenmeyen ayarlar.yerel.json'a yazılır, ayarlar.json'a sunucu
yazmaz: #59 incelemesi), config.SURE_ALANLARI (training_time 1.4.07'nin eğitim kuyruğu; ONR-01 tanımı), config'te
öğe 880'in training_time'ı 510 sn; hile paneliyle aynı koruma (yalnızca 127.0.0.1, aynı köken).
"""

import json
import os
import tempfile
import unittest
from unittest import mock

import ortak  # noqa: F401

from oyun import config, yollar, zaman
from oyun import sunucu as server


class HizSecici(unittest.TestCase):
    def setUp(self):
        self.klasor = tempfile.mkdtemp(prefix="se-hiz-")
        self.ana = os.path.join(self.klasor, "ayarlar.json")
        self.ana_metin = '{"magaza_tema_setleri": true, "zaman_olcegi": 2.0}\n'
        with open(self.ana, "w", encoding="utf-8") as f:
            f.write(self.ana_metin)
        self.yol = os.path.join(self.klasor, "ayarlar.yerel.json")
        with open(self.yol, "w", encoding="utf-8") as f:
            json.dump({"baska": 7}, f)
        for yama in (mock.patch.object(yollar, "AYARLAR", self.ana), mock.patch.object(yollar, "AYARLAR_YEREL", self.yol),
                     mock.patch.dict(os.environ, {}, clear=False)):
            yama.start()
            self.addCleanup(yama.stop)
        os.environ.pop("TIME_SCALE", None)
        self.istemci = server.app.test_client()

    def sec(self, olcek, adres="127.0.0.1"):
        return self.istemci.post("/ayar/hiz", json={"olcek": olcek}, environ_base={"REMOTE_ADDR": adres})

    def ayar(self):
        with open(self.yol, encoding="utf-8") as f:
            return json.load(f)

    def tearDown(self):
        with open(self.ana, encoding="utf-8") as f:
            self.assertEqual(f.read(), self.ana_metin)  # depoda izlenen dosyaya hiç yazılmaz

    def test_secim_kaydedilir_ve_sureler_bolunur(self):
        cevap = self.sec(3)
        self.assertEqual((cevap.status_code, cevap.get_json()), (200, {"olcek": 3.0}))
        self.assertEqual(self.ayar(), {"baska": 7, "zaman_olcegi": 3})  # ötekiler kalır
        self.assertEqual(zaman.zaman_olcegi(), 3.0)  # yerel, ayarlar.json'daki 2.0'ın önüne geçer
        from oyun import ayarlar
        self.assertIs(ayarlar.oku()["magaza_tema_setleri"], True)  # ana dosyanın ötekileri okunur
        birim = next(e for e in config.get_client_game_config("tr")["items"] if e["id"] == "880")
        self.assertEqual(float(birim["training_time"]), 510 / 3)
        self.sec(1)
        birim = next(e for e in config.get_client_game_config("tr")["items"] if e["id"] == "880")
        self.assertEqual(float(birim["training_time"]), 510)  # önbellek eski hızı vermez

    def test_gecersiz_hiz_ve_yabanci_adres_reddedilir(self):
        for olcek in (4, "3", True, None, 1000):
            self.assertEqual(self.sec(olcek).status_code, 400, olcek)
        self.assertEqual(self.sec(3, adres="192.168.1.20").status_code, 403)
        cevap = self.istemci.post("/ayar/hiz", json={"olcek": 3}, headers={"Origin": "http://kotu.site"},
                                  environ_base={"REMOTE_ADDR": "127.0.0.1"})
        self.assertIn(cevap.status_code, (400, 403))
        self.assertNotIn("zaman_olcegi", self.ayar())

    def test_ortam_degiskeni_varsa_degismez(self):
        with mock.patch.dict(os.environ, {"TIME_SCALE": "2"}):
            self.assertEqual(self.sec(3).status_code, 409)
        self.assertNotIn("zaman_olcegi", self.ayar())

    def test_bozuk_ayar_dosyasinin_uzerine_yazilmaz(self):
        with open(self.yol, "w", encoding="utf-8") as f:
            f.write("{bozuk")
        cevap = self.sec(3)
        self.assertEqual(cevap.status_code, 500)
        self.assertNotIn(self.yol, cevap.get_data(as_text=True))  # CodeQL: hata ayrıntısı dışarı verilmez
        with open(self.yol, encoding="utf-8") as f:
            self.assertEqual(f.read(), "{bozuk")
        self.assertEqual(zaman.zaman_olcegi(), 2.0)  # bozuk yerel atlanır, ana dosyadaki hız geçer

    def test_sayfada_secici_yalnizca_bu_makinede(self):
        uid = server.new_village()
        self.istemci.post("/", data={"USERID": uid, "GAMEVERSION": "SocialEmpires1.4.07sec_fixed.swf"})
        sayfa = self.istemci.get("/play.html", environ_base={"REMOTE_ADDR": "127.0.0.1"}).get_data(as_text=True)
        self.assertIn('id="hiz"', sayfa)
        for h in zaman.HIZLAR:
            self.assertIn('value="%d"' % h, sayfa)
        with mock.patch.dict(os.environ, {"TIME_SCALE": "2"}):
            sayfa = self.istemci.get("/play.html", environ_base={"REMOTE_ADDR": "127.0.0.1"}).get_data(as_text=True)
        self.assertNotIn('id="hiz"', sayfa)


class OlcekliSure(unittest.TestCase):
    """DNT-25 (denetim EKF-04). Beklenen değerlerin kaynağı 1.4.07 bayt kodu: StaticData/<kurucu> training_time ve
    sm_training_time'ı int yuvasına yazar (küsurat atılır, "0.5" 0 olur), activation'ı parseFloat ile okur;
    IsoElement/canCollect activation > 0 ve collected_at >= activation. Kuralın kendisi: süre en az 1'e iner, tabandaki
    1'den kısa süre ölçeklenmez; üstel gösterim yok."""

    def config(self, olcek):
        with mock.patch.dict(os.environ, {"TIME_SCALE": str(olcek)}):
            return {e["id"]: e for e in config.get_client_game_config("tr")["items"]}

    def test_on_katta_egitim_anlik_olmaz(self):
        taban = {e["id"]: e for e in config.get_game_config()["items"]}
        on = self.config(10)
        egitilen = [i for i, e in taban.items() if float(e.get("training_time") or 0) >= 1]
        self.assertGreater(len(egitilen), 100)
        for i in egitilen:
            self.assertGreaterEqual(int(float(on[i]["training_time"])), 1, i)  # istemcinin int yuvası
        kisa = next(i for i in egitilen if float(taban[i]["training_time"]) < 10)  # 10 katta 1'in altına düşerdi
        self.assertEqual(on[kisa]["training_time"], "1")

    def test_sunucu_istemciyle_ayni_sureyi_bulur(self):
        from oyun.komutlar import egitim_suresi
        for olcek in (3, 10, 0.1):
            c = self.config(olcek)
            with mock.patch.dict(os.environ, {"TIME_SCALE": str(olcek)}):
                for e in config.get_game_config()["items"]:
                    if float(e.get("training_time") or 0) > 0:
                        self.assertEqual(egitim_suresi(e), int(float(c[e["id"]]["training_time"])), (olcek, e["id"]))

    def test_ustel_gosterim_yok_kisa_taban_sure_kalir(self):
        yavas = self.config(0.1)
        for e in yavas.values():
            for alan in config.SURE_ALANLARI:
                self.assertNotIn("e", str(e.get(alan, "")).lower(), (e["id"], alan))
        self.assertEqual(yavas["229"]["activation"], "1728000")  # taban 172800
        taban = next(e for e in config.get_game_config()["items"] if e["id"] == "144")
        self.assertLess(float(taban["activation"]), 1)
        self.assertEqual(float(self.config(10)["144"]["activation"]), float(taban["activation"]))
        self.assertEqual(zaman.metin(zaman.olcekle(32.4, 100)), "1")
        self.assertEqual(zaman.metin(zaman.olcekle(510, 3)), "170")


if __name__ == "__main__":
    unittest.main()
