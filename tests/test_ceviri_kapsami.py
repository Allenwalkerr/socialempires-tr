"""Çeviri kapsamı (araclar/ceviri_kapsami.py) ve config hattı (araclar/config_hatti.py) ölçüm araçları.

Gerçek istemci gerekmez: küçük bir SWF (test_komut_imzalari.swf_kur) ve elle kurulmuş config ile sınanır.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
import unittest.mock

import ortak  # noqa: F401

sys.path.insert(0, os.path.join(ortak.KOK, "araclar"))
import ceviri_kapsami as ck  # noqa: E402
import config_hatti as ch  # noqa: E402
from test_komut_imzalari import abc_kur, swf_kur  # noqa: E402


class DilMetni(unittest.TestCase):
    def test_dil_metni(self):
        self.assertTrue(ck.dil_metni_mi("Buy now"))
        self.assertTrue(ck.dil_metni_mi("<b>OK</b>"))
        self.assertFalse(ck.dil_metni_mi("12:30"))
        self.assertFalse(ck.dil_metni_mi("#0# / #1#"))
        self.assertFalse(ck.dil_metni_mi("<br>"))
        self.assertFalse(ck.dil_metni_mi("x"))
        self.assertFalse(ck.dil_metni_mi(None))

    def test_oran(self):
        o = ck.oran([("a", "Attack", True), ("b", "Defend", False), ("c", "100", False)])
        self.assertEqual((o["cevrilen"], o["gereken"]), (1, 2))
        self.assertAlmostEqual(o["T"], 0.5)
        self.assertEqual(o["kalan"], [("b", "Defend")])
        self.assertEqual(ck.oran([])["T"], 1.0)

    def test_hedef_metinleri(self):
        hedefler = [{"id": 0, "title": "none", "description": "none", "instructions": ""},
                    {"id": 7, "title": "Build a farm", "description": "Farms give food", "instructions": "Click"}]
        self.assertEqual(ck.hedef_metinleri(hedefler), [
            ("goal:7:baslik", "Build a farm"), ("goal:7:aciklama", "Farms give food"),
            ("goal:7:talimat", "Click")])


class As3Guvenligi(unittest.TestCase):
    """GEC-06: swf_yama bir dizeyi sabit havuzunda değiştirir, o dizenin her kullanımı birlikte değişir. Deneme
    ABC'sinde (test_komut_imzalari): "Level " bir kez itilir ve `x.text = "Level " + y` ile ekrana gider; "buy"
    iki kez itilir (komut adı), hiç ekrana gitmez; "text" ve "cmd" çok adlıdır (özellik adı)."""

    def test_guvensizler(self):
        g = ck.as3_guvensizler(swf_kur(abc_kur()), ["Level ", "buy", "text", "cmd"])
        self.assertEqual(set(g), {"buy", "text", "cmd"})
        self.assertEqual(g["buy"], "2 kullanımın 0'i ekrana gidiyor")
        self.assertEqual(g["text"], "ad olarak da geçiyor")

    def test_sabit_ve_parametre_varsayilani(self):
        """#54 incelemesi: sınıf sabitinin değeri (Slot/Const, değer türü 0x01) ve isteğe bağlı parametrenin
        varsayılan değeri (method_info HAS_OPTIONAL, tür 0x01) dize havuzuna gönderme yapar ama pushstring'le
        itilmez. Bu dizeler ekrana gitse bile güvensizdir. Sahte ABC: dize 1 "Sabit", 2 "Varsayilan", 3 "Ekran";
        üçü de birer kez ekrana gider."""
        import types
        abc = types.SimpleNamespace(
            dizeler=[None, "Sabit", "Varsayilan", "Ekran"], ad_alanlari=[(0, 0)], coklu_adlar=[(0,)],
            yontemler=[{"ad": 0, "adlar": [], "secenekler": [(2, 0x01)]}], ustveriler=[],
            ornekler=[{"ozellikler": [(6, 0, 0, 0, 1, 0x01)]}], siniflar=[], betikler=[], govdeler={},
            yazi_kaynaklari=lambda *a: (set(), 0))
        with unittest.mock.patch.object(ck.abc_okur, "swf_abc", lambda veri: [abc]):
            g = ck.as3_guvensizler(b"", ["Sabit", "Varsayilan", "Ekran"])
        self.assertEqual(set(g), {"Sabit", "Varsayilan"})

    @staticmethod
    def sahte(itmeler, ekran, coz_hatasi=False, cozulemeyen=0):
        """itmeler: {ofset: dize} tek gövdede (yöntem 1) pushstring'ler; ekran: {(1, ofset, dize)}."""
        import types
        from abc_okur import Islem, OkumaHatasi

        def coz(g):
            if coz_hatasi:
                raise OkumaHatasi("bilinmeyen işlem kodu")
            return {o: Islem(o, "pushstring", (o,), o + 2, ()) for o in itmeler}
        return types.SimpleNamespace(
            dizeler=[None], ad_alanlari=[(0, 0)], coklu_adlar=[(0,)], yontemler=[], ustveriler=[], ornekler=[],
            siniflar=[], betikler=[], govdeler={1: types.SimpleNamespace(yontem=1)}, coz=coz,
            deger=lambda isl: itmeler[isl.ofset], yazi_kaynaklari=lambda *a: (set(ekran), cozulemeyen))

    def test_her_itme_noktasi_ekrana_gitmeli(self):
        """#54 incelemesi: "Iki" iki yerden itilir (ofset 0, 5); yalnızca 0'daki ekrana gider (iki yazma noktasına
        gitse de bir itme noktasıdır). 5'teki ekran dışı kullanım güvensiz kılar. "Tek" tek itmesiyle ekrana gider."""
        abc = self.sahte({0: "Iki", 5: "Iki", 9: "Tek"}, {(1, 0, "Iki"), (1, 9, "Tek")})
        with unittest.mock.patch.object(ck.abc_okur, "swf_abc", lambda veri: [abc]):
            g = ck.as3_guvensizler(b"", ["Iki", "Tek"])
        self.assertEqual(g, {"Iki": "2 kullanımın 1'i ekrana gidiyor"})

    def test_iki_abc_ayni_nokta_karismaz(self):
        """#54 incelemesi: yöntem sırası ve ofset her DoABC'de 0'dan başlar. A'da ekrana giden, B'de aynı (yöntem,
        ofset)'te ekran dışı itilen dize güvensizdir; anahtar ABC sırasını taşımazsa A'nın kaydı B'yi örterdi."""
        a = self.sahte({0: "Ortak"}, {(1, 0, "Ortak")})
        b = self.sahte({0: "Ortak"}, set())
        with unittest.mock.patch.object(ck.abc_okur, "swf_abc", lambda veri: [a, b]):
            self.assertEqual(ck.as3_guvensizler(b"", ["Ortak"]), {"Ortak": "2 kullanımın 1'i ekrana gidiyor"})

    def test_cozulemeyen_govde_hepsini_guvensiz_yapar(self):
        """#54 incelemesi: çözülemeyen gövde atlanırsa itmeler eksik sayılır, yanılgı "güvenli" yönüne olur."""
        for abc in (self.sahte({9: "Tek"}, {(1, 9, "Tek")}, coz_hatasi=True),
                    self.sahte({9: "Tek"}, {(1, 9, "Tek")}, cozulemeyen=1)):
            with unittest.mock.patch.object(ck.abc_okur, "swf_abc", lambda veri, abc=abc: [abc]):
                self.assertIn("Tek", ck.as3_guvensizler(b"", ["Tek"]))

    def test_okuyucu_secenekleri_saklar(self):
        """abc_okur._yontem: HAS_OPTIONAL (0x08) bayrağında (sıra, tür) çiftleri okunur ve saklanır."""
        from test_komut_imzalari import _u30
        # 1 parametre, dönüş 0, tür 0, ad 0, bayrak HAS_OPTIONAL; 1 seçenek: sıra 5, tür 0x01 (dize)
        veri = _u30(1) + _u30(0) + _u30(0) + _u30(0) + bytes([0x08]) + _u30(1) + _u30(5) + bytes([0x01])
        y = ck.abc_okur.Abc._yontem(ck.abc_okur._Okur(veri))
        self.assertEqual(y["secenekler"], [(5, 0x01)])

    def test_guvensiz_ceviri_cevrilmis_sayilmaz(self):
        """Ekran dizesi bir yerde ad olarak da geçerse sözlükte olsa bile çevrilmiş sayılmaz ve listelenir."""
        sozluk = {"metin_alanlari": {}, "statik_yazilar": {}, "as3_dizeleri": {"Level ": "Seviye "}}
        with unittest.mock.patch.object(ck, "as3_guvensizler", lambda veri, d: {"Level ": "ad olarak da geçiyor"}):
            sonuc = ck.olc(swf_kur(abc_kur()), {}, [], sozluk, {})
        self.assertEqual((sonuc["as3_dizeleri"]["cevrilen"], sonuc["as3_dizeleri"]["gereken"]), (0, 1))
        self.assertEqual(sonuc["as3_guvensiz"], {"Level ": "ad olarak da geçiyor"})


class Dolgu(unittest.TestCase):
    def test_dolgu_dosyasi(self):
        """ceviri/dolgu.json: her dolgunun bir nedeni var ve anahtar swf_yama.anahtar biçiminde (etiketsiz,
        kırpılmış); yoksa ölçüm onu bulamaz. Dolgu dil metni sayılmaz."""
        from oyun import swf_yama
        dolgu = ck._dolgu_yukle()
        self.assertGreater(len(dolgu), 0)
        for metin, neden in dolgu.items():
            self.assertTrue(neden.strip(), metin)
            self.assertEqual(swf_yama.anahtar(metin), metin)
        self.assertIn("lblScore", dolgu)  # alan adı biçiminde şablon (1.4.07 metin alanı)
        self.assertFalse(ck.dil_metni_mi("lblScore"))
        self.assertTrue(ck.dil_metni_mi("lblScoreX"))


class HedefCevirisi(unittest.TestCase):
    """TRA-01 (GEC-06): 1.4.07'nin hedefleri (config/goals.json → config['goals']) istemciye Türkçe gider."""

    @classmethod
    def setUpClass(cls):
        from oyun import config, turkce
        cls.config, cls.turkce = config, turkce
        with open(os.path.join(ortak.KOK, "config", "goals.json"), encoding="utf-8") as f:
            cls.hedefler = {h["id"]: h for h in json.load(f)}

    def test_anahtarlar_kapsam_araciyla_ayni(self):
        """Sunucunun çevirdiği anahtarlar ölçüm aracının saydıklarıyla aynı (iki ayrı yazım: oyun/turkce.py ve
        araclar/ceviri_kapsami.hedef_metinleri); biri değişirse ölçüm yanlış T verirdi."""
        sunucu = {a for a, bolum, _, _ in self.turkce._bolum_anahtarlari(self.config.get_game_config()) if bolum == "hedef"}
        olcum = {a for a, m in ck.hedef_metinleri(list(self.hedefler.values())) if ck.dil_metni_mi(m)}
        self.assertEqual(sunucu, olcum)

    def test_hedeflerin_hepsi_cevrili(self):
        """Kabul kapısı (docs/YOL_HARITASI_1407.md, GEC-06): hedefler T = 1; çeviri yer tutucu ve satır sonu
        denetiminden (turkce.dogrula) geçer."""
        ceviriler = self.turkce.cevirileri_yukle()
        ogeler = [(a, m, a in ceviriler and not self.turkce.dogrula(m, ceviriler[a]))
                  for a, m in ck.hedef_metinleri(list(self.hedefler.values()))]
        self.assertEqual(ck.oran(ogeler)["kalan"], [])

    def test_istemci_configinde_turkce(self):
        """Hedef 30 'Train 5 Light Archers' (goals.json, params ids 516 …); Türkçesi birimin config'teki Türkçe
        adını (item:516) taşır. İngilizce config değişmez."""
        ingilizce = self.hedefler[30]["title"]
        tr = {h["id"]: h for h in self.config.get_client_game_config("tr")["goals"]}
        en = {h["id"]: h for h in self.config.get_client_game_config("en")["goals"]}
        birim = self.turkce.cevirileri_yukle()["item:516"]
        self.assertIn(birim, tr[30]["title"])
        self.assertNotEqual(tr[30]["title"], ingilizce)
        self.assertEqual(en[30]["title"], ingilizce)
        self.assertEqual(tr[0]["title"], "none")  # yer tutucu çevrilmez


class Olcum(unittest.TestCase):
    def test_dort_oran(self):
        config = {
            "localization_strings": [{"name": "A", "text": "Attack #0#"}, {"name": "B", "text": "Defend"}],
            "items": [{"id": 1, "name": "Farm"}],
            "goals": [{"id": 3, "title": "Win", "description": "none", "instructions": ""}],
        }
        ceviriler = {"loc:A": "Saldır #0#", "loc:B": "Savun yer tutucusuz #1#", "item:1": "Çiftlik"}
        sozluk = {"metin_alanlari": {}, "statik_yazilar": {}, "as3_dizeleri": {"Level ": "Seviye "}}
        sonuc = ck.olc(swf_kur(abc_kur()), config, sozluk=sozluk, ceviriler=ceviriler)
        # B'nin çevirisi yer tutucuyu bozuyor: gönderilmez, çevrilmemiş sayılır
        self.assertEqual((sonuc["config_loc"]["cevrilen"], sonuc["config_loc"]["gereken"]), (1, 2))
        self.assertEqual(sonuc["config_bolumleri"]["esya"]["T"], 1.0)
        self.assertEqual((sonuc["hedefler"]["cevrilen"], sonuc["hedefler"]["gereken"]), (0, 1))
        self.assertEqual((sonuc["as3_dizeleri"]["cevrilen"], sonuc["as3_dizeleri"]["gereken"]), (1, 1))
        self.assertEqual(sonuc["swf_metin_alanlari"]["gereken"], 0)
        self.assertIn("Config loc adları", ck.markdown([("deneme", sonuc)]))

    def test_config_kur_yamalari_sirayla_uygular_ve_tekrari_atar(self):
        klasor = tempfile.mkdtemp()
        try:
            taban = os.path.join(klasor, "taban.json")
            with open(taban, "w", encoding="utf-8") as f:
                json.dump({"items": [{"id": 1, "v": "eski"}], "globals": {}}, f)
            yamalar = os.path.join(klasor, "patch")
            os.mkdir(yamalar)
            for ad, yama in (("b.json", [{"op": "add", "path": "/globals/X", "value": 2}]),
                             ("a.json", [{"op": "add", "path": "/items/-", "value": {"id": 1, "v": "yeni"}},
                                         {"op": "add", "path": "/globals/X", "value": 1}])):
                with open(os.path.join(yamalar, ad), "w", encoding="utf-8") as f:
                    json.dump(yama, f)
            config = ck.config_kur([yamalar], taban)
        finally:
            shutil.rmtree(klasor)
        self.assertEqual(config["items"], [{"id": 1, "v": "yeni"}])
        self.assertEqual(config["globals"]["X"], 2)  # a.json'dan sonra b.json


class ConfigHatti(unittest.TestCase):
    C = {
        "items": [{"id": 1, "ad": "Farm", "sure": 5}, {"id": 2, "ad": "Mill"}],
        "localization_strings": [{"id": "9", "name": "OK", "text": "OK"}],
        "globals": {"X": 1},
    }

    def durum(self, islem):
        return ch.islem_durumu(self.C, islem)[0]

    def test_durumlar(self):
        self.assertEqual(self.durum({"op": "add", "path": "/items/-", "value": {"id": 2, "ad": "Mill"}}), "aynı")
        self.assertEqual(self.durum({"op": "add", "path": "/items/-", "value": {"id": 1, "ad": "Farm"}}),
                         "kapsanıyor")
        self.assertEqual(self.durum({"op": "add", "path": "/items/-", "value": {"id": 1, "ad": "Çiftlik"}}),
                         "farklı")
        self.assertEqual(self.durum({"op": "add", "path": "/items/-", "value": {"id": 3}}), "yeni")
        self.assertEqual(self.durum({"op": "add", "path": "/globals/X", "value": 1}), "aynı")
        self.assertEqual(self.durum({"op": "add", "path": "/globals/Y", "value": 1}), "yeni")
        self.assertEqual(self.durum({"op": "replace", "path": "/globals/Y", "value": 1}), "yolu yok")
        self.assertEqual(self.durum({"op": "add", "path": "/yok/Z", "value": 1}), "yolu yok")
        # yerelleştirmede eş `name` ile bulunur, `id` farkı alan farkı olarak görünür
        durum, ayrinti = ch.islem_durumu(self.C, {"op": "add", "path": "/localization_strings/-",
                                                  "value": {"id": "1", "name": "OK", "text": "OK"}})
        self.assertEqual((durum, ayrinti), ("farklı", {"alanlar": ["id"]}))

    def test_hukum(self):
        self.assertEqual(ch.hukum({"aynı": 2, "kapsanıyor": 1}), "gider")
        self.assertEqual(ch.hukum({"aynı": 1, "yeni": 1}), "kalır")
        self.assertEqual(ch.hukum({"yeni": 1, "farklı": 1}), "çatışır")
        self.assertEqual(ch.hukum({"farklı": 1, "yolu yok": 1}), "uygulanamaz")

    def test_dokunulan_anahtarlar(self):
        yama = [{"op": "add", "path": "/globals/DRAGONS", "value": 1}, {"op": "add", "path": "/items/-"}]
        self.assertEqual(ch.dokunulan_anahtarlar(yama), {"globals", "DRAGONS", "items"})


if __name__ == "__main__":
    unittest.main()
