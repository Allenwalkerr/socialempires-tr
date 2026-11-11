"""Hata ayıklama günlükleri sınırlı büyür (oyun/gunlukler.py).

Beklenen davranışın kaynağı bağımsız denetimin SNK-09 ve DGV-07 bulgusu (docs/denetim/): günlükler hiç
döndürülmüyordu; Android'in bulut yedeğinde 25 MB sınırı aşılınca bütün yedek düşer (android/.../yedek.xml yorumu).
"""

import json
import os
import tempfile
import unittest
from unittest import mock

from ortak import KOK  # noqa: F401

from oyun import gunlukler
from oyun import sunucu as server

DINAMIK = "/dynamic.flash1.dev.socialpoint.es/appsfb/socialempiresdev/srvempires"


class Gunlukler(unittest.TestCase):
    def setUp(self):
        self.klasor = tempfile.mkdtemp()
        for ad, deger in (("SAVES_DIR", self.klasor), ("EN_BUYUK", 1000), ("SATIR_SINIRI", 300)):
            yama = mock.patch.object(gunlukler, ad, deger)
            yama.start()
            self.addCleanup(yama.stop)

    def boyut(self, ad):
        yol = os.path.join(self.klasor, ad)
        return os.path.getsize(yol) if os.path.exists(yol) else 0

    def test_sinirda_bir_eski_kopya_tutulur(self):
        for i in range(100):
            gunlukler.ekle("g.jsonl", json.dumps({"i": i, "dolgu": "x" * 80}) + "\n")
            self.assertLessEqual(self.boyut("g.jsonl"), 1000)
            self.assertLessEqual(self.boyut("g.jsonl.1"), 1000)
        self.assertEqual(sorted(os.listdir(self.klasor)), ["g.jsonl", "g.jsonl.1"])
        with open(os.path.join(self.klasor, "g.jsonl"), encoding="utf-8") as f:
            self.assertEqual(json.loads(f.read().splitlines()[-1])["i"], 99)  # en yeni kayıt kaybolmaz

    def test_istemci_hatasi_govdesi_kesilir(self):
        govde = "0" * 64 + ";" + json.dumps({"error": "y" * 5000})  # istemcinin "<imza>;<json>" biçimi
        cevap = server.app.test_client().post(f"{DINAMIK}/report_error.php", data={"data": govde})
        self.assertEqual(cevap.status_code, 200)
        self.assertLessEqual(self.boyut("istemci_hatalari.jsonl"), 300 + 20)

    def test_komut_paketinin_her_satiri_ayri_ve_gecerli_json(self):
        """#46 incelemesi: satır sınırı paketin tamamına uygulanıyordu; uzun bir argüman sonraki komutları, KAR-18'in
        'red' satırı dahil, günlükten düşürürdü ve kesilen satır bozuk JSON kalırdı."""
        from oyun import komutlar
        with mock.patch.object(gunlukler, "EN_BUYUK", 10 ** 6):
            komutlar._gunluge_yaz("test", [["store_add_items", ["9" * 1000], None],
                                           ["buy", [1, 2, 3], "yetersiz: wood: 0 < 30"]])
        with open(os.path.join(self.klasor, "komut_gunlugu.jsonl"), encoding="utf-8") as f:
            satirlar = [json.loads(s) for s in f]
        self.assertEqual([s["cmd"] for s in satirlar], ["store_add_items", "buy"])
        self.assertTrue(satirlar[0]["args"].startswith("[kesildi"))
        self.assertEqual(satirlar[1]["red"], "yetersiz: wood: 0 < 30")

    def test_komut_gunlugu_de_sinirli(self):
        from oyun import komutlar
        for _ in range(60):
            komutlar._gunluge_yaz("test", [["rt_publish_score", [1] * 20, None]])
        self.assertLessEqual(self.boyut("komut_gunlugu.jsonl"), 1000)
        self.assertTrue(os.path.exists(os.path.join(self.klasor, "komut_gunlugu.jsonl.1")))


if __name__ == "__main__":
    unittest.main()
