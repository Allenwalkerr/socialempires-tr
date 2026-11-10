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


if __name__ == "__main__":
    unittest.main()
