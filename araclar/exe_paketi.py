"""Tek dosyalık Windows programı (.exe) üretir: PyInstaller --onefile, giriş araclar/exe_giris.py.

Oyun dosyaları ve Ruffle (SHA-512 denetlenmiş paket) .exe'nin içine konur; Social Point varlıkları konmaz (ilk
açılışta indirilir). Yanına SHA-256 özeti yazılır. PyInstaller yalnızca kendi işletim sisteminin programını üretir:
Windows .exe'si Windows'ta (GitHub Actions windows-latest) derlenir; başka sistemde aynı betik o sistemin tek dosyalık
programını üretir (yerel deneme için).

Kullanım:
    pip install -r requirements.txt pyinstaller==6.11.1
    python araclar/exe_paketi.py [--ad SocialEmpiresTR] [--cikti dist] [--ruffle yol|yok]
"""

import argparse
import base64
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from oyun import ruffle  # noqa: E402

# Pakete girecek proje klasörleri ve dosyaları (KOK'a göre); Windows zip paketiyle aynı içerik
KLASORLER = ["templates", "config", "ceviri", "villages", "stub", "mods", os.path.join("assets", "fonts")]
DOSYALAR = ["ayarlar.json", "LICENSE"]
AYRAC = ";" if os.name == "nt" else ":"


def ruffle_paketi(kaynak=None):
    if kaynak:
        with open(kaynak, "rb") as f:
            veri = f.read()
    else:
        print(f"[+] Ruffle indiriliyor: {ruffle.PAKET_URL}")
        with urllib.request.urlopen(ruffle.PAKET_URL, timeout=300) as yanit:
            veri = yanit.read()
    if base64.b64encode(hashlib.sha512(veri).digest()).decode() != ruffle.PAKET_SHA512:
        raise SystemExit("Ruffle paketinin SHA-512 özeti tutmuyor")
    return veri


def komut(ad, cikti, gecici, ruffle_yolu):
    k = [sys.executable, "-m", "PyInstaller", "--onefile", "--console", "--noconfirm", "--clean",
         "--name", ad, "--distpath", cikti, "--workpath", os.path.join(gecici, "is"),
         "--specpath", gecici, "--paths", KOK,
         # oyun/ modülleri birbirini döngüsel ve yol modüllerinden içe aktarır (S-46): hepsi pakete girsin
         "--collect-submodules", "oyun", "--hidden-import", "waitress"]
    for klasor in KLASORLER:
        k += ["--add-data", f"{os.path.join(KOK, klasor)}{AYRAC}{klasor}"]
    for dosya in DOSYALAR:
        k += ["--add-data", f"{os.path.join(KOK, dosya)}{AYRAC}."]
    if ruffle_yolu:
        k += ["--add-data", f"{ruffle_yolu}{AYRAC}."]
    return k + [os.path.join(KOK, "araclar", "exe_giris.py")]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ad", default="SocialEmpiresTR")
    ap.add_argument("--cikti", default=os.path.join(KOK, "dist"))
    ap.add_argument("--ruffle", help="Ruffle paketi (.tgz) yolu; 'yok' pakete koymaz, verilmezse indirilir")
    secenek = ap.parse_args()
    cikti = os.path.abspath(secenek.cikti)
    os.makedirs(cikti, exist_ok=True)
    gecici = tempfile.mkdtemp(prefix="se-exe-")
    try:
        ruffle_yolu = None
        if secenek.ruffle != "yok":
            ruffle_yolu = os.path.join(gecici, "ruffle-paketi.tgz")
            with open(ruffle_yolu, "wb") as f:
                f.write(ruffle_paketi(secenek.ruffle))
        subprocess.run(komut(secenek.ad, cikti, gecici, ruffle_yolu), check=True, cwd=KOK)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    program = os.path.join(cikti, secenek.ad + (".exe" if os.name == "nt" else ""))
    with open(program, "rb") as f:
        ozet = hashlib.sha256(f.read()).hexdigest()
    with open(program + ".sha256", "w", encoding="utf-8") as f:
        f.write(f"{ozet}  {os.path.basename(program)}\n")
    print(f"[+] {program} ({os.path.getsize(program) // (1024 * 1024)} MB)\n    SHA-256 {ozet}")


if __name__ == "__main__":
    main()
