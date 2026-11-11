"""Sayfa şablonlarında resim ve dış bağlantı kuralları (denetim TRA-07).

Kaynak: HTML standardı (img'in src'si zorunlu; alt'ı olmayan resim ekran okuyucuya adını okutur) ve
target=_blank bağlantısında rel=noopener (açılan sayfa window.opener ile bu sayfayı yönlendiremesin).
"""

import glob
import os
import re
import unittest

from ortak import KOK


class SayfaHtml(unittest.TestCase):
    def sablonlar(self):
        for yol in sorted(glob.glob(os.path.join(KOK, "templates", "*.html"))):
            with open(yol, encoding="utf-8") as f:
                yield os.path.basename(yol), f.read()

    def test_her_resmin_kaynagi_ve_alt_metni_var(self):
        for ad, html in self.sablonlar():
            for img in re.findall(r"<img\b[^>]*>", html):
                self.assertRegex(img, r"\bsrc=", f"{ad}: {img}")
                self.assertRegex(img, r"\balt=", f"{ad}: {img}")

    def test_yeni_sekmede_acilan_baglanti_noopener(self):
        for ad, html in self.sablonlar():
            for a in re.findall(r"<a\b[^>]*target=[\"']_blank[\"'][^>]*>", html):
                self.assertRegex(a, r"rel=[\"'][^\"']*noopener", f"{ad}: {a}")


if __name__ == "__main__":
    unittest.main()
