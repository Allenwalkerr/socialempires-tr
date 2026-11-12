"""Bot köylerinin yerleşimi ve ordusu (plan: docs/inceleme/bot-koyleri-plani.md).

Sahibinin isteği (12.11.2026): köyler özenli, birbirinden farklı ve askeri seviyesi botun seviyesine uygun olsun. Yalnızca
oyunun kendi binaları, birimleri ve süsleri kullanılır (CLAUDE.md görsel kuralı); hepsi config'teki kimlikleriyle.

Kaynaklar (1.4.07):
- Doluluk: Base/setOccupiedGrid binayı tx-genişlik+1..tx, ty-yükseklik+1..ty karolarına yazar; yani kayıttaki (x, y)
  binanın en büyük köşesidir (villages/initial.json da böyle: Ev I (44,50) ile Ağaç (45,50) yan yana).
- Harita 100×100, 20×20'lik büyük karolar (Config EI_MAP_WIDTH, EI_TILES_IN_BIGTILE); genişleme kimliği
  satır·5 + sütun + 1 (13 = 40..59); büyük karo başına en çok 10 kule (Config MAX_TOWERS_PER_BIGTILE).
- Kademeler: config items min_level ve trains (tests/test_bot_koy.py config'e karşı denetler).
"""

import random

from oyun.config import get_item_from_id

TASARIM_SURUMU = 2
BUYUK_KARO = 20
KULE_SINIRI = 10  # Config.MAX_TOWERS_PER_BIGTILE

# (açılış seviyesi, bina, ürettiği birim): config items min_level, trains
KOLLAR = {
    "piyade": [(1, 38, 509), (8, 39, 510), (16, 40, 511), (28, 136, 539), (37, 390, 608)],
    "okcu": [(3, 41, 516), (10, 42, 517), (18, 43, 518), (30, 137, 540), (42, 391, 609)],
    "suvari": [(5, 44, 512), (12, 45, 513), (20, 46, 514), (32, 138, 541), (46, 392, 610)],
    "kusatma": [(7, 48, 519), (14, 49, 520), (22, 50, 521), (26, 51, 522)],
}
# (açılış seviyesi, kimlik)
BELEDIYE = [(0, 26), (12, 139), (25, 140), (35, 141)]
EV = [(1, 1), (7, 2), (19, 3), (31, 4), (36, 194)]
KULE = [(2, 29), (8, 30), (14, 31), (23, 32), (33, 33)]
SUR = [(3, 34), (9, 35), (17, 36), (25, 195), (34, 196)]
SUR_KAPISI = (21, 37)
KALE = [(0, 27), (10, 28), (27, 198)]
DEGIRMEN = [(1, 5), (11, 6), (23, 7), (32, 202)]
TARLA = [(1, 10)]
ALTIN = [(4, 13), (13, 14), (24, 15), (38, 203)]
MARANGOZ = [(5, 77), (15, 78), (27, 79), (35, 205)]
TAS = [(6, 16), (17, 17), (29, 18), (41, 204)]
KOYUN = [(2, 11), (14, 190), (24, 191)]
INEK = [(5, 12), (17, 192), (26, 193)]
PAZAR = [(5, 23), (11, 188), (25, 189)]
INANC = [(18, 229), (19, 24), (23, 212)]  # Tapınak, Kilise, Katedral
AGAC = [(0, 108), (2, 101), (8, 104), (10, 105), (12, 106)]
CICEK = [(0, 62), (2, 63), (3, 64), (7, 65), (9, 66), (10, 67)]
HEYKEL = [(1, 122), (1, 126), (1, 128), (5, 117), (10, 119), (15, 120)]
CESME = (6, 129)
ATES = (1, 68)
BAYRAK = [(1, 174), (5, 110), (12, 112), (15, 113)]

# Kişiliğe göre kol ağırlıkları, kule sayısı, ordu oranı ve düzen
KISILIK = {
    "agresif": {"kollar": {"piyade": 3, "suvari": 4, "okcu": 1, "kusatma": 2}, "kule": 3, "ordu": 1.0,
                "duzen": "ordugah"},
    "savunmaci": {"kollar": {"piyade": 2, "suvari": 1, "okcu": 4, "kusatma": 1}, "kule": 8, "ordu": 0.9,
                  "duzen": "kale"},
    "tuccar": {"kollar": {"piyade": 2, "suvari": 1, "okcu": 2, "kusatma": 0}, "kule": 3, "ordu": 0.6,
               "duzen": "carsi"},
    "dengeli": {"kollar": {"piyade": 2, "suvari": 2, "okcu": 2, "kusatma": 1}, "kule": 5, "ordu": 0.8,
                "duzen": "ciftlik"},
}


def kademe(tablo, seviye):
    """Tablodan seviyenin açtığı en yüksek kademe (kimlik), yoksa None."""
    acik = [k for s, k in tablo if s <= seviye]
    return acik[-1] if acik else None


def acik_kademeler(kol, seviye):
    return [(bina, birim) for s, bina, birim in KOLLAR[kol] if s <= seviye]


def ordu_buyuklugu(seviye, kisi):
    return max(4, int(min(8 + seviye, 60) * KISILIK.get(kisi, KISILIK["dengeli"])["ordu"]))


def birim_sec(seviye, kisi, rng):
    """Kişiliğin kol ağırlığıyla bir kol, o kolun açık en yüksek iki kademesinden biri (çoğu en yüksek)."""
    agirlik = {k: a for k, a in KISILIK.get(kisi, KISILIK["dengeli"])["kollar"].items()
               if a > 0 and acik_kademeler(k, seviye)}
    if not agirlik:
        agirlik = {"piyade": 1}
    kol = rng.choices(list(agirlik), weights=list(agirlik.values()))[0]
    kademeler = acik_kademeler(kol, seviye)
    if len(kademeler) >= 2 and rng.random() < 0.3:
        return kademeler[-2][1]
    return kademeler[-1][1]


def genislemeler(seviye):
    """Açık büyük karolar ve alanın sınırları (en küçük, en büyük karo; iki eksende aynı)."""
    if seviye >= 30:
        return [7, 8, 9, 12, 13, 14, 17, 18, 19], 20, 79
    if seviye >= 15:
        return [13, 14, 18, 19], 40, 79
    return [13], 40, 59


def boyut(esya_id):
    e = get_item_from_id(esya_id) or {}
    try:
        return max(1, int(e.get("width") or 1)), max(1, int(e.get("height") or 1))
    except (TypeError, ValueError):
        return 1, 1


def kapladigi(esya):
    """Kayıttaki öğenin kapladığı karolar (Base/setOccupiedGrid: x-w+1..x, y-h+1..y)."""
    w, h = boyut(esya[0])
    x, y = int(esya[1]), int(esya[2])
    return {(i, j) for i in range(x - w + 1, x + 1) for j in range(y - h + 1, y + 1)}


class _Plan:
    """Yerel koordinatlarda (0..n-1) yerleşim; sonra döndürülüp haritaya taşınır."""

    def __init__(self, n, rng):
        self.n, self.rng = n, rng
        self.dolu, self.ayrik = set(), set()
        self.ogeler = []  # (kimlik, x0, y0, w) yerel, sol üst köşe

    def bos_mu(self, x0, y0, w, h, ayrik_serbest=False):
        if x0 < 0 or y0 < 0 or x0 + w > self.n or y0 + h > self.n:
            return False
        for i in range(x0, x0 + w):
            for j in range(y0, y0 + h):
                if (i, j) in self.dolu or (not ayrik_serbest and (i, j) in self.ayrik):
                    return False
        return True

    def koy(self, kimlik, x0, y0, ayrik_serbest=False):
        if kimlik is None:
            return False
        w, h = boyut(kimlik)
        if not self.bos_mu(x0, y0, w, h, ayrik_serbest):
            return False
        for i in range(x0, x0 + w):
            for j in range(y0, y0 + h):
                self.dolu.add((i, j))
        self.ogeler.append((kimlik, x0, y0, w))
        return True

    def ayir(self, x0, y0, w, h):
        for i in range(x0, x0 + w):
            for j in range(y0, y0 + h):
                self.ayrik.add((i, j))

    def sirala(self, kimlikler, x0, y0, x1, y1, ara=1):
        """Kimlikleri [x0, x1) × [y0, y1) kutusuna satır satır dizer (raf yerleşimi); konamayanları döndürür."""
        kalan = []
        x, y, satir = x0, y0, 0
        for kimlik in kimlikler:
            w, h = boyut(kimlik)
            konuldu = False
            while y + h <= y1:
                if x + w > x1:
                    x, y, satir = x0, y + satir + ara, 0
                    continue
                if self.koy(kimlik, x, y):
                    x += w + ara
                    satir = max(satir, h)
                    konuldu = True
                    break
                x += 1
            if not konuldu:
                kalan.append(kimlik)
        return kalan

    def serpistir(self, kimlikler, x0, y0, x1, y1, deneme=40):
        for kimlik in kimlikler:
            w, h = boyut(kimlik)
            for _ in range(deneme):
                if x1 - w < x0 or y1 - h < y0:
                    break
                if self.koy(kimlik, self.rng.randint(x0, x1 - w), self.rng.randint(y0, y1 - h)):
                    break


def _uretim(seviye, kisi, rng):
    """Ekonomi binaları (kişiliğe göre adet)."""
    tuccar = kisi == "tuccar"
    liste = []
    liste += [kademe(DEGIRMEN, seviye)] * (3 if tuccar else 2)
    liste += [kademe(ALTIN, seviye)] * (2 if tuccar else 1)
    liste += [kademe(MARANGOZ, seviye)] * (2 if seviye >= 15 else 1)
    liste += [kademe(TAS, seviye)] * (2 if seviye >= 20 else 1)
    return [k for k in liste if k]


def _tarlalar(seviye, kisi, n):
    ciftlik = kisi in ("dengeli", "tuccar")
    tarla = (4 if n == 20 else 8) + (4 if ciftlik else 0)
    agil = [k for k in (kademe(KOYUN, seviye), kademe(INEK, seviye)) if k]
    if n == 20:
        agil = agil[:1]
    return [10] * tarla, agil * (2 if ciftlik and n > 20 else 1)


def _askeri(seviye, kisi):
    binalar = []
    agirlik = KISILIK.get(kisi, KISILIK["dengeli"])["kollar"]
    for kol, a in sorted(agirlik.items(), key=lambda t: -t[1]):
        kademeler = acik_kademeler(kol, seviye)
        if a > 0 and kademeler:
            binalar.append(kademeler[-1][0])
    if kisi == "agresif" and acik_kademeler("piyade", seviye):
        binalar.append(acik_kademeler("piyade", seviye)[-1][0])
    return binalar


def koy_kur(seviye, kisi, tohum, simdi):
    """(items, expansions): botun köyü. Aynı tohum aynı köyü verir."""
    rng = random.Random(str(tohum))
    seviye = max(1, int(seviye))
    kisi = kisi if kisi in KISILIK else "dengeli"
    duzen = KISILIK[kisi]["duzen"]
    acik, alt, ust = genislemeler(seviye)
    n = ust - alt + 1
    p = _Plan(n, rng)
    c = n // 2

    # Sur halkası: küçük köyde alanın kenarından bir karo içeride; büyük köyde çekirdeğin çevresinde
    if n == 20:
        r0, r1 = 1, n - 2
    elif n == 40:
        r0, r1 = 6, n - 7
    else:
        r0, r1 = 12, n - 13
    if duzen == "ciftlik" and n > 20:
        r0, r1 = r0 + 3, r1 - 3  # çiftlik köyünde sur daha dar, tarlalar dışarıda geniş

    # 1. Meydan: belediye ortada, çevresinde bir karo boş meydan; kapıya giden yol (yerel güneye, +y) boş kalır
    p.koy(kademe(BELEDIYE, seviye), c - 2, c - 2)
    p.ayir(c - 3, c - 3, 6, 6)
    p.ayir(c - 1, c + 3, 2, r1 - c - 2)  # ana yol
    kapi_x = c - 1
    # Meydanın köşelerinde süs (çeşme, heykel)
    meydan_susu = [CESME[1] if seviye >= CESME[0] else ATES[1]]
    heykeller = [k for s, k in HEYKEL if s <= seviye]
    meydan_susu += [rng.choice(heykeller) for _ in range(3)]
    for (x, y), kimlik in zip(((c - 3, c - 3), (c + 2, c - 3), (c - 3, c + 2), (c + 2, c + 2)), meydan_susu):
        p.koy(kimlik, x, y, ayrik_serbest=True)

    # 2. Sur ve kapı (sur 3. seviyede açılır)
    sur = kademe(SUR, seviye)
    kapi = SUR_KAPISI[1] if seviye >= SUR_KAPISI[0] else None
    if sur:
        if kapi:
            kapi = kapi if p.koy(kapi, kapi_x - 1, r1 - 2, ayrik_serbest=True) else None  # yolun ucunda, 3×3
        acik_yol = range(kapi_x - 1, kapi_x + 2) if kapi else range(kapi_x, kapi_x + 2)
        halkalar = [(r0, r1)]
        if duzen == "kale" and seviye >= 14 and n > 20:
            halkalar.append((r0 - 3, r1 + 3))  # dış halka
        for q0, q1 in halkalar:
            for i in range(q0, q1 + 1):
                p.koy(sur, i, q0)
                if i not in acik_yol:
                    p.koy(sur, i, q1)
            for j in range(q0 + 1, q1):
                p.koy(sur, q0, j)
                p.koy(sur, q1, j)
        p.ayir(kapi_x - 1, r1 - 2, 4, 5)  # kapı önü boş

    # 3. Kuleler: dört köşe, kapının iki yanı, sonra sur boyunca eşit aralıkla
    kule = kademe(KULE, seviye)
    kule_sayisi = KISILIK[kisi]["kule"] + seviye // 15
    if kule:
        ic0, ic1 = r0 + 1, r1 - 1
        yerler = [(ic0, ic0), (ic1, ic0), (ic0, ic1), (ic1, ic1), (kapi_x - 2, ic1 - 2), (kapi_x + 3, ic1 - 2)]
        adim = max(2, (ic1 - ic0) // 4)
        for k in range(ic0 + adim, ic1, adim):
            yerler += [(k, ic0), (ic0, k), (ic1, k)]
        konan = 0
        for x, y in yerler:
            if konan >= kule_sayisi:
                break
            if p.koy(kule, x, y, ayrik_serbest=True):
                konan += 1

    ic0, ic1 = r0 + 2, r1 - 1  # surun içi (kule sırası hariç)
    # 4. Kale (savunmacı, 10. seviyeden): meydanın kuzeyinde
    if duzen == "kale":
        p.koy(kademe(KALE, seviye) if seviye >= 10 else None, c - 2, c - 8 if n > 20 else ic0)

    # 5. Ordugâh: askeri binalar kapıya yakın (yerel güneydoğu), önünde talim alanı
    askeri = _askeri(seviye, kisi)
    og_x0, og_y0 = c + 3, c + 1
    kalan_askeri = p.sirala(askeri, og_x0, og_y0, ic1, ic1 - 1)
    # 6. Evler: yolun iki yanında sıra sıra (yerel batı yarısı ve kuzey)
    ev = kademe(EV, seviye)
    ev_sayisi = 4 + seviye // 6 + (2 if duzen == "carsi" else 0)
    evler = [ev] * min(ev_sayisi, 14 if n > 20 else 8)
    kalan_ev = p.sirala(evler, ic0, c + 1, c - 1, ic1 - 1)
    kalan_ev = p.sirala(kalan_ev, ic0, ic0, c - 3, c - 3)
    # 7. Pazar, inanç binası (çarşı köyünde meydanın yanında)
    pazar = kademe(PAZAR, seviye)
    ozel = [pazar] if pazar and (duzen == "carsi" or seviye >= 12) else []
    if kademe(INANC, seviye) and seviye >= 20:
        ozel.append(kademe(INANC, seviye))
    kalan_ozel = p.sirala(ozel, c - 2, ic0, ic1, c - 3)
    # 8. Üretim: surun içinde kuzey ve doğu kenarı
    uretim = _uretim(seviye, kisi, rng)
    kalan_uretim = p.sirala(uretim, c + 3, ic0, ic1, c)
    # 9. Tarlalar ve ağıllar: büyük köyde surun dışında çiftlik kuşağı, küçük köyde içeride kalan yerde
    tarlalar, agillar = _tarlalar(seviye, kisi, n)
    if n > 20:
        disari = [(1, 1, n - 1, r0 - 1), (1, r1 + 2, n - 1, n - 1), (1, r0, r0 - 1, r1 + 1),
                  (r1 + 2, r0, n - 1, r1 + 1)]
        rng.shuffle(disari)
        bekleyen = agillar + tarlalar + kalan_uretim + kalan_ev + kalan_ozel + kalan_askeri
        for x0, y0, x1, y1 in disari:
            bekleyen = p.sirala(bekleyen, x0, y0, x1, y1)
    else:
        bekleyen = p.sirala(kalan_uretim + kalan_ozel + kalan_askeri + agillar + tarlalar[:4], ic0, ic0, ic1, ic1)
        p.sirala(kalan_ev, ic0, ic0, ic1, ic1)

    # 10. Ordu: talim alanında düzenli sıralar (bir karo arayla), yer kalmazsa surun içine dağılır
    ordu = [birim_sec(seviye, kisi, rng) for _ in range(ordu_buyuklugu(seviye, kisi))]
    ordu.sort()
    kalan = p.sirala(ordu, c + 3, c + 1 + 4, ic1, ic1 - 1)
    p.serpistir(kalan, ic0, ic0, ic1, ic1)

    # 11. Süs: yol kenarında çiçek, kapıda bayrak, sur dışında ağaç kümeleri
    cicek = [k for s, k in CICEK if s <= seviye]
    for j in range(c + 4, r1 - 2, 2):
        p.koy(rng.choice(cicek), c - 2, j, ayrik_serbest=True)
        p.koy(rng.choice(cicek), c + 1, j, ayrik_serbest=True)
    bayraklar = [k for s, k in BAYRAK if s <= seviye]
    bayrak = 174 if rng.random() < 0.35 else rng.choice(bayraklar)
    for x in (kapi_x - 3, kapi_x + 4):
        p.koy(bayrak, x, r1 + 1, ayrik_serbest=True) or p.koy(bayrak, x, r1 - 1, ayrik_serbest=True)
    agaclar = [k for s, k in AGAC if s <= seviye]
    kume = 6 if n == 20 else 14
    for _ in range(kume):
        ox, oy = rng.randint(0, n - 1), rng.randint(0, n - 1)
        if r0 - 1 <= ox <= r1 + 1 and r0 - 1 <= oy <= r1 + 1 and n > 20:
            continue
        tur = rng.choice(agaclar)
        for _ in range(rng.randint(3, 7)):
            p.koy(tur, ox + rng.randint(-2, 2), oy + rng.randint(-2, 2))

    return _haritaya(p, alt, rng.randrange(8), simdi), acik


def _haritaya(p, alt, donus, simdi):
    """Yerel yerleşimi 8 simetriden biriyle (dönme, ayna) haritaya taşır; kayıttaki konum en büyük köşedir."""
    n = p.n
    items = []
    for kimlik, x0, y0, w in p.ogeler:
        x1, y1 = x0 + w - 1, y0 + w - 1
        koseler = []
        for x, y in ((x0, y0), (x1, y1)):
            if donus & 1:
                x, y = y, x
            if donus & 2:
                x = n - 1 - x
            if donus & 4:
                y = n - 1 - y
            koseler.append((x, y))
        mx = max(koseler[0][0], koseler[1][0])
        my = max(koseler[0][1], koseler[1][1])
        items.append([kimlik, alt + mx, alt + my, 0, simdi, 0, [], {}])
    return items


def ordu_dolu_mu(kayit):
    harita = kayit["maps"][0]
    seviye = max(1, int(harita.get("level", 1)))
    kisi = kayit.get("playerInfo", {}).get("bot_kisi", "dengeli")
    birimler = sum(1 for e in harita.get("items", []) if (get_item_from_id(e[0]) or {}).get("type") == "u")
    return birimler >= ordu_buyuklugu(seviye, kisi)


def birim_ekle(kayit, kimlik, simdi, rng=random):
    """Dünya simülasyonu için: birimi (birim_sec'in seçtiği) köyün boş bir karosuna ekler. Ordu ordu_buyuklugu'na
    ulaştıysa ya da boş karo bulunamazsa eklemez. Eklediyse True."""
    if ordu_dolu_mu(kayit):
        return False
    harita = kayit["maps"][0]
    seviye = max(1, int(harita.get("level", 1)))
    items = harita.setdefault("items", [])
    dolu = set()
    for e in items:
        try:
            dolu |= kapladigi(e)
        except (TypeError, ValueError, IndexError):
            continue
    _, alt, ust = genislemeler(seviye)
    for _ in range(60):
        x, y = rng.randint(alt + 2, ust - 2), rng.randint(alt + 2, ust - 2)
        if (x, y) not in dolu:
            items.append([kimlik, x, y, 0, simdi, 0, [], {}])
            return True
    return False


def yeniden_kur(kayit, simdi):
    """Var olan bot köyünü yeni tasarıma geçirir: kimlik, ad, kaynaklar, seviye ve geçmiş kalır; yerleşim, ordu ve
    genişlemeler yenilenir. Değiştiyse True."""
    pi = kayit.get("playerInfo") or {}
    if not pi.get("bot") or pi.get("bot_tasarim") == TASARIM_SURUMU:
        return False
    harita = kayit["maps"][0]
    items, acik = koy_kur(harita.get("level", 1), pi.get("bot_kisi", "dengeli"), pi.get("pid", ""), simdi)
    harita["items"], harita["expansions"] = items, acik
    pi["bot_tasarim"] = TASARIM_SURUMU
    return True
