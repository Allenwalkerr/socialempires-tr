"""Bayram hedefleri (GEC-07, ICR-01): takvimdeki her etkinlik sürerken istemciye geçici bir hedef gider.

1.4.07 istemcisinin hedef sistemi (bayt kodu, docs/inceleme/1407-hedefler.md):
- Hedefler yalnızca açılışta config'in `goals` listesinden okunur (Base/loadGameConfigSuccess →
  GoalsManager.initMissions); oturum içinde eklenen hedef ancak sonraki girişte görünür.
- `orders` 0 olan hedef atlanır (GoalsManager/_load@64-70); hedefler `order` farkıyla sıralanır
  (goalComparison), en çok 15 tamamlanmamış hedef etkindir. Var olanların hepsi 1'dir; bayram hedefi -1 ile başa gelir.
- Tamamlanan ve ödülü alınanlar privateState.completedMissions / rewardedMissions'ta kimlikle tutulur; config'te
  olmayan kimlik yok sayılır. Bu yüzden bayram bitince hedef listeden çıkar, kayıttaki kimlik zararsız kalır.
- Ödül hedefin `reward`'ı kadar altındır; istemci kendi config'inden ekler, sunucu reward_mission'da aynısını yazar.

Kimlik her etkinlik gerçekleşmesine özgüdür (her yıl yeni hedef, ödül bir kez): 10 000 000 + no × 100 000 + başlangıç
gününün 1 Ocak 2000'den uzaklığı (gün). `no`, config/takvim.json'daki kalıcı numaradır: dosyada sıra değişse de kimlik
kaymaz; başlangıç günü bir yıla düşen iki bayramı da ayırır (2033'te iki Ramazan Bayramı; #56 incelemesi). Var olan hedef
kimlikleri 0 … 1008; en büyük kimlik (no 99, 2099) 2^31'in çok altında.

Hedef: etkinliğin mağazaya açtığı tema setinden (config/tema_setleri.json) bir yapı kurmak (`built_id`; setlerin
bütün eşyaları bina). Resim ve karakter oyunun kendi hedef resimleridir: hedef 32'nin ("Build 5 decorations")
goal_032.jpg ve nino_07.png'si (CLAUDE.md: kendi görsel üretilmez). Ödül 500 altın: goals.json'daki en yüksek ödül.
"""

import json
from datetime import date, timedelta

from oyun import takvim
from oyun import config
from oyun.config import tema_setleri

TABAN = 10_000_000
NO_ADIMI = 100_000
GUN_SIFIRI = date(2000, 1, 1)
ODUL = 500
GEC_ODUL_GUNU = 30  # bayramın son günü tamamlanan hedefin ödülü sonraki girişte de gelebilir
RESIM, KARAKTER = "goal_032.jpg", "nino_07.png"


AYLAR = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım",
         "Aralık")


def _tarih(iso):
    yil, ay, gun = (int(x) for x in iso.split("-"))
    return "%d %s" % (gun, AYLAR[ay - 1])


def hedef_kimligi(no, baslangic):
    return TABAN + int(no) * NO_ADIMI + (baslangic - GUN_SIFIRI).days


def _set_esyalari(setler_adlari):
    """Etkinliğin hedefi olabilir mi: mağazada tema setleri açık olacak (ayarlar.json magaza_tema_setleri false
    değil; #56 incelemesi: kapalıyken hedef tamamlanamazdı) ve setlerinde eşya olacak. Hedef gönderimi ile ödül aynı
    koşula bakar (ayrışırsa istemciye hiç gitmemiş bir hedefin ödülü alınabilirdi)."""
    if config.tema_seti_kipi() is False:
        return []
    setler = tema_setleri()
    return sorted({int(i) for ad in setler_adlari for i in setler.get(ad, [])})


def _hedef(etkinlik):
    ids = _set_esyalari(etkinlik["setler"])
    if not ids or not isinstance(etkinlik.get("no"), int):
        return None
    set_adi = " ya da ".join(etkinlik["setler"])
    return {
        "id": hedef_kimligi(etkinlik["no"], date.fromisoformat(etkinlik["baslangic"])), "types": "built_id", "orders": -1, "min_level": 1, "reward": ODUL,
        "title": "%s kutlu olsun!" % etkinlik["ad"],
        "description": "%s şerefine mağazadaki %s setinden bir yapı kur. (Son gün: %s.)"
                       % (etkinlik["ad"], set_adi, _tarih(etkinlik["son_gun"])),
        "instructions": "", "image": RESIM, "characters": KARAKTER,
        "params": json.dumps({"ids": ids, "ammount": 1, "upgrade_from": -1}),
    }


def aktif_hedefler(gun=None):
    """Bugün süren etkinliklerin hedefleri (kimlik sırasıyla). True kipinde setler hep açık, "takvim" kipinde
    etkinlik sürerken açık (config.takvimdeki_setler); false kipinde hedef yok (_set_esyalari)."""
    cikti = [h for h in (_hedef(e) for e in takvim.etkinlikler(gun, ileri=0) if e["aktif"]) if h]
    return sorted(cikti, key=lambda h: h["id"])


def bayram_kimligi_mi(hedef_id):
    return int(hedef_id) >= TABAN


def odul(hedef_id, gun=None):
    """Bayram hedefinin ödülü; verilemezse 0. Kimlikteki etkinlik numarası takvimde olmalı, kimlikteki başlangıç günü o
    etkinliğin gerçek bir başlangıcı olmalı, etkinlik başlamış ve en çok GEC_ODUL_GUNU gün önce bitmiş olmalı, hedefi
    gönderilir olmalı (_set_esyalari): elle yazılmış bir reward_mission gelecek, uydurma ya da hiç gönderilmemiş bir
    hedeften altın alamaz (KAR-17)."""
    hedef_id, gun = int(hedef_id), gun or takvim.bugun()
    if hedef_id < TABAN:
        return 0
    no, gunler = divmod(hedef_id - TABAN, NO_ADIMI)
    baslangic = GUN_SIFIRI + timedelta(days=gunler)
    etkinlik = next((e for e in takvim._yukle().get("etkinlikler", []) if e.get("no") == no), None)
    if etkinlik is None or not _set_esyalari(etkinlik.get("setler", [])):
        return 0
    for merkez_yili in (baslangic.year, baslangic.year + 1):  # Yılbaşı bir önceki yılın Aralık'ında başlar
        for bas, bitis in takvim._araliklar(etkinlik, merkez_yili):
            if bas == baslangic and bas <= gun < bitis + timedelta(days=GEC_ODUL_GUNU):
                return ODUL
    return 0
