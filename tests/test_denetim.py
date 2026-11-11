"""Bağımsız denetimin bulguları (DNT-*): bozuk kayıt, siteler arası istek, DNS yeniden bağlama."""

import copy
import json
import os
import unittest

from ortak import KOK, bos_kayit  # noqa: F401

from oyun import kayit, kayit_yedek
from oyun import sunucu as server
from oyun.yollar import SAVES_DIR


def _yaz(uid, veri, uzanti=".save.json"):
    with open(os.path.join(SAVES_DIR, uid + uzanti), "w", encoding="utf-8") as f:
        json.dump(veri, f)


def _sil(uid):
    for uzanti in (".save.json", ".save.json.bak", ".save.json.bozuk"):
        try:
            os.remove(os.path.join(SAVES_DIR, uid + uzanti))
        except OSError:
            pass


class BozukKayit(unittest.TestCase):
    def tearDown(self):
        for uid in ("surumsuz", "bakli", "bosharita"):
            _sil(uid)
        kayit.load_saved_villages()

    def test_tek_bozuk_kayit_sunucuyu_durdurmaz_kenara_alinir(self):
        bozuk = bos_kayit("surumsuz")
        del bozuk["version"]
        bozuk["maps"] = []
        _yaz("surumsuz", bozuk)
        kayit.load_saved_villages()  # önce KeyError/IndexError ile bütün yükleme düşüyordu
        self.assertNotIn("surumsuz", kayit.all_saves_userid())
        self.assertTrue(os.path.exists(os.path.join(SAVES_DIR, "surumsuz.save.json.bozuk")))
        self.assertTrue(kayit.all_saves_userid())  # diğer kayıtlar yüklendi

    def test_surumsuz_kayit_goc_edilir(self):
        eski = bos_kayit("surumsuz")
        del eski["version"]
        _yaz("surumsuz", eski)
        kayit.load_saved_villages()
        self.assertIn("surumsuz", kayit.all_saves_userid())

    def test_goc_oncesi_hal_yedekte_kalir(self):
        from oyun.surum import version_code
        eski = bos_kayit("surumsuz")  # 0.05a: 1.4.07'den önceki kayıt
        _yaz("surumsuz", eski)
        yedek = os.path.join(kayit.BACKUP_DIR, "surumsuz.goc-0.05a.save.json")
        self.addCleanup(lambda: os.path.exists(yedek) and os.remove(yedek))
        kayit.load_saved_villages()
        with open(yedek, encoding="utf-8") as f:
            self.assertEqual(json.load(f), eski)
        with open(os.path.join(SAVES_DIR, "surumsuz.save.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["version"], version_code)
        # ikinci yükleme yedeğe dokunmaz, zaman damgalı yedeklerin silinmesi de onu almaz
        os.utime(yedek, (0, 0))
        kayit.load_saved_villages()
        kayit._eski_yedekleri_temizle("surumsuz")
        self.assertEqual(os.path.getmtime(yedek), 0)

    def test_bozuk_kaydin_bak_dosyasi_geri_alinir(self):
        _yaz("bakli", {"playerInfo": {}}, ".save.json")
        _yaz("bakli", bos_kayit("bakli"), ".save.json.bak")
        kayit.load_saved_villages()
        self.assertIn("bakli", kayit.all_saves_userid())
        with open(os.path.join(SAVES_DIR, "bakli.save.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["playerInfo"]["pid"], "bakli")  # yeniden yazıldı

    def test_kayit_yazimi_canli_dosyayi_hic_kaldirmaz(self):
        uid = kayit.new_village()
        kayit.save_session(uid)
        yol = os.path.join(SAVES_DIR, uid + ".save.json")
        self.assertTrue(os.path.exists(yol) and os.path.exists(yol + ".bak"))
        with open(yol, encoding="utf-8") as f:
            self.assertNotIn("\n    ", f.read())  # girintisiz yazılır

    def test_yedekten_acilamayacak_kayit_alinmaz(self):
        kotu = bos_kayit("bosharita")
        kotu["maps"] = []
        ham = json.dumps(kotu).encode("utf-8")
        zarf = {"bicim": kayit_yedek.BICIM, "surum": 1, "kimlik": "bosharita", "ad": "x",
                "sha256": __import__("hashlib").sha256(ham).hexdigest(), "kayit": ham.decode()}
        with self.assertRaises(kayit_yedek.YedekHatasi) as h:
            kayit_yedek.zarfi_ac(json.dumps(zarf), "bosharita")
        self.assertEqual(h.exception.args[0], "sema")


class KokenDenetimi(unittest.TestCase):
    def setUp(self):
        self.uid = kayit.new_village()
        self.istemci = server.app.test_client()

    def test_baska_siteden_durum_degistiren_istek_reddedilir(self):
        for basliklar in ({"Origin": "https://kotu.example"}, {"Sec-Fetch-Site": "cross-site"}, {"Origin": "null"}):
            self.assertEqual(self.istemci.post("/", data={"USERID": self.uid}, headers=basliklar).status_code, 403)
            self.assertEqual(self.istemci.get("/new.html", headers=basliklar).status_code, 403)
        # aynı kökenden (oyunun kendi sayfası) ve başlıksız (yerel araçlar) geçer
        self.assertEqual(self.istemci.post("/", data={"USERID": self.uid},
                                           headers={"Origin": "http://localhost"}).status_code, 302)
        self.assertEqual(self.istemci.get("/", headers={"Sec-Fetch-Site": "cross-site"}).status_code, 200)

    def test_dns_yeniden_baglama_reddedilir(self):
        self.assertEqual(self.istemci.get("/", base_url="http://kotu.example:5050").status_code, 403)
        self.assertEqual(self.istemci.get("/kayit/indir", base_url="http://kotu.example:5050").status_code, 403)
        self.assertEqual(self.istemci.get("/", base_url="http://127.0.0.1:5050").status_code, 200)
        # ev ağındaki cihaz kendi gördüğü adresle gelir
        self.assertEqual(self.istemci.get("/", base_url="http://192.168.1.20:5050",
                                          environ_base={"REMOTE_ADDR": "192.168.1.30"}).status_code, 200)

    def test_cok_buyuk_govde_reddedilir(self):
        self.assertEqual(server.app.config["MAX_CONTENT_LENGTH"], 40 * 1024 * 1024)

    def test_oturum_anahtari_rastgele(self):
        self.assertNotEqual(server.app.secret_key, "SECRET_KEY")
        self.assertGreaterEqual(len(server.app.secret_key), 32)

    @unittest.skipUnless(os.name == "posix", "dosya izinleri POSIX'te")
    def test_oturum_anahtari_yalnizca_sahibine_okunur(self):
        """Denetim DGV-08: anahtar 0644 yazılıyordu; bilen, oturum çerezini (hangi köy, ev ağı girişi) taklit eder."""
        import stat
        import tempfile
        from unittest import mock
        klasor = tempfile.mkdtemp()
        yol = os.path.join(klasor, ".oturum_anahtari")
        with mock.patch.object(server, "BASE_DIR", klasor):
            anahtar = server._oturum_anahtari()
            self.assertEqual(stat.S_IMODE(os.stat(yol).st_mode), 0o600)
            os.chmod(yol, 0o644)  # eski sürümün yazdığı dosya
            self.assertEqual(server._oturum_anahtari(), anahtar)
            self.assertEqual(stat.S_IMODE(os.stat(yol).st_mode), 0o600)



class UygulamaJetonu(unittest.TestCase):
    """DNT-04: Android'de aynı cihazdaki başka uygulamalar jetonsuz kayıtlara ulaşamaz."""

    def setUp(self):
        os.environ["SE_UYGULAMA_JETONU"] = "gizli123"
        self.addCleanup(os.environ.pop, "SE_UYGULAMA_JETONU", None)
        self.istemci = server.app.test_client()

    def test_jetonsuz_istek_reddedilir(self):
        for yol in ("/", "/kayit/indir", "/play.html", "/new.html"):
            self.assertEqual(self.istemci.get(yol).status_code, 403, yol)
        self.istemci.set_cookie(server.UYGULAMA_CEREZI, "yanlis", domain="localhost")
        self.assertEqual(self.istemci.get("/").status_code, 403)

    def test_uygulamanin_cerezi_gecer_saglik_ve_dosyalar_acik(self):
        self.assertEqual(self.istemci.get("/saglik/hazir").status_code, 200)
        self.assertNotEqual(self.istemci.get("/css/oyun.css").status_code, 403)
        self.istemci.set_cookie(server.UYGULAMA_CEREZI, "gizli123", domain="localhost")
        self.assertEqual(self.istemci.get("/").status_code, 200)

    def test_jeton_yoksa_masaustu_eskisi_gibi(self):
        os.environ.pop("SE_UYGULAMA_JETONU")
        self.assertEqual(self.istemci.get("/").status_code, 200)


class VarlikIndirme(unittest.TestCase):
    YOL = "bigbosses/bigboss1.jpg"  # config/varlik_ozetleri.tsv'de (sabit commit'in ağacında)

    def test_basarisiz_indirme_on_dakika_yeniden_denenmez(self):
        from unittest import mock
        from oyun import varliklar
        cagri = []
        with mock.patch.object(varliklar, "_indir_dene", lambda p, h: cagri.append(p) or False):
            varliklar._basarisiz.pop(self.YOL, None)
            self.assertFalse(varliklar._indir(self.YOL, "/tmp/yok.png"))
            self.assertFalse(varliklar._indir(self.YOL, "/tmp/yok.png"))
        self.assertEqual(cagri, [self.YOL])  # ikinci istek beklemeden döner
        varliklar._basarisiz.pop(self.YOL, None)

    def test_agacta_olmayan_ad_indirilmez(self):
        """Denetim DGV-05: uydurma adla dışarıya indirme yaptırılamaz; başarısızlar sözlüğü de büyümez."""
        from unittest import mock
        from oyun import varliklar
        cagri = []
        with mock.patch.object(varliklar, "_indir_dene", lambda p, h: cagri.append(p) or False):
            for i in range(50):
                self.assertIsNone(varliklar.varlik_yolu(f"x/uydurma{i}.png"))
        self.assertEqual(cagri, [])
        self.assertFalse(any(k.startswith("x/uydurma") for k in varliklar._basarisiz))
        self.assertEqual(varliklar.git_ozeti(self.YOL), "78b23b4551f2889001a46781916295f2f425a331")  # git ls-tree

    def test_ozeti_uymayan_indirme_sunulmaz(self):
        """Denetim DGV-04: hangi kaynaktan gelirse gelsin indirilen içerik sabit commit'in git blob özetine uymalı
        (özet: git hash-object = SHA-1("blob <boyut>\\0" + içerik))."""
        import hashlib
        import io
        import tempfile
        from unittest import mock
        from oyun import varliklar
        dogru = b"\x89PNG" + b"d" * 100
        ozet = hashlib.sha1(b"blob %d\0" % len(dogru) + dogru).hexdigest()
        klasor = tempfile.mkdtemp()
        hedef = os.path.join(klasor, "a.png")
        for icerik, beklenen in ((b"\x89PNG" + b"k" * 100, False), (dogru, True)):
            with mock.patch.object(varliklar, "git_ozeti", lambda p: ozet), \
                    mock.patch.object(varliklar.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(icerik)):
                self.assertEqual(varliklar._indir_dene("a.png", hedef), beklenen)
            self.assertEqual(os.path.exists(hedef), beklenen)
        # özeti uymayan eski indirme (denetimden önce inmiş) sunulmaz
        with open(hedef, "wb") as f:
            f.write(b"\x89PNG" + b"e" * 100)
        with mock.patch.object(varliklar, "git_ozeti", lambda p: ozet):
            self.assertFalse(varliklar._indirilen_dogru("a.png", hedef))

    def test_toplu_indirici_ozeti_denetler(self):
        """varliklari_indir.py'nin HTTP yolu da indirdiğini config/varlik_ozetleri.tsv ile denetler (DGV-04)."""
        import hashlib
        import importlib.util
        import io
        import json as js
        import tempfile
        from unittest import mock
        spec = importlib.util.spec_from_file_location("vi", os.path.join(KOK, "varliklari_indir.py"))
        vi = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vi)
        dogru = b"d" * 100
        ozetler = {"a/dogru.png": hashlib.sha1(b"blob 100\0" + dogru).hexdigest(),
                   "a/yanlis.png": hashlib.sha1(b"blob 100\0" + dogru).hexdigest()}
        agac = {"tree": [{"type": "blob", "path": "assets/a/dogru.png"}, {"type": "blob", "path": "assets/a/yanlis.png"},
                         {"type": "blob", "path": "assets/a/listede_yok.png"}]}
        def ac(url, timeout=None):
            if "api.github.com" in url:
                return io.BytesIO(js.dumps(agac).encode())
            return io.BytesIO(dogru if url.endswith("dogru.png") else b"k" * 100)
        klasor = tempfile.mkdtemp()
        with mock.patch.object(vi, "KOK", klasor), mock.patch.object(vi, "_ozetler", lambda: ozetler), \
                mock.patch.object(vi.urllib.request, "urlopen", ac):
            vi.http_ile()
        self.assertEqual(sorted(os.listdir(os.path.join(klasor, "assets", "a"))), ["dogru.png"])


if __name__ == "__main__":
    unittest.main()
