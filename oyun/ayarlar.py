"""Kullanıcı ayarları: `ayarlar.json` ve üstüne binen `ayarlar.yerel.json`.

ayarlar.json elle düzenlenir ve depoda izlenir; sunucu ona hiç yazmaz. Sunucunun kendi değiştirdiği ayarlar (sayfadan
seçilen hız, ONR-01) ayarlar.yerel.json'a yazılır (.gitignore'da). Aynı anahtar ikisinde de varsa yerel olan geçer.
"""

import json
import os
import tempfile

from oyun import yollar


def _dosya_oku(yol) -> dict:
    with open(yol, encoding="utf-8-sig") as f:
        veri = json.load(f)
    if not isinstance(veri, dict):
        raise ValueError("JSON nesnesi değil")
    return veri


def oku() -> dict:
    """ayarlar.json'u, üstüne ayarlar.yerel.json'u bindirerek okur; olmayan ya da bozuk dosya atlanır."""
    veri = {}
    for yol in (yollar.AYARLAR, yollar.AYARLAR_YEREL):
        if not os.path.exists(yol):
            continue
        try:
            veri.update(_dosya_oku(yol))
        except (ValueError, OSError) as hata:
            print(f" ! {yol} okunamadi ({hata}); bu dosyanin ayarlari kullanilmayacak")
    return veri


def yaz(guncelleme: dict) -> None:
    """ayarlar.yerel.json'daki anahtarları günceller, ötekileri korur (ONR-01). Önce geçici dosyaya yazılır, sonra
    yerine konur: yazma yarıda kalırsa eski dosya bozulmaz. Okunamayan (bozuk) dosyanın üzerine yazılmaz."""
    yol = yollar.AYARLAR_YEREL
    if os.path.exists(yol):
        try:
            veri = _dosya_oku(yol)
        except (ValueError, OSError) as hata:
            raise ValueError(f"{yol} okunamadı, üzerine yazılmadı: {hata}") from hata
    else:
        veri = {}
    veri.update(guncelleme)
    klasor = os.path.dirname(yol) or "."
    fd, gecici = tempfile.mkstemp(prefix=".ayarlar-", suffix=".json", dir=klasor)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(gecici, yol)
    except BaseException:
        if os.path.exists(gecici):
            os.remove(gecici)
        raise
