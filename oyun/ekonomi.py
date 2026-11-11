import time

from oyun.config import get_attribute_from_item_id

class Yetersiz(Exception):
    """Bedel bakiyeyi aşıyor (KAR-18): komut uygulanmaz, kayıt komuttan önceki hâline döner (komutlar.command)."""


def bakiyeden_dus(kap: dict, alan: str, bedel: int) -> None:
    """kap[alan] -= bedel. Bedel bakiyeyi aşarsa Yetersiz; eksi bedel (iade) eklenir. Bakiye eksiye düşmez."""
    bakiye = int(kap.get(alan, 0) or 0)
    if bedel > 0 and bakiye < bedel:
        raise Yetersiz(f"{alan}: {bakiye} < {bedel}")
    kap[alan] = max(0, bakiye - bedel)


def apply_cost(playerInfo: dict, map: dict, id: int, price_multiplier: int) -> None:
    """Bedel; eksi çarpan hiçbir durumda kabul edilmez (iade ayrı yoldan: komutlar.satis_iadesi, #46 incelemesi)."""
    if price_multiplier < 0:
        raise Yetersiz(f"eksi fiyat carpani {price_multiplier}")
    cost = int(price_multiplier * int(get_attribute_from_item_id(id, "cost")))
    cost_type = get_attribute_from_item_id(id, "cost_type")
    alan = {"w": "wood", "g": "coins", "s": "stone", "f": "food"}.get(cost_type)
    if alan:
        bakiyeden_dus(map, alan, cost)
    elif cost_type == "c":
        bakiyeden_dus(playerInfo, "cash", cost)


def apply_collect(playerInfo: dict, map: dict, id: int, resource_multiplier: int, miktar: int = None) -> None:
    collect = int(resource_multiplier * int(get_attribute_from_item_id(id, "collect"))) if miktar is None else miktar
    collect_type = get_attribute_from_item_id(id, "collect_type")
    apply_collect_xp(map, id)
    if collect_type == "w":
        map["wood"] = map["wood"] + collect
    elif collect_type == "g":
        map["coins"] = map["coins"] + collect
    elif collect_type == "c":
        playerInfo["cash"] = playerInfo["cash"] + collect
    elif collect_type == "s":
        map["stone"] = map["stone"] + collect
    elif collect_type == "f":
        map["food"] = map["food"] + collect

def apply_collect_xp(map: dict, id: int) -> None:
    collect_xp = int(get_attribute_from_item_id(id, "collect_xp"))
    map["xp"] = map["xp"] + collect_xp

def timestamp_now() -> int:
    return int(time.time())