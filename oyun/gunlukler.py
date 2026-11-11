"""saves/ altındaki hata ayıklama günlükleri: sınırlı büyür (denetim SNK-09, DGV-07).

Günlükler (komut_gunlugu.jsonl, http_gunlugu.jsonl, istemci_hatalari.jsonl, sunucu_hatalari.log) hiç
döndürülmüyordu: uzun oyunda ve Android'in bulut yedeğinde sınırsız büyüyordu. Dosya EN_BUYUK'u aşacaksa bir
önceki `<ad>.1` olarak saklanır ve yeni dosyaya başlanır; böylece bir günlük en çok ~2 × EN_BUYUK yer tutar. Tek
kayıt SATIR_SINIRI'nda kesilir (istemcinin gönderdiği hata gövdesi gibi dışarıdan gelen metin için).
"""

import os
import threading

from oyun.yollar import SAVES_DIR

EN_BUYUK = 2 * 1024 * 1024
SATIR_SINIRI = 16 * 1024
_kilit = threading.Lock()


def ekle(ad: str, metin: str) -> None:
    """saves/<ad> dosyasına metni ekler; yazılamazsa sessizce geçer (günlük oyunu durdurmaz)."""
    if len(metin) > SATIR_SINIRI:
        metin = metin[:SATIR_SINIRI] + " …[kesildi]\n"
    yol = os.path.join(SAVES_DIR, ad)
    try:
        with _kilit:
            os.makedirs(SAVES_DIR, exist_ok=True)
            try:
                boyut = os.path.getsize(yol)
            except OSError:
                boyut = 0
            if boyut and boyut + len(metin.encode("utf-8")) > EN_BUYUK:
                os.replace(yol, yol + ".1")
            with open(yol, "a", encoding="utf-8") as f:
                f.write(metin)
    except OSError:
        pass
