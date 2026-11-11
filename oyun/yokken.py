"""'Sen yokken' özeti (ONR-02, KAR-21): oyuncu döndüğünde, yokken olanların kısa listesi.

Sahibinin onayladığı tanım: botların akınları, kazanılan ve kaybedilen, biten inşaat ve eğitim, Diyar Haberleri; veri
imparatorluk günlüğünden ve haber şeridinden gelir, resimler oyunun kendi resimleridir. Oyunda kendi kendine biten inşaat
yok (config'te build_time yok; istemcinin inşaat çubuğu yalnızca görüntü, kayda bir şey yazmaz): sahibi 11.11.2026'da
yerine "üretimi hazır olan binalar"ı seçti.

"Yokken" aralığı: oyuncunun son komut paketinin (komutlar.command) zamanı ile şimdi arası. Bu zaman kaydın içinde değil,
kayıt klasöründeki son_etkinlik.json'da durur: kayda yazılsaydı her komut kaydı değiştirirdi (komut değişmezleri,
tests/test_degismezler.py). Dosya ancak değer YAZMA_ARALIGI'ndan çok değişince yazılır. Oyun sayfası oyun açılmadan, ilk
komuttan önce kurulur; bu yüzden sayfada son etkinlik bir önceki oturumun son anıdır. Kısa aralar (ESIK'ten kısa) ve
kaydı olmayan oyuncu (ilk kez) özet göstermez.

Kaynaklar:
- akınlar: privateState.attacksReceived (gunluk.savaslar, yön 'savunma'); altın: saldıranın aldığı ya da püskürtünce
  kazanılan savunma ödülü.
- eğitim: privateState.barracksQueues[qid] = {ts: sıradaki birimin başladığı an, amount, unit}; k. birim
  ts + k × süre'de biter (komutlar.pop_queue_unit ile aynı hesap; süre istemcinin gördüğü, komutlar.egitim_suresi).
- üretim: bina e[4] (son toplama/etkinleştirme) + üretim süresi'nde hazır olur (istemci Base/processMap
  collected_at = timestamp - item[4]; IsoElement/canCollect collected_at >= activation). Süre config activation'ı
  (istemciye ölçeğe bölünmüş gider); globals.COLLECT_VARIABLE_IDS'teki binalarda attrs.cp seçimi:
  COLLECT_MINUTES[cp-1] dakika (ölçeklenmez), cp 0 ise bina boşta. Doğal kaynaklar ve adalar (DOGAL_KAYNAKLAR) bina
  değildir, süreleri saniyelerdir; ayrıca istemci ek yapılarla onları erken hazır görebilir, sayılmaz.
- Diyar Haberleri: dunya.etkin.olaylar (bellekte; sunucu yeniden başlarsa eskiler yoktur).
"""

import json
import os
import threading
from datetime import datetime

from oyun import gunluk, yollar
from oyun.config import get_item_from_id
from oyun.takvim import TURKIYE

ESIK = 15 * 60
EN_COK_HABER = 8
YAZMA_ARALIGI = 60
DOSYA_ADI = "son_etkinlik.json"
_kilit = threading.Lock()
_bellek = None  # {uid: zaman}; ilk kullanımda dosyadan
_yazilan = {}


def _dosya():
    return os.path.join(yollar.SAVES_DIR, DOSYA_ADI)


def _yukle():
    global _bellek
    if _bellek is None:
        try:
            with open(_dosya(), encoding="utf-8") as f:
                veri = json.load(f)
            _bellek = {str(k): int(v) for k, v in veri.items()} if isinstance(veri, dict) else {}
        except (OSError, ValueError, TypeError):
            _bellek = {}
        _yazilan.update(_bellek)
    return _bellek


def son_etkinlik(uid):
    with _kilit:
        return _yukle().get(str(uid), 0)


def etkinlik_kaydet(uid, zaman):
    """Oyuncunun son komut zamanı; dosyaya ancak YAZMA_ARALIGI'ndan çok değişince yazılır (geçici dosya + replace)."""
    uid, zaman = str(uid), int(zaman)
    with _kilit:
        bellek = _yukle()
        bellek[uid] = zaman
        if zaman - _yazilan.get(uid, 0) < YAZMA_ARALIGI:
            return
        _yazilan[uid] = zaman
        gecici = _dosya() + ".gecici"
        try:
            with open(gecici, "w", encoding="utf-8") as f:
                json.dump(bellek, f)
            os.replace(gecici, _dosya())
        except OSError as hata:
            print(f" ! {DOSYA_ADI} yazilamadi: {hata}")


def _tam(deger):
    try:
        return int(deger)
    except (TypeError, ValueError):
        return 0


def sure_yazisi(saniye):
    saniye = max(0, int(saniye))
    gun, kalan = divmod(saniye, 86400)
    saat, kalan = divmod(kalan, 3600)
    dakika = kalan // 60
    parcalar = [f"{gun} gün"] * bool(gun) + [f"{saat} saat"] * bool(saat) + [f"{dakika} dakika"] * (not gun and bool(dakika))
    return " ".join(parcalar) or "1 dakikadan az"


def biten_egitimler(kayit, bas, son):
    """{birim kimliği: adet}: (bas, son] aralığında eğitimi biten birimler."""
    from oyun.komutlar import RUH_KARISTIRICI, egitim_suresi
    binalar = {}
    for harita in kayit.get("maps", []):
        for e in harita.get("items", []):
            if len(e) > 7 and isinstance(e[7], dict) and e[7].get("bq"):
                binalar[e[7]["bq"]] = e
    cikti = {}
    for qid, kuyruk in ((kayit.get("privateState") or {}).get("barracksQueues") or {}).items():
        if not isinstance(kuyruk, dict):
            continue
        birim = get_item_from_id(_tam(kuyruk.get("unit"))) or {}
        bina = binalar.get(qid)
        sure = egitim_suresi(birim, bool(bina) and bina[0] == RUH_KARISTIRICI)
        if sure <= 0:
            continue
        ts, adet = _tam(kuyruk.get("ts")), _tam(kuyruk.get("amount"))
        biten = sum(1 for k in range(1, adet + 1) if bas < ts + k * sure <= son)
        if biten:
            kimlik = _tam(kuyruk.get("unit"))
            cikti[kimlik] = cikti.get(kimlik, 0) + biten
    return cikti


DOGAL_KAYNAKLAR = {"125", "126", "127", "128", "1111"}  # ağaç, taş, altın, yenilenen kaynak, ada (subcat_functional)


def uretim_suresi(esya, bina, degiskenler):
    """Binanın etkin üretim süresi (sn), üretmiyorsa 0."""
    from oyun.komutlar import COLLECT_MINUTES, zaman_olcegi
    try:
        sabit = float(bina.get("activation") or 0)
    except (TypeError, ValueError):
        return 0
    if sabit <= 0:
        return 0
    if _tam(esya[0]) in degiskenler:
        cp = _tam(esya[7].get("cp")) if len(esya) > 7 and isinstance(esya[7], dict) else 0
        return COLLECT_MINUTES[cp - 1] * 60 if 1 <= cp <= len(COLLECT_MINUTES) else 0
    olcek = zaman_olcegi()
    return float(f"{sabit / olcek:.6g}") if olcek != 1.0 else sabit


def hazir_uretimler(kayit, bas, son):
    """{bina kimliği: adet}: üretimi (bas, son] aralığında hazır olan binalar (bütün kasabalarda)."""
    from oyun.config import get_game_config
    degiskenler = {_tam(i) for i in get_game_config().get("globals", {}).get("COLLECT_VARIABLE_IDS") or []}
    cikti = {}
    for harita in kayit.get("maps", []):
        for e in harita.get("items", []):
            if not isinstance(e, list) or len(e) < 5:
                continue
            bina = get_item_from_id(_tam(e[0])) or {}
            if bina.get("type") != "b" or str(bina.get("subcat_functional")) in DOGAL_KAYNAKLAR:
                continue
            sure = uretim_suresi(e, bina, degiskenler)
            if sure > 0 and bas < _tam(e[4]) + sure <= son:
                cikti[_tam(e[0])] = cikti.get(_tam(e[0]), 0) + 1
    return cikti


def birim_adi(kimlik, ceviriler):
    """Türkçe adı (ceviri/tr.json 'item:<kimlik>'), yoksa config adı."""
    return ceviriler.get(f"item:{kimlik}") or (get_item_from_id(kimlik) or {}).get("name") or "Birim"


def ozet(kayit, simdi, bas, olaylar=(), ceviriler=None):
    """Özet sözlüğü ya da None (gösterilecek bir şey yoksa). `bas`: son etkinlik zamanı (son_etkinlik); `olaylar`:
    haber şeridinin olayları; `ceviriler`: ceviri/tr.json'un çevirileri (birim adları için) ya da onları döndüren işlev;
    işlev yalnızca özet gösterilecekse çağrılır (300 KB'lık dosya her sayfa açılışında okunmasın, #60 incelemesi)."""
    bas = _tam(bas)
    if bas <= 0 or simdi - bas < ESIK:
        return None
    if callable(ceviriler):
        ceviriler = ceviriler()
    akinlar = [s for s in gunluk.savaslar(kayit) if s["yon"] == "savunma" and bas < s["zaman"] <= simdi]
    egitim = [{"ad": birim_adi(k, ceviriler or {}), "adet": adet,
               "resim": (get_item_from_id(k) or {}).get("img_name") or ""}
              for k, adet in sorted(biten_egitimler(kayit, bas, simdi).items())]
    uretim = [{"ad": birim_adi(k, ceviriler or {}), "adet": adet,
               "resim": (get_item_from_id(k) or {}).get("img_name") or ""}
              for k, adet in sorted(hazir_uretimler(kayit, bas, simdi).items())]
    haberler = [o for o in olaylar if bas < _tam(o.get("zaman")) <= simdi][-EN_COK_HABER:]
    if not (akinlar or egitim or uretim or haberler):
        return None
    pusku = [s for s in akinlar if s["zafer"]]
    return {
        "sure": sure_yazisi(simdi - bas),
        "akin": len(akinlar), "puskurtulen": len(pusku),
        "kayip": sum(s["altin"] for s in akinlar if not s["zafer"]),
        "savunma_odulu": sum(s["altin"] for s in pusku),
        "akinlar": [{"rakip": s["rakip"]["ad"], "zafer": s["zafer"], "altin": s["altin"], "tarih": s["tarih"]}
                    for s in akinlar[:5]],
        "egitim": egitim,
        "uretim": uretim,
        "haberler": [{"metin": o.get("metin", ""),
                      "saat": datetime.fromtimestamp(_tam(o.get("zaman")), TURKIYE).strftime("%H:%M")}
                     for o in reversed(haberler)],
    }
