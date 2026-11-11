"""Dağıtım güvenliği (DGV-03, 06, 07, 08): iş akışları, Android yedek kuralları, bağımlılık sabitleme.

Beklenen değerlerin kaynağı: GitHub Actions belgeleri ("Security hardening": eylemleri tam commit SHA'sına
sabitle, bağlam değerlerini run: içine gömme, sırları güvenilmeyen kodla çalıştırma) ve Android yedek kuralı
belgesi (exclude yolları joker karakter almaz, tek tek yazılır).
"""

import glob
import hashlib
import importlib.util
import os
import re
import unittest
from unittest import mock

from ortak import KOK

AKIS_DIZINI = os.path.join(KOK, ".github", "workflows")
XML_DIZINI = os.path.join(KOK, "android", "app", "src", "main", "res", "xml")
JAVA = os.path.join(KOK, "android", "app", "src", "main", "java", "io", "github", "lahmacunveayran",
                    "socialempirestr", "MainActivity.java")


def oku(*yol):
    with open(os.path.join(KOK, *yol), encoding="utf-8") as f:
        return f.read()


def akislar():
    yollar = sorted(glob.glob(os.path.join(AKIS_DIZINI, "*.yml")))
    assert yollar
    sonuc = {}
    for y in yollar:
        with open(y, encoding="utf-8") as f:
            sonuc[os.path.basename(y)] = f.read()
    return sonuc


def adimlar(metin):
    """Adım bloklarına böler (iş akışlarında adımlar 6 boşluk girintili '- ' ile başlar)."""
    bloklar, simdiki = [], None
    for satir in metin.splitlines():
        if re.match(r"^ {6}- ", satir):
            simdiki = [satir]
            bloklar.append(simdiki)
        elif simdiki is not None and (satir.startswith("       ") or not satir.strip()):
            simdiki.append(satir)
        else:
            simdiki = None
    return ["\n".join(b) for b in bloklar]


class IsAkislari(unittest.TestCase):
    def test_her_eylem_tam_sha_ile_sabit(self):
        for ad, metin in akislar().items():
            kullanimlar = re.findall(r"^\s*-?\s*uses:\s*(\S.*)$", metin, re.M)
            self.assertTrue(kullanimlar, ad)
            for k in kullanimlar:
                self.assertRegex(k, r"^[\w.-]+/[\w./-]+@[0-9a-f]{40} # v\d+(\.\d+)*$", f"{ad}: {k}")

    def test_imza_sirri_pull_requestte_kullanilmaz(self):
        metin = akislar()["android.yml"]
        self.assertIn("pull_request:", metin)  # PR'da derleme sürüyor; yalnızca sır girmemeli
        sir_adimlari = [a for a in adimlar(metin) if "secrets.ANDROID_IMZA" in a]
        self.assertGreaterEqual(len(sir_adimlari), 2)  # anahtar adımı ve sürüm derlemesi
        for adim in sir_adimlari:
            self.assertIn("if: github.event_name != 'pull_request'", adim)
        # Sır başka yerde (iş düzeyi env, with, çıktı) geçmesin
        self.assertEqual(metin.count("secrets.ANDROID_IMZA"), sum(a.count("secrets.ANDROID_IMZA") for a in sir_adimlari))
        # PR'da imzasız sürüm derlemesi var
        self.assertIn("if: github.event_name == 'pull_request'", metin)

    def test_pull_request_tetikli_hicbir_is_baska_sir_kullanmaz(self):
        for ad, metin in akislar().items():
            if "pull_request:" not in metin or ad == "claude-inceleme.yml":
                continue
            for adim in adimlar(metin):
                for sir in re.findall(r"secrets\.(\w+)", adim):
                    self.assertIn("if: github.event_name != 'pull_request'", adim, f"{ad}: secrets.{sir}")

    def test_run_ve_script_icinde_baglam_degeri_yok(self):
        for ad, metin in akislar().items():
            if ad == "claude-inceleme.yml":
                continue
            for adim in adimlar(metin):
                govde = False
                for satir in adim.splitlines():
                    if re.match(r"^\s+(run|script):", satir):
                        govde = True
                    elif re.match(r"^\s{8}\w[\w-]*:", satir):
                        govde = False  # sonraki anahtar (env:, with:...) betik değildir
                    if govde:
                        self.assertNotIn("${{", satir, f"{ad}: {satir.strip()}")

    def test_sinama_hata_ayiklama_apk_ile_calisir(self):
        # DGV-06: "sinama" ek değeri yalnızca hata ayıklama yapısında etkili; CI sınaması o yapıyla yapılmalı
        metin = akislar()["android.yml"]
        self.assertIn(":app:assembleDebug", metin)
        self.assertIn("app-debug.apk", metin)
        self.assertIn("-sinama.apk", re.search(r"script: (.*)", metin).group(1))
        # yayımlanan artefakt (android-apk) hata ayıklama APK'sını içermez
        self.assertIn("name: android-sinama-apk", metin)
        surum = metin[metin.index("  surum:"):]
        self.assertNotIn("android-sinama-apk", surum)
        self.assertNotIn("-sinama.apk", surum)


class AndroidYedekKurallari(unittest.TestCase):
    def kurallar(self):
        return {ad: oku("android", "app", "src", "main", "res", "xml", ad)
                for ad in ("yedek.xml", "yedek_eski.xml")}

    def test_gunlukler_ve_ayarlar_dislanir(self):
        # Beklenen adlar kaynaktan: sunucunun saves/ altına yazdığı bütün .jsonl/.log dosyaları
        gunlukler = set()
        for yol in glob.glob(os.path.join(KOK, "oyun", "*.py")):
            with open(yol, encoding="utf-8") as f:
                gunlukler |= set(re.findall(r"""["']([a-z_]+\.(?:jsonl|log))["']""", f.read()))
        self.assertTrue({"komut_gunlugu.jsonl", "http_gunlugu.jsonl", "istemci_hatalari.jsonl",
                         "sunucu_hatalari.log"} <= gunlukler, gunlukler)
        for ad, xml in self.kurallar().items():
            kopya = 2 if ad == "yedek.xml" else 1  # yedek.xml: cloud-backup ve device-transfer bölümleri
            for g in gunlukler:
                self.assertEqual(xml.count(f'<exclude domain="file" path="socialempires/saves/{g}" />'), kopya, f"{ad}: {g}")
            self.assertEqual(xml.count('<exclude domain="file" path="socialempires/ayarlar.json" />'), kopya, ad)
            self.assertNotIn('<include domain="file" path="socialempires/ayarlar.json"', xml, ad)

    def test_onceki_dislamalar_korunur(self):
        for ad, xml in self.kurallar().items():
            for klasor in ("backups/", "gunluk_yedek/"):
                self.assertIn(f'<exclude domain="file" path="socialempires/saves/{klasor}" />', xml, ad)


class AndroidEtkinligi(unittest.TestCase):
    def test_sinama_yalnizca_hata_ayiklama_yapisinda(self):
        java = oku("android", "app", "src", "main", "java", "io", "github", "lahmacunveayran",
                   "socialempirestr", "MainActivity.java")
        satir = next(s for s in java.splitlines() if 'getBooleanExtra("sinama"' in s)
        self.assertIn("hataAyiklamaYapisi &&", satir)
        self.assertIn("(getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0", java)

    def test_yedek_indirme_adresi_denetlenir(self):
        java = oku("android", "app", "src", "main", "java", "io", "github", "lahmacunveayran",
                   "socialempirestr", "MainActivity.java")
        govde = java[java.index("private void yedekIndir("):]
        self.assertLess(govde.index("yedekAdresiGecerli(adres)"), govde.index("openConnection()"))
        gecerli = java[java.index("static boolean yedekAdresiGecerli"):java.index("private void yedekIndir(")]
        for parca in ('"http".equals(uri.getScheme())', '"127.0.0.1".equals(uri.getHost())'):
            self.assertIn(parca, gecerli)
        self.assertIn("setInstanceFollowRedirects(false)", govde)
        self.assertIn("YEDEK_EN_COK", govde)


class BagimlilikSabitleme(unittest.TestCase):
    def test_requirements_tam_surum_sabit(self):
        satirlar = [s.strip() for s in oku("requirements.txt").splitlines() if s.strip() and not s.startswith("#")]
        self.assertTrue(satirlar)
        for s in satirlar:
            self.assertRegex(s, r"^[A-Za-z0-9_.-]+==\d+(\.\d+)*$", s)
        adlar = {s.split("==")[0].lower() for s in satirlar}
        # Doğrudan bağımlılıklar ve Flask'ın dolaylıları da sabit (Flask belgeleri: Werkzeug, Jinja2, MarkupSafe,
        # ItsDangerous, Click, Blinker)
        self.assertTrue({"flask", "jsonpatch", "waitress", "brotli", "werkzeug", "jinja2", "markupsafe",
                         "itsdangerous", "click", "blinker", "jsonpointer"} <= adlar, adlar)

    def test_windows_paketi_colorama_sabit(self):
        self.assertIn('"colorama==0.4.6"', oku("araclar", "windows_paketi.py"))


class GomuluPythonOzeti(unittest.TestCase):
    def setUp(self):
        tanim = importlib.util.spec_from_file_location("windows_paketi", os.path.join(KOK, "araclar", "windows_paketi.py"))
        self.paket = importlib.util.module_from_spec(tanim)
        tanim.loader.exec_module(self.paket)

    def test_ozet_gercek_zip_bicimli_ve_surum_icin_var(self):
        ozet = self.paket.PYTHON_ZIP_OZETLERI["3.12.10"]
        self.assertRegex(ozet, r"^[0-9a-f]{64}$")

    def test_ozet_tutmayan_zip_reddedilir(self):
        veri = b"gomulu python"
        with mock.patch.dict(self.paket.PYTHON_ZIP_OZETLERI, {"9.9.9": hashlib.sha256(veri).hexdigest()}):
            self.assertEqual(self.paket.python_zip_dogrula("9.9.9", veri), veri)
            with self.assertRaises(SystemExit):
                self.paket.python_zip_dogrula("9.9.9", veri + b"x")

    def test_bilinmeyen_surum_reddedilir(self):
        with self.assertRaises(SystemExit):
            self.paket.python_zip_dogrula("0.0.1", b"x")

    def test_yerel_zip_de_denetlenir(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".zip") as f:
            f.write(b"sahte")
            f.flush()
            with self.assertRaises(SystemExit):
                self.paket.python_zip("3.12.10", f.name)


if __name__ == "__main__":
    unittest.main()
