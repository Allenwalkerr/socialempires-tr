"""Çeviri kapsamı: dört T = çevrilen / çevrilmesi gereken oranı ve kalan İngilizce listesi (GEC-01).

Ölçülen dört küme (`docs/YOL_HARITASI_1407.md` §2.1):

1. **SWF metinleri.** İstemcideki metin alanlarının başlangıç yazıları (DefineEditText) ve yazı tipine
   gömülü sabit yazılar (DefineText). Çeviri: `ceviri/arayuz_tr.json` `metin_alanlari` / `statik_yazilar`.
2. **AS3 dizeleri.** Oyun kodunun ekrana yazdığı sabit dizeler (`abc_okur.Abc.yazi_dizeleri`): metin alanına
   atanan ya da yazı çağrısına (`setHTML`, `say` ...) giden dizeler. Çeviri: `as3_dizeleri`.
3. **Config metinleri.** Sunucunun gönderdiği config'teki metinler (`oyun.turkce._bolum_anahtarlari`); kapıdaki
   "loc adları" bunların `arayuz` bölümüdür (`localization_strings`). Çeviri: `ceviri/tr.json`; çeviri yer
   tutucuları ya da etiketleri bozuyorsa (`turkce.dogrula`) çevrilmemiş sayılır, çünkü gönderilmez.
4. **Hedefler.** Config'in `goals` listesindeki (1.4.07'de `goals.json`) başlık, açıklama ve talimat.
   Anahtar `goal:<id>:<alan>`.

Çevrilmesi gereken: HTML etiketleri ve `#0#` gibi yer tutucular çıkınca en az iki Latin harfi kalan metin.
Hariç: `DOLGU` (geliştiricinin bıraktığı dolgu metinleri) ve resimdeki yazılar (KAR-01; zaten metin değildir).

Komut satırı:
    python araclar/ceviri_kapsami.py istemci.swf [--yama klasör ...] [--hedefler goals.json] [--md çıktı.md]
"""

import argparse
import copy
import html
import json
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
sys.path.insert(0, os.path.join(KOK, "araclar"))
import abc_okur  # noqa: E402
from oyun import swf_font, swf_yama, turkce  # noqa: E402

TABAN_CONFIG = os.path.join(KOK, "config", "game_config_20120826.json")
BIZIM_YAMALAR = os.path.join(KOK, "config", "patch")

# Ekrana yazı koyan atama ve çağrılar. 1.4.07 ve 0926'daki örnekler okunarak seçildi (◐): geliştirici
# paneli (addButton), iz kayıtları (trace), hata nesneleri ve iç adlar (SpecialUnitAttack) dışarıda.
YAZI_ALANLARI = {"text", "htmlText", "noElementsText", "STR_TEXT_DESC", "requirementMsg"}
YAZI_CAGRILARI = {"setHTML", "setText", "appendText", "failAlert", "say", "setTextAssault", "confirm",
                  "withAttackName", "withCantMessage"}

# Geliştiricinin bıraktığı dolgu, şablon ya da dile bağlı olmayan metinler: {metin: neden}. Ölçümle bulunur,
# `ceviri/dolgu.json`'a nedeniyle tek tek yazılır; hepsi `docs/inceleme/ceviri-kapsami.md`'de listelenir (GEC-06).
DOLGU_DOSYASI = os.path.join(KOK, "ceviri", "dolgu.json")


def _dolgu_yukle(yol=DOLGU_DOSYASI):
    if not os.path.exists(yol):
        return {}
    with open(yol, encoding="utf-8") as f:
        return dict(json.load(f).get("dolgu", {}))


DOLGU = _dolgu_yukle()

_ETIKET = re.compile(r"<[^>]+>")
_YER_TUTUCU = re.compile(r"#\d+#|%[sd]|\{\d+\}")
_HARF = re.compile(r"[A-Za-z]{2,}")


def dil_metni_mi(metin) -> bool:
    if not isinstance(metin, str):
        return False
    yalin = _YER_TUTUCU.sub("", _ETIKET.sub("", html.unescape(metin)))
    return bool(_HARF.search(yalin)) and swf_yama.anahtar(metin) not in DOLGU


# ---------------------------------------------------------------------------
# Kümeler
# ---------------------------------------------------------------------------

def swf_metinleri(veri: bytes):
    """{"metin_alanlari": [anahtar], "statik_yazilar": ["satır|satır"]} (tekrarsız, sıralı).

    Bütün metin alanları sayılır; kodun açılışta üzerine yazdığı yer tutucuları ("Unit name") ayırmak için
    güvenilir bir ölçüt yok (örnek adları sınıflar arasında çakışıyor, düğme içi yazılar ayrı tutuluyor).
    Onlar `DOLGU`'ya kanıtıyla tek tek eklenir.
    """
    govde = swf_yama._govde(veri)
    etiketler = list(swf_yama._etiketler(govde))
    fontlar = {}
    for kod, bas, son, _ in etiketler:
        if kod == swf_font.DEFINE_FONT3:
            f = swf_font.Font3(govde[bas:son])
            fontlar[f.kimlik] = f
    alanlar, statik = set(), set()
    for kod, bas, son, _ in etiketler:
        if kod == 37:  # DefineEditText
            t = govde[bas:son]
            konum = swf_yama._metin_konumu(t)
            if konum:
                alanlar.add(swf_yama.anahtar(t[konum[0]:konum[1]].decode("utf-8", "replace")))
        elif kod in (swf_font.DEFINE_TEXT, swf_font.DEFINE_TEXT2):
            _, kayitlar = swf_font.metin_kayitlari(govde[bas:son], kod)
            satirlar = swf_font.metni_coz(kayitlar, fontlar)
            if satirlar:
                statik.add("|".join(satirlar))
    return {"metin_alanlari": sorted(alanlar), "statik_yazilar": sorted(statik)}


def as3_dizeleri(veri: bytes):
    dizeler = set()
    for abc in abc_okur.swf_abc(veri):
        dizeler |= {d for _, _, d in abc.yazi_dizeleri(YAZI_ALANLARI, YAZI_CAGRILARI)}
    return sorted(dizeler)


def as3_guvensizler(veri: bytes, dizeler):
    """Çevrilmesi oyunu bozabilecek dizeler: {dize: neden}.

    oyun/swf_yama.abc_dizelerini_degistir sabit havuzundaki dizeyi değiştirir; o dizeyi kullanan HER yer değişir.
    Bu yüzden bir dize ancak (1) ad olarak (ad alanı, çok adlı, yöntem/parametre adı, üst veri) geçmiyorsa,
    (2) bir sınıf sabitinin ya da isteğe bağlı parametrenin varsayılan değeri değilse (#54 incelemesi) ve (3) bütün `pushstring` kullanımları ekran yazısına (yazi_dizeleri)
    gidiyorsa güvenle çevrilir. Örnek: "Whirlwind" 26 yerde itilir, 10'u ekrana gider; geri kalanı eşleştirme
    anahtarıdır, çevrilirse o eşleşmeler kırılır (GEC-06)."""
    dizeler = set(dizeler)
    ad_olan, sabit, it, ekran = set(), set(), {}, {}
    for abc in abc_okur.swf_abc(veri):
        havuz = abc.dizeler

        def ekle(kume, i):
            if 0 < i < len(havuz):
                kume.add(havuz[i])

        for _, i in abc.ad_alanlari[1:]:
            ekle(ad_olan, i)
        for m in abc.coklu_adlar[1:]:
            if m[0] in (abc_okur.QNAME, abc_okur.QNAME_A):
                ekle(ad_olan, m[2])
            elif m[0] in (abc_okur.RTQNAME, abc_okur.RTQNAME_A, abc_okur.MULTINAME, abc_okur.MULTINAME_A):
                ekle(ad_olan, m[1])
        for y in abc.yontemler:
            for i in [y["ad"]] + list(y["adlar"]):
                ekle(ad_olan, i)
            for sira, tur in y.get("secenekler", ()):
                if tur == 0x01:  # varsayılan değer dize: pushstring'le itilmez, sayımda görünmez
                    ekle(sabit, sira)
        for ad, ciftler in abc.ustveriler:
            for i in [ad] + [x for c in ciftler for x in c]:
                ekle(ad_olan, i)
        for liste in ([o["ozellikler"] for o in abc.ornekler] + [s[1] for s in abc.siniflar]
                      + [b[1] for b in abc.betikler]):
            for k in liste:
                if k[0] in (0, 6) and k[4] and k[5] == 0x01:  # Slot/Const, değer türü dize
                    ekle(sabit, k[4])
        for g in abc.govdeler.values():
            try:
                islemler = abc.coz(g)
            except Exception:  # gizlenmiş gövde: çözülemeyen kullanım bilinemez, sayım eksik kalabilir (◐)
                continue
            for isl in islemler.values():
                if isl.ad == "pushstring":
                    d = abc.deger(isl)
                    it[d] = it.get(d, 0) + 1
        for _, _, d in abc.yazi_dizeleri(YAZI_ALANLARI, YAZI_CAGRILARI):
            ekran[d] = ekran.get(d, 0) + 1
    cikti = {}
    for d in sorted(dizeler):
        if d in ad_olan:
            cikti[d] = "ad olarak da geçiyor"
        elif d in sabit:
            cikti[d] = "sınıf sabitinin ya da parametre varsayılanının değeri"
        elif it.get(d, 0) > ekran.get(d, 0):
            cikti[d] = "%d kullanımın %d'i ekrana gidiyor" % (it.get(d, 0), ekran.get(d, 0))
    return cikti


def config_kur(yama_klasorleri, taban=TABAN_CONFIG):
    """Taban config'e klasörlerdeki yamaları ad sırasıyla uygular (`oyun/config.py` gibi), sonra eşya
    tekrarlarını atar (son gelen kalır)."""
    import jsonpatch
    with open(taban, encoding="utf-8") as f:
        config = json.load(f)
    for klasor in yama_klasorleri:
        for ad in sorted(os.listdir(klasor)):
            if ad.endswith(".json"):
                with open(os.path.join(klasor, ad), encoding="utf-8") as f:
                    jsonpatch.apply_patch(config, json.load(f), in_place=True)
    esyalar = config.get("items", [])
    son = {e.get("id"): i for i, e in enumerate(esyalar) if isinstance(e, dict)}
    config["items"] = [e for i, e in enumerate(esyalar) if not isinstance(e, dict) or son[e.get("id")] == i]
    return config


def config_metinleri(config):
    """[(anahtar, bölüm, metin)]; bölüm `arayuz` kapıdaki loc adlarıdır."""
    return [(a, b, m) for a, b, m, _ in turkce._bolum_anahtarlari(copy.deepcopy(config))]


HEDEF_ALANLARI = (("title", "baslik"), ("description", "aciklama"), ("instructions", "talimat"))


def hedef_metinleri(hedefler):
    cikti = []
    for h in hedefler or []:
        for alan, etiket in HEDEF_ALANLARI:
            m = h.get(alan)
            if isinstance(m, str) and m.strip() and m != "none":
                cikti.append(("goal:%s:%s" % (h.get("id"), etiket), m))
    return cikti


# ---------------------------------------------------------------------------
# Oranlar
# ---------------------------------------------------------------------------

def oran(ogeler):
    """ogeler: [(anahtar, kaynak_metin, çevrildi_mi)]; yalnızca dil metinleri sayılır."""
    gereken = [(a, m, c) for a, m, c in ogeler if dil_metni_mi(m)]
    cevrilen = sum(1 for _, _, c in gereken if c)
    return {"gereken": len(gereken), "cevrilen": cevrilen,
            "T": cevrilen / len(gereken) if gereken else 1.0,
            "kalan": sorted((a, m) for a, m, c in gereken if not c)}


def olc(swf_veri, config, hedefler=None, sozluk=None, ceviriler=None):
    sozluk = swf_yama._sozluk() if sozluk is None else sozluk
    ceviriler = turkce.cevirileri_yukle() if ceviriler is None else ceviriler
    alanlar, statik = sozluk.get("metin_alanlari", {}), sozluk.get("statik_yazilar", {})
    as3 = sozluk.get("as3_dizeleri", {})
    swf = swf_metinleri(swf_veri)
    sonuc = {
        "swf_metin_alanlari": oran([(k, k, k in alanlar) for k in swf["metin_alanlari"]]),
        "swf_statik_yazilar": oran([(k, k, k in statik) for k in swf["statik_yazilar"]]),
    }
    adaylar = as3_dizeleri(swf_veri)
    guvensiz = {d: n for d, n in as3_guvensizler(swf_veri, adaylar).items() if dil_metni_mi(d)}
    sonuc["as3_dizeleri"] = oran([(d, d, d in as3 and d not in guvensiz) for d in adaylar])
    sonuc["as3_guvensiz"] = guvensiz  # çevrilmemeli; sözlükte varsa çevrilmiş sayılmaz
    bolumler = {}
    for anahtar, bolum, metin in config_metinleri(config):
        c = anahtar in ceviriler and not turkce.dogrula(metin, ceviriler[anahtar])
        bolumler.setdefault(bolum, []).append((anahtar, metin, c))
    sonuc["config_loc"] = oran(bolumler.get("arayuz", []))
    sonuc["config_tum"] = oran([x for v in bolumler.values() for x in v])
    sonuc["config_bolumleri"] = {b: oran(v) for b, v in sorted(bolumler.items())}
    hedefler = config.get("goals") if hedefler is None else hedefler
    sonuc["hedefler"] = oran([(a, m, a in ceviriler) for a, m in hedef_metinleri(hedefler)])
    return sonuc


KAPI = (("swf_metin_alanlari", "SWF metin alanları"), ("swf_statik_yazilar", "SWF sabit yazılar"),
        ("as3_dizeleri", "AS3 dizeleri"), ("config_loc", "Config loc adları"), ("hedefler", "Hedefler"))


def _hucre(m):
    m = str(m).replace("|", "\\|").replace("\n", "\\n").replace("\r", "\\r")
    return m if len(m) <= 90 else m[:87] + "…"


def markdown(olcumler, notlar=()):
    """olcumler: [(başlık, olc() sonucu)]."""
    satir = ["# Çeviri kapsamı", "", "Bu dosya `araclar/ceviri_kapsami.py` ile üretilir; elle düzenlenmez.", ""]
    satir += list(notlar) + [""] if notlar else []
    satir += ["## Oranlar", "", "| Küme | " + " | ".join(b for b, _ in olcumler) + " |",
              "|---|" + "---|" * len(olcumler)]
    for anahtar, ad in KAPI + (("config_tum", "Config, bütün metinler"),):
        satir.append("| %s | %s |" % (ad, " | ".join(
            "%d / %d = %.3f" % (o[anahtar]["cevrilen"], o[anahtar]["gereken"], o[anahtar]["T"])
            for _, o in olcumler)))
    satir += ["", "Kapı: ilk beş satırın hepsinde T = 1.", ""]
    satir += ["## Config bölümleri", "", "| Bölüm | " + " | ".join(b for b, _ in olcumler) + " |",
              "|---|" + "---|" * len(olcumler)]
    bolumler = sorted({b for _, o in olcumler for b in o["config_bolumleri"]})
    for b in bolumler:
        satir.append("| %s | %s |" % (b, " | ".join(
            ("%d / %d" % (o["config_bolumleri"][b]["cevrilen"], o["config_bolumleri"][b]["gereken"])
             if b in o["config_bolumleri"] else "—") for _, o in olcumler)))
    for baslik, o in olcumler:
        satir += ["", "## Kalan İngilizce: %s" % baslik]
        for anahtar, ad in KAPI:
            kalan = o[anahtar]["kalan"]
            satir += ["", "### %s (%d)" % (ad, len(kalan)), ""]
            if anahtar in ("config_loc", "hedefler") and len(kalan) > 60:
                satir.append("İlk 60 (tamamı `--json` çıktısında):")
                satir.append("")
                kalan = kalan[:60]
            satir += ["- `%s`" % _hucre(a) if a == m else "- `%s`: %s" % (_hucre(a), _hucre(m))
                      for a, m in kalan]
    for baslik, o in olcumler:
        guvensiz = o.get("as3_guvensiz", {})
        satir += ["", "## Çevrilmeyecek AS3 dizeleri: %s (%d)" % (baslik, len(guvensiz)), "",
                  "Sabit havuzundaki dize her kullanımda birlikte değişir; bunlar ekran dışında da kullanılıyor.", ""]
        satir += ["- `%s`: %s" % (_hucre(d), n) for d, n in guvensiz.items()] or ["yok"]
    satir += ["", "## Dolgu (hariç tutulan, %d; `ceviri/dolgu.json`)" % len(DOLGU), ""]
    satir += ["- `%s`: %s" % (_hucre(d), _hucre(n)) for d, n in sorted(DOLGU.items())] or ["yok"]
    return "\n".join(satir) + "\n"


def main(argv=None):
    import hashlib
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("swf")
    ap.add_argument("--yama", action="append", help="config yama klasörü (varsayılan: config/patch)")
    ap.add_argument("--hedefler", help="goals.json")
    ap.add_argument("--eski", help="yanında ölçülecek eski istemci (bizim config/patch ile)")
    ap.add_argument("--md", help="raporu bu dosyaya yaz")
    ap.add_argument("--json", help="bütün sonucu bu dosyaya yaz")
    a = ap.parse_args(argv)
    olcumler, notlar = [], []

    def ekle(yol, yamalar, hedef_yolu):
        with open(yol, "rb") as f:
            veri = f.read()
        hedefler = None
        if hedef_yolu:
            with open(hedef_yolu, encoding="utf-8") as f:
                hedefler = json.load(f)
        ad = os.path.basename(yol)
        olcumler.append((ad, olc(veri, config_kur(yamalar), hedefler)))
        dosyalar = sorted(x[:-5] for y in yamalar for x in os.listdir(y) if x.endswith(".json"))
        notlar.append("- `%s` (SHA-256 `%s…`): taban config + yamalar (%s)%s." % (
            ad, hashlib.sha256(veri).hexdigest()[:12], ", ".join(dosyalar),
            " + `goals.json`" if hedef_yolu else ""))

    ekle(a.swf, a.yama or [BIZIM_YAMALAR], a.hedefler)
    if a.eski:
        ekle(a.eski, [BIZIM_YAMALAR], None)
    for baslik, sonuc in olcumler:
        print(baslik)
        for anahtar, ad in KAPI + (("config_tum", "Config, bütün"),):
            o = sonuc[anahtar]
            print("  %-22s %5d / %5d = %.3f" % (ad, o["cevrilen"], o["gereken"], o["T"]))
    if a.md:
        with open(a.md, "w", encoding="utf-8", newline="\n") as f:
            f.write(markdown(olcumler, notlar))
    if a.json:
        with open(a.json, "w", encoding="utf-8", newline="\n") as f:
            json.dump(dict(olcumler), f, ensure_ascii=False, indent=1)
            f.write("\n")
    return olcumler


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
