"""SWF yamaları (oyun.swf_yama, oyun.swf_font) için el yapımı SWF'lerle testler.

Gerçek oyun SWF'leri depoda yok (CI'da da yok); her girdi burada SWF biçim belgesine göre baytı baytına
kurulur (Adobe "SWF File Format Specification" v19, aşağıda "belge"). Beklenen değerler belgeden, elle
hesaplanmış formüllerden ya da gidiş-dönüş değişmezlerinden gelir; uygulamanın kendi çıktısından değil.
"""

import json
import os
import shutil
import struct
import tempfile
import unittest
import zlib
from unittest import mock

from ortak import KOK  # noqa: F401

from oyun import swf_font, swf_yama
from oyun.swf_font import Font3


# --- belgeye göre kurucular (uygulamadan bağımsız) -------------------------------------------------------

def _bitler(*alanlar):
    """(değer, bit_sayısı) alanlarını en anlamlı bit önce yazar, bayta sıfırla tamamlar (belge: Bit values).
    İşaretli değerler ikiye tümleyenle yazılır; maske ikisini de karşılar."""
    s = "".join(format(d & ((1 << n) - 1), "0%db" % n) for d, n in alanlar if n)
    s += "0" * (-len(s) % 8)
    return bytes(int(s[i:i + 8], 2) for i in range(0, len(s), 8))


def _rect(n, xmin, xmax, ymin, ymax):
    """RECT: Nbits UB[5], ardından dört SB[Nbits]."""
    return _bitler((n, 5), (xmin, n), (xmax, n), (ymin, n), (ymax, n))


def _u30(n):
    """AVM2 overview 4.1: u30, 7 bitlik gruplar, düşük grup önce, üst bit 'devamı var'."""
    cikti = b""
    while n >= 0x80:
        cikti += bytes([n & 0x7F | 0x80])
        n >>= 7
    return cikti + bytes([n])


def _dize(s):
    """AVM2 string_info: u30 bayt uzunluğu + UTF-8 baytları."""
    b = s.encode("utf-8")
    return _u30(len(b)) + b


def _etiket(kod, icerik, uzun=False):
    """RECORDHEADER: kısa biçim (kod << 6 | uzunluk) ya da uzunluk 0x3F + UI32 (uzun biçim)."""
    if uzun or len(icerik) >= 0x3F:
        return struct.pack("<HI", kod << 6 | 0x3F, len(icerik)) + icerik
    return struct.pack("<H", kod << 6 | len(icerik)) + icerik


# Belgedeki örnek başlık: 550x400 piksellik sahne = (0, 11000, 0, 8000) twip, 15 bitlik RECT.
SAHNE = bytes.fromhex("7800055F00000FA000")
BASLIK = SAHNE + b"\x00\x18" + b"\x01\x00"  # RECT + kare hızı 24.0 (UI16 8.8) + kare sayısı 1


def _swf(*etiketler, imza=b"FWS", surum=10):
    govde = BASLIK + b"".join(etiketler) + b"\x00\x00"  # End
    veri = govde if imza == b"FWS" else zlib.compress(govde)
    return imza + bytes([surum]) + struct.pack("<I", len(govde) + 8) + veri


def _etiketleri_ayir(govde):
    """Bağımsız etiket ayırıcı: [(kod, ham_etiket, içerik)]."""
    p, cikti = len(BASLIK), []
    while p < len(govde):
        bas = p
        ku = struct.unpack_from("<H", govde, p)[0]
        p += 2
        kod, uz = ku >> 6, ku & 0x3F
        if uz == 0x3F:
            uz = struct.unpack_from("<I", govde, p)[0]
            p += 4
        cikti.append((kod, govde[bas:p + uz], govde[p:p + uz]))
        p += uz
    return cikti


def _ac(veri):
    return zlib.decompress(veri[8:]) if veri[:3] == b"CWS" else veri[8:]


def _edit_text(kimlik, metin, font=None, font_sinifi=None, html=False, renk=None, azami=None, yerlesim=False):
    """DefineEditText (kod 37): (içerik, InitialText'in başlangıcı). Sıra belgedeki gibi: FontID, FontClass,
    FontHeight, TextColor, MaxLength, Align+LeftMargin+RightMargin+Indent+Leading, VariableName, InitialText.
    Düzeni etkilemeyen bayraklar da (WordWrap, ReadOnly, AutoSize, Border, UseOutlines) açılır."""
    b1, b2, ek = 0x40 | 0x08, 0x40 | 0x08 | 0x01, b""
    if metin is not None:
        b1 |= 0x80
    if font is not None:
        b1 |= 0x01
        ek += struct.pack("<H", font)
    if font_sinifi is not None:
        b2 |= 0x80
        ek += font_sinifi + b"\0"
    if font is not None or font_sinifi is not None:
        ek += struct.pack("<H", 240)  # FontHeight
    if renk is not None:
        b1 |= 0x04
        ek += renk
    if azami is not None:
        b1 |= 0x02
        ek += struct.pack("<H", azami)
    if yerlesim:  # son baytı sıfır: 9 bayt tam atlanmazsa değişken adı yanlış yerde biter
        b2 |= 0x20
        ek += bytes([1]) + struct.pack("<HHHh", 2, 3, 4, 5)
    if html:
        b2 |= 0x02
    onek = struct.pack("<H", kimlik) + _rect(12, -40, 1500, 0, 300) + bytes([b1, b2]) + ek + b"_txt\0"
    return onek + (metin.encode("utf-8") + b"\0" if metin is not None else b""), len(onek)


def _do_abc(dizeler, ad=b"frame"):
    """DoABC (kod 82): Flags UI32 + Name STRING + abcData. Ad tek uzunlukta: ad sonu tek konumda kalır."""
    havuz = _u30(3) + _u30(1000) + b"\xff\xff\xff\xff\x0f"          # int: 1000, -1 (5 baytlık s32)
    havuz += _u30(2) + _u30(300)                                      # uint: 300 (iki bayt)
    havuz += _u30(3) + struct.pack("<dd", 1.5, -2.25)                 # double: 8'er bayt
    havuz += _u30(len(dizeler) + 1) + b"".join(_dize(d) for d in dizeler)
    return struct.pack("<I", 1) + ad + b"\0" + b"\x10\x00\x2e\x00" + havuz + b"\x00\x01KOD"


def _font3(kimlik, ad, kodlar, sekiller, ilerleme=None, sinirlar=None, kerning=b"\x00\x00", genis=False,
           ek_bayrak=0, yukselti=b"\x00\x04\x00\x01\x20\x00"):
    """DefineFont3 (kod 75): FontID, bayraklar (HasLayout 0x80, WideOffsets 0x08, WideCodes 0x04), dil,
    ad, NumGlyphs, OffsetTable + CodeTableOffset, şekiller, CodeTable UI16[n], (Ascent/Descent/Leading,
    AdvanceTable SI16[n], BoundsTable RECT[n], KerningCount + kayıtlar)."""
    n = len(kodlar)
    bayrak = (0x80 if ilerleme is not None else 0) | (0x08 if genis else 0) | 0x04 | ek_bayrak
    boy = 4 if genis else 2
    ofsetler, o = [], boy * (n + 1)
    for s in sekiller:
        ofsetler.append(o)
        o += len(s)
    ofsetler.append(o)  # CodeTableOffset
    t = struct.pack("<HBBB", kimlik, bayrak, 1, len(ad)) + ad + struct.pack("<H", n)
    t += struct.pack(("<%dI" if genis else "<%dH") % (n + 1), *ofsetler) + b"".join(sekiller)
    t += struct.pack("<%dH" % n, *kodlar)
    if ilerleme is not None:
        t += yukselti + struct.pack("<%dh" % n, *ilerleme) + b"".join(sinirlar) + kerning
    return t


def _bolge(a, b):
    """ZONERECORD: NumZoneData=2, iki ZONEDATA (FLOAT16 koordinat + FLOAT16 aralık), ZoneMask baytı."""
    return bytes([2]) + struct.pack("<HHHH", a, 1, b, 2) + b"\x03"


def _bolgeler(kimlik, kayitlar):
    """DefineFontAlignZones (kod 73): FontID UI16, CSMTableHint UB[2] + Reserved UB[6], ZoneTable."""
    return struct.pack("<H", kimlik) + b"\x40" + b"".join(kayitlar)


def _kutu(x, y, w, h):
    """Bir glif SHAPE'i: NumFillBits=1, NumLineBits=0; MoveTo(x, y) + FillStyle0=1, sonra yatay w, dikey h,
    yatay -w, dikey -h; EndShapeRecord. Bit genişlikleri en küçük seçilir (MoveBits işaretli, kenar >= 2)."""
    def gen(*d):
        n = 1
        while not all(-(1 << (n - 1)) <= v < (1 << (n - 1)) for v in d):
            n += 1
        return n
    m = gen(x, y)
    alan = [(1, 4), (0, 4), (0, 1), (0b00011, 5), (m, 5), (x, m), (y, m), (1, 1)]
    for d, dikey in ((w, 0), (h, 1), (-w, 0), (-h, 1)):
        n = max(2, gen(d))
        alan += [(0b11, 2), (n - 2, 4), (0, 1), (dikey, 1), (d, n)]
    return _bitler(*alan, (0, 6))


def _kutu_kayitlari(x, y, w, h):
    return [("stil", (x, y), 1, None, None), ("duz", w, 0), ("duz", 0, h), ("duz", -w, 0), ("duz", 0, -h)]


# --- swf_yama: SWF kabı ----------------------------------------------------------------------------------

class SwfKabiTestleri(unittest.TestCase):
    def test_govde_fws_cws_ve_desteklenmeyen_imza(self):
        """Belge: ilk 8 bayt başlık; 'FWS' sıkıştırmasız, 'CWS' 8. bayttan sonrası zlib. 'ZWS' (LZMA)
        desteklenmez; tanınmayan imza da açıkça reddedilir (zlib hatası değil)."""
        govde = BASLIK + b"\x00\x00"
        self.assertEqual(swf_yama._govde(_swf()), govde)
        self.assertEqual(swf_yama._govde(_swf(imza=b"CWS")), govde)
        for imza in (b"ZWS", b"ABC"):
            with self.assertRaises(ValueError):
                swf_yama._govde(imza + b"\x0a" + struct.pack("<I", 21) + zlib.compress(govde))

    def test_etiket_basliklari_kisa_ve_uzun_bicim(self):
        """Belge RECORDHEADER: uzunluk < 63 kısa biçim; 0x3F ise UI32 uzunluk gelir (63'ten kısa etiket de uzun
        biçimde yazılabilir). End (kod 0) son etikettir; ardındaki bayt okunmaz. Konumlar elle sayıldı."""
        govde = (BASLIK + _etiket(9, b"\x11\x22\x33") + _etiket(37, bytes(100)) + _etiket(43, b"kare\0", uzun=True)
                 + _etiket(1, b"") + b"\x00\x00" + b"\xff\xff\xff")
        self.assertEqual(list(swf_yama._etiketler(govde)), [
            (None, 0, 13, 0),       # 9 baytlık RECT + kare hızı + kare sayısı
            (9, 15, 18, 13),
            (37, 24, 124, 18),      # 2 + 4 baytlık uzun başlık
            (43, 130, 135, 124),
            (1, 137, 137, 135),     # ShowFrame: boş içerik, okumayı bitirmez
            (0, 139, 139, 137),
        ])

    def test_uzun_baslik_her_zaman_ui32(self):
        """Yamanın yazdığı başlık uzun biçimdir: (kod << 6 | 0x3F) UI16 + UI32 uzunluk."""
        self.assertEqual(swf_yama._baslik(37, 5), b"\x7f\x09\x05\x00\x00\x00")


class U30Testleri(unittest.TestCase):
    ORNEKLER = {0: "00", 127: "7f", 128: "8001", 300: "ac02", 16384: "808001", (1 << 30) - 1: "ffffffff03"}

    def test_elle_kodlanmis_degerler(self):
        """AVM2 overview 4.1 (u30): değerler elle kodlandı."""
        for n, hx in self.ORNEKLER.items():
            self.assertEqual(swf_yama._u30_yaz(n), bytes.fromhex(hx), n)
            b = b"\x99" + bytes.fromhex(hx) + b"\x99"
            self.assertEqual(swf_yama._u30_oku(b, 1), (n, 1 + len(hx) // 2), n)


class AbcDizeTestleri(unittest.TestCase):
    def test_dize_havuzu_degisir_kalan_bayt_ayni(self):
        """AVM2 cpool_info: int (s32), uint (u32), double (8 bayt), string. Dizeler sırayla değişir; uzunluk
        öneki yeni bayt uzunluğuna göre büyür/küçülür; havuzdan sonrası ve diğer dizeler aynı kalır."""
        uzun = "x" * 200  # uzunluk öneki iki bayt (c8 01)
        t = _do_abc(["Cancel", uzun, "Next", "Kalsın"])
        harita = {"Cancel": "İptal", uzun: "kısa", "Next": "y" * 130}
        yeni, sayi = swf_yama.abc_dizelerini_degistir(t, harita)
        self.assertEqual(sayi, 3)
        self.assertEqual(yeni, _do_abc(["İptal", "kısa", "y" * 130, "Kalsın"]))

    def test_bos_havuzlar(self):
        """Sayı 0 ya da 1 ise o havuzda kayıt yoktur (AVM2: 0. kayıt örtüktür)."""
        abc = b"\x10\x00\x2e\x00" + b"\x00" + b"\x01" + b"\x00" + _u30(2) + _dize("Cargando") + b"KOD"
        t = struct.pack("<I", 1) + b"\0" + abc  # boş ad
        yeni, sayi = swf_yama.abc_dizelerini_degistir(t, {"Cargando": "Yükleniyor"})
        self.assertEqual(sayi, 1)
        self.assertEqual(yeni, t.replace(_dize("Cargando"), _dize("Yükleniyor")))


class BuyutmeTestleri(unittest.TestCase):
    """DNT-35 (denetim TRA-02): AS3 toUpperCase Türkçe kuralı bilmez ("Değirmen" → "DEĞIRMEN"). Kaynak 1.4.07 bayt
    kodu (araclar/abc_okur.py ile okundu): PopUpCollectionComplete/<kurucu> @45 getlocal_0, getlocal_1, getproperty
    name (multiname 158), @50 callproperty toUpperCase (2767) 0, @54 initproperty buildingStringName (10828); öteki
    büyütmeler @140, @198, @216. İşlem kodları AVM2 overview: getlocal_0 0xd0, getlocal_1 0xd1, getproperty 0x66,
    callproperty 0x46, initproperty 0x68, nop 0x02."""

    CAGRI = b"\x46" + _u30(2767) + _u30(0)

    def _kod(self, capa_sayisi=1, bozuk=None):
        capa = b"\xd0\xd1\x66" + _u30(158) + self.CAGRI + b"\x68" + _u30(10828)
        kod = bytearray(b"\x01" * 300)  # 0x01 = bkpt: dolgu, çağrı değil
        kod[45:45 + len(capa)] = capa
        for yer in (140, 198, 216):
            kod[yer:yer + 4] = self.CAGRI
        kod[260:264] = self.CAGRI  # yöntemin dışındaki bir büyütme (ör. StringUtil): dokunulmaz
        if bozuk:
            kod[bozuk:bozuk + 4] = b"\x01" * 4
        kod = bytes(kod)
        return kod + capa * (capa_sayisi - 1)

    def test_tebrik_penceresinin_dort_buyutmesi_kalkar(self):
        yeni, sayi = swf_yama.buyutmeyi_kaldir(self._kod())
        self.assertEqual(sayi, 4)
        self.assertEqual(len(yeni), 300)  # bayt kaymaz: atlama hedefleri bozulmaz
        for yer in (50, 140, 198, 216):
            self.assertEqual(yeni[yer:yer + 4], b"\x02" * 4, yer)
        self.assertEqual(yeni[260:264], self.CAGRI)
        eski = self._kod()
        degisen = [i for i in range(300) if yeni[i] != eski[i]]
        self.assertEqual(degisen, [y + k for y in (50, 140, 198, 216) for k in range(4)])

    def test_capa_yoksa_iki_kezse_ya_da_bir_yer_uymazsa_dokunmaz(self):
        for kod in (self._kod(capa_sayisi=2), self._kod(bozuk=198), self._kod(bozuk=216), self.CAGRI * 3):
            self.assertEqual(swf_yama.buyutmeyi_kaldir(kod), (kod, 0))

    def test_turkcelestir_dizesiz_doabc_de_yamalar(self):
        abc = _do_abc(["Loading"])
        girdi = _swf(_etiket(82, abc + self._kod()), surum=13)
        cikti, sayi = swf_yama.turkcelestir(girdi, {"metin_alanlari": {}})
        self.assertEqual(sayi, 4)
        (_, _, icerik), _ = _etiketleri_ayir(_ac(cikti))
        self.assertEqual(icerik[len(abc) + 50:len(abc) + 54], b"\x02" * 4)


class HarfiEksikYaziTipiTestleri(unittest.TestCase):
    """DNT-37 (denetim TRA-05). 1.4.07 istemcisinde (yamalı SWF, DefineFont3 kod tablosu) Curse Casual JVE ve Freestyle
    Script'te Ç ç Ğ ğ İ ı Ş ş yok; Arial Narrow'da yalnızca ACDEHIMNORSUY var. Bu yazı tiplerini kullanan alanlar:
    703 "REMAINING QUESTS: 3" (oyun kodu da "REMAINING QUESTS: " + sayı yazar), 707 "10/100", 1353 "00:00:00"
    (Curse Casual), 3213 "SN" (Arial Narrow). Sözlükten gelen çeviride harf eksikse swf_yama._yazi_tipini_uydur alanı
    Arial Rounded'a geçirir; oyun kodunun çalışırken yazdığı dize ise geçirilemez, çevirisi bu harfler olmadan
    seçilmelidir."""

    CURSE_CASUAL_EKSIK = set("ÇçĞğİıŞş")

    def test_sefer_sayaci_cevirisi_yazi_tipinin_harfleriyle(self):
        with open(swf_yama.SOZLUK, encoding="utf-8") as f:
            sozluk = json.load(f)
        for kaynak in (sozluk["as3_dizeleri"], sozluk["metin_alanlari"]):
            for anahtar in ("REMAINING QUESTS: ", "REMAINING QUESTS: 3"):
                if anahtar in kaynak:
                    self.assertFalse(set(kaynak[anahtar]) & self.CURSE_CASUAL_EKSIK, (anahtar, kaynak[anahtar]))
        self.assertIn("REMAINING QUESTS: ", sozluk["as3_dizeleri"])  # çalışırken yazılan dize çevrili


# --- swf_yama: DefineEditText ----------------------------------------------------------------------------

class EditTextTestleri(unittest.TestCase):
    def test_metin_ve_font_konumu_butun_alanlarla(self):
        t, bas = _edit_text(5, "Cancel", font=0x0102, html=True, renk=b"\x10\x20\x30\xff", azami=99, yerlesim=True)
        self.assertEqual(swf_yama._metin_konumu(t), (bas, bas + 6, True))
        konum = swf_yama._font_konumu(t)
        self.assertEqual(konum, 2 + 7 + 2)  # CharacterID + 7 baytlık RECT (12 bit) + iki bayrak baytı
        self.assertEqual(struct.unpack_from("<H", t, konum)[0], 0x0102)

    def test_font_sinifi_ile(self):
        """HasFontClass: FontClass dizesi ve FontHeight gelir, FontID gelmez (FontHeight'ı HasFont veya
        HasFontClass açar; Flash Player ve JPEXS böyle okur)."""
        t, bas = _edit_text(5, "Next", font_sinifi=b"pkg.Yazi")
        self.assertEqual(swf_yama._metin_konumu(t), (bas, bas + 4, False))
        self.assertIsNone(swf_yama._font_konumu(t))

    def test_metni_olmayan_alan(self):
        t, _ = _edit_text(5, None, font=3, renk=b"\0\0\0\xff")
        self.assertIsNone(swf_yama._metin_konumu(t))

    def test_anahtar_ve_html_degistir(self):
        self.assertEqual(swf_yama.anahtar('<p align="center"><font face="E">Tom &amp; Jerry</font></p>\r'),
                         "Tom & Jerry")
        kaynak = '<p><font size="12">Cancel</font><font> now</font>  </p>'
        self.assertEqual(swf_yama._html_degistir(kaynak, "Ali & <Veli>\rson"),
                         '<p><font size="12">Ali &amp; &lt;Veli&gt;<br>son</font><font></font>  </p>')


# --- swf_yama: bütün yama (yazı tipsiz) ------------------------------------------------------------------

class TurkcelestirTestleri(unittest.TestCase):
    SOZLUK = {"metin_alanlari": {"Cancel": "İptal", "Next": "İleri"},
              "as3_dizeleri": {"Cargando": "Yükleniyor"}}
    HTML = '<p align="center"><font face="X">%s</font></p>'

    def setUp(self):
        yama = mock.patch.object(swf_yama, "_turkce_fontlar", return_value={})
        yama.start()
        self.addCleanup(yama.stop)

    def _girdi(self, **k):
        return _swf(_etiket(9, b"\x11\x22\x33"),
                    _etiket(37, _edit_text(2, "Cancel")[0]),
                    _etiket(37, _edit_text(3, self.HTML % "Next", html=True)[0]),
                    _etiket(37, _edit_text(4, "Unknown")[0]),
                    _etiket(82, _do_abc(["Cargando", "Loading"])),
                    _etiket(1, b""), surum=13, **k)

    def test_eslesen_alanlar_degisir_gerisi_bayt_bayt_ayni(self):
        girdi = self._girdi()
        cikti, sayi = swf_yama.turkcelestir(girdi, self.SOZLUK)
        self.assertEqual(sayi, 3)  # iki metin alanı + bir AS3 dizesi
        self.assertEqual(cikti[:4], b"CWS\x0d")  # sıkıştırılır, sürüm (13) korunur
        govde = _ac(cikti)
        self.assertEqual(struct.unpack_from("<I", cikti, 4)[0], len(govde) + 8)  # FileLength = açık uzunluk
        self.assertEqual(govde[:len(BASLIK)], BASLIK)
        eski, yeni = _etiketleri_ayir(_ac(girdi)), _etiketleri_ayir(govde)
        self.assertEqual([k for k, _, _ in yeni], [9, 37, 37, 37, 82, 1, 0])
        for i in (0, 3, 5, 6):  # dokunulmayan etiketler: kısa başlıkları dahil aynı
            self.assertEqual(yeni[i][1], eski[i][1])
        self.assertEqual(yeni[1][2], _edit_text(2, "İptal")[0])
        self.assertEqual(yeni[2][2], _edit_text(3, self.HTML % "İleri", html=True)[0])
        self.assertEqual(yeni[4][2], _do_abc(["Yükleniyor", "Loading"]))

    def test_ikinci_gecis_degistirmez_ve_cws_fws_ayni(self):
        cikti, _ = swf_yama.turkcelestir(self._girdi(), self.SOZLUK)
        tekrar, sayi = swf_yama.turkcelestir(cikti, self.SOZLUK)
        self.assertEqual(sayi, 0)
        self.assertEqual(_ac(tekrar), _ac(cikti))
        self.assertEqual(swf_yama.turkcelestir(self._girdi(imza=b"CWS"), self.SOZLUK)[0], cikti)

    def test_duz_sozluk_metin_alanlari_sayilir(self):
        _, sayi = swf_yama.turkcelestir(self._girdi(), {"Cancel": "İptal"})
        self.assertEqual(sayi, 1)


class OnbellekTestleri(unittest.TestCase):
    def setUp(self):
        self.klasor = tempfile.mkdtemp(prefix="se-swf-")
        self.addCleanup(shutil.rmtree, self.klasor, True)
        self.sozluk = os.path.join(self.klasor, "sozluk.json")
        self._sozluk_yaz('{"metin_alanlari": {"Cancel": "İptal"}}')
        self.kaynak = os.path.join(self.klasor, "ui.swf")
        with open(self.kaynak, "wb") as f:
            f.write(_swf(_etiket(37, _edit_text(2, "Cancel")[0])))
        for ad, deger in (("SOZLUK", self.sozluk), ("_turkce_fontlar", lambda: {})):
            yama = mock.patch.object(swf_yama, ad, deger)
            yama.start()
            self.addCleanup(yama.stop)

    def _sozluk_yaz(self, metin):
        with open(self.sozluk, "w", encoding="utf-8") as f:
            f.write(metin)

    def test_uretir_yeniden_kullanir_sozluk_degisince_yeniler(self):
        onbellek = os.path.join(self.klasor, "onbellek")
        with mock.patch("builtins.print"):
            yol = swf_yama.onbellekli_turkcelestir(self.kaynak, onbellek)
        self.assertEqual(os.path.dirname(yol), onbellek)
        self.assertRegex(os.path.basename(yol), r"^ui\.tr-[0-9a-f]{12}\.swf$")
        with open(yol, "rb") as f:
            govde = _ac(f.read())
        self.assertEqual(_etiketleri_ayir(govde)[0][2], _edit_text(2, "İptal")[0])
        with mock.patch.object(swf_yama, "turkcelestir", side_effect=AssertionError("yeniden üretildi")):
            self.assertEqual(swf_yama.onbellekli_turkcelestir(self.kaynak, onbellek), yol)
        self._sozluk_yaz('{"metin_alanlari": {"Cancel": "Vazgeç"}}')
        with mock.patch("builtins.print"):
            yeni = swf_yama.onbellekli_turkcelestir(self.kaynak, onbellek)
        self.assertNotEqual(yeni, yol)
        baska = os.path.join(onbellek, "uibaska.tr-0123456789ab.swf")  # başka bir SWF'nin kopyası
        yedek = os.path.join(onbellek, "ui.tr-0123456789ab.swf.yedek")  # adı uyan ama kopya olmayan dosya
        for y in (baska, yedek):
            with open(y, "wb") as f:
                f.write(b"x")
        with open(self.kaynak, "wb") as f:  # kaynak SWF değişince de yenilenir
            f.write(_swf(_etiket(37, _edit_text(2, "Cancel")[0]), _etiket(1, b"")))
        with mock.patch("builtins.print"):
            ucuncu = swf_yama.onbellekli_turkcelestir(self.kaynak, onbellek)
        self.assertNotIn(ucuncu, (yol, yeni))
        # TRA-06 (DNT-38): eski kopyalar (her biri ~4 MB) birikmez; yalnızca son kalır, başka SWF'ninkine dokunulmaz
        self.assertEqual(sorted(os.listdir(onbellek)), sorted(os.path.basename(y) for y in (ucuncu, baska, yedek)))


# --- swf_font: DefineFont3 -------------------------------------------------------------------------------

S0, S1, S2 = b"\x10\x00", b"\x11\x22\x33", b"\x44\x55\x66\x77\x88"
SINIRLAR = [_rect(0, 0, 0, 0, 0), _rect(11, -10, 500, -700, 30), _rect(4, 1, 2, 3, 4)]
KERNING = b"\x01\x00" + struct.pack("<HHh", 97, 115, -20)  # KerningCount=1, geniş kodlu KERNINGRECORD


class Font3Testleri(unittest.TestCase):
    def test_dar_ofsetli_yazi_tipi_okunur(self):
        """WideOffsets kapalı (UI16 ofset) ve Bold (0x01) açık; üç glif, farklı uzunlukta RECT'ler."""
        t = _font3(7, b"Eras Bold ITC\0", [97, 115, 8364], [S0, S1, S2], [500, -3, 1200], SINIRLAR, KERNING,
                   ek_bayrak=0x01)
        f = Font3(t)
        self.assertEqual((f.kimlik, f.dil, f.ad, f.adi()), (7, 1, b"Eras Bold ITC\0", "Eras Bold ITC"))
        self.assertEqual(f.kodlar, [97, 115, 8364])
        self.assertEqual(f.sekiller, [S0, S1, S2])
        self.assertEqual(f.duzen, (b"\x00\x04\x00\x01\x20\x00", [500, -3, 1200], SINIRLAR, KERNING))

    def test_duzensiz_yazi_tipi(self):
        f = Font3(_font3(3, b"Arial Narrow __Embedded__TR\0", [48, 49, 50], [S2, S0, S1], genis=True))
        self.assertIsNone(f.duzen)
        self.assertEqual((f.adi(), f.kodlar, f.sekiller), ("Arial Narrow", [48, 49, 50], [S2, S0, S1]))

    def test_yaz_genis_ofsetle_ayni_baytlar(self):
        """yaz() hep geniş ofset + geniş kod yazar (UI32 ofset yazdığı için WideOffsets açık olmalı). Belgeye
        göre geniş kurulmuş yazı tipi baytı baytına geri gelir; dar kurulmuş olan geniş eşine dönüşür."""
        alan = (7, b"Eras Bold ITC\0", [97, 115, 8364], [S0, S1, S2], [500, -3, 1200], SINIRLAR, KERNING)
        genis = _font3(*alan, genis=True, ek_bayrak=0x01)
        self.assertEqual(Font3(genis).yaz(), genis)
        self.assertEqual(Font3(_font3(*alan, ek_bayrak=0x01)).yaz(), genis)
        duzensiz = _font3(3, b"A\0", [48, 49, 50], [S2, S0, S1], genis=True)
        self.assertEqual(Font3(_font3(3, b"A\0", [48, 49, 50], [S2, S0, S1])).yaz(), duzensiz)


def _hedef_kaynak():
    hedef = Font3(_font3(1, b"Arial Rounded MT Bold\0", [97, 252, 8364], [b"Ha", b"Hu", b"He"],
                         [500, 510, 520], [_rect(2, 0, 1, 0, 1)] * 3, KERNING))
    kaynak = Font3(_font3(1, b"Arial Rounded MT Bold __Embedded__TR\0", [97, 287, 304, 351, 8364],
                          [b"Ka", b"Kg", b"KI", b"Ks", b"Ke"], [600, 610, 620, 630, 640],
                          [_rect(4, i, 0, 0, 0) for i in range(5)], b"\x00\x00", yukselti=b"\x99" * 6))
    return hedef, kaynak


class HarfEkleTestleri(unittest.TestCase):
    def test_eksik_harfler_sirali_araya_girer(self):
        """Kod tablosu sıralı kalır; €'nun glifi 2'den 5'e kayar. Glif, ilerleme, sınır ve bölge kaynaktan;
        hedefin yükseklik ve kerning bilgisi korunur. Kaynakta olmayan Türkçe harfler eklenmez."""
        hedef, kaynak = _hedef_kaynak()
        h_bolge = _bolgeler(1, [_bolge(i, 0) for i in (1, 2, 3)])
        k_bolge = _bolgeler(1, [_bolge(0, i) for i in (11, 12, 13, 14, 15)])
        eslem, bolge = swf_font.harf_ekle(hedef, kaynak, h_bolge, k_bolge)
        self.assertEqual(eslem, {0: 0, 1: 1, 2: 5})
        self.assertEqual(hedef.kodlar, [97, 252, 287, 304, 351, 8364])
        self.assertEqual(hedef.sekiller, [b"Ha", b"Hu", b"Kg", b"KI", b"Ks", b"He"])
        y, ilerleme, sinirlar, kerning = hedef.duzen
        self.assertEqual((y, kerning), (b"\x00\x04\x00\x01\x20\x00", KERNING))
        self.assertEqual(ilerleme, [500, 510, 610, 620, 630, 520])
        self.assertEqual(sinirlar[2:5], [_rect(4, i, 0, 0, 0) for i in (1, 2, 3)])
        self.assertEqual(bolge, _bolgeler(1, [_bolge(1, 0), _bolge(2, 0), _bolge(0, 12), _bolge(0, 13),
                                              _bolge(0, 14), _bolge(3, 0)]))
        self.assertEqual(Font3(hedef.yaz()).kodlar, hedef.kodlar)

    def test_kaynak_bolgesi_yoksa_bos_bolge_kaydi(self):
        """Bölge tablosu glif sayısıyla eşit kalmalı; kaynakta bölge yoksa yeni glife bölgesiz ZONERECORD
        (NumZoneData=0 + ZoneMask) konur."""
        hedef, kaynak = _hedef_kaynak()
        _, bolge = swf_font.harf_ekle(hedef, kaynak, _bolgeler(1, [_bolge(i, 0) for i in (1, 2, 3)]))
        self.assertEqual(bolge, _bolgeler(1, [_bolge(1, 0), _bolge(2, 0)] + [b"\x00\x00"] * 3 + [_bolge(3, 0)]))

    def test_eklenecek_yoksa_dokunmaz(self):
        hedef, kaynak = _hedef_kaynak()
        self.assertEqual(swf_font.harf_ekle(hedef, kaynak, harfler="çÇ"), (None, None))
        hedef.duzen = None
        self.assertEqual(swf_font.harf_ekle(hedef, kaynak), (None, None))
        self.assertEqual(hedef.kodlar, [97, 252, 8364])


# --- swf_font: DefineText --------------------------------------------------------------------------------

# DefineText2: CharacterID 9, TextBounds, MATRIX (ölçek 18 bit, döndürme 3 bit, öteleme 10 bit), GlyphBits 5,
# AdvanceBits 9 (değerlere yeten en küçük genişlikler: 17 < 32; -256 <= -200, 150 < 256).
MATRIX = _bitler((1, 1), (18, 5), (65536, 18), (65536, 18), (1, 1), (3, 5), (1, 3), (-2, 3), (10, 5), (300, 10),
                 (-400, 10))
ONEK2 = struct.pack("<H", 9) + _rect(13, -100, 2000, -300, 50) + MATRIX
METIN2 = (ONEK2 + bytes([5, 9])
          + b"\x8f" + struct.pack("<H", 7) + b"\x11\x22\x33\xff" + struct.pack("<hhH", -50, 120, 240) + b"\x03"
          + _bitler((17, 5), (150, 9), (0, 5), (-200, 9), (3, 5), (7, 9))
          + b"\x82" + struct.pack("<h", 360) + b"\x02" + _bitler((1, 5), (100, 9), (16, 5), (-1, 9))
          + b"\x00")
KAYITLAR2 = [
    {"bayrak": 0x8F, "font": 7, "renk": b"\x11\x22\x33\xff", "x": -50, "y": 120, "yukseklik": 240,
     "glifler": [(17, 150), (0, -200), (3, 7)]},
    {"bayrak": 0x82, "font": None, "renk": None, "x": None, "y": 360, "yukseklik": None,
     "glifler": [(1, 100), (16, -1)]},
]


class DefineTextTestleri(unittest.TestCase):
    def test_define_text2_ayrisir_ve_ayni_baytlara_doner(self):
        """TEXTRECORD: StyleFlags (HasFont 0x08, HasColor 0x04, HasYOffset 0x02, HasXOffset 0x01), FontID,
        RGBA (DefineText2), X, Y, TextHeight, GlyphCount, GLYPHENTRY'ler, kayıt sonu bayt hizası."""
        onek, kayitlar = swf_font.metin_kayitlari(METIN2, swf_font.DEFINE_TEXT2)
        self.assertEqual(onek, ONEK2)
        self.assertEqual(kayitlar, KAYITLAR2)
        self.assertEqual(swf_font.metin_yaz(onek, kayitlar), METIN2)

    def test_define_text_renk_uc_bayt(self):
        """DefineText'te renk RGB'dir (3 bayt). MATRIX boş: üç bayrak sıfır, öteleme 0 bit -> tek bayt."""
        onek = struct.pack("<H", 4) + _rect(1, 0, 0, 0, 0) + b"\x00"
        t = (onek + bytes([2, 6]) + b"\x8c" + struct.pack("<H", 7) + b"\xaa\xbb\xcc" + struct.pack("<H", 200)
             + b"\x01" + _bitler((2, 2), (30, 6)) + b"\x00")
        _, kayitlar = swf_font.metin_kayitlari(t, swf_font.DEFINE_TEXT)
        self.assertEqual(kayitlar, [{"bayrak": 0x8C, "font": 7, "renk": b"\xaa\xbb\xcc", "x": None, "y": None,
                                     "yukseklik": 200, "glifler": [(2, 30)]}])
        self.assertEqual(swf_font.metin_yaz(onek, kayitlar), t)

    def test_glifsiz_kayit_gidip_doner(self):
        kayit = [{"bayrak": 0x88, "font": 7, "renk": None, "x": None, "y": None, "yukseklik": 100, "glifler": []}]
        t = swf_font.metin_yaz(ONEK2, kayit)
        self.assertEqual(swf_font.metin_kayitlari(t, swf_font.DEFINE_TEXT2), (ONEK2, kayit))

    def test_bit_genisligi_ikiye_tumleyen_araliklari(self):
        """n bit işaretsiz: [0, 2^n); işaretli: [-2^(n-1), 2^(n-1)). En küçük n, en az 1."""
        for degerler, beklenen in (([0], 1), ([1], 1), ([2], 2), ([255], 8), ([256], 9), ([3, 300, 1], 9)):
            self.assertEqual(swf_font._bit_genisligi(degerler, False), beklenen, degerler)
        for degerler, beklenen in (([0], 1), ([-1], 1), ([1], 2), ([-2], 2), ([-3], 3), ([127], 8),
                                   ([-128], 8), ([128], 9), ([-129], 9), ([5, -60], 7)):
            self.assertEqual(swf_font._bit_genisligi(degerler, True), beklenen, degerler)

    def test_glifleri_esle_font_onceki_kayittan_gecer(self):
        kayitlar = [{"font": 7, "glifler": [(0, 10), (2, 20)]}, {"font": None, "glifler": [(2, 5)]},
                    {"font": 8, "glifler": [(2, 1)]}]
        sonuc = swf_font.glifleri_esle(kayitlar, {7: {0: 0, 2: 5}})
        self.assertEqual([k["glifler"] for k in sonuc], [[(0, 10), (5, 20)], [(5, 5)], [(2, 1)]])
        self.assertEqual(kayitlar[0]["glifler"], [(0, 10), (2, 20)])  # girdi değişmez


def _fontlar(kodlar, ilerleme):
    n = len(kodlar)
    return Font3(_font3(7, b"F\0", kodlar, [b"s"] * n, ilerleme, [_rect(0, 0, 0, 0, 0)] * n))


class MetinCevirTestleri(unittest.TestCase):
    def test_metni_coz(self):
        fontlar = {7: _fontlar([65, 66, 287], [1, 1, 1])}
        kayitlar = [{"font": 7, "glifler": [(0, 1), (2, 1), (5, 1)]}, {"font": None, "glifler": [(1, 1)]}]
        self.assertEqual(swf_font.metni_coz(kayitlar, fontlar), ["Ağ?", "B"])  # aralık dışı glif '?'
        self.assertIsNone(swf_font.metni_coz([{"font": 9, "glifler": []}], fontlar))

    def test_metni_degistir_olcek_ve_ortalama(self):
        """Ölçek = kayıttaki ilerlemeler / yazı tipi ilerlemeleri = 150 / 3000 = 0,05. 'ğA' -> ğ: 1500*0,05=75,
        A: 50; genişlik 125, fark 25: kısa yazı ortalı kalsın diye x 25 // 2 = 12 kayar."""
        eski = {7: _fontlar([65, 66], [1000, 2000])}
        yeni = {7: _fontlar([65, 66, 287], [1000, 2000, 1500])}
        kayit = {"bayrak": 0x89, "font": 7, "x": 100, "glifler": [(0, 50), (1, 100)]}
        sonuc = swf_font.metni_degistir([kayit], eski, yeni, ["ğA"])
        self.assertEqual(sonuc, [dict(kayit, x=112, glifler=[(2, 75), (0, 50)])])
        sinirda = swf_font.metni_degistir([dict(kayit, x=32767)], eski, yeni, ["ğA"])
        self.assertEqual(sinirda[0]["x"], 32767)  # SI16 sınırı
        iki = swf_font.metni_degistir([kayit, dict(kayit, font=None)], eski, yeni, ["ğA", "AB"])
        self.assertEqual([k["x"] for k in iki], [112, 100])  # iki satıra kadar ortalı ("AB": fark 0)
        uc = [kayit, dict(kayit, font=None), dict(kayit, font=None)]
        self.assertEqual([k["x"] for k in swf_font.metni_degistir(uc, eski, yeni, ["ğA", "A", "B"])],
                         [100, 100, 100])  # uzun açıklama sola dayalı: x kaymaz
        self.assertIsNone(swf_font.metni_degistir([kayit], eski, yeni, ["Ş"]))       # eksik harf
        self.assertIsNone(swf_font.metni_degistir([kayit], eski, yeni, ["A", "B"]))  # satır sayısı tutmuyor


# --- swf_font: SHAPE ve RECT -----------------------------------------------------------------------------

# Belge SHAPE: NumFillBits=1, NumLineBits=0; StyleChange(MoveTo 6 bit (10, -20), FillStyle0=1); yatay 30
# (6 bit); dikey -40 (7 bit); genel (5, 7) (4 bit); eğri (3, -30, 6, 34) (7 bit); taşımasız StyleChange
# (FillStyle0=0); yatay 1 ve -1 (NumBits en az 2: alan 0); EndShapeRecord.
SEKIL = _bitler((1, 4), (0, 4),
                (0, 1), (0b00011, 5), (6, 5), (10, 6), (-20, 6), (1, 1),
                (0b11, 2), (4, 4), (0, 1), (0, 1), (30, 6),
                (0b11, 2), (5, 4), (0, 1), (1, 1), (-40, 7),
                (0b11, 2), (2, 4), (1, 1), (5, 4), (7, 4),
                (0b10, 2), (5, 4), (3, 7), (-30, 7), (6, 7), (34, 7),
                (0, 1), (0b00010, 5), (0, 1),
                (0b11, 2), (0, 4), (0, 1), (0, 1), (1, 2),
                (0b11, 2), (0, 4), (0, 1), (0, 1), (-1, 2),
                (0, 6))
SEKIL_KAYITLARI = [("stil", (10, -20), 1, None, None), ("duz", 30, 0), ("duz", 0, -40), ("duz", 5, 7),
                   ("egri", 3, -30, 6, 34), ("stil", None, 0, None, None), ("duz", 1, 0),
                   ("duz", -1, 0)]


class SekilTestleri(unittest.TestCase):
    def test_sekil_coz_yaz(self):
        self.assertEqual(swf_font.sekil_coz(SEKIL), (1, 0, SEKIL_KAYITLARI))
        self.assertEqual(swf_font.sekil_yaz(1, 0, SEKIL_KAYITLARI), SEKIL)

    def test_glifte_yeni_stil_reddedilir(self):
        with self.assertRaises(ValueError):
            swf_font.sekil_coz(_bitler((1, 4), (0, 4), (0, 1), (0b10000, 5), (0, 6)))

    def test_sekil_siniri(self):
        """Noktalar: (10,-20) (40,-20) (40,-60) (45,-53), eğri kontrol (48,-83) ve çapa (54,-49), (55,-49),
        (54,-49). En üst nokta eğrinin kontrol noktasıdır."""
        self.assertEqual(swf_font.sekil_siniri(SEKIL), (10, 55, -83, -20))
        self.assertEqual(swf_font.sekil_siniri(_bitler((0, 8), (0, 6))), (0, 0, 0, 0))

    def test_rect(self):
        self.assertEqual(swf_font.rect_yaz(0, 11000, 0, 8000), SAHNE)
        self.assertEqual(swf_font.rect_coz(SAHNE), [0, 11000, 0, 8000])
        self.assertEqual(swf_font.rect_yaz(-1, 1, -4, 3), _rect(3, -1, 1, -4, 3))
        self.assertEqual(swf_font.rect_coz(_rect(3, -1, 1, -4, 3)), [-1, 1, -4, 3])
        self.assertEqual(swf_font._rect_sonu(b"\xff" + _rect(0, 0, 0, 0, 0) + b"\xff", 1), 2)
        self.assertEqual(swf_font._rect_sonu(b"\xff" + _rect(2, 1, 1, 1, 1), 1), 3)


class AksanliHarfTestleri(unittest.TestCase):
    """turkce_harfleri_uret: harf + aksan. Beklenenler belge dizesindeki kuraldan elle hesaplandı:
    aksan yatayda temel harfin ortasına (dx = ((tx0+tx1) - (ax0+ax1)) // 2); büyük harfte aksanın altı ile
    'o'nun tepesi arasındaki boşluk korunarak temel harfin tepesinin üstüne alınır (SWF'te y aşağı artar)."""

    KUTULAR = {
        "I": (50, -700, 100, 700), "S": (30, -700, 400, 700), "g": (10, -500, 300, 700), "o": (10, -500, 400, 500),
        "s": (20, -500, 300, 500), "¸": (100, 10, 60, 150), "˘": (40, -650, 200, 100), "˙": (200, -650, 80, 80),
    }

    def _font(self):
        harfler = sorted(self.KUTULAR, key=ord)
        n = len(harfler)
        return harfler, Font3(_font3(1, b"Eras Bold ITC\0", [ord(h) for h in harfler],
                                     [_kutu(*self.KUTULAR[h]) for h in harfler], [100 + i for i in range(n)],
                                     [_rect(5, i, 0, 0, 0) for i in range(n)], KERNING))

    def test_eksik_harfler_harf_ve_aksandan(self):
        harfler, font = self._font()
        bolge = _bolgeler(1, [_bolge(i, i) for i in range(len(harfler))])
        yeni_bolge = swf_font.turkce_harfleri_uret(font, bolge)
        # Ğ için G yok: üretilmez. Sıralı tablo: I S g o s ¸ ğ İ Ş ş ˘ ˙
        self.assertEqual("".join(chr(k) for k in font.kodlar), "ISgos¸ğİŞş˘˙")
        temel = {"ğ": ("g", 20, 0), "İ": ("I", -140, -200), "Ş": ("S", 100, 0), "ş": ("s", 40, 0)}
        aksan = {"ğ": "˘", "İ": "˙", "Ş": "¸", "ş": "¸"}
        for yeni, (harf, dx, dy) in temel.items():
            i, t_i = font.kodlar.index(ord(yeni)), harfler.index(harf)
            ax, ay, aw, ah = self.KUTULAR[aksan[yeni]]
            self.assertEqual(swf_font.sekil_coz(font.sekiller[i])[2],
                             _kutu_kayitlari(*self.KUTULAR[harf]) + _kutu_kayitlari(ax + dx, ay + dy, aw, ah), yeni)
            self.assertEqual(font.duzen[1][i], 100 + t_i)               # ilerleme temel harfinki
            self.assertEqual(font.duzen[2][i], _rect(5, t_i, 0, 0, 0))   # sınır tablosu temel harfinki
        self.assertEqual(font.duzen[3], KERNING)
        beklenen = [_bolge(harfler.index(h), harfler.index(h)) if h in harfler else
                    _bolge(harfler.index(temel[h][0]), harfler.index(temel[h][0])) for h in "ISgos¸ğİŞş˘˙"]
        self.assertEqual(yeni_bolge, _bolgeler(1, beklenen))

    def test_buyuk_harfte_bosluk_korunur(self):
        """İ: noktanın altı ile 'o'nun tepesi arası 70; yeni noktanın altı I'nın tepesinden 70 yukarıda."""
        _, font = self._font()
        swf_font.turkce_harfleri_uret(font)
        _, _, ymin, ymax = swf_font.sekil_siniri(font.sekiller[font.kodlar.index(ord("İ"))])
        self.assertEqual((ymin, ymax), (-850, 0))  # nokta -850..-770 (I'nın tepesi -700'den 70 yukarı); I -700..0

    def test_uretilecek_harf_yoksa_none(self):
        font = Font3(_font3(1, b"X\0", [65], [_kutu(0, 0, 1, 1)], [1], [b"\x00"]))
        self.assertIsNone(swf_font.turkce_harfleri_uret(font, _bolgeler(1, [_bolge(0, 0)])))
        self.assertEqual(font.kodlar, [65])


# --- swf_yama + swf_font: gömülü yazı tipi tamamlama -----------------------------------------------------

class YaziTipiTamamlamaTestleri(unittest.TestCase):
    """SWF'te 'Arial Rounded MT Bold' (ğ İ ş eksik) ve yalnızca rakamlı 'Arial Narrow' var; kaynak yazı tipi
    yapay. Eski glif sırası: A a l p t € ; yeni: A a l p t ğ İ ş €."""

    ILERLEME = [1000, 900, 400, 950, 500, 1100]

    def setUp(self):
        kaynak = Font3(_font3(1, b"Arial Rounded MT Bold __Embedded__TR\0", [287, 304, 351],
                              [b"Kg", b"KI", b"Ks"], [920, 300, 800], [b"\x00"] * 3))
        yama = mock.patch.object(swf_yama, "_turkce_fontlar",
                                 return_value={"Arial Rounded MT Bold": (kaynak, _bolgeler(1, [_bolge(9, 9)] * 3))})
        yama.start()
        self.addCleanup(yama.stop)

    def _girdi(self):
        self.font1 = _font3(1, b"Arial Rounded MT Bold\0", [65, 97, 108, 112, 116, 8364],
                            [b"A", b"a", b"l", b"p", b"t", b"E"], self.ILERLEME, [b"\x00"] * 6, KERNING, genis=True)
        self.font2 = _font3(2, b"Arial Narrow\0", [48, 49], [b"0", b"1"], [500, 500], [b"\x00"] * 2)
        onek = struct.pack("<H", 20) + _rect(1, 0, 0, 0, 0) + b"\x00"
        # "Al€" 0,1 ölçekli: 100 + 40 + 110; "a€" yalnızca glif kayar
        metin1 = (onek + bytes([3, 8]) + b"\x89" + struct.pack("<HhH", 1, 200, 240) + b"\x03"
                  + _bitler((0, 3), (100, 8), (2, 3), (40, 8), (5, 3), (110, 8)) + b"\x00")
        metin2 = (onek + bytes([3, 8]) + b"\x88" + struct.pack("<HH", 1, 240) + b"\x02"
                  + _bitler((1, 3), (90, 8), (5, 3), (110, 8)) + b"\x00")
        return _swf(_etiket(75, self.font1), _etiket(73, _bolgeler(1, [_bolge(i, 0) for i in range(6)])),
                    _etiket(75, self.font2),
                    _etiket(11, metin1), _etiket(11, metin2),
                    _etiket(37, _edit_text(30, "Cancel", font=2)[0]), _etiket(37, _edit_text(31, "01", font=2)[0]))

    def test_yazi_tipi_metinler_ve_alanlar(self):
        sozluk = {"metin_alanlari": {"Cancel": "İptal", "01": "10"}, "statik_yazilar": {"Al€": "Ağa"}}
        cikti, sayi = swf_yama.turkcelestir(self._girdi(), sozluk)
        self.assertEqual(sayi, 3)
        govde = _ac(cikti)
        self.assertEqual(struct.unpack_from("<I", cikti, 4)[0], len(govde) + 8)
        e = _etiketleri_ayir(govde)
        self.assertEqual([k for k, _, _ in e], [75, 73, 75, 11, 11, 37, 37, 0])

        font = Font3(e[0][2])
        self.assertEqual(font.kodlar, [65, 97, 108, 112, 116, 287, 304, 351, 8364])
        self.assertEqual(font.sekiller, [b"A", b"a", b"l", b"p", b"t", b"Kg", b"KI", b"Ks", b"E"])
        self.assertEqual(font.duzen[1], self.ILERLEME[:5] + [920, 300, 800, 1100])
        self.assertEqual(font.duzen[3], KERNING)
        self.assertEqual(e[1][2], _bolgeler(1, [_bolge(i, 0) for i in range(5)] + [_bolge(9, 9)] * 3
                                            + [_bolge(5, 0)]))
        self.assertEqual(e[2][2], self.font2)  # kaynağı olmayan yazı tipi aynı

        _, k1 = swf_font.metin_kayitlari(e[3][2], 11)
        # Ölçek 250 / 2500 = 0,1: A 100, ğ 92, a 90 -> genişlik 282, fark -32, x 200 - 16 = 184
        self.assertEqual([(k["font"], k["x"], k["glifler"]) for k in k1], [(1, 184, [(0, 100), (5, 92), (1, 90)])])
        _, k2 = swf_font.metin_kayitlari(e[4][2], 11)
        self.assertEqual(k2[0]["glifler"], [(1, 90), (8, 110)])  # € 5 -> 8, metin aynı kalır

        self.assertEqual(e[5][2], _edit_text(30, "İptal", font=1)[0])  # Arial Narrow'da İ yok: yazı tipi 1
        self.assertEqual(e[6][2], _edit_text(31, "10", font=2)[0])     # rakamlar var: yazı tipi aynı

    def test_ceviri_yoksa_yalnizca_glifler_kayar(self):
        cikti, sayi = swf_yama.turkcelestir(self._girdi(), {})
        self.assertEqual(sayi, 0)
        e = _etiketleri_ayir(_ac(cikti))
        fontlar = {1: Font3(e[0][2])}
        for i, beklenen in ((3, ["Al€"]), (4, ["a€"])):
            _, kayitlar = swf_font.metin_kayitlari(e[i][2], 11)
            self.assertEqual(swf_font.metni_coz(kayitlar, fontlar), beklenen)


class DepoYaziTipleriTestleri(unittest.TestCase):
    def test_turkce_yazi_tipleri_butun_harfleri_tasir(self):
        """assets/fonts/tr_*.swf yamanın kaynağıdır: iki yazı tipi, 12 Türkçe harfin hepsi ve bölge tablosu."""
        fontlar = swf_yama._turkce_fontlar()
        self.assertEqual(set(fontlar), {"Arial Rounded MT Bold", "Eras Bold ITC"})
        for ad, (font, bolge) in fontlar.items():
            for h in swf_font.TURKCE_HARFLER:
                self.assertIn(ord(h), font.kodlar, (ad, h))
            self.assertEqual(len(swf_font._bolgeler(bolge, len(font.kodlar))[1]), len(font.kodlar))
            self.assertTrue(font.ad.startswith(ad.encode()), font.ad)


if __name__ == "__main__":
    unittest.main()


# --- swf_yama: kesik çeviri için metin kutusunu genişletme -------------------------------------------------

def _kutu_alani(metin, genislik=1000, font=9, hiza=None, kaydir=False, boyutlan=False, sol=0, sag=0, html=False):
    """Belgeye göre DefineEditText: RECT (0, genislik, 0, 300), HasText, isteğe bağlı WordWrap (b1 0x40),
    AutoSize (b2 0x40), HasLayout (b2 0x20: Align UI8, Left/RightMargin UI16, Indent UI16, Leading SI16)."""
    b1 = 0x80 | 0x01 | (0x40 if kaydir else 0)
    b2 = (0x40 if boyutlan else 0) | (0x20 if hiza is not None else 0) | (0x02 if html else 0)
    ek = struct.pack("<HH", font, 240)  # FontID, FontHeight (twip)
    if hiza is not None:
        ek += bytes([hiza]) + struct.pack("<HHHh", sol, sag, 0, 0)
    return struct.pack("<H", 4) + _rect(14, 0, genislik, 0, 300) + bytes([b1, b2]) + ek + b"_txt\0" + \
        metin.encode("utf-8") + b"\0"


def _kutu_rect(t):
    """RECT'i belgeye göre (Nbits UB[5], dört SB[Nbits]) uygulamadan bağımsız çöz."""
    nbit = t[2] >> 3
    bitler = int.from_bytes(t[2:2 + (5 + 4 * nbit + 7) // 8], "big")
    toplam = ((5 + 4 * nbit + 7) // 8) * 8
    sonuc = []
    for i in range(4):
        d = (bitler >> (toplam - 5 - nbit * (i + 1))) & ((1 << nbit) - 1)
        sonuc.append(d - (1 << nbit) if d >> (nbit - 1) else d)
    return sonuc


class AlanGenisletmeTestleri(unittest.TestCase):
    """'28 NAKİ' (sahibinin bildirimi): çeviri kutudan uzunsa son harf kesilir. Belge: DefineFont3 ilerlemeleri em
    karesi 1024 × 20 = 20480 birimdir, ekrandaki en = ilerleme × FontHeight / 20480 twip. Flash metin alanının iki
    yanında 2'şer piksel (toplam 80 twip) boşluk vardır. Yazı tipi: 'A' yarım em (240 twip yazıda 120), 'B' bir em
    (240), boşluk çeyrek em (60)."""

    def setUp(self):
        self.fontlar = {9: Font3(_font3(9, b"F\0", [32, 65, 66], [S0, S0, S0], [5120, 10240, 20480],
                                        [_rect(0, 0, 0, 0, 0)] * 3))}

    def _en(self, metin):  # belgenin formülü, elle: harf ilerlemeleri toplamı
        return sum({" ": 5120, "A": 10240, "B": 20480}[h] for h in metin) * 240 / 20480

    def test_sigan_metin_bayt_bayt_ayni(self):
        t = _kutu_alani("AB")  # 360 + 80 twip, kutu 1000
        self.assertEqual(swf_yama.alani_genislet(t, "AB", self.fontlar), t)

    def test_sigmayan_metin_sigacak_kadar_genisler(self):
        metin = "BBBB A"
        self.assertEqual(self._en(metin), 1140)
        t = _kutu_alani(metin)
        yeni = swf_yama.alani_genislet(t, metin, self.fontlar)
        xmin, xmax, ymin, ymax = _kutu_rect(yeni)
        self.assertEqual((xmin, ymin, ymax), (0, 0, 300))  # sola dayalı: yalnızca sağa açılır, yükseklik aynı
        self.assertGreaterEqual(xmax - xmin, 1140 + 80)
        self.assertLessEqual(xmax - xmin, 1600)
        rect_uz = lambda b: (5 + 4 * (b[2] >> 3) + 7) // 8  # noqa: E731 (belge: RECT uzunluğu Nbits'ten)
        self.assertEqual(yeni[2 + rect_uz(yeni):], t[2 + rect_uz(t):])  # RECT dışında bayt bayt aynı

    def test_hizaya_gore_acilir(self):
        metin = "BBBB A"
        xmin, xmax, _, _ = _kutu_rect(swf_yama.alani_genislet(_kutu_alani(metin, hiza=1), metin, self.fontlar))
        self.assertEqual(xmax, 1000)  # sağa dayalı: sağ kenar yerinde, sola açılır
        self.assertLessEqual(xmin, -220)
        xmin, xmax, _, _ = _kutu_rect(swf_yama.alani_genislet(_kutu_alani(metin, hiza=2), metin, self.fontlar))
        self.assertLessEqual(abs(-xmin - (xmax - 1000)), 1)  # ortalı: iki yana eşit
        self.assertGreaterEqual(xmax - xmin, 1220)

    def test_kenar_boslugu_da_sayilir(self):
        """Align + LeftMargin/RightMargin: metin kenar boşluklarının içinde dizilir (belge, HasLayout)."""
        metin = "BB A"  # 660 + 80 = 740: boşluksuz sığar, 300 + 300 kenar boşluğuyla (1340) sığmaz
        t = _kutu_alani(metin, hiza=0)
        self.assertEqual(swf_yama.alani_genislet(t, metin, self.fontlar), t)
        xmin, xmax, _, _ = _kutu_rect(swf_yama.alani_genislet(_kutu_alani(metin, hiza=0, sol=300, sag=300), metin,
                                                               self.fontlar))
        self.assertGreaterEqual(xmax - xmin, 660 + 80 + 600)

    def test_genisleme_en_cok_yuzde_altmis(self):
        metin = "B" * 10  # 2400 twip
        xmin, xmax, _, _ = _kutu_rect(swf_yama.alani_genislet(_kutu_alani(metin), metin, self.fontlar))
        self.assertEqual((xmin, xmax), (0, 1600))

    def test_en_genis_kutuya_sigmayan_yazi_kuculur(self):
        """FontHeight UI16, FontID'nin hemen ardından (belge). 1,6 kat kutuya da sığmayan yazıda harf boyu düşer,
        ama en çok 0,7 katına (240 → 168); sığan yazının boyu hiç değişmez."""
        yukseklik = lambda b: struct.unpack_from("<H", b, 2 + (5 + 4 * (b[2] >> 3) + 7) // 8 + 4)[0]  # noqa: E731
        self.assertEqual(yukseklik(_kutu_alani("x")), 240)  # kurucunun kendisi: konum doğru
        metin = "B" * 7  # 1680 twip: 1600'lük kutuya sığmaz
        yeni = swf_yama.alani_genislet(_kutu_alani(metin), metin, self.fontlar)
        h = yukseklik(yeni)
        self.assertLess(h, 240)
        self.assertGreaterEqual(h, 168)
        xmin, xmax, _, _ = _kutu_rect(yeni)
        self.assertGreaterEqual(xmax - xmin, self._en(metin) * h / 240 + 80)  # küçülen yazı kutuya sığar
        self.assertLess(xmax - xmin, 1600)  # kutu küçülen yazıya göre genişler, sınıra dek değil (yanındakine taşmasın)
        self.assertEqual(yukseklik(swf_yama.alani_genislet(_kutu_alani("B" * 20), "B" * 20, self.fontlar)), 168)
        self.assertEqual(yukseklik(swf_yama.alani_genislet(_kutu_alani("BBBB A"), "BBBB A", self.fontlar)), 240)

    def test_html_alanda_boy_font_etiketinden_ve_kucultulmez(self):
        """HTML alanda (b2 0x02) çizilen boy <font size> (piksel ×20 twip) etiketinden gelir, FontHeight geçersizdir
        (Flash/Ruffle HTML metni). size="20" = 400 twip: 'BBB' 720 × 400 / 240 = 1200 twip."""
        yukseklik = lambda b: struct.unpack_from("<H", b, 2 + (5 + 4 * (b[2] >> 3) + 7) // 8 + 4)[0]  # noqa: E731
        kisa = '<p><font size="20">BBB</font></p>'
        t = _kutu_alani(kisa, html=True)
        _, xmax, _, _ = _kutu_rect(swf_yama.alani_genislet(t, kisa, self.fontlar))
        self.assertGreaterEqual(xmax, 1200 + 80)  # FontHeight (240) ile ölçülse 720 + 80 sığardı
        uzun = '<p><font size="20">BBBBBBB</font></p>'  # 2800 twip: 1600'e sığmaz
        yeni = swf_yama.alani_genislet(_kutu_alani(uzun, html=True), uzun, self.fontlar)
        self.assertEqual(yukseklik(yeni), 240)  # küçültme etkisiz olacağı için yapılmaz
        self.assertEqual(_kutu_rect(yeni)[:2], [0, 1600])  # en geniş kutu

    def test_sozcuk_kaydiran_alanda_yalniz_uzun_sozcuk_genisletir(self):
        metin = "AAAA AAAA AAAA"  # tek satır 1560, her sözcük 480: kaydıran alanda sığar
        t = _kutu_alani(metin, kaydir=True)
        self.assertEqual(swf_yama.alani_genislet(t, metin, self.fontlar), t)
        self.assertNotEqual(swf_yama.alani_genislet(_kutu_alani(metin), metin, self.fontlar), _kutu_alani(metin))
        uzun = "A BBBBB"  # 1200 twip'lik tek sözcük kaydırmayla da bölünmez
        _, xmax, _, _ = _kutu_rect(swf_yama.alani_genislet(_kutu_alani(uzun, kaydir=True), uzun, self.fontlar))
        self.assertGreaterEqual(xmax, 1200 + 80)

    def test_satirlar_ayri_olculur_ve_html_etiketi_sayilmaz(self):
        t = _kutu_alani("x")
        self.assertEqual(swf_yama.alani_genislet(t, "BBB\rBBB", self.fontlar), t)  # her satır 720
        self.assertEqual(swf_yama.alani_genislet(t, '<font size="20">BBB</font>', self.fontlar), t)
        # HTML alanda ölçülen yalnızca görünen yazı: etiket harfleri yazı tipinde yok, yine de ölçülür
        _, xmax, _, _ = _kutu_rect(swf_yama.alani_genislet(t, '<p><font size="20">BBBBB</font></p>', self.fontlar))
        self.assertGreaterEqual(xmax, 1200 + 80)

    def test_dokunulmayan_alanlar(self):
        metin = "B" * 6
        for t in (_kutu_alani(metin, boyutlan=True),   # AutoSize: kutu kendisi büyür
                  _kutu_alani(metin, font=8)):         # yazı tipi bilinmiyor
            self.assertEqual(swf_yama.alani_genislet(t, metin, self.fontlar), t)
        t = _kutu_alani("BBBBBBÇ")                     # yazı tipinde olmayan harf: en ölçülemez
        self.assertEqual(swf_yama.alani_genislet(t, "BBBBBBÇ", self.fontlar), t)

    def test_turkcelestir_cevrilen_alani_genisletir(self):
        """Bütün yamada: sözlükten gelen uzun çeviri SWF'nin kendi yazı tipiyle ölçülür ve kutu genişler."""
        font = _font3(9, b"F\0", [32, 65, 66], [S0, S0, S0], [5120, 10240, 20480], [_rect(0, 0, 0, 0, 0)] * 3)
        girdi = _swf(_etiket(75, font), _etiket(37, _kutu_alani("AB")), _etiket(1, b""), surum=13)
        with mock.patch.object(swf_yama, "_turkce_fontlar", return_value={}):
            cikti, _ = swf_yama.turkcelestir(girdi, {"metin_alanlari": {"AB": "BBBB A"}})
        alan = [ic for k, _, ic in _etiketleri_ayir(_ac(cikti)) if k == 37][0]
        xmin, xmax, _, _ = _kutu_rect(alan)
        self.assertGreaterEqual(xmax - xmin, 1140 + 80)


class KomsudanKomsuyaTestleri(unittest.TestCase):
    """Sahibinin isteği (12.11.2026): komşu köydeyken alttaki arkadaş düğmesiyle doğrudan başka köye geçilsin.
    1.4.07 FriendButton/mouseUsed@41-58: getlex Base, getproperty Main, getproperty gameModeCurrent, getlex GameMode,
    getproperty NORMAL, ifeq +1, returnvoid. AVM2 işlem kodları (Adobe AVM2 Overview): nop 0x02, decrement 0x93,
    convert_u 0x74, pushbyte 0x24, ifle 0x16, ifeq 0x13 (s24 göreli konum, komutun sonundan). GameMode: TUTORIAL 0,
    NORMAL 1, NEIGHBOUR 2, ASSAULT 3, CAMPAIGN 4, SURVIVAL 5, TOURNAMENT 6, SPY 7, EDITOR 10."""

    ESKI = bytes.fromhex("6001660c66c201" "609c01" "669b02" "13010000" "47")

    def test_kosul_ayni_uzunlukta_normal_ve_komsuyu_gecirir(self):
        govde = _do_abc(["x"]) + b"\x00" + self.ESKI + b"\xd0\x30"
        yeni, sayi = swf_yama.komsudan_komsuya(govde)
        self.assertEqual(sayi, 1)
        self.assertEqual(len(yeni), len(govde))
        bas = govde.index(self.ESKI)
        kod = yeni[bas:bas + len(self.ESKI)]
        self.assertEqual(kod[:7], self.ESKI[:7])           # Base.Main.gameModeCurrent yığında
        self.assertEqual(kod[7:9], b"\x02\x02")           # nop nop
        self.assertEqual(kod[9:13], b"\x93\x74\x24\x01")  # decrement, convert_u, pushbyte 1
        self.assertEqual(kod[13], 0x16)                   # ifle
        self.assertEqual(kod[14:17], self.ESKI[14:17])    # aynı göreli konum: hedef returnvoid'in ardı
        self.assertEqual(kod[17:], b"\x47")
        self.assertEqual(yeni[:bas] + yeni[bas + len(kod):], govde[:bas] + govde[bas + len(kod):])
        # Koşulun AVM2 anlamı: decrement Number, convert_u ToUint32, ifle sayısal <=
        gecen = {m for m in (0, 1, 2, 3, 4, 5, 6, 7, 10) if ((m - 1) % 2 ** 32) <= 1}
        self.assertEqual(gecen, {1, 2})  # yalnızca NORMAL ve NEIGHBOUR; eğitim, saldırı, görev geçmez

    def test_capa_yoksa_ya_da_iki_kezse_dokunmaz(self):
        for govde in (_do_abc(["x"]), _do_abc(["x"]) + self.ESKI + self.ESKI):
            self.assertEqual(swf_yama.komsudan_komsuya(govde), (govde, 0))

    def test_turkcelestir_yamayi_uygular(self):
        with mock.patch.object(swf_yama, "_turkce_fontlar", return_value={}):
            girdi = _swf(_etiket(82, _do_abc(["x"]) + self.ESKI), _etiket(1, b""), surum=13)
            cikti, sayi = swf_yama.turkcelestir(girdi, {"metin_alanlari": {}})
        abc = [ic for k, _, ic in _etiketleri_ayir(_ac(cikti)) if k == 82][0]
        self.assertNotIn(self.ESKI, abc)
        self.assertIn(bytes.fromhex("020293742401"), abc)
        self.assertEqual(sayi, 1)


class KaynakYenilemeTestleri(unittest.TestCase):
    """Sahibinin kararı (12.11.2026, "Günde bir yenilensin"): ağaç, taş ve altın her açılışta değil, günde bir yenilensin.
    1.4.07 bayt kodu (araclar/abc_okur.py): MapInitializer$/Init@462-503 her açılışta spawnInit (@25-31 getlex
    MapInitializer, callpropvoid cleanBorderTiles 0: orta 3×3 dışındaki halkayı CLEAN_0 ile satar), spawnInitResources
    (altın, taş) ve spawnRemainingResources (ağaç, hayvan) çağırır. Gövde uzunlukları 837, 672, 119; istisna tabloları
    boş. Çok adlılar: Base 1, Items 110, globals 175 (Base/loadGameConfigSuccess@542-550: 60 01 66 6e 66 af01), Main 12,
    gameModeCurrent 194, GameMode 156, NORMAL 283 (FriendButton/mouseUsed@41-58), NUM_TREE_CLUSTERS 12596 (QName genel
    ad alanı), townID 197, dizi erişimi [] 1631 (MultinameL; MissionPopup/refreshGoals), MapInitializer 141,
    cleanBorderTiles 833, Config 29, BG_SKIN_COLORS 5501 (Config/<sınıf> Const yuvası: oturum boyunca aynı Array). Kasaba
    değişince ve komşudan dönüşte config yeniden istenmez (TownManager$/loadTown, Base/realLoadMap): bayrak kasaba
    başına, oturum işareti Config.BG_SKIN_COLORS.NUM_TREE_CLUSTERS'ta (globals her okumada yeni nesne: OData/get v).
    AVM2: iftrue 0x11, ifne 0x14, jump 0x10 (s24, komutun sonundan), returnvoid 0x47."""

    @staticmethod
    def _coz(kod):
        import sys
        sys.path.insert(0, os.path.join(KOK, "araclar"))
        from abc_okur import Abc
        p, cikti = 0, []
        while p < len(kod):
            isl = Abc._islem(kod, p)
            cikti.append(isl)
            p = isl.sonraki
        return cikti

    MOD = [("getlex", 1), ("getproperty", 12), ("getproperty", 194), ("getlex", 156), ("getproperty", 283)]
    KASABA = [("getlex", 1), ("getproperty", 12), ("getproperty", 197)]
    BAYRAK = [("getlex", 1), ("getproperty", 110), ("getproperty", 175), ("getproperty", 12596)] + KASABA + [
        ("getproperty", 1631)]
    ISARET = [("getlex", 29), ("getproperty", 5501), ("getproperty", 12596)]
    BIT = ISARET + KASABA + [("rshift", None), ("pushbyte", 1), ("bitand", None)]

    def _kosul(self, ek, tuket=False):
        """Koşulun AVM2 akışı: mod NORMAL değilse asıl koda; NORMAL'de bayrak[townID] yoksa ya da bu oturumda o kasaba
        zaten yenilendiyse (işaret biti) izin yok; izin varsa (tuket) işarete bit konur ve asıl koda geçilir.
        Dönen: izin yokken çalışan kuyruk."""
        islemler = self._coz(ek)
        adlar = [(i.ad, i.isl[0] if i.isl else None) for i in islemler]
        tuketme = [("getlex", 29), ("getproperty", 5501)] + self.ISARET + [("pushbyte", 1)] + self.KASABA + [
            ("lshift", None), ("bitor", None), ("setproperty", 12596)] if tuket else []
        bas = self.MOD + [("ifne", None)] + self.BAYRAK + [("iffalse", None)] + self.BIT + [("iftrue", None)] + tuketme
        self.assertEqual(adlar[:len(bas) + 1], bas + [("jump", None)])
        sira = {ad: i for i, (ad, _) in enumerate(adlar[:len(bas) + 1]) if ad in ("ifne", "iffalse", "iftrue", "jump")}
        kuyruk = islemler[len(bas) + 1].ofset
        self.assertEqual(islemler[sira["ifne"]].hedefler, (len(ek),))     # NORMAL değil (komşu, akın, eğitim): asıl koda
        self.assertEqual(islemler[sira["iffalse"]].hedefler, (kuyruk,))   # bu kasabanın bugünkü bayrağı yok
        self.assertEqual(islemler[sira["iftrue"]].hedefler, (kuyruk,))    # bu oturumda zaten yenilendi
        self.assertEqual(islemler[sira["jump"]].hedefler, (len(ek),))     # izin var: asıl koda
        return islemler[len(bas) + 1:]

    def test_kosul_izin_yoksa_kendi_koyunde_doner_ya_da_atlar(self):
        self.assertEqual([i.ad for i in self._kosul(swf_yama.KAYNAK_DONUS)], ["returnvoid"])  # spawnInitResources
        self.assertEqual([i.ad for i in self._kosul(swf_yama.KAYNAK_DONUS_SON, tuket=True)], ["returnvoid"])
        atla = self._kosul(swf_yama.KAYNAK_ATLA)
        self.assertEqual([i.ad for i in atla], ["jump"])
        cagri = [y for y in swf_yama.KAYNAK_YAMALARI if y[0] == "spawnInit"][0]
        sonraki = cagri[2][cagri[3]:]
        self.assertEqual([(i.ad, i.isl) for i in self._coz(sonraki)], [("getlex", (141,)), ("callpropvoid", (833, 0))])
        self.assertEqual(atla[0].hedefler, (len(swf_yama.KAYNAK_ATLA) + len(sonraki),))  # yalnızca halka temizliği atlanır

    def test_isareti_yalniz_son_cagri_koyar(self):
        """spawnRemainingResources Init'te üçünün sonuncusu (@500): işaret ondan önce konursa altın, taş ve halka o
        oturumda hiç yenilenmezdi; hiç konmazsa komşudan dönüşte (config yeniden gelmez) yine yenilenirdi."""
        ekler = {y[0]: y[4] for y in swf_yama.KAYNAK_YAMALARI}
        self.assertEqual(ekler, {"spawnRemainingResources": swf_yama.KAYNAK_DONUS_SON,
                                 "spawnInitResources": swf_yama.KAYNAK_DONUS, "spawnInit": swf_yama.KAYNAK_ATLA})
        setleri = {ad: sum(i.ad == "setproperty" for i in self._coz(ek)) for ad, ek in ekler.items()}
        self.assertEqual(setleri, {"spawnRemainingResources": 1, "spawnInitResources": 0, "spawnInit": 0})

    def test_uc_govde_uzar_ve_kodun_geri_kalani_ayni(self):
        dolgu = b"\x47" * 50
        govde = _do_abc(["x"]) + b"".join(swf_yama._u30_yaz(u) + bas + dolgu for _, u, bas, _, _ in swf_yama.KAYNAK_YAMALARI)
        yeni, sayi = swf_yama.kaynaklari_gunde_bir(govde)
        self.assertEqual(sayi, 3)
        beklenen = _do_abc(["x"])
        for ad, uzunluk, bas, yer, ek in swf_yama.KAYNAK_YAMALARI:
            self.assertEqual(uzunluk, {"spawnRemainingResources": 837, "spawnInitResources": 672, "spawnInit": 119}[ad])
            beklenen += swf_yama._u30_yaz(uzunluk + len(ek)) + bas[:yer] + ek + bas[yer:] + dolgu
        self.assertEqual(yeni, beklenen)
        # spawnInit'in uzunluğu bir bayttan (119 < 128) iki bayta çıkar: çapa uzunluk önekini de değiştirir
        self.assertEqual((len(swf_yama._u30_yaz(119)), len(swf_yama._u30_yaz(119 + len(swf_yama.KAYNAK_ATLA)))), (1, 2))

    def test_capalardan_biri_eksikse_dokunmaz(self):
        parcalar = [swf_yama._u30_yaz(u) + bas for _, u, bas, _, _ in swf_yama.KAYNAK_YAMALARI]
        for eksik in range(3):
            govde = _do_abc(["x"]) + b"".join(p for i, p in enumerate(parcalar) if i != eksik)
            self.assertEqual(swf_yama.kaynaklari_gunde_bir(govde), (govde, 0))
        govde = _do_abc(["x"]) + b"".join(parcalar) + parcalar[0]
        self.assertEqual(swf_yama.kaynaklari_gunde_bir(govde), (govde, 0))

    def test_turkcelestir_yamayi_uygular(self):
        icerik = b"".join(swf_yama._u30_yaz(u) + bas for _, u, bas, _, _ in swf_yama.KAYNAK_YAMALARI)
        with mock.patch.object(swf_yama, "_turkce_fontlar", return_value={}):
            girdi = _swf(_etiket(82, _do_abc(["x"]) + icerik), _etiket(1, b""), surum=13)
            cikti, sayi = swf_yama.turkcelestir(girdi, {"metin_alanlari": {}})
        abc = [ic for k, _, ic in _etiketleri_ayir(_ac(cikti)) if k == 82][0]
        self.assertEqual(abc.count(swf_yama.KAYNAK_DONUS), 1)
        self.assertEqual(abc.count(swf_yama.KAYNAK_DONUS_SON), 1)
        self.assertEqual(abc.count(swf_yama.KAYNAK_ATLA), 1)
        self.assertEqual(sayi, 3)

    def test_gercek_istemcide_dallar_kaymaz(self):
        """SWF depoda yok (indirilen varlık); SE_ISTEMCI_SWF verilirse gerçek istemcide denenir."""
        yol = os.environ.get("SE_ISTEMCI_SWF")
        if not yol or not os.path.exists(yol):
            self.skipTest("SE_ISTEMCI_SWF yok")
        import sys
        sys.path.insert(0, os.path.join(KOK, "araclar"))
        from abc_okur import Abc, abc_etiketleri
        et = [e for _, e in abc_etiketleri(open(yol, "rb").read()) if b"spawnRemainingResources" in e][0]
        yeni, sayi = swf_yama.kaynaklari_gunde_bir(et)
        self.assertEqual(sayi, 3)
        eski_abc, yeni_abc = Abc(et), Abc(yeni)
        adlar = eski_abc.yontem_adlari()
        for ad, _, _, yer, ek in swf_yama.KAYNAK_YAMALARI:
            i = [k for k, v in adlar.items() if v == "MapInitializer$/" + ad][0]
            self.assertEqual(eski_abc.govdeler[i].istisnalar, [])
            eski, yeni_isl = eski_abc.coz(eski_abc.govdeler[i]), yeni_abc.coz(yeni_abc.govdeler[i])
            kay = lambda o: o if o < yer else o + len(ek)  # noqa: E731
            for o, isl in eski.items():
                karsi = yeni_isl[kay(o)]
                self.assertEqual((karsi.ad, karsi.isl, karsi.hedefler), (isl.ad, isl.isl, tuple(map(kay, isl.hedefler))))


class HikayeGoreviTestleri(unittest.TestCase):
    """Sahibinin bildirimi (12.11.2026): kendi adasındaki hikâye görevi (prenses, düşman kampı) hiç çıkmıyor. 0926
    istemcisi (SocialEmpires0926bsec.swf) MapInitializer$/spawnInit@82-92: findpropstrict spawnQuestInMap, getlex Base,
    getproperty Main, getproperty currentQuestId, callpropvoid spawnQuestInMap 1. 1.4.07'de bu satır yok; spawnQuestInMap
    yalnızca AdminPanel komutundan çağrılır. 1.4.07 çok adlıları: spawnQuestInMap 16185, Base 1, Main 12,
    currentQuestId 474; ekleme yeri @73 (setCorrectQuest sonucu currentQuestId'ye yazıldıktan sonra, tutorialMode'dan
    önce)."""

    def test_cagri_0926daki_gibi(self):
        islemler = KaynakYenilemeTestleri._coz(swf_yama.GOREV_CAGRISI)
        self.assertEqual([(i.ad, i.isl) for i in islemler],
                         [("findpropstrict", (16185,)), ("getlex", (1,)), ("getproperty", (12,)),
                          ("getproperty", (474,)), ("callpropvoid", (16185, 1))])

    def test_yer_setCorrectQuestin_ardi(self):
        islemler = KaynakYenilemeTestleri._coz(swf_yama._GOREV_KOD[:swf_yama.GOREV_YERI])
        adlar = [i.ad for i in islemler]
        cagri = adlar.index("callproperty")
        self.assertEqual(islemler[cagri].isl, (22731, 1))  # setCorrectQuest, 1 argüman
        self.assertEqual(adlar[cagri + 1:], ["dup", "setlocal_1", "setproperty", "getlocal_1", "kill", "pop"])
        self.assertEqual(islemler[cagri + 3].isl, (474,))  # setproperty currentQuestId

    def test_yamasiz_ve_kaynak_yamali_govdeye_konur(self):
        kod = swf_yama._GOREV_KOD
        ek = swf_yama.SAYAC_KURULUMU + swf_yama.GOREV_CAGRISI
        for kaynakli in (False, True):
            # gövde başlığı: yöntem 5, max_stack 3, local_count 2, init_scope 1, max_scope 2 (1.4.07 spawnInit)
            govde = _do_abc(["x"]) + b"".join(swf_yama._u30_yaz(u) + bas for ad, u, bas, _, _ in swf_yama.KAYNAK_YAMALARI
                                              if ad != "spawnInit") + b"\x05\x03\x02\x01\x02" + swf_yama._u30_yaz(len(kod)) + kod
            if kaynakli:
                govde, sayi = swf_yama.kaynaklari_gunde_bir(govde)
                self.assertEqual(sayi, 3)
            yeni, sayi = swf_yama.hikaye_gorevini_kur(govde)
            self.assertEqual(sayi, 1)
            self.assertEqual(yeni.count(ek), 1)
            i = yeni.index(ek)
            self.assertEqual(yeni[i - 1], 0x29)  # önünde setCorrectQuest bloğunun pop'u
            self.assertEqual(yeni[i + len(ek):][:5], bytes.fromhex("6001660c66"))  # ardı tutorialMode
            uzunluk = len(kod) + len(ek) + (len(swf_yama.KAYNAK_ATLA) if kaynakli else 0)
            baslik = b"\x05" + bytes([swf_yama.SAYAC_YIGINI]) + b"\x02\x01\x02"
            self.assertIn(baslik + swf_yama._u30_yaz(uzunluk) + kod[:25], yeni)  # yığın 7, uzunluk eklemeyle büyür

    def test_baslik_beklenmedikse_dokunmaz(self):
        """max_stack/local_count 3/2 değilse (başka sürüm) yığın yükseltilemez; gövdeye hiç dokunulmaz."""
        kod = swf_yama._GOREV_KOD
        govde = _do_abc(["x"]) + b"\x05\x04\x02\x01\x02" + swf_yama._u30_yaz(len(kod)) + kod
        self.assertEqual(swf_yama.hikaye_gorevini_kur(govde), (govde, 0))

    def test_govde_yoksa_dokunmaz(self):
        govde = _do_abc(["x"])
        self.assertEqual(swf_yama.hikaye_gorevini_kur(govde), (govde, 0))

    def test_gercek_istemcide_dallar_kaymaz(self):
        yol = os.environ.get("SE_ISTEMCI_SWF")
        if not yol or not os.path.exists(yol):
            self.skipTest("SE_ISTEMCI_SWF yok")
        import sys
        sys.path.insert(0, os.path.join(KOK, "araclar"))
        from abc_okur import Abc, abc_etiketleri
        et = [e for _, e in abc_etiketleri(open(yol, "rb").read()) if b"spawnRemainingResources" in e][0]
        for kaynakli in (False, True):
            once = swf_yama.kaynaklari_gunde_bir(et)[0] if kaynakli else et
            yeni, sayi = swf_yama.hikaye_gorevini_kur(once)
            self.assertEqual(sayi, 1)
            a0, a1 = Abc(once), Abc(yeni)
            i = [k for k, v in a0.yontem_adlari().items() if v == "MapInitializer$/spawnInit"][0]
            yer = swf_yama.GOREV_YERI + (len(swf_yama.KAYNAK_ATLA) if kaynakli else 0)
            d = len(swf_yama.SAYAC_KURULUMU + swf_yama.GOREV_CAGRISI)
            self.assertEqual(a1.govdeler[i].max_yigin, swf_yama.SAYAC_YIGINI)
            eski, yeni_isl = a0.coz(a0.govdeler[i]), a1.coz(a1.govdeler[i])
            kay = lambda o: o if o < yer else o + d  # noqa: E731
            for o, isl in eski.items():
                karsi = yeni_isl[kay(o)]
                self.assertEqual((karsi.ad, karsi.isl, karsi.hedefler), (isl.ad, isl.isl, tuple(map(kay, isl.hedefler))))
            adlar = [(yeni_isl[o].ad, a1.ad(yeni_isl[o].isl[0]) if yeni_isl[o].isl and yeni_isl[o].ad != "pushint" else "")
                     for o in sorted(yeni_isl) if yer <= o < yer + d]
            self.assertEqual([a for a, _ in adlar[-5:]],
                             ["findpropstrict", "getlex", "getproperty", "getproperty", "callpropvoid"])
            # 0926 GuiManager/addTimer@95-236: new CountdownTimer(5 argüman) -> countdownTimerOgres, mcTrolls.addChild
            self.assertIn(("constructprop", "CountdownTimer"), adlar)
            self.assertIn(("setproperty", "countdownTimerOgres"), adlar)
            self.assertIn(("getproperty", "TIMER_CAMPAMENTO_ENEMIGO"), adlar)
            self.assertIn(("callpropvoid", "addChild"), adlar)


class KampSayaciTestleri(unittest.TestCase):
    """DNT-68. Sahibi (14.11.2026): prenses kampı geldi ama 'bu kadar düşman kaldı' yazmıyor. 0926 IsoEngine/Update
    @248-256: trol varken countdownTimerOgres.setTextOgres(trol sayısı). 1.4.07 Update'te o satır yok; @171, @185 ve
    @235'teki dallar 248'e gider. Çok adlar (1.4.07): Base 1, Gui 45, bgBar 148, mcTrolls 4259, countdownTimerOgres 5382,
    visible 34, setTextOgres 21102. Ruffle'da (30. seviye köy): sağ altta 'Düşman Ordugâhı 51 düşman kaldı', kamp tek
    (41 duvar), konsolda hata yok."""

    def test_yazi_kodunun_bicimi(self):
        islemler = KaynakYenilemeTestleri._coz(swf_yama.SAYAC_YAZISI)
        adlar = [(i.ad, i.isl) for i in islemler]
        self.assertIn(("callpropvoid", (21102, 1)), adlar)  # setTextOgres(trol)
        self.assertIn(("getproperty", (4259,)), adlar)      # mcTrolls
        self.assertIn(("ifngt", ()), [(i.ad, ()) for i in islemler])  # trol yoksa yazmaz
        self.assertIn(("ifeq", ()), [(i.ad, ()) for i in islemler])   # kendi köyü değilse gizler
        # setVisibleTimerOgres (23807) çağrılmaz: 1.4.07 arayüzünde TypeError #1009 verir
        self.assertNotIn(23807, [x for i in islemler for x in i.isl])

    def test_gercek_istemcide_dallar(self):
        yol = os.environ.get("SE_ISTEMCI_SWF")
        if not yol or not os.path.exists(yol):
            self.skipTest("SE_ISTEMCI_SWF yok")
        import sys
        sys.path.insert(0, os.path.join(KOK, "araclar"))
        from abc_okur import Abc, abc_etiketleri
        et = [e for _, e in abc_etiketleri(open(yol, "rb").read()) if b"spawnRemainingResources" in e][0]
        yeni, sayi = swf_yama.kamp_sayaci(et)
        self.assertEqual(sayi, 1)
        a0, a1 = Abc(et), Abc(yeni)
        i = [k for k, v in a0.yontem_adlari().items() if v == "IsoEngine/Update"][0]
        eski, yeni_isl = a0.coz(a0.govdeler[i]), a1.coz(a1.govdeler[i])
        yer, d = swf_yama.SAYI_YERI, len(swf_yama.SAYAC_YAZISI)
        self.assertEqual(sorted(o for o, isl in eski.items() if yer in isl.hedefler), [171, 185, 235])
        kay = lambda o: o if o <= yer else o + d  # noqa: E731  (248'e giden dallar eklenen kodun başına)
        for o, isl in eski.items():
            karsi = yeni_isl[kay(o) if o != yer else o + d]
            self.assertEqual((karsi.ad, karsi.isl), (isl.ad, isl.isl))
            self.assertEqual(karsi.hedefler, tuple(h if h <= yer else h + d for h in isl.hedefler))
        self.assertLessEqual(3, a1.govdeler[i].max_yigin)
        self.assertEqual(a1.govdeler[i].istisnalar, [])

    def test_turkcelestir_iki_yamayi_da_koyar(self):
        yol = os.environ.get("SE_ISTEMCI_SWF")
        if not yol or not os.path.exists(yol):
            self.skipTest("SE_ISTEMCI_SWF yok")
        sonuc = swf_yama.turkcelestir(open(yol, "rb").read())
        veri = sonuc[0] if isinstance(sonuc, tuple) else sonuc
        govde = swf_yama._govde(veri)
        govde = govde[0] if isinstance(govde, tuple) else govde
        self.assertIn(swf_yama.SAYAC_YAZISI, govde)
        self.assertIn(swf_yama.SAYAC_KURULUMU + swf_yama.GOREV_CAGRISI, govde)


class TamEkranBoyuTestleri(unittest.TestCase):
    """DNT-70. 1.4.07 Base/getStageDimensions@51-67: displayState FULL_SCREEN ise stage.fullScreenWidth/Height
    (çok adlar 18101, 17418), değilse Config.STAGE_WIDTH/HEIGHT. Ruffle 0.7.1'de iki alıcı taslak ("Encountered stub:
    AVM2 flash.display.Stage.fullScreenWidth getter"); menüler ekranın kenarına dizilmedi. stageWidth 28860, stageHeight
    28861 (1.4.07'de başka yöntemlerde kullanılan çok adlar), dördü de 4 baytlık u30."""

    def test_yalnizca_iki_ad_degisir_uzunluk_ayni(self):
        govde = _do_abc(["x"]) + swf_yama._u30_yaz(len(swf_yama._EKRAN_BOYU_KOD)) + swf_yama._EKRAN_BOYU_KOD
        yeni, sayi = swf_yama.tam_ekran_boyu(govde)
        self.assertEqual(sayi, 1)
        self.assertEqual(len(yeni), len(govde))
        fark = [i for i, (a, b) in enumerate(zip(govde, yeni)) if a != b]
        self.assertEqual(len(fark), 4)  # u30 b58d01→bce101, 8a8801→bde101: üçüncü baytlar (01) ortak
        islemler = KaynakYenilemeTestleri._coz(yeni[len(govde) - len(swf_yama._EKRAN_BOYU_KOD):])
        self.assertIn(("getproperty", (28860,)), [(i.ad, i.isl) for i in islemler])
        self.assertIn(("getproperty", (28861,)), [(i.ad, i.isl) for i in islemler])
        self.assertNotIn(("getproperty", (18101,)), [(i.ad, i.isl) for i in islemler])

    def test_govde_yoksa_dokunmaz(self):
        govde = _do_abc(["x"])
        self.assertEqual(swf_yama.tam_ekran_boyu(govde), (govde, 0))

    def test_gercek_istemcide_adlar(self):
        yol = os.environ.get("SE_ISTEMCI_SWF")
        if not yol or not os.path.exists(yol):
            self.skipTest("SE_ISTEMCI_SWF yok")
        import sys
        sys.path.insert(0, os.path.join(KOK, "araclar"))
        from abc_okur import Abc, abc_etiketleri
        et = [e for _, e in abc_etiketleri(open(yol, "rb").read()) if b"spawnRemainingResources" in e][0]
        yeni, sayi = swf_yama.tam_ekran_boyu(et)
        self.assertEqual(sayi, 1)
        a = Abc(yeni)
        i = [k for k, v in a.yontem_adlari().items() if v == "Base/getStageDimensions"][0]
        adlar = [a.ad(x.isl[0]) for _, x in sorted(a.coz(a.govdeler[i]).items()) if x.ad == "getproperty"]
        self.assertIn("stageWidth", adlar)
        self.assertIn("stageHeight", adlar)
        self.assertNotIn("fullScreenWidth", adlar)
        sonuc = swf_yama.turkcelestir(open(yol, "rb").read())
        veri = sonuc[0] if isinstance(sonuc, tuple) else sonuc
        self.assertNotIn(swf_yama._EKRAN_BOYU_KOD, swf_yama._govde(veri))  # turkcelestir yamayı uygular
