"""Oyun hızı seçici (ONR-01, KAR-21): oyun sayfasından ayarlar.json'daki `zaman_olcegi` seçilir.

Hız bütün oyunu etkiler (bot dünyası, kuyruklar, istemciye giden süreler: config.SURE_ALANLARI eğitim kuyruğunu ve
Ruh Kazanı'nı da kapsar). Bu yüzden hile paneli gibi yalnızca bu makineden ve aynı kökenden değiştirilir. İstemci
süreleri config'ten açılışta okur; sayfa seçimden sonra oyunu yeniden yükler.
"""

from flask import request

from oyun import ayarlar, zaman
from oyun.hile import _hile_izinli
from oyun.sunucu import app


@app.route("/ayar/hiz", methods=["POST"])
def hiz_sec():
    if not _hile_izinli():
        return ({"hata": "yasak"}, 403)
    if zaman.ortamdan_mi():
        return ({"hata": "hız TIME_SCALE ortam değişkeniyle verilmiş"}, 409)
    veri = request.get_json(silent=True) or {}
    olcek = veri.get("olcek")
    if isinstance(olcek, bool) or olcek not in zaman.HIZLAR:
        return ({"hata": "geçersiz hız"}, 400)
    try:
        ayarlar.yaz({"zaman_olcegi": olcek})
    except (ValueError, OSError) as hata:
        print(f" ! hiz kaydedilemedi: {hata}")  # ayrıntı yalnızca konsolda (CodeQL: hata metni dışarı verilmez)
        return ({"hata": "ayar dosyası yazılamadı"}, 500)
    return {"olcek": zaman.zaman_olcegi()}
