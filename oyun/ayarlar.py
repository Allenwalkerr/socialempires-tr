"""Kullanıcı ayarları (`ayarlar.json`)."""

import json
import os
import tempfile

from oyun import yollar


def oku() -> dict:
    """ayarlar.json'u okur; dosya yoksa veya bozuksa boş sözlük döner."""
    if not os.path.exists(yollar.AYARLAR):
        return {}
    try:
        with open(yollar.AYARLAR, encoding="utf-8-sig") as f:
            return json.load(f)
    except (ValueError, OSError) as hata:
        print(f" ! {yollar.AYARLAR} okunamadi ({hata}); varsayilan ayarlar kullanilacak")
        return {}


def yaz(guncelleme: dict) -> None:
    """ayarlar.json'daki anahtarları günceller, ötekileri korur (ONR-01). Önce geçici dosyaya yazılır, sonra
    yerine konur: yazma yarıda kalırsa eski dosya bozulmaz. Okunamayan (bozuk) dosyanın üzerine yazılmaz."""
    if os.path.exists(yollar.AYARLAR):
        try:
            with open(yollar.AYARLAR, encoding="utf-8-sig") as f:
                veri = json.load(f)
        except (ValueError, OSError) as hata:
            raise ValueError(f"{yollar.AYARLAR} okunamadı, üzerine yazılmadı: {hata}") from hata
    else:
        veri = {}
    veri.update(guncelleme)
    klasor = os.path.dirname(yollar.AYARLAR) or "."
    fd, gecici = tempfile.mkstemp(prefix=".ayarlar-", suffix=".json", dir=klasor)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(gecici, yollar.AYARLAR)
    except BaseException:
        if os.path.exists(gecici):
            os.remove(gecici)
        raise
