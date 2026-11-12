"""Hedeflerin açılış seviyesi ve sırası (DNT-51).

1.4.07 istemcisi hedefte min_level'e hiç bakmaz: GoalsManager/checkAllGoals @50-276 hedefleri `order`
(AbstractGoal/<kurucu> @49-60: parseInt(orders)) farkıyla sıralar, ödülü alınmamış ilk MAX_ACTIVE_GOALS (15) hedefi
gösterir; GoalsManager/isGoalAvailable her zaman true döner. config/goals.json (GEC-02, upstream) ise 206 hedefin
195'inde min_level 1, hepsinde orders 1 taşır: saldırı hedefi PvP açılmadan çıkar, bayram hedefleri (orders -1)
en başa geçerdi.

Sunucu bu yüzden:
- her hedefin seviyesini, istediği özelliğin istemcideki açılış seviyesiyle yükseltir (Config sabitleri, eşyaların
  min_level'i; asla düşürmez),
- `orders`'ı dosyadaki sıraya göre 1, 2, 3... yazar (eşit order'lı sıralama istemcide kararsız),
- istemciye yalnızca oyuncunun seviyesine gelmiş hedefleri yollar (oyun/config.py get_client_game_config).
"""

# Config/<sınıf> (1.4.07 bayt kodu): özelliklerin açılış seviyeleri
MIN_LEVEL_PVP = 8
MIN_LEVEL_QUESTS = 6
MIN_LEVEL_TOURNAMENT = 15
MIN_LEVEL_SURVIVAL = 20

TUR_SEVIYESI = {
    "attack_player": MIN_LEVEL_PVP,
    "assaults_won": MIN_LEVEL_QUESTS,  # Assault: görev adası ve PvP saldırısı; ikisinin erkeni
    "complete_quest": MIN_LEVEL_QUESTS,
    "popup_opened_quests": MIN_LEVEL_QUESTS,
}


def _sayi(deger, varsayilan=0):
    try:
        return int(deger)
    except (TypeError, ValueError):
        return varsayilan


def _kimlikler(params):
    ids = params.get("ids")
    if isinstance(ids, list):
        return [i for i in ids if _sayi(i, None) is not None]
    if params.get("id") is not None and _sayi(params.get("id"), -1) >= 0:
        return [params["id"]]
    return []


def gerekli_seviye(hedef, esyalar, alt_kategoriler, globals_):
    """Hedefin istemcide yapılabildiği en düşük seviye (en az config'teki min_level)."""
    import json
    seviye = _sayi(hedef.get("min_level"), 1) or 1
    tur = hedef.get("types")
    try:
        params = json.loads(hedef.get("params") or "{}")
    except ValueError:
        params = {}
    if not isinstance(params, dict):
        params = {}
    seviye = max(seviye, TUR_SEVIYESI.get(tur, 1))
    if tur == "recruit_market_friend":  # pazar binası (SUBCATFUNC_BUILDING_MARKET 132)
        seviye = max(seviye, alt_kategoriler.get("132", 1))
    if tur == "soulmixer_mix_unit":
        seviye = max(seviye, _sayi(globals_.get("SOUL_MIXER_MIN_LEVEL"), 1))
    if tur == "complete_quest":
        seviye = max(seviye, _sayi((globals_.get("QUESTS_MIN_LEVELS") or {}).get(str(params.get("id"))), 1))

    def esya_seviyesi(kimlikler):
        # Listedeki eşyalardan biri yeter: en düşüğü
        seviyeler = [_sayi((esyalar.get(str(k)) or {}).get("min_level"), 1) for k in kimlikler if str(k) in esyalar]
        return min(seviyeler) if seviyeler else 1

    if tur in ("built_subcatfunc", "collected_subcatfunc", "contained_subcatfunc", "select_time_subcatfunc",
               "pop_unit_subcatfunc", "complete_social_subcat"):
        seviye = max(seviye, alt_kategoriler.get(str(params.get("id")), 1))
        if params.get("building_subcat") is not None:
            seviye = max(seviye, alt_kategoriler.get(str(params.get("building_subcat")), 1))
    elif tur in ("built_id", "contained_id", "collected_id", "trained_id", "select_time_id", "complete_social_id",
                 "train_ids_in_id"):
        seviye = max(seviye, esya_seviyesi(_kimlikler(params)))
        if _sayi(params.get("building_id"), -1) > 0:
            seviye = max(seviye, esya_seviyesi([params["building_id"]]))
    return seviye


def duzenle(hedefler, esyalar_listesi, globals_):
    """Hedeflerin kopyası: min_level istemciye göre yükseltilmiş, orders dosya sırasında 1, 2, 3..."""
    esyalar = {str(e.get("id")): e for e in esyalar_listesi}
    alt_kategoriler = {}
    for e in esyalar_listesi:
        alt = str(e.get("subcat_functional"))
        sv = _sayi(e.get("min_level"), 1) or 1
        alt_kategoriler[alt] = min(alt_kategoriler.get(alt, sv), sv)
    sonuc = []
    for sira, hedef in enumerate(hedefler, start=1):
        yeni = dict(hedef)
        if _sayi(hedef.get("orders"), 0) != 0:  # orders 0 istemcide atlanır (GoalsManager/_load @64-70): korunur
            yeni["orders"] = sira
        yeni["min_level"] = gerekli_seviye(hedef, esyalar, alt_kategoriler, globals_)
        sonuc.append(yeni)
    return sonuc


def seviyeye_gore(hedefler, seviye):
    """Oyuncunun seviyesine gelmiş hedefler."""
    return [h for h in hedefler if _sayi(h.get("min_level"), 1) <= seviye]
