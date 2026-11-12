"""Bot yardımı (KMT-09, OYN-29, KAR-26, KAR-27, KAR-29): oyunun "arkadaşından iste" düğmeleri botlarla çalışır.

Asıl oyunda bu düğmeler Facebook'ta arkadaş seçtirirdi (çok oyunculu; burada yok). İstemci (1.4.07 bayt kodu, ayrıntı
docs/inceleme/1407-asker-ada.md):
- Asker Toplama (387): PopupRecruitment/onFindFriend@89-133 ExternalInterface.call("showPopupSEHelpSocialItem", tx, ty,
  kasaba, bina, si, ad). Yardım edenler binanın attrs.si listesidir (canlı referans, <kurucu>@186-224); işe al düğmesi
  si.length >= num_recruitments iken açılır, istemci en çok 4 sayar (onOpenBuilding@248-250).
- Viral teklifler ve Ada Ocağı'nın boru malzemesi: ExternalInterface.call("showPopupSEHelpOffer", no); yardım edenler
  privateState.viralOffers[no].friends (SpecialDayOfferManager/setPlayerInfo), en çok num_workers.
- İstemci listeyi kendisi doldurmaz: sayfa (templates/js/oyun.js) bu yola yazar, sonra oyunun forceReloadInfo geri
  çağrısıyla (Base/init addCallback) oyuncu bilgisini yeniden okutur.

Sahibinin kararları: botlar yardım eder (KAR-26, KAR-27); her yardım yerine günde bir bot (KAR-29). Bot kimliği istemcide
friendsInfoMap'ten ad ve resimle çözülür; parseInt(kimlik) 0 olan kimlik "Köylü" sayılır (refreshFotos@230-705), bu yüzden
0'la başlayan kimlikler seçilmez.
"""

import random

from flask import request, session

from oyun import takvim
from oyun.config import get_game_config
from oyun.kayit import all_saves_userid, save_lock, save_session
from oyun.kayit import session as kayit_oturumu
from oyun.sunucu import app

ASKER_TOPLAMA = 387  # ID_BUILDING_ALLIES_RECRUITMENT
SI_SINIRI = 4  # PopupRecruitment/onOpenBuilding: Math.min(si.length, 4)
KAYIT_ALANI = "botYardimi"  # privateState: {hedef: "YYYY-AA-GG"}; istemci okumaz


def _bugun():
    return takvim.bugun().isoformat()


def _botlar(haric):
    from oyun.kayit import neighbor_session
    adaylar = []
    for uid in all_saves_userid():
        k = neighbor_session(uid)
        kimlik = str(((k or {}).get("playerInfo") or {}).get("pid") or uid)  # istemci friendsInfo uid'si (fb_friends_str)
        if k and (k.get("playerInfo") or {}).get("bot") and kimlik not in haric and not kimlik.startswith("0"):
            adaylar.append(kimlik)
    return adaylar


def _gunluk_hak(ps, hedef):
    defter = ps.get(KAYIT_ALANI)
    if not isinstance(defter, dict):
        defter = ps[KAYIT_ALANI] = {}
    return defter.get(hedef) != _bugun(), defter


def _sosyal_liste(kayit, veri):
    from oyun.komutlar import esya_bul, harita, ozellikler
    if int(veri.get("id", 0)) != ASKER_TOPLAMA:
        return None, None, "Bu bina için bot yardımı yok."
    kasaba = int(veri.get("town", 0))
    esya = esya_bul(harita(kayit, kasaba), int(veri.get("tx", -1)), int(veri.get("ty", -1)), ASKER_TOPLAMA)
    if esya is None:
        return None, None, "Asker Toplama binası bulunamadı."
    ozellik = ozellikler(esya)
    if not isinstance(ozellik.get("si"), list):
        ozellik["si"] = []
    return ozellik["si"], SI_SINIRI, f"si:{kasaba}:{esya[1]}:{esya[2]}"


def _teklif_liste(kayit, veri):
    from oyun.komutlar import _viral_teklif
    no = int(veri.get("no", 0))
    teklif, durum = _viral_teklif(kayit, no)
    if not teklif:
        return None, None, "Teklif bulunamadı."
    return durum["friends"], int(teklif.get("num_workers", 0)), f"teklif:{no}"


def yardim_et(kayit, veri):
    """(cevap, kod). veri: {tur: "sosyal", tx, ty, town, id} ya da {tur: "teklif", no}."""
    tur = veri.get("tur")
    try:
        liste, sinir, hedef = (_sosyal_liste if tur == "sosyal" else _teklif_liste)(kayit, veri)
    except (TypeError, ValueError):
        return {"hata": "Geçersiz istek."}, 400
    if liste is None:
        return {"hata": hedef}, 400
    if len(liste) >= sinir:
        return {"hata": "Yardımcılar tamam."}, 409
    hak, defter = _gunluk_hak(kayit["privateState"], hedef)
    if not hak:
        return {"hata": "Bugün bir bot yardım etti; yarın yeni biri gelir.", "yarin": True}, 409
    adaylar = _botlar({str(x) for x in liste})
    if not adaylar:
        return {"hata": "Yardım edecek bot yok."}, 409
    bot = random.choice(adaylar)
    liste.append(bot)
    defter[hedef] = _bugun()
    return {"bot": bot, "yardimci": len(liste), "gerekli": sinir}, 200


@app.route("/yardim/bot", methods=["POST"])
def bot_yardimi_ucu():
    uid = session.get("USERID")
    if not uid or uid not in all_saves_userid():
        return ({"hata": "Oturum yok."}, 404)
    veri = request.get_json(silent=True) or {}
    with save_lock:
        kayit = kayit_oturumu(uid)
        cevap, kod = yardim_et(kayit, veri)
        if kod == 200:
            save_session(uid)
    return cevap, kod
