"""Tek dosyalık Windows programının (.exe) girişi. araclar/exe_paketi.py bunu PyInstaller ile paketler.

Oyun dosyaları (oyun/, templates/, config/...) .exe'nin içindedir ve her açılışta geçici bir klasöre açılır
(sys._MEIPASS). Kayıtlar, ayarlar, modlar ve indirilen varlıklar .exe'nin yanında durur (oyun/yollar.py BASE_DIR):
.exe yenisiyle değiştirilince korunur. İlk açılışta ayarlar.json ve mods/ yanına kopyalanır (var olanlara dokunulmaz),
Ruffle pakette gelir ve SHA-512 denetlenerek açılır. Sunucu hazır olunca tarayıcı kendiliğinden açılır.
"""

import os
import shutil
import sys
import threading
import time
import urllib.request
import webbrowser

DONDURULMUS = getattr(sys, "frozen", False)
VERI = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TABAN = os.path.dirname(sys.executable) if DONDURULMUS else VERI
RUFFLE_PAKETI = os.path.join(VERI, "ruffle-paketi.tgz")
ADRES = "http://127.0.0.1:5050/"


def _icerigi_kopyala(kaynak, hedef):
    for klasor, _, dosyalar in os.walk(kaynak):
        hedef_klasor = os.path.join(hedef, os.path.relpath(klasor, kaynak))
        os.makedirs(hedef_klasor, exist_ok=True)
        for ad in dosyalar:
            shutil.copyfile(os.path.join(klasor, ad), os.path.join(hedef_klasor, ad))


def hazirla(taban=TABAN, veri=VERI):
    """İlk açılışta ayarları ve modları yazılabilir klasöre kopyalar; yarıda kesilirse yarım kopya kalmaz."""
    os.makedirs(taban, exist_ok=True)
    ayar = os.path.join(taban, "ayarlar.json")
    if not os.path.exists(ayar):
        shutil.copyfile(os.path.join(veri, "ayarlar.json"), ayar + ".tmp")
        os.replace(ayar + ".tmp", ayar)
    modlar = os.path.join(taban, "mods")
    if not os.path.isdir(modlar):
        gecici = modlar + ".tmp"
        shutil.rmtree(gecici, ignore_errors=True)
        _icerigi_kopyala(os.path.join(veri, "mods"), gecici)
        os.replace(gecici, modlar)


def tarayiciyi_ac(adres=ADRES, sure=240):
    """Sunucu hazır olunca (/saglik/hazir 200) oyunu varsayılan tarayıcıda açar."""
    bitis = time.monotonic() + sure
    while time.monotonic() < bitis:
        try:
            with urllib.request.urlopen(adres + "saglik/hazir", timeout=2) as yanit:
                if yanit.status == 200:
                    webbrowser.open(adres)
                    return True
        except OSError:
            pass
        time.sleep(0.5)
    return False


def main():
    if os.name == "nt":
        os.system("title Social Empires Sunucusu")
    print("Social Empires Turkce: oyun tarayicida kendiliginden acilacak:", ADRES)
    print("Oyunu kapatmak icin bu pencereyi kapatin.")
    hazirla()
    from oyun import ruffle
    if not ruffle.hazir_mi() and os.path.exists(RUFFLE_PAKETI):
        with open(RUFFLE_PAKETI, "rb") as f:
            ruffle.hazirla(f.read())  # SHA-512 denetlenir; olmazsa ilk oyunda internetten indirilir
    if not os.environ.get("SE_TARAYICI_ACMA"):
        threading.Thread(target=tarayiciyi_ac, name="tarayici", daemon=True).start()
    from oyun.sunucu import calistir
    calistir()


if __name__ == "__main__":
    main()
