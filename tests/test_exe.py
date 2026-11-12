"""Tek dosyalık Windows programı (araclar/exe_giris.py, araclar/exe_paketi.py).

Beklenen davranışın kaynağı: sahibinin kararı (12.11.2026) "kayıtlar .exe'nin yanında", oyun/yollar.py BASE_DIR (donmuş
programda sys.executable'ın klasörü) ve Android girişinin aynı ilk açılış kuralı (android_giris.hazirla: var olana
dokunulmaz). Programın kendisi Windows'ta CI'da derlenip boş klasörde sınanır (.github/workflows/windows.yml exe).
"""

import base64
import hashlib
import importlib.util
import os
import tempfile
import unittest
from unittest import mock

from ortak import KOK


def yukle(ad):
    tanim = importlib.util.spec_from_file_location(ad, os.path.join(KOK, "araclar", ad + ".py"))
    modul = importlib.util.module_from_spec(tanim)
    tanim.loader.exec_module(modul)
    return modul


class IlkAcilis(unittest.TestCase):
    def setUp(self):
        self.giris = yukle("exe_giris")
        self.gecici = tempfile.TemporaryDirectory()
        self.veri = os.path.join(self.gecici.name, "veri")
        self.taban = os.path.join(self.gecici.name, "program")
        os.makedirs(os.path.join(self.veri, "mods"))
        with open(os.path.join(self.veri, "ayarlar.json"), "w", encoding="utf-8") as f:
            f.write('{"zaman_olcegi": 3.0}')
        with open(os.path.join(self.veri, "mods", "mods.txt"), "w", encoding="utf-8") as f:
            f.write("kompu\n")

    def tearDown(self):
        self.gecici.cleanup()

    def oku(self, *yol):
        with open(os.path.join(self.taban, *yol), encoding="utf-8") as f:
            return f.read()

    def test_ilk_acilista_ayar_ve_modlar_programin_yanina(self):
        self.giris.hazirla(self.taban, self.veri)
        self.assertEqual((self.oku("ayarlar.json"), self.oku("mods", "mods.txt")), ('{"zaman_olcegi": 3.0}', "kompu\n"))
        self.assertFalse(os.path.exists(os.path.join(self.taban, "mods.tmp")))

    def test_oyuncunun_degistirdigine_dokunulmaz(self):
        self.giris.hazirla(self.taban, self.veri)
        with open(os.path.join(self.taban, "ayarlar.json"), "w", encoding="utf-8") as f:
            f.write('{"zaman_olcegi": 1.0}')
        with open(os.path.join(self.taban, "mods", "mods.txt"), "w", encoding="utf-8") as f:
            f.write("")
        self.giris.hazirla(self.taban, self.veri)  # yeni .exe ile ikinci açılış
        self.assertEqual((self.oku("ayarlar.json"), self.oku("mods", "mods.txt")), ('{"zaman_olcegi": 1.0}', ""))

    def test_donmus_programda_kayitlar_programin_yaninda(self):
        """oyun/yollar.py: frozen iken BASE_DIR = sys.executable'ın klasörü; kayıtlar orada saves/."""
        import subprocess
        import sys
        program = os.path.join(self.taban, "SocialEmpiresTR.exe")
        kod = ("import sys; sys.frozen = True; sys.executable = %r; import os; os.environ.pop('SE_KAYIT_DIZINI', None);"
               "os.environ.pop('SE_TABAN_DIZINI', None); from oyun import yollar; print(yollar.SAVES_DIR); "
               "print(yollar.MODS_DIR); print(yollar.AYARLAR)" % program)
        cikti = subprocess.run([sys.executable, "-c", kod], cwd=KOK, capture_output=True, text=True, check=True,
                               env={k: v for k, v in os.environ.items() if k not in ("SE_KAYIT_DIZINI", "SE_TABAN_DIZINI")})
        self.assertEqual(cikti.stdout.split(), [os.path.join(self.taban, "saves"), os.path.join(self.taban, "mods"),
                                                os.path.join(self.taban, "ayarlar.json")])


class Paketleme(unittest.TestCase):
    def setUp(self):
        self.paket = yukle("exe_paketi")

    def test_oyun_verisi_ve_ruffle_pakete_girer(self):
        k = self.paket.komut("SE", "/cikti", "/gecici", "/gecici/ruffle-paketi.tgz")
        hedefler = {k[i + 1].rsplit(self.paket.AYRAC, 1)[1] for i, x in enumerate(k) if x == "--add-data"}
        # oyun/yollar.py'nin _MEIPASS altında aradığı klasörler; ayarlar ve modlar ilk açılışta kopyalanır (exe_giris)
        self.assertTrue({"templates", "config", "ceviri", "villages", "stub", "mods", os.path.join("assets", "fonts"),
                         "."} <= hedefler, hedefler)
        self.assertIn("/gecici/ruffle-paketi.tgz" + self.paket.AYRAC + ".", k)
        self.assertEqual((k[k.index("--collect-submodules") + 1], k[-1]),
                         ("oyun", os.path.join(KOK, "araclar", "exe_giris.py")))
        self.assertIn("--onefile", k)

    def test_ruffle_ozeti_tutmazsa_paket_yapilmaz(self):
        with tempfile.NamedTemporaryFile(suffix=".tgz", delete=False) as f:
            f.write(b"sahte ruffle")
        try:
            with self.assertRaises(SystemExit):
                self.paket.ruffle_paketi(f.name)
            dogru = base64.b64encode(hashlib.sha512(b"sahte ruffle").digest()).decode()
            with mock.patch.object(self.paket.ruffle, "PAKET_SHA512", dogru):
                self.assertEqual(self.paket.ruffle_paketi(f.name), b"sahte ruffle")
        finally:
            os.unlink(f.name)

    def test_derleme_araclari_sabit(self):
        """DGV-08: Windows programı her derlemede aynı araçlarla çıksın."""
        with open(os.path.join(KOK, "requirements-exe.txt"), encoding="utf-8") as f:
            satirlar = [s.split("#")[0].strip() for s in f if s.split("#")[0].strip()]
        self.assertIn("-r requirements.txt", satirlar)
        for s in satirlar:
            if s.startswith("-r "):
                continue
            self.assertRegex(s, r"^[A-Za-z0-9_.-]+==\d+(\.\d+)*(; sys_platform == \"win32\")?$", s)
        self.assertIn("pyinstaller==6.11.1", satirlar)


if __name__ == "__main__":
    unittest.main()
