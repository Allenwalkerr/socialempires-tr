# -*- coding: utf-8 -*-
"""Oyun SWF'sindeki sabit arayüz yazılarını Türkçeleştirir.

İstemcideki bazı yazılar (ör. "Cancel", "Next", "Share") config'teki
yerelleştirme metinlerinden değil, SWF içindeki metin alanlarının
(DefineEditText) başlangıç değerlerinden gelir. Bu modül o alanları
`ceviri/arayuz_tr.json` sözlüğüne göre değiştirip yeni bir SWF üretir.

Oyun kodundaki (DoABC) bazı sabit dizeler de ekrana çıkar: yükleme perdesindeki
"Cargando" böyledir (dil İngilizce değilse gösterilir). Bunlar `as3_dizeleri`
sözlüğüyle sabit havuzunda değiştirilir.

Yalnızca eşleşen metin alanları ve dizeler değişir; geri kalan etiketler bayt bayt
korunur. Gömülü yazı tiplerine eksik Türkçe harfler eklenir (swf_font).
Yazı tipine gömülü sabit yazılar (DefineText) çevrilemez.
"""

import hashlib
import html
import json
import os
import re
import struct
import tempfile
import threading
import zlib

from oyun import swf_font
from oyun.yollar import ASSETS_DIR, CEVIRI_DIR
TR_FONTLARI = ("tr_ArialRoundedBold.swf", "tr_ErasBold.swf")
_URETIM_KILIDI = threading.Lock()
YAMA_SURUMU = b"12"  # yama mantığı değişince artırın (önbellek yenilensin)
SOZLUK = os.path.join(CEVIRI_DIR, "arayuz_tr.json")

_ETIKET = re.compile(r"<[^>]+>")


def anahtar(metin: str) -> str:
    """Metin alanının içeriğini sözlük anahtarına çevirir (HTML'siz)."""
    return html.unescape(_ETIKET.sub("", metin)).strip()


def _sozluk():
    with open(SOZLUK, encoding="utf-8") as f:
        return json.load(f)


def _govde(veri: bytes):
    imza = veri[:3]
    if imza == b"FWS":
        return veri[8:]
    if imza == b"CWS":
        return zlib.decompress(veri[8:])
    raise ValueError("desteklenmeyen SWF bicimi: %r" % imza)


def _etiketler(govde: bytes):
    """(kod, içerik_başı, içerik_sonu, başlık_başı) dörtlülerini üretir."""
    nbit = govde[0] >> 3
    p = (5 + nbit * 4 + 7) // 8 + 4  # RECT + kare hızı + kare sayısı
    yield None, 0, p, 0
    while p < len(govde):
        bas = p
        kod_uzunluk = struct.unpack_from("<H", govde, p)[0]
        p += 2
        kod, uzunluk = kod_uzunluk >> 6, kod_uzunluk & 0x3F
        if uzunluk == 0x3F:
            uzunluk = struct.unpack_from("<I", govde, p)[0]
            p += 4
        yield kod, p, p + uzunluk, bas
        p += uzunluk
        if kod == 0:
            break


def _baslik(kod: int, uzunluk: int) -> bytes:
    return struct.pack("<HI", (kod << 6) | 0x3F, uzunluk)


DO_ABC = 82


def _u30_oku(b: bytes, p: int):
    deger = kayma = 0
    while True:
        x = b[p]
        p += 1
        deger |= (x & 0x7F) << kayma
        kayma += 7
        if not x & 0x80:
            return deger, p


def _u30_yaz(n: int) -> bytes:
    cikti = bytearray()
    while True:
        x, n = n & 0x7F, n >> 7
        cikti.append(x | 0x80 if n else x)
        if not n:
            return bytes(cikti)


def abc_dizelerini_degistir(t: bytes, harita: dict):
    """DoABC etiketinin sabit havuzundaki dizeleri değiştirir: (yeni_etiket, değişen_sayısı).

    Havuz sırayla okunur (int, uint, double, dize); dizelerden sonrası olduğu gibi kalır.
    Kod dizelere sıra numarasıyla eriştiği için uzunluk değişmesi bir şeyi kaydırmaz.
    """
    ad_sonu = t.index(b"\0", 4) + 1  # bayraklar (4 bayt) + ad
    abc = t[ad_sonu:]
    p = 4  # küçük ve büyük sürüm
    for boy in (None, None, 8):  # int, uint (değişken uzunluk), double (8 bayt)
        sayi, p = _u30_oku(abc, p)
        for _ in range(max(sayi - 1, 0)):
            if boy:
                p += boy
            else:
                _, p = _u30_oku(abc, p)
    sayi, p = _u30_oku(abc, p)
    havuz_basi, parcalar, degisen = p, [], 0
    for _ in range(max(sayi - 1, 0)):
        uzunluk, bas = _u30_oku(abc, p)
        p = bas + uzunluk
        dize = abc[bas:p].decode("utf-8", "replace")
        if dize in harita:
            yeni = harita[dize].encode("utf-8")
            parcalar.append(_u30_yaz(len(yeni)) + yeni)
            degisen += 1
        else:
            parcalar.append(abc[bas - len(_u30_yaz(uzunluk)):p])
    if not degisen:
        return t, 0
    return t[:ad_sonu] + abc[:havuz_basi] + b"".join(parcalar) + abc[p:], degisen


def _font_konumu(t: bytes):
    """DefineEditText'teki FontID'nin konumu (yoksa None)."""
    nbit = t[2] >> 3
    p = 2 + (5 + nbit * 4 + 7) // 8
    return p + 2 if t[p] & 0x01 else None


def _metin_konumu(t: bytes):
    """DefineEditText içindeki InitialText'in (başlangıç, bitiş, html) konumu."""
    nbit = t[2] >> 3
    p = 2 + (5 + nbit * 4 + 7) // 8
    b1, b2 = t[p], t[p + 1]
    p += 2
    metin_var, renk_var, uzunluk_var, font_var = b1 & 0x80, b1 & 0x04, b1 & 0x02, b1 & 0x01
    font_sinifi_var, yerlesim_var, html_mi = b2 & 0x80, b2 & 0x20, b2 & 0x02
    if not metin_var:
        return None
    if font_var:
        p += 2
    if font_sinifi_var:
        p = t.index(b"\0", p) + 1
    if font_var or font_sinifi_var:
        p += 2
    if renk_var:
        p += 4
    if uzunluk_var:
        p += 2
    if yerlesim_var:
        p += 9
    p = t.index(b"\0", p) + 1  # değişken adı
    son = t.index(b"\0", p)
    return p, son, bool(html_mi)


def _rect_oku(t: bytes, p: int = 2):
    """SWF RECT (Xmin, Xmax, Ymin, Ymax) ve bayt uzunluğu."""
    nbit = t[p] >> 3
    bitler = int.from_bytes(t[p:p + (5 + nbit * 4 + 7) // 8], "big")
    toplam = ((5 + nbit * 4 + 7) // 8) * 8
    degerler = []
    for i in range(4):
        kaydir = toplam - 5 - nbit * (i + 1)
        d = (bitler >> kaydir) & ((1 << nbit) - 1)
        if nbit and d >> (nbit - 1):
            d -= 1 << nbit
        degerler.append(d)
    return degerler, (5 + nbit * 4 + 7) // 8


def _rect_yaz(degerler) -> bytes:
    nbit = max(max(abs(d) for d in degerler).bit_length() + 1, 1)
    bitler = nbit
    for d in degerler:
        bitler = (bitler << nbit) | (d & ((1 << nbit) - 1))
    toplam = 5 + nbit * 4
    dolgu = (-toplam) % 8
    return (bitler << dolgu).to_bytes((toplam + dolgu) // 8, "big")


EN_COK_GENISLEME = 1.6
EN_KUCUK_YAZI = 0.7  # sığmayan yazıda harf boyu en çok bu kata iner


def _gorunen(metin: str) -> str:
    return re.sub(r"<[^>]+>", "", html.unescape(metin)) if "<" in metin else metin


def _alan_bilgisi(t: bytes):
    """DefineEditText'ten (b1, b2, font_id, yukseklik, hiza, sol_bosluk, sag_bosluk, rect_uz, yukseklik_konumu)."""
    _, rect_uz = _rect_oku(t)
    p = 2 + rect_uz
    b1, b2 = t[p], t[p + 1]
    q = p + 2
    font_id = yukseklik = yk = None
    if b1 & 0x01:
        font_id = struct.unpack_from("<H", t, q)[0]
        q += 2
    if b2 & 0x80:
        q = t.index(b"\0", q) + 1
    if b1 & 0x01 or b2 & 0x80:
        yk = q
        yukseklik = struct.unpack_from("<H", t, q)[0]
        q += 2
    if b1 & 0x04:
        q += 4
    if b1 & 0x02:
        q += 2
    hiza = sol = sag = 0
    if b2 & 0x20:
        hiza = t[q]
        sol, sag = struct.unpack_from("<HH", t, q + 1)
    return b1, b2, font_id, yukseklik, hiza, sol, sag, rect_uz, yk


KENAR = 80  # Flash metin alanının iki yanındaki 2'şer piksellik boşluk (twip)


def alani_genislet(t: bytes, metin: str, fontlar) -> bytes:
    """DefineEditText'te çeviri kutuya sığmıyorsa kutuyu hizasına göre gerektiği kadar genişletir (kesik yazı:
    '28 NAKİ', sahibinin bildirimi 12.11.2026). Metnin eni yazı tipinin harf ilerlemelerinden hesaplanır (DefineFont3:
    em 1024 × 20). Satırlar ayrı ayrı ölçülür; sözcük kaydıran alanda (WordWrap) satır kendiliğinden bölündüğü için
    yalnızca en uzun sözcük. Kendiliğinden boyutlanan (AutoSize) alana, yazı tipi ya da harfi bilinmeyen alana
    dokunmaz; genişlik en çok EN_COK_GENISLEME kat olur, yine sığmazsa harf boyu (FontHeight) en çok EN_KUCUK_YAZI katına
    iner. Sığan alan değişmez (gereksiz geniş metin kutusu yanındaki
    düğmenin tıklanmasını kapatabilirdi). %6 + 2 piksellik pay ölçülmüş değil, Ruffle dizgisine karşı güvenlik payıdır."""
    bilgi = _alan_bilgisi(t)
    b1, b2, font_id, yukseklik, hiza, sol, sag, rect_uz, yk = bilgi
    if b2 & 0x40 or font_id is None or not yukseklik:  # AutoSize: kutu zaten metne göre büyür
        return t
    font = fontlar.get(font_id)
    if font is None or not font.duzen:
        return t
    ilerleme = font.duzen[1]
    sira = {k: i for i, k in enumerate(font.kodlar)}
    gorunen = _gorunen(metin).replace("\n", "\r").strip()
    if any(ord(h) not in sira for h in gorunen if not h.isspace()) or not gorunen:
        return t
    bosluk = ilerleme[sira[32]] if 32 in sira else 0

    # HTML alanda (b2 0x02) çizilen boy <font size="..."> etiketinden gelir (piksel; ×20 twip), FontHeight geçersiz
    # kalır: ölçüm etiketteki en büyük boyla yapılır ve harf küçültülmez, yalnızca kutu genişler (#81 incelemesi)
    html_mi = bool(b2 & 0x02)
    boylar = [int(b) * 20 for b in re.findall(r'size="(\d+)"', metin)] if html_mi else []
    olcu_boyu = max(boylar) if boylar else yukseklik

    def olc(parca):
        return sum(ilerleme[sira[ord(h)]] if ord(h) in sira else bosluk for h in parca) * olcu_boyu / 20480

    satirlar = [s.strip() for s in gorunen.split("\r")]
    # Sözcük kaydıran alanda (WordWrap) satır bölünür; kesilen yalnızca kutudan uzun tek sözcüktür
    parcalar = [w for s in satirlar for w in s.split()] if b1 & 0x40 else satirlar
    en = max((olc(p) for p in parcalar), default=0)
    (xmin, xmax, ymin, ymax), _ = _rect_oku(t)
    genislik = xmax - xmin
    # Ruffle'ın dizgisi yazı tipi ilerlemesinden biraz geniş olabilir: %6 ve 2 piksel pay
    ek = int(en * 1.06 + 40 + sol + sag + KENAR - genislik + 0.5)
    sinir = int(genislik * (EN_COK_GENISLEME - 1))
    yeni_yukseklik = yukseklik
    if ek > sinir and html_mi:
        ek = sinir
    elif ek > sinir:
        # En geniş kutuya da sığmıyor: önce harf boyu küçülür (en çok EN_KUCUK_YAZI katına, kutuyu hiç
        # genişletmeden sığacak kadar), kutu kalan kadar genişler (yandaki yazının üstüne az taşsın)
        sigan = genislik - sol - sag - KENAR - 40
        yeni_yukseklik = max(int(yukseklik * sigan / (en * 1.06)), int(yukseklik * EN_KUCUK_YAZI + 0.5))
        en = en * yeni_yukseklik / yukseklik
        ek = min(int(en * 1.06 + 40 + sol + sag + KENAR - genislik + 0.5), sinir)
    if ek <= 0:
        return t
    if hiza == 1:      # sağa dayalı: sola açılır
        xmin -= ek
    elif hiza == 2:    # ortalı: iki yana
        xmin -= ek // 2
        xmax += ek - ek // 2
    else:              # sola dayalı ya da iki yana yaslı: sağa açılır
        xmax += ek
    if yeni_yukseklik != yukseklik:
        t = t[:yk] + struct.pack("<H", yeni_yukseklik) + t[yk + 2:]
    return t[:2] + _rect_yaz((xmin, xmax, ymin, ymax)) + t[2 + rect_uz:]


def _html_degistir(kaynak: str, ceviri: str) -> str:
    """HTML metnin ilk yazı düğümüne çeviriyi koyar, diğerlerini boşaltır."""
    parcalar = re.split(r"(<[^>]+>)", kaynak)
    yeni = html.escape(ceviri, quote=False).replace("\r", "<br>")
    yazildi = False
    for i, parca in enumerate(parcalar):
        if parca.startswith("<") or not parca.strip():
            continue
        parcalar[i] = "" if yazildi else yeni
        yazildi = True
    return "".join(parcalar)


def _turkce_fontlar():
    """assets/fonts/tr_*.swf içindeki yazı tiplerini {ad: (Font3, bölge)} olarak yükler."""
    fontlar = {}
    klasor = os.path.join(ASSETS_DIR, "fonts")
    for ad in TR_FONTLARI:
        yol = os.path.join(klasor, ad)
        if not os.path.exists(yol):
            continue
        with open(yol, "rb") as f:
            govde = _govde(f.read())
        font, bolge = None, None
        for kod, bas, son, _ in _etiketler(govde):
            if kod == swf_font.DEFINE_FONT3:
                font = swf_font.Font3(govde[bas:son])
            elif kod == swf_font.ALIGN_ZONES:
                bolge = govde[bas:son]
        if font:
            fontlar[font.adi()] = (font, bolge)
    return fontlar


def _fontlari_tamamla(govde, etiketler):
    """Gömülü yazı tiplerine eksik Türkçe harfleri ekler.

    Dönüş: {başlık_başı: yeni_etiket_baytları}, glif eşlemeleri ve
    yazı tipleri (önceki/sonraki hâlleriyle, kimliğe göre).
    """
    kaynaklar = _turkce_fontlar()
    bolgeler = {}
    for kod, bas, son, _ in etiketler:
        if kod == swf_font.ALIGN_ZONES:
            bolgeler[struct.unpack_from("<H", govde, bas)[0]] = (bas, son)
    degisim, eslemeler, eski_fontlar, yeni_fontlar = {}, {}, {}, {}
    for kod, bas, son, baslik_bas in etiketler:
        if kod != swf_font.DEFINE_FONT3:
            continue
        font = swf_font.Font3(govde[bas:son])
        eski_fontlar[font.kimlik] = swf_font.Font3(govde[bas:son])
        yeni_fontlar[font.kimlik] = font
        if font.adi() not in kaynaklar:
            continue
        kaynak, kaynak_bolge = kaynaklar[font.adi()]
        b = bolgeler.get(font.kimlik)
        eslem, yeni_bolge = swf_font.harf_ekle(font, kaynak, govde[b[0]:b[1]] if b else None, kaynak_bolge)
        if eslem is None:
            continue
        eslemeler[font.kimlik] = eslem
        t = font.yaz()
        degisim[baslik_bas] = _baslik(kod, len(t)) + t
        if b and yeni_bolge:
            degisim[("bolge", b[0])] = yeni_bolge
    return degisim, eslemeler, eski_fontlar, yeni_fontlar


def _yazi_tipini_uydur(t, metin, fontlar):
    """Alanın yazı tipinde çevirinin bir harfi yoksa (ör. yalnızca 13 harfli
    Arial Narrow sayaç etiketleri), harflerin hepsini içeren bir yazı tipine geçer."""
    konum = _font_konumu(t)
    if konum is None:
        return t
    gerekli = {ord(h) for h in metin if not h.isspace()}
    mevcut = fontlar.get(struct.unpack_from("<H", t, konum)[0])
    if mevcut is None or gerekli <= set(mevcut.kodlar):
        return t
    for kimlik, font in fontlar.items():
        if font.adi() == "Arial Rounded MT Bold" and gerekli <= set(font.kodlar):
            return t[:konum] + struct.pack("<H", kimlik) + t[konum + 2:]
    return t


# DNT-35 (denetim TRA-02): AS3'ün String.toUpperCase'i Türkçe kuralı bilmez ("Değirmen" → "DEĞIRMEN"; Ruffle da
# Unicode'un dile bağsız eşlemesini kullanır). Ekrana çıkan tek yer, koleksiyonu tamamlanan binanın tebrik penceresi:
# PopUpCollectionComplete/<kurucu> bina adını dört kez büyütür: buildingStringName @50, POPUP_EDIFICIO_ENHORABUENA
# metnine giden ad @140, vurgulanacak yeri bulan iki indexOf @198 ve @216 (1.4.07 bayt kodu, araclar/abc_okur.py).
# Dördü birlikte kaldırılır: ad olduğu gibi ("Değirmen") yazılır ve indexOf yine bulur, vurgu bozulmaz. Öteki
# toUpperCase'ler ekrana çıkmaz (düğme durumu adları, karşılaştırmalar, turnuva sonuç kodu) ya da yalnızca ASCII
# çevirisi olan dizeleri büyütür.
#
# Çapa: getlocal_0, getlocal_1, getproperty name (158), callproperty toUpperCase (2767) 0, initproperty
# buildingStringName (10828). Bu dizi 1.4.07 istemcisinde bir kez geçer; çağrılar çapanın toUpperCase'inden +0, +90,
# +148, +166 bayttadır. Bir şey uymazsa hiç dokunulmaz.
BUYUTME = bytes.fromhex("46cf1500")      # callproperty toUpperCase, 0 argüman
BUYUTME_CAPASI = bytes.fromhex("d0d1669e01") + BUYUTME + bytes.fromhex("68cc54")
BUYUTME_ARALARI = (0, 90, 148, 166)
NOP = 0x02  # yığına dokunmaz: alıcı dize yığında kalır, toUpperCase hiç çağrılmamış gibi olur


def buyutmeyi_kaldir(t: bytes):
    """(yeni_etiket, kaldırılan_çağrı_sayısı). Yalnızca çapa tek kez geçiyor ve dört yerin dördü de beklenen çağrıysa."""
    if t.count(BUYUTME_CAPASI) != 1:
        return t, 0
    bas = t.index(BUYUTME_CAPASI) + 5
    yerler = [bas + ara for ara in BUYUTME_ARALARI]
    if any(t[y:y + len(BUYUTME)] != BUYUTME for y in yerler):
        return t, 0
    b = bytearray(t)
    for y in yerler:
        b[y:y + len(BUYUTME)] = bytes([NOP]) * len(BUYUTME)
    return bytes(b), len(yerler)


# Köyden köye geçiş (sahibinin isteği, 12.11.2026: "başka bir farklı köye bakmak için illa my towna dönmem lazım").
# FriendButton/mouseUsed@41-58 (1.4.07 bayt kodu, araclar/abc_okur.py): `if (Base.Main.gameModeCurrent != GameMode.NORMAL)
# return;` Komşu köyde mod NEIGHBOUR olduğundan alttaki arkadaş düğmesi hiçbir şey yapmaz. GameMode: TUTORIAL 0,
# NORMAL 1, NEIGHBOUR 2, ASSAULT 3, CAMPAIGN 4, SURVIVAL 5, TOURNAMENT 6, SPY 7, EDITOR 10. Koşul aynı uzunlukta
# `(uint)(mod - 1) <= 1` olur: yalnızca NORMAL ve NEIGHBOUR geçer (eğitim -1 → 2^32-1, saldırı ve görevler > 1).
# Bayt: getlex GameMode (60 9c01), getproperty NORMAL (66 9b02), ifeq +1 (13 010000) → nop nop (02 02), decrement
# (93), convert_u (74), pushbyte 1 (24 01), ifle +1 (16 010000); atlamanın sonu ve hedefi (returnvoid'in ardı) aynı.
# Çapa öncesi getlex Base (60 01), getproperty Main (66 0c), getproperty gameModeCurrent (66 c201), sonrası returnvoid.
# Tek kez geçmezse dokunulmaz.
KOMSU_KOSULU = bytes.fromhex("6001660c66c201" "609c01669b0213010000" "47")
KOMSU_KOSULU_YENI = bytes.fromhex("6001660c66c201" "0202937424011601000" "0" "47")


def komsudan_komsuya(t: bytes):
    """(yeni_etiket, değişen): FriendButton'ın komşu köyde de çalışması; çapa tek değilse dokunmaz."""
    if t.count(KOMSU_KOSULU) != 1:
        return t, 0
    return t.replace(KOMSU_KOSULU, KOMSU_KOSULU_YENI), 1


def turkcelestir(veri: bytes, sozluk=None):
    """SWF baytlarını alır, (yeni_swf_baytları, değişen_alan_sayısı) döndürür."""
    sozluk = _sozluk() if sozluk is None else sozluk
    govde = _govde(veri)
    etiketler = list(_etiketler(govde))
    degisim, eslemeler, eski_fontlar, yeni_fontlar = _fontlari_tamamla(govde, etiketler)
    statik = sozluk.get("statik_yazilar", {})
    as3 = sozluk.get("as3_dizeleri", {})
    sozluk = sozluk.get("metin_alanlari", sozluk)
    cikti = []
    degisen = 0
    for kod, bas, son, baslik_bas in etiketler:
        if kod is None:
            cikti.append(govde[bas:son])
            continue
        if baslik_bas in degisim:
            cikti.append(degisim[baslik_bas])
            continue
        if ("bolge", bas) in degisim:
            t = degisim[("bolge", bas)]
            cikti.append(_baslik(kod, len(t)) + t)
            continue
        if kod == DO_ABC:
            t, sayi = abc_dizelerini_degistir(govde[bas:son], as3) if as3 else (govde[bas:son], 0)
            t, kaldirilan = buyutmeyi_kaldir(t)
            t, komsu = komsudan_komsuya(t)
            if sayi or kaldirilan or komsu:
                cikti.append(_baslik(kod, len(t)) + t)
                degisen += sayi + kaldirilan + komsu
                continue
        if kod in (swf_font.DEFINE_TEXT, swf_font.DEFINE_TEXT2):
            t = govde[bas:son]
            onek, kayitlar = swf_font.metin_kayitlari(t, kod)
            satirlar = swf_font.metni_coz(kayitlar, eski_fontlar)
            ceviri = statik.get("|".join(satirlar)) if satirlar else None
            yeni = swf_font.metni_degistir(kayitlar, eski_fontlar, yeni_fontlar, ceviri.split("|")) if ceviri else None
            if yeni:
                t = swf_font.metin_yaz(onek, yeni)
                degisen += 1
            elif eslemeler:
                t = swf_font.metin_yaz(onek, swf_font.glifleri_esle(kayitlar, eslemeler))
            cikti.append(_baslik(kod, len(t)) + t)
            continue
        if kod == 37:
            t = govde[bas:son]
            konum = _metin_konumu(t)
            if konum:
                m_bas, m_son, html_mi = konum
                metin = t[m_bas:m_son].decode("utf-8", "replace")
                ceviri = sozluk.get(anahtar(metin))
                if ceviri:
                    yeni_metin = _html_degistir(metin, ceviri) if html_mi else ceviri
                    t = t[:m_bas] + yeni_metin.encode("utf-8") + t[m_son:]
                    t = _yazi_tipini_uydur(t, ceviri, yeni_fontlar)
                    t = alani_genislet(t, yeni_metin, yeni_fontlar)
                    cikti.append(_baslik(kod, len(t)) + t)
                    degisen += 1
                    continue
        cikti.append(govde[baslik_bas:son])
    yeni_govde = b"".join(cikti)
    basluk = b"CWS" + veri[3:4] + struct.pack("<I", len(yeni_govde) + 8)
    return basluk + zlib.compress(yeni_govde, 6), degisen


def onbellekli_turkcelestir(kaynak_yol: str, onbellek_klasoru: str) -> str:
    """Yamalanmış SWF'yi önbellekte üretir ve yolunu döndürür.

    Kaynak dosya veya sözlük değişince yeniden üretilir.
    """
    with open(kaynak_yol, "rb") as f:
        veri = f.read()
    ozet = hashlib.sha1(veri + YAMA_SURUMU)
    for yol in [SOZLUK] + [os.path.join(ASSETS_DIR, "fonts", ad) for ad in TR_FONTLARI]:
        if os.path.exists(yol):
            with open(yol, "rb") as f:
                ozet.update(f.read())
    ad = os.path.splitext(os.path.basename(kaynak_yol))[0]
    hedef = os.path.join(onbellek_klasoru, f"{ad}.tr-{ozet.hexdigest()[:12]}.swf")
    with _URETIM_KILIDI:  # aynı anda gelen istekler dosyayı iki kez üretmesin
        if not os.path.exists(hedef):
            os.makedirs(onbellek_klasoru, exist_ok=True)
            yeni, degisen = turkcelestir(veri)
            fd, gecici = tempfile.mkstemp(dir=onbellek_klasoru, suffix=".tmp")
            with os.fdopen(fd, "wb") as f:
                f.write(yeni)
            os.replace(gecici, hedef)
            print(f" [+] {ad}.swf Turkcelestirildi ({degisen} metin alani)")
            _eskileri_sil(onbellek_klasoru, ad, hedef)
    return hedef


def _eskileri_sil(klasor, ad, kalacak):
    """Aynı SWF'nin önceki sözlükle üretilmiş kopyaları (her biri ~4 MB) birikmesin (TRA-06, DNT-38). Yalnızca
    `<ad>.tr-<12 hex>.swf`; başka SWF'lerin kopyalarına dokunulmaz. Silinemeyen (ör. Windows'ta açık) dosya kalır."""
    desen = re.compile(re.escape(ad) + r"\.tr-[0-9a-f]{12}\.swf")
    for dosya in os.listdir(klasor):
        yol = os.path.join(klasor, dosya)
        if desen.fullmatch(dosya) and yol != kalacak:
            try:
                os.remove(yol)
            except OSError as hata:
                print(f" ! Eski Turkce SWF silinemedi ({dosya}): {hata}")
