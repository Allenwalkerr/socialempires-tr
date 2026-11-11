"""Bayram hedefleri (GEC-07, ICR-01): takvimdeki her etkinlik sürerken istemciye geçici bir hedef gider.

1.4.07 istemcisinin hedef sistemi (bayt kodu, docs/inceleme/1407-hedefler.md):
- Hedefler yalnızca açılışta config'in `goals` listesinden okunur (Base/loadGameConfigSuccess →
  GoalsManager.initMissions); oturum içinde eklenen hedef ancak sonraki girişte görünür.
- `orders` 0 olan hedef atlanır (GoalsManager/_load@64-70); hedefler `order` farkıyla sıralanır
  (goalComparison), en çok 15 tamamlanmamış hedef etkindir. Var olanların hepsi 1'dir; bayram hedefi -1 ile başa gelir.
- Tamamlanan ve ödülü alınanlar privateState.completedMissions / rewardedMissions'ta kimlikle tutulur; config'te
  olmayan kimlik yok sayılır. Bu yüzden bayram bitince hedef listeden çıkar, kayıttaki kimlik zararsız kalır.
- Ödül hedefin `reward`'ı kadar altındır; istemci kendi config'inden ekler, sunucu reward_mission'da aynısını yazar.

Kimlik yıla ve etkinliğe göre değişir (her yıl yeni hedef, ödül bir kez): 900000 + (yıl − 2000) × 100 + etkinlik sırası
(config/takvim.json'daki sırası, 1'den). Var olan hedef kimlikleri 0 … 1008; eski görev numaraları da 1008'in altında.

Hedef: etkinliğin mağazaya açtığı tema setinden (config/tema_setleri.json) bir yapı kurmak (`built_id`; setlerin
bütün eşyaları bina). Resim ve karakter oyunun kendi hedef resimleridir: hedef 32'nin ("Build 5 decorations")
goal_032.jpg ve nino_07.png'si (CLAUDE.md: kendi görsel üretilmez). Ödül 500 altın: goals.json'daki en yüksek ödül.
"""

import json
from datetime import timedelta

from oyun import takvim
from oyun import config
from oyun.config import tema_setleri

TABAN = 900000
ODUL = 500
GEC_ODUL_GUNU = 30  # bayramın son günü tamamlanan hedefin ödülü sonraki girişte de gelebilir
RESIM, KARAKTER = "goal_032.jpg", "nino_07.png"


AYLAR = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım",
         "Aralık")


def _tarih(iso):
    yil, ay, gun = (int(x) for x in iso.split("-"))
    return "%d %s" % (gun, AYLAR[ay - 1])


def hedef_kimligi(yil, sira):
    return TABAN + (int(yil) - 2000) * 100 + int(sira)


def _etkinlik_sirasi():
    return {e["ad"]: i + 1 for i, e in enumerate(takvim._yukle().get("etkinlikler", []))}


def _hedef(etkinlik, sira):
    setler = tema_setleri()
    ids = sorted({int(i) for ad in etkinlik["setler"] for i in setler.get(ad, [])})
    if not ids:
        return None
    yil = int(etkinlik["baslangic"][:4])
    set_adi = " ya da ".join(etkinlik["setler"])
    return {
        "id": hedef_kimligi(yil, sira), "types": "built_id", "orders": -1, "min_level": 1, "reward": ODUL,
        "title": "%s kutlu olsun!" % etkinlik["ad"],
        "description": "%s şerefine mağazadaki %s setinden bir yapı kur. (Son gün: %s.)"
                       % (etkinlik["ad"], set_adi, _tarih(etkinlik["son_gun"])),
        "instructions": "", "image": RESIM, "characters": KARAKTER,
        "params": json.dumps({"ids": ids, "ammount": 1, "upgrade_from": -1}),
    }


def aktif_hedefler(gun=None):
    """Bugün süren etkinliklerin hedefleri (kimlik sırasıyla). Mağazada tema setleri kapalıysa
    (ayarlar.json magaza_tema_setleri: false) hedef tamamlanamazdı; o kipte hedef yok (#56 incelemesi). True kipinde
    setler hep açık, "takvim" kipinde etkinlik sürerken açık (config.takvimdeki_setler)."""
    if config.tema_seti_kipi() is False:
        return []
    sira = _etkinlik_sirasi()
    cikti = []
    for e in takvim.etkinlikler(gun, ileri=0):
        if e["aktif"] and e["ad"] in sira:
            h = _hedef(e, sira[e["ad"]])
            if h:
                cikti.append(h)
    return sorted(cikti, key=lambda h: h["id"])


def bayram_kimligi_mi(hedef_id):
    return int(hedef_id) >= TABAN


def odul(hedef_id, gun=None):
    """Bayram hedefinin ödülü; verilemezse 0. Kimlik takvimdeki bir etkinliğe ve yıla denk gelmeli, o yılki etkinlik
    başlamış ve en çok GEC_ODUL_GUNU gün önce bitmiş olmalı: elle yazılmış bir reward_mission gelecek ya da hiç
    açılmamış bir yılın hedefinden altın alamaz (KAR-17)."""
    hedef_id, gun = int(hedef_id), gun or takvim.bugun()
    yil, sira = 2000 + (hedef_id - TABAN) // 100, (hedef_id - TABAN) % 100
    etkinlikler = takvim._yukle().get("etkinlikler", [])
    if hedef_id < TABAN or not 1 <= sira <= len(etkinlikler):
        return 0
    etkinlik = etkinlikler[sira - 1]
    if not any(tema_setleri().get(ad) for ad in etkinlik.get("setler", [])):
        return 0
    for merkez_yili in (yil, yil + 1):  # Yılbaşı bir önceki yılın Aralık'ında başlar; kimlik başlangıç yılını taşır
        for baslangic, bitis in takvim._araliklar(etkinlik, merkez_yili):
            if baslangic.year == yil and baslangic <= gun < bitis + timedelta(days=GEC_ODUL_GUNU):
                return ODUL
    return 0
