"""Dünya haritası (kıtalar) ve fetih.

İstemci haritayı `get_continent_ranking.php` ile yükler: her kıtada 8 yuva
vardır; biri oyuncunun, diğer 7'si fethedilecek rakiplerdir (bot köyleri).
Fethedilen yuvaların numaraları `maps[0].universAttackWin` listesinde durur;
7/7 olunca istemci `worldChange=1` ile sonraki kıtayı ister.

Kayıtta: privateState.kita (kıta no, 1'den), privateState.kita_konum (oyuncunun
yuvası), privateState.kita_karisim (yer değiştirince rakipler değişir), privateState.kita_dizilis
(rakip sırası → yuva; yalnızca oyuncu yuva değiştirince yazılır, DNT-48).
"""

from oyun.kayit import all_saves_userid, session

YUVA = 8
VARSAYILAN_RESIM = "/img/profile/1025.png"


def _bot_kayitlari():
    botlar = []
    for uid in all_saves_userid():
        kayit = session(uid)
        if kayit and kayit.get("playerInfo", {}).get("bot"):
            botlar.append((int(kayit["maps"][0].get("level", 1)), str(uid), kayit))
    botlar.sort(key=lambda b: (b[0], b[1]))  # kolaydan zora
    return [(uid, kayit) for _, uid, kayit in botlar]


def kita_no(kayit):
    return max(1, int(kayit["privateState"].get("kita", 1) or 1))


def kendi_konumu(kayit):
    return int(kayit["privateState"].get("kita_konum", YUVA - 1)) % YUVA


def _dizilis(kayit):
    """Rakip k'nin yuvası. Varsayılan: rakip k k. yuvada, oyuncunun yuvasındaki rakip son yuvada (7)."""
    konum = kendi_konumu(kayit)
    varsayilan = [YUVA - 1 if k == konum else k for k in range(YUVA - 1)]
    kayitli = kayit["privateState"].get("kita_dizilis")
    if (isinstance(kayitli, list) and len(kayitli) == YUVA - 1 and all(isinstance(y, int) for y in kayitli)
            and sorted(kayitli + [konum]) == list(range(YUVA))):
        return list(kayitli)
    return varsayilan


def yuva_degistir(kayit, eski, yeni):
    """ExplorationsManager/evalUserPositionNotConquered @286-376: oyuncu (eski yuva) fethedilmemiş rakiple (yeni yuva)
    yer değiştirir; rakip oyuncunun eski yuvasına geçer. Sıra saklanır ki ikinci değişimde de istemciyle aynı kalsın."""
    eski, yeni = int(eski) % YUVA, int(yeni) % YUVA
    dizilis = _dizilis(kayit)
    ps = kayit["privateState"]
    if eski == kendi_konumu(kayit) and yeni in dizilis:
        dizilis[dizilis.index(yeni)] = eski
        ps["kita_dizilis"] = dizilis
    else:  # beklenmeyen eski yuva: rakipler varsayılan sıraya döner
        ps.pop("kita_dizilis", None)
    ps["kita_konum"] = yeni


def fetihler(kayit):
    liste = kayit["maps"][0].get("universAttackWin")
    if not isinstance(liste, list):
        liste = kayit["maps"][0]["universAttackWin"] = []
    return liste


def _rakipler(kita, karisim, adet):
    """Kıtanın rakip botları: kıta ilerledikçe daha güçlü botlar gelir."""
    botlar = _bot_kayitlari()
    if not botlar:
        return []
    baslangic = ((kita - 1) * (YUVA - 1) + karisim * 3) % len(botlar)
    return [botlar[(baslangic + i) % len(botlar)] for i in range(min(adet, len(botlar)))]


def _giris(konum, uid, kayit):
    pi = kayit.get("playerInfo", {})
    harita = kayit["maps"][0]
    return {
        "posicion": konum,
        "user_id": str(uid),
        "name": pi.get("name") or "Oyuncu",
        "level": int(harita.get("level", 1)),
        "race": harita.get("race") or "h",
        "pic": pi.get("pic") or VARSAYILAN_RESIM,
    }


def kita_listesi(kayit, kita=None):
    """get_continent_ranking'in `continent` dizisi. [0].nivel kıta numarasıdır."""
    karisim = int(kayit["privateState"].get("kita_karisim", 0) or 0)
    kendi = kita is None or kita == kita_no(kayit)
    kita = kita_no(kayit) if kita is None else max(1, kita)
    if kendi:
        # Rakip k k. yuvada; oyuncu bir yuvaya geçerse o yuvanın rakibi oyuncunun
        # boşalttığı yuvaya taşınır (_dizilis). Böylece kayıtlı fetih numaraları kaymaz.
        konum = kendi_konumu(kayit)
        rakipler = _rakipler(kita, karisim, YUVA - 1)
        yuvalar = _dizilis(kayit)
        liste = [_giris(yuvalar[k], *r) for k, r in enumerate(rakipler)]
        liste.append(_giris(konum, kayit["playerInfo"]["pid"], kayit))
        liste.sort(key=lambda g: g["posicion"])
    else:
        liste = [_giris(i, *r) for i, r in enumerate(_rakipler(kita, karisim, YUVA))]
    if liste:
        liste[0]["nivel"] = kita
    return liste


def dunya_kimligi(kayit):
    return (kita_no(kayit) - 1) * YUVA + kendi_konumu(kayit) + 1


def sonraki_kita(kayit):
    """7 yuva fethedilince (istemci worldChange=1 gönderir) sonraki kıtaya geç."""
    if len(fetihler(kayit)) >= YUVA - 1:
        kayit["privateState"]["kita"] = kita_no(kayit) + 1
        kayit["privateState"].pop("kita_dizilis", None)  # yeni kıtanın rakipleri varsayılan sırada
        kayit["maps"][0]["universAttackWin"] = []
        return True
    return False


def yer_degistir(kayit):
    """Oyuncu kıtasını değiştirmek istedi (relocate): rakipler yenilenir."""
    ps = kayit["privateState"]
    ps["kita_karisim"] = int(ps.get("kita_karisim", 0) or 0) + 1
    ps.pop("kita_dizilis", None)
    kayit["maps"][0]["universAttackWin"] = []


def fetih_kaydet(kayit, kurban):
    """Kazanılan saldırının hedefi bu kıtadaysa yuvası fethedilmiş sayılır."""
    kurban_id = str((kurban or {}).get("user_id", ""))
    for giris in kita_listesi(kayit):
        if giris["user_id"] == kurban_id and giris["user_id"] != str(kayit["playerInfo"]["pid"]):
            liste = fetihler(kayit)
            if giris["posicion"] not in liste:
                liste.append(giris["posicion"])
            return giris["posicion"]
    return None
