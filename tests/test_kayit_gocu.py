"""Kayıt göçünün kabul kapısı (GEC-04, docs/YOL_HARITASI_1407.md §2 "Kayıt göçü"): değişmezlik, eşgüçlülük, geri dönüş.

g, sunucunun yükleme yolu (`kayit.load_saved_villages`: doğrulama, göç öncesi yedek, `migrate_loaded_save`,
seviye düzeltmesi, gerekirse kayıt). I(s), belgedeki liste: seviye, XP, altın, odun, yemek, taş, nakit, eşya
çoklukümesi, birim sayıları, depo, mezarlık, harita sayısı. Beklenen değerin kaynağı eski kaydın kendisidir: göç
bunları değiştirmemelidir (belge). Örnek kayıtlar depodaki gerçek biçimli köyler (`villages/`, sürümsüz) ve en
küçük kaydın 1.4.07 öncesi her sürümü.
"""

import collections
import json
import os
import unittest

from ortak import KOK, bos_kayit

from oyun import kayit
from oyun.config import get_item_from_id
from oyun.surum import ESKI_ISTEMCI_SURUMLERI, version_code
from oyun.yollar import SAVES_DIR

ORNEKLER = ("AcidCaos", "Arthur30", "Arthur31", "Arthur32", "initial")


def _coklu(liste):
    return collections.Counter(json.dumps(x, sort_keys=True) for x in (liste or []))


def degismezler(s):
    pi, ps = s["playerInfo"], s["privateState"]
    haritalar = []
    for h in s["maps"]:
        kimlikler = [e[0] for e in h.get("items", [])]
        birimler = collections.Counter(i for i in kimlikler if (get_item_from_id(i) or {}).get("type") == "u")
        haritalar.append({k: h.get(k) for k in ("level", "xp", "coins", "wood", "food", "stone")}
                         | {"esya": collections.Counter(kimlikler), "birim": birimler})
    return {"nakit": pi.get("cash"), "harita_sayisi": len(s["maps"]), "haritalar": haritalar,
            "depo": list(ps.get("gifts") or []),  # gifts[id] = adet (komutlar depo yardımcısı)
            "mezarlik": (_coklu(ps.get("resurrectableUnits")), ps.get("graveyardCapacity"))}


def ornek_kayitlar():
    for ad in ORNEKLER:
        with open(os.path.join(KOK, "villages", f"{ad}.json"), encoding="utf-8") as f:
            s = json.load(f)
        s["playerInfo"]["pid"] = f"goc-{ad.lower()}"
        yield s
    for surum in ESKI_ISTEMCI_SURUMLERI + ("0.06a", "0.07a"):
        s = bos_kayit("goc-" + surum.replace(".", "-"))  # kimlikte nokta geçersiz (kayit.gecerli_uid)
        s["version"] = surum
        s["privateState"].update(gifts=[0, 0, 3, 0, 1], resurrectableUnits=[512, 512, 516], graveyardCapacity=5)
        yield s


def _oku(yol):
    with open(yol, "rb") as f:
        return f.read()


class KayitGocu(unittest.TestCase):
    def setUp(self):
        self.yazilan = []
        for s in ornek_kayitlar():
            uid = s["playerInfo"]["pid"]
            yol = os.path.join(SAVES_DIR, f"{uid}.save.json")
            with open(yol, "w", encoding="utf-8") as f:
                json.dump(s, f, ensure_ascii=False, indent=2)  # elle düzenlenmiş/eski biçim: girintili
            surum = s.get("version") or "surumsuz"
            self.yazilan.append((uid, s, _oku(yol), os.path.join(kayit.BACKUP_DIR, f"{uid}.goc-{surum}.save.json")))
        self.addCleanup(self._temizle)
        kayit.load_saved_villages()

    def _temizle(self):
        for uid, _, _, yedek in self.yazilan:
            for yol in (os.path.join(SAVES_DIR, f"{uid}.save.json" + u) for u in ("", ".bak", ".bozuk")):
                if os.path.exists(yol):
                    os.remove(yol)
            if os.path.exists(yedek):
                os.remove(yedek)
        kayit.load_saved_villages()

    def test_hepsi_bu_surume_gecer(self):
        for uid, _, _, _ in self.yazilan:
            self.assertIn(uid, kayit.all_saves_userid())
            self.assertEqual(kayit.session(uid)["version"], version_code, uid)

    def test_degismezlik(self):
        """I(g(s)) = I(s)."""
        for uid, eski, _, _ in self.yazilan:
            self.assertEqual(degismezler(kayit.session(uid)), degismezler(eski), uid)

    def test_esgucluluk(self):
        """g(g(s)) = g(s): ikinci yükleme kaydı değiştirmez, dosyayı da yeniden yazmaz."""
        once = {uid: (json.loads(json.dumps(kayit.session(uid))), _oku(os.path.join(SAVES_DIR, f"{uid}.save.json")))
                for uid, _, _, _ in self.yazilan}
        kayit.load_saved_villages()
        for uid, (veri, bayt) in once.items():
            self.assertEqual(kayit.session(uid), veri, uid)
            self.assertEqual(_oku(os.path.join(SAVES_DIR, f"{uid}.save.json")), bayt, uid)
        for uid, _, eski_bayt, _ in self.yazilan:  # yeniden yazılsaydı .bak göçmüş kaydın kopyası olurdu
            self.assertEqual(_oku(os.path.join(SAVES_DIR, f"{uid}.save.json.bak")), eski_bayt, uid)

    def test_geri_donus(self):
        """Göçten önce alınan .bak eski kaydın baytlarıdır; göç öncesi yedek eski kaydın kendisidir."""
        for uid, eski, bayt, yedek in self.yazilan:
            self.assertEqual(_oku(os.path.join(SAVES_DIR, f"{uid}.save.json.bak")), bayt, uid)
            with open(yedek, encoding="utf-8") as f:
                self.assertEqual(json.load(f), eski, uid)


class SeviyeDuzeltmesi(unittest.TestCase):
    """İstemci seviyeyi yalnızca yukarı taşır (PlayerStatus/checkForLevelUp) ve kayıttakini en çok `length - 1`'e
    indirir (PlayerStatus/Init); config'te 100 eşik, en yüksek seviye 99, 34. seviyenin eşiği 69 467'nin altında."""

    def test_xpden_yuksek_seviye_korunur(self):
        k = bos_kayit()
        k["maps"][0].update(level=53, xp=69467)  # villages/Arthur30.json
        self.assertFalse(kayit._seviyeyi_duzelt(k))
        self.assertEqual(k["maps"][0]["level"], 53)

    def test_tavanin_ustu_en_yuksek_seviyeye(self):
        k = bos_kayit()
        k["maps"][0].update(level=150, xp=0)
        self.assertTrue(kayit._seviyeyi_duzelt(k))
        self.assertEqual(k["maps"][0]["level"], 99)

    def test_sonsuz_seviye_ve_xp_yuklemeyi_dusurmez(self):
        """JSON'da 1e999 sonsuz olur (Python json belgesi), int(inf) OverflowError verir. Doğrulama yalnızca ilk
        haritaya bakar; ikinci haritadaki bozuk değer tek kaydın değil bütün yüklemenin düşmesine yol açmamalı."""
        k = bos_kayit("sonsuz-harita")
        k["maps"].append(dict(k["maps"][0], id=1, xp="SONSUZ", level="SONSUZ"))
        yol = os.path.join(SAVES_DIR, "sonsuz-harita.save.json")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(json.dumps(k).replace('"SONSUZ"', "1e999"))
        self.addCleanup(lambda: [os.remove(y) for y in (yol, yol + ".bak") if os.path.exists(y)])
        self.addCleanup(kayit.load_saved_villages)
        kayit.load_saved_villages()
        self.assertEqual(kayit.session("sonsuz-harita")["maps"][1]["level"], float("inf"))

    def test_xpnin_altindaki_seviye_yukselir(self):
        k = bos_kayit()
        k["maps"][0].update(level=1, xp=69467)
        self.assertTrue(kayit._seviyeyi_duzelt(k))
        self.assertEqual(k["maps"][0]["level"], 34)



class YuklemeDayanikliligi(unittest.TestCase):
    """Bağımsız denetimin kayıt alanı (KAR-13): KYG-01, KYG-03. Beklenen: her kayıt yüklenir ve bu sürüme göçer
    (docs/YOL_HARITASI_1407.md §2 "Kayıt göçü"); kayıt anahtarı str'dir (`kayit.session` bunu şart koşar)."""

    def _yol(self, uid, uzanti=".save.json"):
        yol = os.path.join(SAVES_DIR, uid + uzanti)
        self.addCleanup(lambda: [os.remove(y) for y in (yol, yol + ".bak", yol + ".bozuk") if os.path.exists(y)])
        return yol

    def setUp(self):
        self.addCleanup(kayit.load_saved_villages)

    def test_sayi_kimlikli_eski_kayit_yuklemeyi_dusurmez(self):
        k = bos_kayit("777")
        k["playerInfo"]["pid"] = 777  # 0.05a: göç kaydı yazar, yazım session(777)'yi çağırırdı
        with open(self._yol("777"), "w", encoding="utf-8") as f:
            json.dump(k, f)
        diger = kayit.new_village()
        kayit.save_session(diger)
        kayit.load_saved_villages()
        self.assertIn(diger, kayit.all_saves_userid())  # yükleme sonuna kadar sürdü
        self.assertEqual(kayit.session("777")["version"], version_code)
        with open(self._yol("777"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["playerInfo"]["pid"], "777")

    def test_sayi_kimlikli_yedek_iceri_alinmaz(self):
        from oyun import kayit_yedek
        import hashlib
        k = bos_kayit("778")
        k["playerInfo"]["pid"] = 778
        ham = json.dumps(k).encode("utf-8")
        zarf = {"bicim": kayit_yedek.BICIM, "surum": 1, "kimlik": "778", "ad": "x",
                "sha256": hashlib.sha256(ham).hexdigest(), "kayit": ham.decode()}
        with self.assertRaises(kayit_yedek.YedekHatasi) as h:
            kayit_yedek.zarfi_ac(json.dumps(zarf), "778")
        self.assertEqual(str(h.exception), "kimlik")

    def test_gecersiz_kimlikli_kayit_atlanir_yukleme_surer(self):
        """#45 incelemesi: null kimlik "None"a çevrilip None.save.json'a yazılmamalı; kimlik hiç yoksa KeyError
        bütün yüklemeyi düşürmemeli."""
        diger = kayit.new_village()
        kayit.save_session(diger)
        for uid, pid in (("kimliksiz", None), ("dogru-yanlis", True), ("eksik", "SIL")):
            k = bos_kayit(uid)
            if pid == "SIL":
                del k["playerInfo"]["pid"]
            else:
                k["playerInfo"]["pid"] = pid
            with open(self._yol(uid), "w", encoding="utf-8") as f:
                json.dump(k, f)
        kayit.load_saved_villages()
        self.assertIn(diger, kayit.all_saves_userid())
        for ad in ("None", "True"):
            self.assertFalse(os.path.exists(os.path.join(SAVES_DIR, f"{ad}.save.json")), ad)
            self.assertNotIn(ad, kayit.all_saves_userid())

    def test_duzeltme_yarida_patlarsa_kayit_degismez(self):
        """#45 incelemesi: düzeltme kopyada yapılır; yarıda patlarsa bellekte ve diskte yarım kayıt kalmaz."""
        from unittest import mock
        yol = self._yol("yarida")
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(bos_kayit("yarida"), f)
        with open(yol, "rb") as f:
            bayt = f.read()

        def patlayan(save):
            save["maps"][0]["coins"] = -1  # yarım değişiklik
            raise RuntimeError("deneme")

        with mock.patch.object(kayit, "_yukleme_duzeltmeleri", patlayan):
            kayit.load_saved_villages()
        self.assertNotIn("yarida", kayit.all_saves_userid())
        with open(yol, "rb") as f:
            self.assertEqual(f.read(), bayt)

    def test_baktan_alinip_atlanan_kayit_diskte_kalir(self):
        """#45 incelemesi: bozuk canlı dosya .bozuk'a alınır; .bak'tan gelen kayıt sonra atlanırsa canlı dosya
        geri konmalı, yoksa yükleyici (yalnızca *.save.json) imparatorluğu bir daha görmez."""
        yol = self._yol("bakatla")
        with open(yol, "w", encoding="utf-8") as f:
            f.write('{"yarim')
        k = bos_kayit("bakatla")
        k["playerInfo"]["pid"] = None
        with open(yol + ".bak", "w", encoding="utf-8") as f:
            json.dump(k, f)
        kayit.load_saved_villages()
        with open(yol, encoding="utf-8") as f, open(yol + ".bak", encoding="utf-8") as g:
            self.assertEqual(json.load(f), json.load(g))

    def test_ice_aktarmadan_onceki_hal_kalici_yedekte(self):
        """KYG-02 (bağımsız denetim): içe aktarılan yedeğin ezdiği kayıt yalnızca .bak'ta kalıyordu, .bak da ilk
        kayıtta eziliyordu. Önceki hâl backups/ altında adlı bir dosyada kalmalı; yedek budaması onu silmemeli."""
        import glob
        from oyun import kayit_yedek
        uid = kayit.new_village()
        yol = self._yol(uid)
        kayit.session(uid)["maps"][0]["coins"] = 999999
        kayit.save_session(uid)
        with open(yol, "rb") as f:
            onceki = f.read()
        yeni = json.loads(onceki)
        yeni["maps"][0]["coins"] = 5
        kayit_yedek.geri_yukle(uid, json.dumps(yeni).encode("utf-8"))
        desen = os.path.join(kayit.BACKUP_DIR, f"{uid}.ice-aktarma-*.save.json")
        self.addCleanup(lambda: [os.remove(y) for y in glob.glob(desen)])
        kayit.save_session(uid)
        kayit.save_session(uid)  # .bak artık içe aktarılan hâl
        for _ in range(kayit.MAX_BACKUPS + 1):
            kayit.backup_session(uid)  # budama
        yedekler = glob.glob(desen)
        self.assertEqual(len(yedekler), 1)
        with open(yedekler[0], "rb") as f:
            self.assertEqual(f.read(), onceki)
        self.assertEqual(kayit.session(uid)["maps"][0]["coins"], 5)

    def test_geri_yukleme_kotu_kimligi_reddeder(self):
        """CodeQL (#46): yedek yolu kimlikten kurulur; yol geçişi taşıyan kimlik hiçbir dosyaya yazılmaz."""
        from oyun import kayit_yedek
        for kotu in ("../disari", "a/b", "", 777, "x" * 65):
            with self.assertRaises(kayit_yedek.YedekHatasi):
                kayit_yedek.geri_yukle(kotu, b"{}")
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(SAVES_DIR), "disari.save.json")))

    def test_bak_ile_geri_alinan_eski_kayit_da_gocer(self):
        yol = self._yol("bakgoc")
        with open(yol, "w", encoding="utf-8") as f:
            f.write('{"yarim')  # yarım yazım
        eski = bos_kayit("bakgoc")  # 0.05a
        with open(yol + ".bak", "w", encoding="utf-8") as f:
            json.dump(eski, f)
        yedek = os.path.join(kayit.BACKUP_DIR, "bakgoc.goc-0.05a.save.json")
        self.addCleanup(lambda: os.path.exists(yedek) and os.remove(yedek))
        kayit.load_saved_villages()
        self.assertEqual(kayit.session("bakgoc")["version"], version_code)
        with open(yol, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["version"], version_code)
        with open(yedek, encoding="utf-8") as f:
            self.assertEqual(json.load(f), eski)


if __name__ == "__main__":
    unittest.main()
