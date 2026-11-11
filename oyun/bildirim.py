"""Android bildirimleri (ONR-03, KAR-21, KAR-23): uygulama kapalıyken yerel bildirim.

Sahibinin onayladığı tanım: üretim hazır (KAR-23: oyunda kendi kendine biten inşaat yok, yerine üretim), eğitim ya da
kuyruk bitti, kalkan bitiyor, saldırıya uğradın. Zamanlar oyunun sürelerinden hesaplanır; bildirim internetsiz çalışır.

İki yol:
- `yaklasan`: zamanı önceden belli olanlar. Uygulama arka plana geçerken (MainActivity.onStop) bir kez hesaplanır,
  Android'in zamanlayıcısına (AlarmManager) kurulur; uygulama ya da sunucu kapansa da zamanında gelir. Uygulama yeniden
  öne gelince iptal edilir.
- `saldiri`: bot akınları yalnızca sunucu çalışırken olur (oyun.dunya). Uygulama arka plandayken sunucu sürer; akın
  olunca `dinleyici` çağrılır (Android'de android_giris kurar). Masaüstünde dinleyici yoktur, hiçbir şey olmaz.

Hesaplar "sen yokken" özetiyle aynıdır (oyun.yokken: kuyruklar, uretimler); kalkan pvp_yeni.kalkan_bitisi'nden.
"""

from datetime import datetime

from oyun import yokken
from oyun.takvim import TURKIYE

GRUP = 10 * 60  # bu kadar yakın olaylar tek bildirimde birleşir (bildirim yağmuru olmasın)
EN_COK = 20  # kurulacak bildirim sayısının üst sınırı
KALKAN_UYARISI = 60 * 60  # kalkan bitmeden bu kadar önce uyarılır
EN_YAKIN = 60  # bundan yakın olay kurulmaz (uygulama kapanırken hemen çalan bildirim olmasın)

dinleyici = None  # saldırı bildirimi: işlev(metin); Android'de android_giris kurar


def _ad(kimlik, ceviriler):
    return yokken.birim_adi(kimlik, ceviriler)


def _sayili(adetler, ceviriler):
    return ", ".join(f"{adet} {_ad(k, ceviriler)}" for k, adet in sorted(adetler.items()))


def olaylar(kayit, simdi, ceviriler=None):
    """(zaman, tür, kimlik, adet): şimdiden sonraki olaylar, zamana göre."""
    from oyun.pvp_yeni import kalkan_bitisi
    cikti = []
    for kimlik, hazir in yokken.uretimler(kayit):
        if hazir > simdi:
            cikti.append((hazir, "uretim", kimlik, 1))
    for kimlik, ts, adet, sure in yokken.kuyruklar(kayit):
        bitis = ts + adet * sure  # kuyruğun son birimi (yokken.kuyruklar)
        if adet > 0 and bitis > simdi:
            cikti.append((bitis, "egitim", kimlik, adet))
    kalkan = kalkan_bitisi(kayit)
    if kalkan > simdi:
        cikti.append((max(simdi + EN_YAKIN, kalkan - KALKAN_UYARISI), "kalkan", kalkan, 1))
    return sorted(c for c in cikti if c[0] >= simdi + EN_YAKIN)


def _metin(grup, ceviriler):
    uretim, egitim, parcalar = {}, {}, []
    for _, tur, kimlik, adet in grup:
        hedef = uretim if tur == "uretim" else egitim if tur == "egitim" else None
        if hedef is not None:
            hedef[kimlik] = hedef.get(kimlik, 0) + adet
    if uretim:
        parcalar.append("Üretim hazır: " + _sayili(uretim, ceviriler))
    if egitim:
        parcalar.append("Eğitim bitti: " + _sayili(egitim, ceviriler))
    for zaman, tur, bitis, _ in grup:
        if tur == "kalkan":
            saat = datetime.fromtimestamp(bitis, TURKIYE).strftime("%H:%M")
            parcalar.append(f"Kalkan bitiyor (bitiş {saat})")
    return ". ".join(parcalar) + "."


def yaklasan(kayit, simdi, ceviriler=None):
    """[{kimlik, zaman, metin}]: kurulacak bildirimler. Grubun ilk olayından GRUP içinde kalan üretim ve eğitim olayları
    tek bildirimde birleşir; bildirim grubun SON olayının zamanında gelir, böylece "hazır/bitti" dediği her şey o anda
    gerçekten hazırdır (#62 incelemesi; en çok GRUP kadar gecikir). Kalkan uyarısı birleşmez, kendi zamanında gelir."""
    gruplar, kalkanlar = [], []
    for olay in olaylar(kayit, simdi, ceviriler):
        if olay[1] == "kalkan":
            kalkanlar.append([olay])
        elif gruplar and olay[0] - gruplar[-1][0][0] < GRUP:
            gruplar[-1].append(olay)
        else:
            gruplar.append([olay])
    hepsi = sorted(gruplar + kalkanlar, key=lambda g: g[-1][0])[:EN_COK]
    return [{"kimlik": i + 1, "zaman": grup[-1][0], "metin": _metin(grup, ceviriler or {})}
            for i, grup in enumerate(hepsi)]


def android_listesi():
    """MainActivity.onStop'un kuracağı bildirimler (JSON metni): en son oynayan oyuncunun kaydından."""
    import json
    from oyun import turkce
    from oyun.kayit import save_lock, session
    from oyun.ekonomi import timestamp_now
    uid = yokken.son_oyuncu()
    with save_lock:
        kayit = session(uid) if uid else None
        if not kayit or (kayit.get("playerInfo") or {}).get("bot"):
            return "[]"
        return json.dumps(yaklasan(kayit, timestamp_now(), turkce.cevirileri_yukle()), ensure_ascii=False)


def saldiri(saldiran_ad, kazandi, ganimet):
    """Oyuncu bot akınına uğradı (dunya._savas); dinleyici varsa bildirim gider. Hata oyunu durdurmaz."""
    if dinleyici is None:
        return
    metin = (f"{saldiran_ad} akın etti ve {ganimet} kaynak yağmaladı." if kazandi
             else f"{saldiran_ad} akın etti, saldırı püskürtüldü.")
    try:
        dinleyici(metin)
    except Exception as hata:  # Android tarafındaki bir hata bot dünyasını durdurmasın
        print(f" ! Saldiri bildirimi gonderilemedi: {hata}")
