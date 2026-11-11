"""1.4.07'nin yeni PvP'si (GEC-05): rakip arama, kalkan, saldırı başlangıcı (yalnızca botlara karşı, KAR-02).

Kaynak: istemcinin bayt kodu (SocialEmpires1.4.07sec_fixed.swf), araclar/abc_okur.py ile okundu (11.11.2026):

- PVPManager/searchEnemy: get_enemy_new [arama_bedeli, searchesBeforeAttack]; bedeli istemci altından kendisi
  düşer. Rakip ayrı HTTP ucundan gelir: pvp/web/app.php/pvp/enemy → {"result": "success", "data": {"id": ...}}.
- PVPManager/getSearchEnemyCost: globals.PVP_SEARCH_ENEMY_COST'un sayıya çevrilmiş anahtarları sıralanır; oyuncu
  seviyesinden BÜYÜK ilk anahtarda durulur ve o satırın "g"si alınır (hiçbiri büyük değilse son satır).
- PVPManager/loadMap: begin_attack_new [clientTimestamp] → attack_player [rakip] → (intikamsa) reply_attack
  [attackTime]; sendBegin içinde ShieldManager.removeShields: kalkan kalkar (shieldEndTime = -1), reset_shield [].
- ShieldManager/buyShield: buy_shield [kalkan_id]. shieldEndTime: -1 ise şimdi + protection_time, değilse eski +
  protection_time; shieldCooldown fiilen şimdi + cooldown; purchasedShields'e id eklenir; bedel price/price_type.
- ShieldManager/_checkCoolDown: bekleme bitince purchasedShields = [], shieldCooldown = -1, reset_shield [].
- İstemci kalkanı privateState.shieldEndTime/shieldCooldown/purchasedShields'ten okur; 0'ı -1 sayar
  (ShieldManager/setPlayerShieldState). Sunucu "yok" için 0 yazar.
- PopupAttackLog/checkCanAttack: pvp/web/app.php/pvp/pool/check {user_id} → data == 1 ise saldırılabilir.
"""

import random

from oyun.config import get_game_config
from oyun.ekonomi import timestamp_now
from oyun.kayit import all_saves_userid, neighbor_session

AYNI_HEDEF_SURESI = 4 * 3600  # Config.ATTACKS_SAME_PLAYER_HOURS (pvp.AYNI_HEDEF_SURESI ile aynı)


def _tam(deger, varsayilan=0):
    try:
        return int(deger)
    except (TypeError, ValueError, OverflowError):
        return varsayilan


def arama_bedeli(seviye):
    """PVPManager/getSearchEnemyCost: seviyeden büyük ilk anahtarın altını; yoksa son anahtarınki."""
    tablo = get_game_config().get("globals", {}).get("PVP_SEARCH_ENEMY_COST") or {}
    anahtarlar = sorted(_tam(k) for k in tablo)
    bedel = 0
    for anahtar in anahtarlar:
        bedel = _tam((tablo.get(str(anahtar)) or {}).get("g"))
        if seviye < anahtar:
            break
    return bedel


def kalkan_bitisi(kayit):
    """Kalkanın bitiş zamanı: 1.4.07 kalkanı (shieldEndTime, istemcinin okuduğu; satın alınan) ile sunucunun yeni
    oyuncu kalkanının (shield_until) sonraki (KYT-03: iki kalkan tek kalkan sayılır)."""
    ps = (kayit or {}).get("privateState", {})
    return max(_tam(ps.get("shieldEndTime")), _tam(ps.get("shield_until")))


def kalkan_aktif(kayit, simdi=None):
    return kalkan_bitisi(kayit) > (timestamp_now() if simdi is None else simdi)


def _bot_mu(kayit):
    return bool((kayit or {}).get("playerInfo", {}).get("bot"))


def rakip_sec(oyuncu, rastgele=random):
    """Saldırılabilir bir bot: kalkansız, son 4 saatte saldırılmamış; seviyesi oyuncuya en yakın olanlardan."""
    simdi = timestamp_now()
    seviye = _tam(oyuncu["maps"][0].get("level"), 1)
    son = {str(a.get("victim_id")) for a in oyuncu.get("privateState", {}).get("attacksSent", [])
           if isinstance(a, dict) and simdi - _tam(a.get("time")) < AYNI_HEDEF_SURESI}
    adaylar = []
    for uid in all_saves_userid():
        kayit = neighbor_session(uid)
        if not _bot_mu(kayit) or uid in son or kalkan_aktif(kayit, simdi):
            continue
        adaylar.append((abs(_tam(kayit["maps"][0].get("level"), 1) - seviye), uid))
    if not adaylar:
        return None
    adaylar.sort()
    en_yakin = [uid for fark, uid in adaylar[:5]]  # aynı rakip hep çıkmasın
    return rastgele.choice(en_yakin)


def saldirilabilir_mi(uid):
    kayit = neighbor_session(str(uid))
    return kayit is not None and not kalkan_aktif(kayit)


# --- komutlar (oyun.komutlar kaydeder) ---

def arama(save, a, kaynak_ekle):
    """get_enemy_new [bedel, aramaSayisi]: istemci bedeli kendisi düşer; sunucu kendi formülüyle düşer."""
    h = save["maps"][0]
    bedel = arama_bedeli(_tam(h.get("level"), 1))
    if bedel != a.tam(0):
        print(f" ! get_enemy_new: istemci bedeli {a.tam(0)}, sunucu {bedel} (sunucunun hesabı kullanildi)")
    kaynak_ekle(save, h, "g", -bedel)


def saldiri_basladi(save, a):
    """begin_attack_new [zaman]: saldıranın kalkanı kalkar (ShieldManager.removeShields)."""
    ps = save["privateState"]
    ps["shieldEndTime"] = 0
    ps["shield_until"] = 0  # KYT-03: saldıran yeni oyuncu korumasını da bırakır


def kalkan_sifirla(save, a):
    """reset_shield []: argümansız ve üç yerden gelir (saldırı başı, kalkan bitişi, bekleme bitişi); sunucu yalnızca
    süresi dolmuş alanları temizler. Saldırı başındaki kalkanı begin_attack_new kaldırır (aynı pakette)."""
    ps = save["privateState"]
    simdi = timestamp_now()
    if _tam(ps.get("shieldEndTime")) <= simdi:
        ps["shieldEndTime"] = 0
    if _tam(ps.get("shieldCooldown")) <= simdi:
        ps["shieldCooldown"] = 0
        ps["purchasedShields"] = []


def kalkan_al(save, a, kaynak_ekle):
    """buy_shield [kalkan_id]: istemcinin ShieldManager/buyShield hesabı."""
    kalkan_id = a.tam(0)
    kalkan = next((k for k in get_game_config().get("pvp_shields", []) if _tam(k.get("id")) == kalkan_id), None)
    ps = save["privateState"]
    alinan = ps.get("purchasedShields") if isinstance(ps.get("purchasedShields"), list) else []
    if kalkan is None or kalkan_id in alinan:  # ShieldManager.isShieldAvailable: alınan yeniden alınamaz
        print(f" ! buy_shield: kalkan {kalkan_id} yok ya da zaten alinmis")
        return
    kaynak_ekle(save, save["maps"][0], kalkan.get("price_type", "c"), -_tam(kalkan.get("price")))
    simdi = timestamp_now()
    bitis = _tam(ps.get("shieldEndTime"))
    ps["shieldEndTime"] = (simdi if bitis <= 0 else bitis) + _tam(kalkan.get("protection_time"))
    ps["shieldCooldown"] = simdi + _tam(kalkan.get("cooldown"))
    ps["purchasedShields"] = alinan + [kalkan_id]
