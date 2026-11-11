"""Android bildirimleri (ONR-03, KAR-21, KAR-23; oyun/bildirim.py, android_giris, Bildirimler.java).

Beklenen değerlerin kaynağı: sahibinin onayladığı tanım (KAR-21; KAR-23: inşaat yerine üretim hazır); süreler
tests/test_yokken.py ile aynı kaynaktan: config'te 880 training_time 510 sn, ceviri/tr.json item:880 "Türk Kılıççısı",
item:5 "Değirmen I"; 5 Mill I COLLECT_VARIABLE_IDS'te, attrs.cp 2 → istemcinin COLLECT_MINUTES[1] = 60 dakika. Kalkan
privateState.shieldEndTime (pvp_yeni.kalkan_bitisi). Saat Türkiye saatiyle (UTC+3): 1793310000 = 30.10.2026 00:40.
Android: POST_NOTIFICATIONS izni Android 13'te geldi (API 33); Python'un çağırdığı sınıf ve yöntem Java'daki adla aynı.
"""

import json
import os
import re
import unittest
from unittest import mock

from ortak import KOK, bos_kayit
from test_android import GIRIS, modul

from oyun import bildirim, komutlar, turkce, yokken

T0 = 1_793_300_000
TR = turkce.cevirileri_yukle()
JAVA = os.path.join(KOK, "android", "app", "src", "main", "java", "io", "github", "lahmacunveayran",
                    "socialempirestr")


def kayit(degirmenler=(), kuyruk=None, kalkan=0):
    k = bos_kayit()
    k["maps"][0]["items"] = [[5, i, i, 0, ts, 0, [], {"cp": 2}] for i, ts in enumerate(degirmenler)]
    if kuyruk:
        k["maps"][0]["items"].append([1, 9, 9, 0, 0, 0, 0, {"bq": "7"}])
        k["privateState"]["barracksQueues"] = {"7": kuyruk}
    k["privateState"]["shieldEndTime"] = kalkan
    return k


class Yaklasan(unittest.TestCase):
    def setUp(self):
        yama = mock.patch.object(komutlar, "zaman_olcegi", lambda: 1.0)  # depodaki ayarlar.json 3 kat
        yama.start()
        self.addCleanup(yama.stop)

    def test_uc_tur_ayri_zamanlarda(self):
        k = kayit(degirmenler=[T0], kuyruk={"ts": T0, "amount": 3, "unit": 880}, kalkan=T0 + 10000)
        self.assertEqual(bildirim.yaklasan(k, T0 + 100, TR), [
            {"kimlik": 1, "zaman": T0 + 3 * 510, "metin": "Eğitim bitti: 3 Türk Kılıççısı."},
            {"kimlik": 2, "zaman": T0 + 3600, "metin": "Üretim hazır: 1 Değirmen I."},
            {"kimlik": 3, "zaman": T0 + 10000 - 3600, "metin": "Kalkan bitiyor (bitiş 00:40)."},
        ])

    def test_yakin_olaylar_birlesir(self):
        """GRUP (10 dk) içindekiler tek bildirim; grup ilk olaydan ölçülür, zincirlenmez (500 ve 1000 sn sonrakiler
        birbirine 10 dk'dan yakın ama ilkine 1000 sn uzak). Bildirim grubun SON olayında gelir: "2 Değirmen I hazır"
        dediği anda ikisi de hazırdır (#62 incelemesi)."""
        k = kayit(degirmenler=[T0, T0 + 500, T0 + 1000])
        self.assertEqual(bildirim.yaklasan(k, T0, TR), [
            {"kimlik": 1, "zaman": T0 + 4100, "metin": "Üretim hazır: 2 Değirmen I."},
            {"kimlik": 2, "zaman": T0 + 4600, "metin": "Üretim hazır: 1 Değirmen I."},
        ])

    def test_bildirim_aninda_soyledigi_her_sey_hazir(self):
        """Değirmenler T0+3600, +3720, +4000'de hazır; kuyruk T0+2600 + 2 × 510 = T0+3620'de biter; hepsi ilkinden
        10 dk içinde: tek bildirim, sonuncusunun anında (T0+4000). Kalkan T0+7400'de biter: uyarı birleşmez, bir saat
        önce (T0+3800) ayrı gelir; metindeki bitiş T0+7400 = 29.10.2026 23:56 TSİ. Değişmez: bildirim anında saydığı
        her şey hazırdır."""
        k = kayit(degirmenler=[T0, T0 + 120, T0 + 400], kuyruk={"ts": T0 + 2600, "amount": 2, "unit": 880},
                  kalkan=T0 + 7400)
        sonuc = bildirim.yaklasan(k, T0, TR)
        self.assertEqual(sonuc, [
            {"kimlik": 1, "zaman": T0 + 3800, "metin": "Kalkan bitiyor (bitiş 23:56)."},
            {"kimlik": 2, "zaman": T0 + 4000, "metin": "Üretim hazır: 3 Değirmen I. Eğitim bitti: 2 Türk Kılıççısı."},
        ])
        son = sonuc[-1]["zaman"]
        self.assertTrue(all(z <= son for z, tur, _, _ in bildirim.olaylar(k, T0, TR) if tur != "kalkan"))

    def test_gecmis_ve_cok_yakin_olay_kurulmaz_sinir(self):
        k = kayit(degirmenler=[T0 - 4000, T0 - 3600 + bildirim.EN_YAKIN - 1, T0 - 3600 + bildirim.EN_YAKIN])
        self.assertEqual([b["zaman"] for b in bildirim.yaklasan(k, T0, TR)], [T0 + bildirim.EN_YAKIN])
        cok = kayit(degirmenler=[T0 + 3600 * i for i in range(30)])
        self.assertEqual(len(bildirim.yaklasan(cok, T0, TR)), bildirim.EN_COK)

    def test_kalkan_bir_saatten_az_kaldiysa_hemen(self):
        k = kayit(kalkan=T0 + 1800)
        self.assertEqual([b["zaman"] for b in bildirim.yaklasan(k, T0, TR)], [T0 + bildirim.EN_YAKIN])
        self.assertEqual(bildirim.yaklasan(kayit(kalkan=-1), T0, TR), [])  # -1: kalkan yok (ShieldManager)
        # #62 incelemesi: EN_YAKIN'dan önce biten kalkana uyarı kurulmaz (bittikten sonra "bitiyor" demesin)
        for kalan in (30, bildirim.EN_YAKIN):
            self.assertEqual(bildirim.yaklasan(kayit(kalkan=T0 + kalan), T0, TR), [], kalan)
        self.assertEqual([b["zaman"] for b in bildirim.yaklasan(kayit(kalkan=T0 + bildirim.EN_YAKIN + 1), T0, TR)],
                         [T0 + bildirim.EN_YAKIN])


class AndroidListesi(unittest.TestCase):
    def test_en_son_oynayan_oyuncu_bot_degil(self):
        kayitlar = {"oyuncu": kayit(degirmenler=[T0]), "bot": kayit(degirmenler=[T0])}
        kayitlar["bot"]["playerInfo"]["bot"] = True
        with mock.patch("oyun.kayit.session", kayitlar.get), mock.patch.object(komutlar, "zaman_olcegi", lambda: 1.0), \
                mock.patch("oyun.ekonomi.timestamp_now", lambda: T0):
            with mock.patch.object(yokken, "son_oyuncu", lambda: "oyuncu"):
                self.assertEqual([b["zaman"] for b in json.loads(bildirim.android_listesi())], [T0 + 3600])
            for kim in ("bot", None):
                with mock.patch.object(yokken, "son_oyuncu", lambda kim=kim: kim):
                    self.assertEqual(bildirim.android_listesi(), "[]")

    def test_son_oyuncu_en_son_komut_gonderen(self):
        with mock.patch.object(yokken, "_bellek", {"a": 10, "b": 30, "c": 20}):
            self.assertEqual(yokken.son_oyuncu(), "b")
        with mock.patch.object(yokken, "_bellek", {}):
            self.assertIsNone(yokken.son_oyuncu())


class Saldiri(unittest.TestCase):
    def test_dinleyiciye_metin_gider_hata_yutulur(self):
        gelen = []
        with mock.patch.object(bildirim, "dinleyici", gelen.append):
            bildirim.saldiri("Tardu", True, 700)
            bildirim.saldiri("Modu Han", False, 0)
        self.assertEqual(gelen, ["Tardu akın etti ve 700 kaynak yağmaladı.", "Modu Han akın etti, saldırı püskürtüldü."])
        bildirim.saldiri("Tardu", True, 1)  # dinleyici yok: hiçbir şey olmaz
        with mock.patch.object(bildirim, "dinleyici", mock.Mock(side_effect=RuntimeError("java"))):
            bildirim.saldiri("Tardu", True, 1)  # bot dünyası durmaz

    def test_dunya_oyuncuya_akinda_cagirir_bota_akinda_cagirmaz(self):
        from test_dunya import SIMDI, DunyaTesti, koy

        class T(DunyaTesti):
            def runTest(self):
                pass
        t = T()
        t.setUp()
        self.addCleanup(t.doCleanups)  # DunyaTesti.kur'un yamaları geri alınsın
        for v_bot, beklenen in ((False, 1), (True, 0)):
            d = t.kur(a=koy("a", birim=10, ittifak=0), v=koy("v", bot=v_bot, ittifak=None if not v_bot else 1))
            with mock.patch.object(bildirim, "saldiri") as cagri:
                d._savas("a", t.kayitlar["a"], "v", t.kayitlar["v"], SIMDI, oyuncuya=not v_bot)
            self.assertEqual(cagri.call_count, beklenen, v_bot)
            if beklenen:
                ganimet = d._son_sonuc["ganimet"]
                cagri.assert_called_once_with("Köy a", d._son_sonuc["kazandi"], ganimet)


class AndroidKabugu(unittest.TestCase):
    def test_giris_java_yokken_ve_hata_olunca(self):
        g = modul("android_giris_bildirim", GIRIS)
        g._saldiri_bildirimini_bagla()  # masaüstünde `java` modülü yok: sessizce geçer
        with mock.patch.object(bildirim, "android_listesi", mock.Mock(side_effect=OSError("disk"))):
            self.assertEqual(g.bildirimler(), "[]")
        with mock.patch.object(bildirim, "android_listesi", lambda: '[{"kimlik": 1}]'):
            self.assertEqual(g.bildirimler(), '[{"kimlik": 1}]')

    def test_java_adlari_ve_izinler_tutarli(self):
        with open(GIRIS, encoding="utf-8") as f:
            giris = f.read()
        with open(os.path.join(JAVA, "Bildirimler.java"), encoding="utf-8") as f:
            java = f.read()
        with open(os.path.join(KOK, "android", "app", "src", "main", "AndroidManifest.xml"), encoding="utf-8") as f:
            manifest = f.read()
        self.assertIn('jclass("io.github.lahmacunveayran.socialempirestr.Bildirimler")', giris)
        self.assertIn("kopru.saldiri(metin)", giris)
        self.assertRegex(java, r"public static void saldiri\(String metin\)")
        self.assertIn("android.permission.POST_NOTIFICATIONS", manifest)
        self.assertRegex(manifest, r'android:name="\.Bildirimler\$Alici"\s+android:exported="false"')
        self.assertIn("Build.VERSION.SDK_INT < 33", java)
        # Python'un EN_COK'u ile Java'nın iptal ettiği kimlik sayısı aynı olmalı (fazlası iptal edilmeden kalırdı)
        self.assertEqual(int(re.search(r"EN_COK = (\d+);", java).group(1)), bildirim.EN_COK)
        with open(os.path.join(JAVA, "MainActivity.java"), encoding="utf-8") as f:
            ana = f.read()
        self.assertIn("Bildirimler.iptal(this)", ana)
        self.assertIn('callAttr("bildirimler")', ana)


if __name__ == "__main__":
    unittest.main()
