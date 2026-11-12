# -*- coding: utf-8 -*-
"""Oyun hızı (zaman ölçeği) ayarı.

Oyun istemcisi üretim/inşaat sürelerini `game_config` içindeki
`activation` / `expiration` alanlarından okuyor. Bu alanları istemciye
gönderirken ölçeğe bölerek oyunu hızlandırıyoruz; sunucudaki ve
kayıttaki değerler değişmiyor.

Ayar sırası:
1. `TIME_SCALE` ortam değişkeni
2. `ayarlar.json` içindeki `zaman_olcegi` (ör. 3.0)
3. Varsayılan 1.0 (normal hız)

Örnek: 3.0 => süreler üçte bire iner (6 saatlik üretim 2 saat olur).

Ölçeklenenler: eşyaların config.SURE_ALANLARI'ndaki süreleri (activation, expiration, training_time,
sm_training_time; olcekle'nin kuralıyla) ve bot dünyasının akışı. Ölçeklenmeyenler (denetim EKF-04, DNT-25): istemcinin
kendi sabiti COLLECT_MINUTES (üretim seçimi 5/60/240/480 dk; değişken üretimli binalar), config globals'taki
COLLECT_HELP_SECONDS (arkadaş yardımı), ATTACKS_PERIOD_HOURS ve sunucunun PvP hakkı (denge.SALDIRI_PERIYODU),
TIME_MACHINE. Bunlar istemcide sabit ya da gerçek saate bağlı; değiştirmek istemcide ayrı yama ister.
"""

import os

from oyun import ayarlar


def zaman_olcegi() -> float:
    ham = os.environ.get("TIME_SCALE")
    if ham is None:
        ham = ayarlar.oku().get("zaman_olcegi")

    if ham is None:
        return 1.0

    try:
        olcek = float(ham)
    except (TypeError, ValueError):
        print(f" ! Gecersiz zaman olcegi: {ham!r}; 1.0 kullanilacak")
        return 1.0

    if not (0.1 <= olcek <= 100):
        print(f" ! Zaman olcegi 0.1-100 araliginda olmali (verilen: {olcek}); 1.0 kullanilacak")
        return 1.0

    return olcek


# ONR-01: oyun sayfasındaki hız seçicinin seçenekleri (kat). Sınır yukarıdaki 0.1-100 aralığının içinde.
HIZLAR = (1, 2, 3, 5, 10)


def olcekle(sayi: float, olcek: float) -> float:
    """Ölçekli süre: istemciye giden config (config.get_client_game_config) ve sunucunun aynı süreyi bulan hesapları
    (komutlar.egitim_suresi, yokken) bunu kullanır, iki taraf aynı değeri görür (DNT-25, EKF-04).

    - 6 anlamlı basamağa yuvarlanır (önceki `.6g` ile aynı değer).
    - En az 1, ama asıl süreden uzun değil: istemci training_time ve sm_training_time'ı int yuvasında tutar
      (1.4.07 StaticData), "0.5" orada 0 olur ve eğitim anında biterdi (10 katta 63 birim). Tabanda 1'den kısa süreler
      (ör. öğe 144 activation 0,36) olduğu gibi kalır.
    """
    if sayi <= 0 or olcek == 1.0:
        return sayi
    return max(float(f"{sayi / olcek:.6g}"), min(sayi, 1.0))


def metin(sayi: float) -> str:
    """Config'e yazılan biçim: üstel gösterim yok ("1.728e+06" yerine "1728000"), gereksiz sıfır yok."""
    return f"{sayi:.6f}".rstrip("0").rstrip(".")


def ortamdan_mi() -> bool:
    """Hız TIME_SCALE ortam değişkeniyle verildiyse sayfadan değiştirilemez (ortam ayar dosyasından önce gelir)."""
    return os.environ.get("TIME_SCALE") is not None
