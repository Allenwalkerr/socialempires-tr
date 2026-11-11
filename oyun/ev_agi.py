"""Ev ağı kipinin parolası (KAR-17, DGV-01, SNK-05).

`ayarlar.json` `"ev_agi": true` iken sunucu ev ağına açılır. O zaman bu bilgisayar dışındaki her cihaz önce parolayı
girer; girmeden kayıtlara, komutlara, yedeklere ve giriş listesine ulaşamaz. Bu bilgisayar (127.0.0.1) parola sormaz.

Parola: `ayarlar.json` `"ev_agi_parolasi"` (en az 8 karakter) varsa odur; yoksa ilk açılışta rastgele üretilir,
taban klasördeki `.ev_agi_parolasi` dosyasında (yalnızca sahibine okunur) saklanır ve her açılışta konsola yazılır.
Oturum, parolanın özetine bağlıdır: parola değişince önceki girişler geçersiz olur. Yanlış denemeler adres başına
sınırlanır.
"""

import hashlib
import hmac
import os
import secrets
import threading
import time

from flask import redirect, render_template, request, session

from oyun import ayarlar
from oyun.yollar import BASE_DIR

DOSYA = os.path.join(BASE_DIR, ".ev_agi_parolasi")
EN_KISA = 8
HARFLER = "abcdefghjkmnpqrstuvwxyz23456789"  # karışan harfler yok: 0/o, 1/l/i
DENEME_SINIRI = 5
KILIT_SURESI = 300  # saniye
YEREL = ("127.0.0.1", "::1")
# Parolasız açık kalanlar: giriş sayfası, sayfanın durağan dosyaları, sağlık yoklaması ve oyunun kendi SWF/resim
# dosyaları. Bunlar gizli değil; Android'in uygulama jetonu da aynılarını açık bırakır (sunucu.JETONSUZ_YOLLAR).
# Kayıtlar, komutlar (command.php), oyuncu bilgisi, yedekler ve giriş listesi parolaya bağlıdır.
ACIK_YOLLAR = ("/ev-agi-giris", "/saglik", "/img/", "/css/", "/fonts/", "/js/", "/ruffle/", "/favicon.ico",
               "/default01.static.socialpointgames.com/")

_kilit = threading.Lock()
_yanlislar = {}  # adres -> (sayı, ilk yanlışın zamanı)


def acik_mi() -> bool:
    return bool(ayarlar.oku().get("ev_agi"))


def _dosyadan():
    try:
        with open(DOSYA, encoding="utf-8") as f:
            parola = f.read().strip()
        return parola if len(parola) >= EN_KISA else None
    except OSError:
        return None


def _uret():
    parola = "-".join("".join(secrets.choice(HARFLER) for _ in range(4)) for _ in range(3))
    try:
        fd = os.open(DOSYA, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(parola)
    except OSError as hata:
        print(f" ! Ev agi parolasi kaydedilemedi ({hata}); bu acilis icin gecerli")
    return parola


_uretilen = None
_kisa_uyarildi = False


def parola() -> str:
    """Geçerli parola: ayarlardaki, yoksa dosyadaki, yoksa yeni üretilen."""
    global _uretilen, _kisa_uyarildi
    # Formdaki giriş de kırpılır (giris): baştaki/sondaki boşluk iki yolda aynı sayılsın (#46 incelemesi)
    ayardaki = str(ayarlar.oku().get("ev_agi_parolasi") or "").strip()
    if len(ayardaki) >= EN_KISA:
        return ayardaki
    if ayardaki and not _kisa_uyarildi:  # her istekte değil, bir kez
        _kisa_uyarildi = True
        print(f" ! ayarlar.json ev_agi_parolasi en az {EN_KISA} karakter olmali; uretilen parola kullaniliyor")
    with _kilit:
        if _uretilen is None:
            _uretilen = _dosyadan() or _uret()
        return _uretilen


def _ozet(p):
    return hashlib.sha256(("se-ev-agi:" + p).encode("utf-8")).hexdigest()


def _yerel_mi():
    return request.remote_addr in YEREL


def girisli_mi() -> bool:
    kayitli = session.get("ev_agi")
    return isinstance(kayitli, str) and hmac.compare_digest(kayitli, _ozet(parola()))


def denetle():
    """before_request: ev ağı açıkken yerel olmayan, girişsiz isteği durdurur."""
    if not acik_mi() or _yerel_mi() or request.path.startswith(ACIK_YOLLAR) or girisli_mi():
        return None
    if request.method == "GET" and request.accept_mimetypes.accept_html:
        return redirect("/ev-agi-giris")
    return ("Ev agi parolasi gerekli", 401)


def _kilitli(adres):
    with _kilit:
        sayi, ilk = _yanlislar.get(adres, (0, 0))
        if sayi and time.time() - ilk > KILIT_SURESI:
            _yanlislar.pop(adres, None)
            return False
        return sayi >= DENEME_SINIRI


def _yanlis(adres):
    with _kilit:
        sayi, ilk = _yanlislar.get(adres, (0, time.time()))
        _yanlislar[adres] = (sayi + 1, ilk)


def giris():
    if not acik_mi() or _yerel_mi():
        return redirect("/")
    ileti = None
    durum = 200
    if request.method == "POST":
        adres = request.remote_addr or "?"
        if _kilitli(adres):
            ileti, durum = "Çok fazla yanlış deneme. Beş dakika sonra yeniden deneyin.", 429
        elif hmac.compare_digest(str(request.form.get("parola", "")).strip().encode("utf-8"),
                                 parola().encode("utf-8")):
            with _kilit:
                _yanlislar.pop(adres, None)
            session["ev_agi"] = _ozet(parola())
            session.permanent = True
            return redirect("/")
        else:
            _yanlis(adres)
            ileti, durum = "Parola yanlış.", 403
    return render_template("ev_agi_giris.html", ileti=ileti), durum


def baslangic_iletisi():
    """Açılışta konsola: parolanın kendisi (bu bilgisayarın ekranında)."""
    print(f" [+] Ev agi parolasi: {parola()}  (telefon ve tabletler ilk acilista bunu sorar)")


from oyun.sunucu import app  # noqa: E402  (oyun.sunucu bu modülü dosya sonunda içe aktarır)

app.before_request(denetle)  # _uygulama_jetonu ve _koken_denetimi'nden sonra çalışır
app.add_url_rule("/ev-agi-giris", "ev_agi_giris", giris, methods=["GET", "POST"])
