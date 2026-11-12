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


class YazilamayanKlasor(unittest.TestCase):
    def test_hata_yazilir_ve_pencere_bekler(self):
        """#78 incelemesi: .exe yazılamayan klasörden açılırsa (PermissionError) konsol iletisi okunmadan kapanmasın."""
        giris = yukle("exe_giris")
        with mock.patch.object(giris, "konsolu_hazirla") as konsol, \
                mock.patch.object(giris, "hazirla", side_effect=PermissionError("erisim engellendi")), \
                mock.patch.object(giris.sys, "stdin") as stdin, mock.patch("builtins.input") as bekle, \
                mock.patch("builtins.print") as yaz:
            stdin.isatty.return_value = True
            with self.assertRaises(SystemExit) as son:
                giris.main()
        self.assertEqual(son.exception.code, 1)
        konsol.assert_called_once()  # S-77: ilk iş konsolun kodlaması
        bekle.assert_called_once()
        self.assertIn("yazilamadi", " ".join(str(a) for c in yaz.call_args_list for a in c.args))


class Konsol(unittest.TestCase):
    def test_yonlendirilmis_ciktida_turkce_harf_programi_dusurmez(self):
        """S-77: #78 CI'ında windows-latest'te çıktı dosyaya yönlendirilince kodlama cp1252 oldu ve kayıt adındaki 'ı'
        UnicodeEncodeError ile programı düşürdü (oyun/kayit.py _load_saved_villages)."""
        import io
        giris = yukle("exe_giris")
        ham = io.BytesIO()
        akim = io.TextIOWrapper(ham, encoding="cp1252")
        with mock.patch.object(giris.sys, "stdout", akim), mock.patch.object(giris.sys, "stderr", None):
            giris.konsolu_hazirla()
            print("Mızrakçı Kalesi", file=giris.sys.stdout)
            akim.flush()
        self.assertEqual(ham.getvalue().decode("utf-8").strip(), "Mızrakçı Kalesi")


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

    def test_klasor_kipi_ve_simge(self):
        k = self.paket.komut("SE", "/c", "/g", None, klasor=True, simge="/g/simge.ico")
        self.assertIn("--onedir", k)
        self.assertNotIn("--onefile", k)
        self.assertEqual(k[k.index("--icon") + 1], "/g/simge.ico")

    def test_simge_png_degismeden_ico_icinde(self):
        """ICO biçimi (Microsoft ICONDIR/ICONDIRENTRY, Vista'dan beri PNG görüntü): 6 bayt başlık (0, tür 1, adet 1),
        16 bayt kayıt (genişlik, yükseklik, renk, 0, düzlem 1, 32 bit, boyut, konum 22), ardından PNG olduğu gibi.
        CLAUDE.md: görsel yeniden çizilmez; simge uygulamanın kendi simgesidir."""
        import struct
        with tempfile.TemporaryDirectory() as d:
            ico = self.paket.simge_ico(self.paket.SIMGE, os.path.join(d, "s.ico"))
            with open(ico, "rb") as f:
                veri = f.read()
        with open(self.paket.SIMGE, "rb") as f:
            png = f.read()
        self.assertEqual(veri[22:], png)
        self.assertEqual(struct.unpack("<HHH", veri[:6]), (0, 1, 1))
        self.assertEqual(struct.unpack("<BBBBHHII", veri[6:22]), (192, 192, 0, 0, 1, 32, len(png), 22))
        with self.assertRaises(SystemExit):  # 512 piksel ICO'ya sığmaz
            self.paket.simge_ico(os.path.join(KOK, "templates", "img", "simge-512.png"), os.path.join(d, "b.ico"))

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


class KurulumTarifi(unittest.TestCase):
    """araclar/kurulum.iss (Inno Setup 6). Beklenenin kaynağı: sahibinin isteği (12.11.2026) "exe kurulumu yapar,
    masaüstüne kısayol koyar"; KAR-32 kayıtlar programın yanında; Inno Setup belgeleri (PrivilegesRequired=lowest
    yönetici istemez, uninsneveruninstall kaldırmada silmez, UTF-8 betik BOM ile)."""

    def setUp(self):
        with open(os.path.join(KOK, "araclar", "kurulum.iss"), "rb") as f:
            self.ham = f.read()
        self.metin = self.ham.decode("utf-8-sig")

    def test_yonetici_istemez_ve_kullanici_klasorune_kurar(self):
        self.assertIn("PrivilegesRequired=lowest", self.metin)
        self.assertIn(r"DefaultDirName={localappdata}\Programs\SocialEmpiresTR", self.metin)

    def test_masaustu_ve_baslat_kisayolu(self):
        self.assertIn(r'Name: "{userdesktop}\Social Empires Türkçe"; Filename: "{app}\SocialEmpiresTR.exe"', self.metin)
        self.assertIn(r'Name: "{group}\Social Empires Türkçe"; Filename: "{app}\SocialEmpiresTR.exe"', self.metin)

    def test_kayitlar_kaldirmada_silinmez(self):
        self.assertIn(r'Name: "{app}\saves"; Flags: uninsneveruninstall', self.metin)
        self.assertNotIn("[UninstallDelete]", self.metin)

    def test_yukseltmede_eski_oyun_verisi_temizlenir(self):
        """#79 incelemesi: PyInstaller --onedir verisi {app}\\_internal altında; eski sürümden kalan yama yine uygulanırdı.
        Kayıtlar BASE_DIR'de (_internal dışında) olduğundan bu silmeden etkilenmez."""
        self.assertIn("[InstallDelete]\n", self.metin)
        bolum = self.metin[self.metin.index("[InstallDelete]"):self.metin.index("[Files]")]
        self.assertIn(r'Type: filesandordirs; Name: "{app}\_internal"', bolum)
        self.assertNotIn("saves", bolum.split("\n", 4)[-1])

    def test_kimlik_sabit_turkce_ve_utf8(self):
        self.assertTrue(self.ham.startswith(b"\xef\xbb\xbf"))
        self.assertIn("AppId={{6E0C5A2B-2F4E-4C1B-9B57-5E3D2B8A41C7}", self.metin)
        self.assertIn(r'MessagesFile: "compiler:Languages\Turkish.isl"', self.metin)


if __name__ == "__main__":
    unittest.main()
