"""1.4.07'nin 5 günlük günlük ödülü (OYN-11, KYT-02, KAR-24): ödülü sunucu verir, pencere yalnızca takvimi gösterir.

İstemcinin kuralları (bayt kodu; ayrıntı docs/inceleme/1407-gunluk-odul.md):
- DailyBonusManager/initPlayerData@56-142: pencere (showDailyBonus || lastDayRewarded == 0) && !tutorialMode ise açılır.
  Alanlar get_player_info yanıtının privateState'inden okunur (Base/loadPlayerInfoSuccess); showDailyBonus == 1.
- PopupNewDailyBonus/init@754-797: o günün ödülü (_currentReward) day == numDaysLogged ve
  numDaysLogged != lastDayRewarded olan kayıttır; yalnızca o zaman giveReward çağrılır (@1077-1086).
- DailyBonusManager/giveReward: birim için store_add_items yollar; kaynak, nakit ve iksiri yalnızca ekranda ekler
  (kayda gitmez); day == 1 ise hiçbir şey vermez. lastDayRewarded sunucuya hiç bildirilmez.

Bu yüzden önce (lastDayRewarded kayıtta hiç yokken, yani hep 0) pencere her girişte açılıyor ve 2. ile 5. günün birimi
her açılışta yeniden veriliyordu; kaynak, nakit ve iksir ise hiç kalıcı olmuyordu.

Sahibinin kararı (KAR-24, 11.11.2026): ödülü sunucu verir; 5. günden sonra pencere açılmaz (oyunun tablosu 5 gün,
istemcide döngü yok). Her yeni giriş gününün ilk get_player_info'sunda o günün ödülü bir kez kayda yazılır,
lastDayRewarded = numDayLogged olur. Yanıt o gün pencereyi açar (showDailyBonus 1; yalnızca yanıtta, kayda yazılmaz);
lastDayRewarded == numDayLogged olduğundan istemci ödülü bir kez daha vermez.
"""

from oyun.config import get_game_config


def tablo():
    """config `daily_bonus`: [{id, reward_day, reward: {g|w|f|s|c|p|u: değer}, img}] (Base/loadGameConfigSuccess)."""
    return get_game_config().get("daily_bonus") or []


def _ver(kayit, odul):
    from oyun.komutlar import _tur_deger_odulu
    harita = kayit["maps"][0]
    for tur, deger in (odul or {}).items():
        if tur == "p":  # iksir (DailyBonusManager/givePotions; privateState.potion, graveyard_buy_potions ile aynı)
            kayit["privateState"]["potion"] = int(kayit["privateState"].get("potion", 0) or 0) + int(deger)
        else:
            _tur_deger_odulu(kayit, harita, tur, deger)


def isle(kayit):
    """get_player_info'da, giris_gunu_say'dan sonra. Pencere bugün açılacaksa True (ödül o anda verildi)."""
    ps = kayit["privateState"]
    gun = int(ps.get("numDayLogged") or 1)
    son = ps.get("lastDayRewarded")
    son = son if isinstance(son, int) else 0
    if gun <= son:
        return False
    ps["lastDayRewarded"] = gun  # 5. günden sonra da: pencere (lastDayRewarded == 0 koşuluyla) bir daha açılmaz
    kaydi = next((t for t in tablo() if int(t.get("reward_day", 0)) == gun), None)
    if kaydi is None:
        return False
    _ver(kayit, kaydi.get("reward"))
    return True
