# -*- coding: utf-8 -*-
"""Ekonomi ve PvP denge ayarları.

3x hızda kaynaklar hızlı biriktiği için ganimet oranı ve tavanı düşürüldü;
yeni oyuncular 24 saat kalkanla başlar.
"""

GANIMET_ORANI = 0.10          # kurbanın kaynağının en fazla %10'u
GANIMET_TAVANI = 50000        # kaynak başına üst sınır
YENI_OYUNCU_KALKANI = 24 * 3600
# İstemcinin kendi sabitleri (1.4.07 Config/<sınıf>: ATTACKS_MAX = 3, ATTACKS_PERIOD_HOURS = 6; Base/processAttacks ve
# IsoEngine/getNumAttacks bunları okur). Config globals'taki ATTACKS_PERIOD_MAX/_HOURS istemcide hiç okunmuyor
# (loadGameConfigSuccess'te yok): sunucu onlara bağlansaydı config değişince istemciden ayrılırdı (DNT-28, EKF-09).
# Tek kaynak burası; oyun.pvp buradan alır.
SALDIRI_HAKKI = 3
SALDIRI_PERIYODU = 6 * 3600
