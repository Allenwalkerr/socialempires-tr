"""'Sen yokken' özeti (ONR-02, KAR-21; oyun/yokken.py).

Beklenen değerlerin kaynağı: sahibinin onayladığı tanım (KAR-21: akınlar, kazanılan/kaybedilen, biten eğitim, Diyar
Haberleri); config'te öğe 880 (Turkish Swordsman) training_time 510 sn, sm_training_time 113000 sn; Ruh Karıştırıcı
1529 (komutlar.RUH_KARISTIRICI); kuyrukta k. birim ts + k × süre'de biter (BuildingQueueData/setData zinciri,
komutlar.pop_queue_unit); akın kaydının biçimi privateState.attacksReceived (gunluk.savaslar, tests/test_gunluk.py);
ceviri/tr.json'da item:880 = "Türk Kılıççısı", item:5 = "Değirmen I"; komut değişmezi D1 (komut kaydı ancak işi
gereği değiştirir). Üretim (sahibinin 11.11.2026 seçimi, inşaat yerine): istemci Base/processMap collected_at =
timestamp − item[4], IsoElement/canCollect collected_at >= activation; config'te 52 Chichen Itza activation 21600,
80 yenilenen altın 10800 (subcat 128, doğal kaynak); globals.COLLECT_VARIABLE_IDS'teki 5 Mill I ve 13 Gold Mine I'da
süre istemcinin Config.COLLECT_MINUTES'i [5, 60, 240, 480] dakika (attrs.cp, ölçeklenmez), cp 0 boşta.
"""

import json
import os
import tempfile
import unittest
from unittest import mock

from ortak import KomutTesti, bos_kayit

from oyun import turkce, yokken, yollar
from oyun import sunucu as server

T0 = 1_793_300_000  # Kasım 2026
TR = turkce.cevirileri_yukle()


def akin(zaman, kazandi, altin, ad):
    alan = "resources" if kazandi else "resources_victim"
    return {"time": zaman, "attacker_id": "bot", "description": {"win": int(kazandi), alan: {"g": altin},
                                                                  "oponent": {"name": ad}}}


def kayit_kuyruklu(bina=1):
    k = bos_kayit()
    k["maps"][0]["items"].append([bina, 5, 5, 0, 0, 0, 0, {"bq": "7"}])
    k["privateState"]["barracksQueues"] = {"7": {"ts": T0, "amount": 3, "unit": 880}}
    return k


class Ozet(unittest.TestCase):
    def setUp(self):
        # süreler config'teki gibi (depodaki ayarlar.json hızı 3 kat; ölçek komutlar.egitim_suresi'nde bölünür)
        from oyun import komutlar
        yama = mock.patch.object(komutlar, "zaman_olcegi", lambda: 1.0)
        yama.start()
        self.addCleanup(yama.stop)

    def test_kisa_ara_ve_ilk_giris_ozet_vermez(self):
        k = kayit_kuyruklu()
        self.assertIsNone(yokken.ozet(k, T0 + 600 + yokken.ESIK - 1, T0 + 600))
        self.assertIsNone(yokken.ozet(k, T0 + 5000, 0))  # son etkinlik yok: ilk kez
        self.assertIsNotNone(yokken.ozet(k, T0 + 600 + yokken.ESIK, T0 + 600))

    def test_biten_egitim_aralikta_sayilir(self):
        # bitişler T0+510, T0+1020, T0+1530; aralık (T0+600, T0+2000] → 2 birim
        o = yokken.ozet(kayit_kuyruklu(), T0 + 2000, T0 + 600, ceviriler=TR)
        self.assertEqual(o["egitim"], [{"ad": "Türk Kılıççısı", "adet": 2, "resim": "880_tk_sword"}])
        self.assertEqual(o["sure"], "23 dakika")

    def test_ruh_karistiricida_sure_uzun(self):
        """Aynı birim Ruh Karıştırıcı'da sm_training_time (113000 sn) ile eğitilir: bu aralıkta biten yok."""
        self.assertEqual(yokken.biten_egitimler(kayit_kuyruklu(1529), T0 + 600, T0 + 2000), {})
        self.assertEqual(yokken.biten_egitimler(kayit_kuyruklu(1529), T0, T0 + 113000), {880: 1})

    def uretim_kaydi(self):
        k = bos_kayit()
        k["maps"][0]["items"] = [
            [5, 1, 1, 0, T0, 0, [], {"cp": 2}],  # 3600 sn: T0+3600, aralıkta
            [5, 2, 2, 0, T0 - 10000, 0, [], {"cp": 4}],  # 28800 sn: T0+18800, aralıkta (ölçeklenseydi önce)
            [5, 3, 3, 0, T0 - 10000, 0, [], {"cp": 0}],  # boşta (config süresi 21600 sayılsaydı T0+11600, aralıkta)
            [5, 4, 4, 0, T0 - 5000, 0, [], {"cp": 2}],  # T0-1400: zaten hazırdı
            [13, 5, 5, 0, T0, 0, [], {"cp": 1}],  # 300 sn: T0+300, aralıktan önce
            [52, 6, 6, 0, T0, 0],  # 21600 sn: T0+21600, aralıktan sonra
            [80, 7, 7, 0, T0, 0],  # doğal kaynak: sayılmaz
        ]
        return k

    def test_uretimi_hazir_binalar(self):
        k = self.uretim_kaydi()
        self.assertEqual(yokken.hazir_uretimler(k, T0 + 600, T0 + 20000), {5: 2})
        from oyun import komutlar
        with mock.patch.object(komutlar, "zaman_olcegi", lambda: 3.0):  # 21600 / 3 = 7200: T0+7200, aralıkta
            self.assertEqual(yokken.hazir_uretimler(k, T0 + 600, T0 + 20000), {5: 2, 52: 1})
        o = yokken.ozet(k, T0 + 20000, T0 + 600, ceviriler=TR)
        self.assertEqual(o["uretim"], [{"ad": "Değirmen I", "adet": 2, "resim": "molino1"}])

    def test_akinlar_kazanilan_ve_kaybedilen(self):
        k = bos_kayit()
        k["privateState"]["attacksReceived"] = [
            akin(T0 + 100, True, 999, "Eski"),  # aralıktan önce: sayılmaz
            akin(T0 + 1000, True, 700, "Tardu"),
            akin(T0 + 1500, False, 90, "Modu Han"),
            akin(T0 + 1600, True, 50, "Bumin"),
        ]
        o = yokken.ozet(k, T0 + 2000, T0 + 600)
        self.assertEqual((o["akin"], o["puskurtulen"], o["kayip"], o["savunma_odulu"]), (3, 1, 750, 90))
        self.assertEqual([a["rakip"] for a in o["akinlar"]], ["Bumin", "Modu Han", "Tardu"])  # yeniden eskiye
        self.assertEqual([a["zafer"] for a in o["akinlar"]], [False, True, False])

    def test_haberler_aralikta_ve_sinirli(self):
        olaylar = [{"zaman": T0 + 100, "metin": "eski"}] + [{"zaman": T0 + 700 + i, "metin": "h%d" % i}
                                                             for i in range(12)]
        o = yokken.ozet(bos_kayit(), T0 + 2000, T0 + 600, olaylar)
        self.assertEqual([h["metin"] for h in o["haberler"]], ["h%d" % i for i in range(11, 3, -1)])
        self.assertEqual(len(o["haberler"]), yokken.EN_COK_HABER)

    def test_bir_sey_olmadiysa_ozet_yok(self):
        self.assertIsNone(yokken.ozet(bos_kayit(), T0 + 5000, T0))


class SonEtkinlik(unittest.TestCase):
    def setUp(self):
        self.klasor = tempfile.mkdtemp(prefix="se-yokken-")
        for yama in (mock.patch.object(yollar, "SAVES_DIR", self.klasor), mock.patch.object(yokken, "_bellek", None),
                     mock.patch.object(yokken, "_yazilan", {})):
            yama.start()
            self.addCleanup(yama.stop)
        self.dosya = os.path.join(self.klasor, yokken.DOSYA_ADI)

    def oku(self):
        with open(self.dosya, encoding="utf-8") as f:
            return json.load(f)

    def test_dosyaya_yazilir_ve_seyrek_yazilir(self):
        yokken.etkinlik_kaydet("a", T0)
        self.assertEqual(self.oku(), {"a": T0})
        yokken.etkinlik_kaydet("a", T0 + yokken.YAZMA_ARALIGI - 1)
        self.assertEqual(self.oku(), {"a": T0})  # bir dakikadan kısa: diske yazılmaz
        self.assertEqual(yokken.son_etkinlik("a"), T0 + yokken.YAZMA_ARALIGI - 1)  # bellekte güncel
        yokken.etkinlik_kaydet("a", T0 + yokken.YAZMA_ARALIGI)
        self.assertEqual(self.oku(), {"a": T0 + yokken.YAZMA_ARALIGI})
        yokken._bellek = None  # sunucu yeniden başladı
        self.assertEqual(yokken.son_etkinlik("a"), T0 + yokken.YAZMA_ARALIGI)
        self.assertEqual(yokken.son_etkinlik("yok"), 0)

    def test_bozuk_dosya_oyunu_durdurmaz(self):
        with open(self.dosya, "w", encoding="utf-8") as f:
            f.write("{bozuk")
        self.assertEqual(yokken.son_etkinlik("a"), 0)


class Komut(KomutTesti):
    def test_komut_zamani_kaydin_disinda(self):
        """Her komut paketi son etkinliği kaydeder; kayıt değişmez (D1: başarısız komut kaydı değiştirmez)."""
        once = json.dumps(self.kayit, sort_keys=True)
        with mock.patch.object(yokken, "etkinlik_kaydet") as kaydet, \
                mock.patch.object(self.komutlar, "timestamp_now", lambda: T0):
            self.komutlar.command("test", {"commands": [{"cmd": "olmayan_komut", "args": []}]})
        kaydet.assert_called_once_with("test", T0)
        self.assertEqual(json.dumps(self.kayit, sort_keys=True), once)


class Sayfa(unittest.TestCase):
    def test_sayfada_ozet_gorunur(self):
        uid = server.new_village()
        istemci = server.app.test_client()
        istemci.post("/", data={"USERID": uid, "GAMEVERSION": "SocialEmpires1.4.07sec_fixed.swf"})
        kayit = server.kayit_oturumu(uid)
        simdi = server.timestamp_now()
        kayit["privateState"]["attacksReceived"] = [akin(simdi - 600, False, 40, "Tardu")]
        kayit["maps"][0]["items"].append([5, 30, 30, 0, simdi - 3700, 0, [], {"cp": 2}])
        with mock.patch.object(yokken, "son_etkinlik", lambda u: simdi - 7200):
            sayfa = istemci.get("/play.html").get_data(as_text=True)
        self.assertIn("Sen yokken (2 saat)", sayfa)
        self.assertIn("Tardu: püskürtüldü, +40 altın", sayfa)
        self.assertIn("Üretimi hazır: 1 Değirmen I", sayfa)
        self.assertIn("buildingthumbs/molino1.jpg", sayfa)
        with mock.patch.object(yokken, "son_etkinlik", lambda u: simdi - 60):
            self.assertNotIn("Sen yokken", istemci.get("/play.html").get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
