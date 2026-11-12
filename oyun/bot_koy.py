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

TASARIM_SURUMU = 8  # 8: iç sur kapı kuleleri; 7: arazi türü; 6: iç surlar ve asker geçidi; 5: şerit sırası köyden köye karışır; 4: Arthur köyleri örnek alındı (sahibi, 12.11.2026)
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

# Arazi türü (haritanın "skin" alanı; Base/_parseLoadedInfo map.skin → skinMap, Base/addExpandedTileBuilding arazi öğesi
# 1000 + skin): 0 çimen, 1 çöl, 2 buz, 4 maden, 5 orman (3 deniz, 6 bulut kara köyüne uymaz). Sahibi (12.11.2026):
# "arazi türünü çok değil ama az da olsa değiştirsen güzel olurdu": botların yaklaşık altıda biri. Çizimleri temel pakette
# (araclar/onindirme_listesi.py).
BOT_ARAZILERI = (1, 2, 4, 5)
ARAZI_ORANI = 1 / 6


def arazi_sec(tohum):
    """Botun arazi türü (aynı tohum aynı arazi)."""
    rng = random.Random("arazi-%s" % tohum)
    return rng.choice(BOT_ARAZILERI) if rng.random() < ARAZI_ORANI else 0


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


def _uretim(seviye, kisi, rng):
    """Ekonomi binaları (kişiliğe göre adet)."""
    tuccar = kisi == "tuccar"
    liste = []
    liste += [kademe(DEGIRMEN, seviye)] * (3 if tuccar else 2)
    liste += [kademe(ALTIN, seviye)] * (2 if tuccar else 1)
    liste += [kademe(MARANGOZ, seviye)] * (2 if seviye >= 15 else 1)
    liste += [kademe(TAS, seviye)] * (2 if seviye >= 20 else 1)
    return [k for k in liste if k]


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


BOSTAN = [(1, 10), (9, 8), (21, 9), (28, 200), (34, 201)]  # Tarla, Balkabağı, Patlıcan, Havuç, Karpuz Bostanı

# Köyün biçimi: büyük karo (sütun, satır) kümeleri; hepsi başlangıç karosunu (2, 2 = genişleme 13) içerir.
# Arthur köyleri gibi kare olmak zorunda değil (Arthur30 20×40, Arthur31 L).
_IKI = [{(2, 2), (3, 2)}, {(2, 2), (2, 3)}, {(1, 2), (2, 2)}, {(2, 1), (2, 2)}]
_UC = [{(2, 2), (2 + dx, 2), (2, 2 + dy)} for dx in (-1, 1) for dy in (-1, 1)]
_DORT = [{(2, 2), (2 + dx, 2), (2, 2 + dy), (2 + dx, 2 + dy)} for dx in (-1, 1) for dy in (-1, 1)]
_ALTI = [{(c, r) for c in range(c0, c0 + 3) for r in range(r0, r0 + 2)} for c0 in (1, 2) for r0 in (1, 2)
         if c0 <= 2 < c0 + 3] + [{(c, r) for c in range(c0, c0 + 2) for r in range(r0, r0 + 3)}
                                 for c0 in (1, 2) for r0 in (1, 2)]


def sekil(seviye, rng):
    """Büyük karo kümesi: seviye büyüdükçe köy büyür (1-9: 1, 10-19: 2 (Arthur30 gibi dikdörtgen), 20-29: 3 (Arthur31
    gibi L), 30+: 4 (Arthur32 gibi 40×40))."""
    if seviye < 10:
        return {(2, 2)}
    secenek = _IKI if seviye < 20 else _UC if seviye < 30 else _DORT  # en çok 40×40 (Arthur32 gibi)
    return set(rng.choice(secenek))


def genisleme_kimligi(sutun, satir):
    """Genişleme kimliği: satır·5 + sütun + 1; x = sütun·20, y = satır·20 (Arthur30: [18, 13] → x 40..59, y 40..79)."""
    return satir * 5 + sutun + 1


def karolari(genislemeler):
    """Genişleme kimliklerinin kapladığı karolar."""
    sonuc = set()
    for g in genislemeler:
        satir, sutun = divmod(int(g) - 1, 5)
        sonuc |= {(sutun * BUYUK_KARO + i, satir * BUYUK_KARO + j) for i in range(BUYUK_KARO) for j in range(BUYUK_KARO)}
    return sonuc


def genislemeler(seviye):
    """Geriye uyum: seviyenin en küçük köyünün alanı (kimlikler, alt, üst)."""
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


class _Alan:
    """Harita koordinatlarında yerleşim; yalnızca köyün karolarına, boş ve ayrılmamış yere konur."""

    def __init__(self, karolar, rng, simdi):
        self.karolar, self.rng, self.simdi = karolar, rng, simdi
        self.dolu, self.ayrik = set(), set()
        self.items = []
        self.kule_sayisi = {}

    def bos_mu(self, x0, y0, w, h, ayrik_serbest=False):
        for i in range(x0, x0 + w):
            for j in range(y0, y0 + h):
                t = (i, j)
                if t not in self.karolar or t in self.dolu or (not ayrik_serbest and t in self.ayrik):
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
        self.items.append([kimlik, x0 + w - 1, y0 + h - 1, 0, self.simdi, 0, [], {}])  # kayıtta en büyük köşe
        return True

    def kule_koy(self, kimlik, x, y):
        bk = (x // BUYUK_KARO, y // BUYUK_KARO)
        if self.kule_sayisi.get(bk, 0) >= KULE_SINIRI:
            return False
        if self.koy(kimlik, x, y, ayrik_serbest=True):
            self.kule_sayisi[bk] = self.kule_sayisi.get(bk, 0) + 1
            return True
        return False

    def ayir(self, karolar):
        self.ayrik |= set(karolar)

    def serit(self, kimlikler, x0, y0, w, h, yatay=True):
        """Kimlikleri [x0, x0+w) × [y0, y0+h) şeridine boşluksuz dizer (Arthur'un sura yaslı mahalleleri gibi);
        yatayda önce x boyunca, dikeyde önce y boyunca. Konamayanları döndürür."""
        kalan = list(kimlikler)
        uzun, kisa = (range(x0, x0 + w), range(y0, y0 + h)) if yatay else (range(y0, y0 + h), range(x0, x0 + w))
        for b in kisa:
            for a in uzun:
                if not kalan:
                    return kalan
                x, y = (a, b) if yatay else (b, a)
                kw, kh = boyut(kalan[0])
                if x + kw <= x0 + w and y + kh <= y0 + h and self.koy(kalan[0], x, y):
                    kalan.pop(0)
        return kalan

    def kume(self, kimlikler, x, y):
        """Birimleri (x, y) çevresinde düzensiz bir küme (manga) hâlinde dizer; yer kalmazsa döndürür."""
        kalan = list(kimlikler)
        if kalan:
            bos = sorted((t for t in self.karolar if t not in self.dolu and t not in self.ayrik),
                         key=lambda t: (abs(t[0] - x) + abs(t[1] - y), t))
            if bos:
                x, y = bos[0]
        uc = [(x, y)]
        gorulen = {(x, y)}
        while kalan and uc:
            # Merkeze en yakın uçlardan biri: toplu ama kenarı düzensiz bir manga
            uc.sort(key=lambda t: abs(t[0] - x) + abs(t[1] - y) + self.rng.random() * 1.5)
            cx, cy = uc.pop(0)
            if self.koy(kalan[0], cx, cy):
                kalan.pop(0)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)):
                    t = (cx + dx, cy + dy)
                    if t not in gorulen:
                        gorulen.add(t)
                        uc.append(t)
        return kalan


def _halka(karolar):
    """Köyün kenar karoları (dört komşusundan biri köyün dışında): sur buradan geçer (Arthur köyleri gibi)."""
    return {(x, y) for x, y in karolar
            if any((x + dx, y + dy) not in karolar for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))}


def _kenarlar(bks):
    """Dışa bakan büyük karo kenarları: (sütun, satır, yön) yön ∈ {K, G, B, D} (y-, y+, x-, x+)."""
    sonuc = []
    for c, r in sorted(bks):
        for yon, (dc, dr) in (("K", (0, -1)), ("G", (0, 1)), ("B", (-1, 0)), ("D", (1, 0))):
            if (c + dc, r + dr) not in bks:
                sonuc.append((c, r, yon))
    return sonuc


def _serit_kutusu(c, r, yon, derinlik):
    """Büyük karonun dış kenarı boyunca, surun hemen içinde (köşelerden ikişer karo içeride) şerit kutusu."""
    x0, y0 = c * BUYUK_KARO, r * BUYUK_KARO
    if yon == "K":
        return x0 + 2, y0 + 1, BUYUK_KARO - 4, derinlik, True
    if yon == "G":
        return x0 + 2, y0 + BUYUK_KARO - 1 - derinlik, BUYUK_KARO - 4, derinlik, True
    if yon == "B":
        return x0 + 1, y0 + 2, derinlik, BUYUK_KARO - 4, False
    return x0 + BUYUK_KARO - 1 - derinlik, y0 + 2, derinlik, BUYUK_KARO - 4, False


def _mahalle(tur, seviye, kisi):
    """Şerit türünün öğeleri ve derinliği (karo)."""
    if tur == "ev":
        return [kademe(EV, seviye)] * 16, 4
    if tur == "bostan":
        return [kademe(BOSTAN, seviye)] * 24, 6
    if tur == "kisla":
        return _askeri(seviye, kisi) * 2, 3
    if tur == "agil":
        return [k for k in (kademe(KOYUN, seviye), kademe(INEK, seviye)) if k] * 2, 4
    return _uretim(seviye, kisi, None), 2


SERIT_SIRASI = {
    "agresif": ["kisla", "ev", "uretim", "bostan", "kisla", "agil"],
    "savunmaci": ["ev", "kisla", "uretim", "bostan", "ev", "agil"],
    "tuccar": ["ev", "uretim", "bostan", "agil", "ev", "uretim"],
    "dengeli": ["bostan", "ev", "agil", "kisla", "uretim", "bostan"],
}


def serit_sirasi(kisi, rng):
    """Kişiliğin şerit türleri: ilk ikisi kişiliği belirler (sabit), kalanı köyden köye karışır (#81 incelemesi:
    dilim kopyası karıştırılıyordu, sıra hiç değişmiyordu)."""
    sira = list(SERIT_SIRASI[kisi])
    bas, son = sira[:2], sira[2:]
    rng.shuffle(son)
    return bas + son


def koy_kur(seviye, kisi, tohum, simdi):
    """(items, expansions): botun köyü. Aynı tohum aynı köyü verir. Arthur köylerindeki düzen: sur köyün kenarında,
    köşelerde kule öbekleri, kapı bir boşluk ve iki yanında kule, içeri ağaçlı bir yol; mahalleler sura yaslı
    boşluksuz şeritler; ortada çiçekli meydan; askerler düzensiz mangalar; aralarda çimen."""
    rng = random.Random(str(tohum))
    seviye = max(1, int(seviye))
    kisi = kisi if kisi in KISILIK else "dengeli"
    bks = sekil(seviye, rng)
    acik = sorted(genisleme_kimligi(c, r) for c, r in bks)
    karolar = karolari(acik)
    a = _Alan(karolar, rng, simdi)
    halka = _halka(karolar)
    kenarlar = _kenarlar(bks)
    rng.shuffle(kenarlar)

    # 1. Kapılar: dış kenarların ortasında 3 karoluk boşluk; içeri 6 karoluk yol ayrılır
    kapilar = kenarlar[:1 if seviye < 20 else 2]
    yol = set()
    for c, r, yon in kapilar:
        x0, y0 = c * BUYUK_KARO, r * BUYUK_KARO
        for k in range(9, 12):
            for d in range(0, 7):
                if yon == "K":
                    yol.add((x0 + k, y0 + d))
                elif yon == "G":
                    yol.add((x0 + k, y0 + BUYUK_KARO - 1 - d))
                elif yon == "B":
                    yol.add((x0 + d, y0 + k))
                else:
                    yol.add((x0 + BUYUK_KARO - 1 - d, y0 + k))
    a.ayir(yol)

    # 2. Belediye ve meydan: başlangıç karosunun ortasında; çevresi çiçek halısı, köşelerinde çeşme ve heykel
    mx, my = 2 * BUYUK_KARO + 8, 2 * BUYUK_KARO + 8
    a.koy(kademe(BELEDIYE, seviye), mx, my)
    meydan = {(i, j) for i in range(mx - 2, mx + 6) for j in range(my - 2, my + 6)}
    a.ayir(meydan)
    cicek = [k for s, k in CICEK if s <= seviye]
    hali = rng.choice(cicek)
    for i in range(mx - 1, mx + 5):
        for j in (my - 1, my + 4):
            a.koy(hali, i, j, ayrik_serbest=True)
    for j in range(my, my + 4):
        for i in (mx - 1, mx + 4):
            a.koy(hali, i, j, ayrik_serbest=True)
    heykeller = [k for s, k in HEYKEL if s <= seviye]
    sus = [CESME[1] if seviye >= CESME[0] else ATES[1], rng.choice(heykeller), rng.choice(heykeller),
           CESME[1] if seviye >= CESME[0] else rng.choice(heykeller)]
    for (i, j), k in zip(((mx - 2, my - 2), (mx + 5, my - 2), (mx - 2, my + 5), (mx + 5, my + 5)), sus):
        a.koy(k, i, j, ayrik_serbest=True)

    # 3. Sur (3. seviyeden) ve kuleler: köşelerde üçlü öbek, kapının iki yanında birer, kalan bütçe sur boyunca
    sur, kule = kademe(SUR, seviye), kademe(KULE, seviye)
    kapi_bosluk = {t for t in yol if t in halka}
    # İç sur kapılarının iki yanındaki kuleler önce konur: büyük karonun 10 kuleli bütçesi dış köşelerde tükenmesin
    if sur and kule and len(bks) >= 3:
        for c, r in sorted(bks):
            for dc, dr in ((1, 0), (0, 1)):
                if (c + dc, r + dr) in bks:
                    for k in (7, 13):
                        a.kule_koy(kule, *(((c + 1) * BUYUK_KARO, r * BUYUK_KARO + k) if dc
                                          else (c * BUYUK_KARO + k, (r + 1) * BUYUK_KARO)))
    if kule:
        for x, y in sorted(halka):
            dis = sum((x + dx, y + dy) not in karolar for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if dis >= 2:  # dış köşe: köşe ve iki yanı
                for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                    t = (x + dx, y + dy)
                    if t in halka and t not in kapi_bosluk:
                        a.kule_koy(kule, *t)
        for x, y in sorted(kapi_bosluk):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                t = (x + dx, y + dy)
                if t in halka and t not in kapi_bosluk:
                    a.kule_koy(kule, *t)
        fazla = KISILIK[kisi]["kule"] + seviye // 15
        kalan_halka = [t for t in sorted(halka) if t not in a.dolu and t not in kapi_bosluk]
        adim = max(5, len(kalan_halka) // max(1, fazla))
        for t in kalan_halka[rng.randrange(adim)::adim][:fazla]:
            a.kule_koy(kule, *t)
    if sur:
        for t in sorted(halka - kapi_bosluk):
            a.koy(sur, *t, ayrik_serbest=True)
        if seviye >= SUR_KAPISI[0] and kapilar:  # ilk kapıya Sur Kapısı (3×3), boşluğun içine
            c, r, yon = kapilar[0]
            x0, y0 = c * BUYUK_KARO, r * BUYUK_KARO
            yer = {"K": (x0 + 9, y0), "G": (x0 + 9, y0 + BUYUK_KARO - 3), "B": (x0, y0 + 9),
                   "D": (x0 + BUYUK_KARO - 3, y0 + 9)}[yon]
            a.koy(SUR_KAPISI[1], *yer, ayrik_serbest=True)
    # Kapıdan içeri yolun iki yanında ağaç
    agaclar = [k for s, k in AGAC if s <= seviye]
    agac = rng.choice(agaclar)
    for c, r, yon in kapilar:
        x0, y0 = c * BUYUK_KARO, r * BUYUK_KARO
        for d in range(2, 7, 2):
            for k in (8, 12):
                t = {"K": (x0 + k, y0 + d), "G": (x0 + k, y0 + BUYUK_KARO - 1 - d), "B": (x0 + d, y0 + k),
                     "D": (x0 + BUYUK_KARO - 1 - d, y0 + k)}[yon]
                a.koy(agac, *t, ayrik_serbest=True)

    # 3b. İç surlar (3 ve daha çok büyük karolu köyde): bitişik büyük karoların arasında, ortası 3 karo kapı; köy
    #     avlulara bölünür (internet taraması: oyuncu köylerinde iç surlarla bölünmüş avlular; DNT-60)
    if sur and len(bks) >= 3:
        for c, r in sorted(bks):
            for dc, dr in ((1, 0), (0, 1)):
                if (c + dc, r + dr) not in bks:
                    continue
                for k in range(1, BUYUK_KARO - 1):
                    x, y = ((c + 1) * BUYUK_KARO, r * BUYUK_KARO + k) if dc else (c * BUYUK_KARO + k, (r + 1) * BUYUK_KARO)
                    if 8 <= k <= 12:  # kapı ve iki yanında birer karo boşluk
                        a.ayir([(x, y), (x - dc, y - dr), (x + dc, y + dr)])
                        continue
                    a.koy(sur, x, y, ayrik_serbest=True)  # kapı kulelerinin yeri doluysa (yukarıda konan) atlanır

    # 4. Mahalleler: her dış kenar boyunca surun içinde boşluksuz şerit (kişiliğin sırasıyla)
    sira = serit_sirasi(kisi, rng)
    ic_kenarlar = [k for k in kenarlar]
    kullanilan = set()
    for n, (c, r, yon) in enumerate(ic_kenarlar):
        tur = sira[n % len(sira)]
        if tur in ("kisla", "agil") and tur in kullanilan:  # ordugâh ve ağıl birer şerit; fazlası ev
            tur = "ev"
        kullanilan.add(tur)
        ogeler, derinlik = _mahalle(tur, seviye, kisi)
        x0, y0, w, h, yatay = _serit_kutusu(c, r, yon, derinlik)
        a.serit(ogeler, x0, y0, w, h, yatay)
        # Şeridin iç kenarında seyrek ağaç sırası (Arthur31'deki gibi mahalleyi çimenden ayırır)
        if tur in ("ev", "bostan") and rng.random() < 0.6:
            for s in range(0, (w if yatay else h), 3):
                t = (x0 + s, y0 + h) if yatay and yon == "K" else (x0 + s, y0 - 1) if yatay else \
                    (x0 + w, y0 + s) if yon == "B" else (x0 - 1, y0 + s)
                a.koy(agac, *t)

    # 5. Mahalle blokları: her büyük karonun ortasında 10×10'luk sık blok (Arthur32'deki ev ve bostan blokları gibi);
    #    başlangıç karosunda meydanın doğusu ve güneyi
    buyukler = [k for k in (kademe(PAZAR, seviye), kademe(INANC, seviye) if seviye >= 20 else None,
                            kademe(KALE, seviye) if kisi == "savunmaci" and seviye >= 10 else None) if k]
    bloklar = {"ev": [kademe(EV, seviye)] * 25, "bostan": [kademe(BOSTAN, seviye)] * 25,
               "kisla": _askeri(seviye, kisi) * 4, "carsi": buyukler + _uretim(seviye, kisi, None) * 2}
    turler = list(SERIT_SIRASI[kisi])
    rng.shuffle(turler)
    turler = ["carsi"] + [t if t in bloklar and not (t == "kisla" and "kisla" in kullanilan) else "ev" for t in turler]
    diger = [(c, r) for c, r in sorted(bks) if (c, r) != (2, 2)]
    rng.shuffle(diger)
    for n, (c, r) in enumerate(diger):
        tur = turler[n % len(turler)]
        a.serit(bloklar[tur], c * BUYUK_KARO + 5, r * BUYUK_KARO + 5, 10, 10, rng.random() < 0.5)
    if not diger:  # tek karolu köy: pazar ve üretim meydanın yanında
        a.serit(bloklar["carsi"], mx + 6, my - 3, 6, 6)
    else:
        a.serit(_uretim(seviye, kisi, None)[:3], mx + 6, my - 3, 6, 9)

    # 6. Ordu: kışlaların önünde ve meydanda 2-4 düzensiz manga
    ordu = [birim_sec(seviye, kisi, rng) for _ in range(ordu_buyuklugu(seviye, kisi))]
    ordu.sort()
    # 15. seviyeden bir avluda asker geçidi: ordunun yarısı (en az 8, en çok 16), türüne göre sıra sıra, bir karo arayla
    #     (internet taraması: 55. seviye oyuncu köyünde avluda sıralı ordu; DNT-60)
    if seviye >= 15 and len(ordu) >= 12:
        sutun = 4
        adet = min(16, max(8, len(ordu) // 2)) // sutun * sutun  # en az iki sıra
        hedefler = sorted(karolar, key=lambda t: (abs(t[0] - mx - 1) + abs(t[1] - my - 10), t))
        bitti = False
        for satir in range(adet // sutun, 1, -1):  # yer yoksa sıra sayısı azalır, en az iki sıra
            gecit = sorted(ordu, key=lambda k: (-ordu.count(k), k))[:satir * sutun]
            for x0, y0 in hedefler:
                if a.bos_mu(x0, y0, 2 * sutun - 1, 2 * satir - 1):
                    for n, k in enumerate(gecit):
                        a.koy(k, x0 + 2 * (n % sutun), y0 + 2 * (n // sutun))
                        ordu.remove(k)
                    bitti = True
                    break
            if bitti:
                break
    manga_sayisi = min(4, 2 + seviye // 20)
    adaylar = [(mx + rng.randint(-1, 4), my + 6 + rng.randint(0, 2))]
    for c, r in sorted(bks):
        adaylar.append((c * BUYUK_KARO + rng.randint(6, 13), r * BUYUK_KARO + rng.randint(6, 13)))
    rng.shuffle(adaylar)
    boy = max(1, len(ordu) // manga_sayisi)
    kalan = []
    for m in range(manga_sayisi):
        parca = ordu[m * boy:(m + 1) * boy] if m < manga_sayisi - 1 else ordu[m * boy:]
        x, y = adaylar[m % len(adaylar)]
        kalan += a.kume(parca, x, y)
    for _ in range(4):  # sığmayanlar yeni bir manga olur (boş çimende)
        if not kalan:
            break
        x, y = rng.choice(sorted(karolar))
        kalan = a.kume(kalan, x, y)

    # 7. Süs: çimende ağaç öbekleri, kapı kulelerinin içinde bayrak
    bayraklar = [k for s, k in BAYRAK if s <= seviye]
    bayrak = 174 if rng.random() < 0.35 else rng.choice(bayraklar)
    for t in sorted(yol)[:: max(1, len(yol) // 4)]:
        a.koy(bayrak, t[0] + 2, t[1], ayrik_serbest=False)
    for _ in range(2 + 2 * len(bks)):
        x, y = rng.choice(sorted(karolar))
        tur = rng.choice(agaclar)
        for _ in range(rng.randint(3, 6)):
            a.koy(tur, x + rng.randint(-1, 1), y + rng.randint(-1, 1))
    return a.items, acik


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
    items = harita.setdefault("items", [])
    dolu = set()
    for e in items:
        try:
            dolu |= kapladigi(e)
        except (TypeError, ValueError, IndexError):
            continue
    alan = sorted(karolari(harita.get("expansions") or [13]) - dolu)
    for _ in range(60 if alan else 0):
        x, y = rng.choice(alan)
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
    harita["skin"] = arazi_sec(pi.get("pid", ""))
    pi["bot_tasarim"] = TASARIM_SURUMU
    return True
