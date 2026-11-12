import copy
import datetime
import json
import random
import os
import time
import jsonpatch
from oyun.yollar import MODS_DIR, CONFIG_DIR, CONFIG_PATCH_DIR, json_oku
from oyun.zaman import metin as sure_metni, olcekle, zaman_olcegi
from oyun.turkce import turkce_uygula, ascii_uygula

__game_config = json_oku(os.path.join(CONFIG_DIR, "game_config_20120826.json"))

def remove_duplicate_items():
    indexes = {}
    items = __game_config["items"]
    num_duplicate = 0

    while True:
        index = 0
        duplicate = False
        for item in items:
            if item["id"] in indexes:
                del items[indexes[item["id"]]]
                indexes.clear()
                duplicate = True
                num_duplicate += 1
                break

            indexes[item["id"]] = index
            index += 1

        if duplicate:
            continue
        
        if num_duplicate:
            print(f" * Removed {num_duplicate} duplicate items from config patches")
        break

def apply_config_patch(filename):
    patch = json_oku(filename)
    jsonpatch.apply_patch(__game_config, patch, in_place=True)

def mod_listesi(klasor):
    """mods.txt'teki modlar sırayla: [(ad, yol)]. '#' satırı ve boş satır atlanır; '.json' yazılmışsa ayıklanır
    (denetim EKF-06: replace'in sonucu atılıyordu, 'x.json' satırı 'x.json.json' arıyordu)."""
    try:
        with open(os.path.join(klasor, "mods.txt"), encoding="utf-8-sig") as f:
            satirlar = f.read().splitlines()
    except OSError:
        return []
    sonuc = []
    for satir in satirlar:
        mod = satir.strip()
        if not mod or mod.startswith("#"):
            continue
        mod = mod.removesuffix(".json")
        sonuc.append((mod, os.path.join(klasor, mod + ".json")))
    return sonuc


def patch_game_config():

    # Apply patches

    for patch_file in sorted(os.listdir(CONFIG_PATCH_DIR)):  # her sistemde aynı sıra
        if patch_file.endswith(".json"):
            f = os.path.join(CONFIG_PATCH_DIR, patch_file)
            apply_config_patch(f)
            patch = patch_file.replace(".json", "")
            print(" * Patch applied:", patch)

    # Apply mods

    for mod, mod_path in mod_listesi(MODS_DIR):
        if os.path.exists(mod_path):
            apply_config_patch(mod_path)
            print(" * Mod applied:", mod)
        else:
            print(f" ! Mod bulunamadi: {mod_path}")

    remove_duplicate_items()
    hedefleri_ekle()
    tema_setlerini_ac()


def hedefleri_ekle():
    """config/goals.json'u 1.4.07'nin okuduğu `goals` listesi yapar (GEC-02).

    Hedeflerin resimleri ve karakterleri config'in `images` listesinde yoksa eklenir ki istemci
    onları da yüklesin. "none" resim yok demektir.
    """
    yol = os.path.join(CONFIG_DIR, "goals.json")
    if not os.path.exists(yol):
        return
    hedefler = json_oku(yol)
    resimler = __game_config["images"]
    for hedef in hedefler:
        for ad in (hedef.get("image"), hedef.get("characters")):
            if ad and ad != "none" and ad not in resimler:
                resimler[ad] = ""
    from oyun import hedef_seviye
    # DNT-51: istemci min_level'e bakmaz, order'la sıralar; seviyeler istemcinin açılış seviyelerine göre düzeltilir
    __game_config["goals"] = hedef_seviye.duzenle(hedefler, __game_config.get("items", []),
                                                 __game_config.get("globals", {}))
    print(f" * Hedefler yuklendi: {len(hedefler)}")


def tema_setleri():
    """{set adı: [eşya kimlikleri]} (config/tema_setleri.json)."""
    yol = os.path.join(CONFIG_DIR, "tema_setleri.json")
    if not os.path.exists(yol):
        return {}
    with open(yol, encoding="utf-8") as f:
        return json.load(f)["setler"]


def tema_seti_kipi():
    """ayarlar.json -> magaza_tema_setleri: True (hepsi açık), False ya da "takvim"."""
    from oyun import ayarlar
    return ayarlar.oku().get("magaza_tema_setleri", True)


def takvimdeki_setler():
    """Takvim kipinde bugün mağazada açık olacak eşya kimlikleri (kipi kapalıysa None)."""
    if tema_seti_kipi() != "takvim":
        return None
    from oyun import takvim
    setler = tema_setleri()
    return frozenset(str(i) for ad in takvim.acik_setler() for i in setler.get(ad, []))


# ONR-04 (sahibinin kararı, 11.11.2026: "Milli bayramlarda"): oyunun kendi Türk birimleri (config: Turkish Swordsman,
# Axeman, Archer, Horseman; in_store 0, mağaza kategorisi 7, nakitle) yalnızca milli bayram günlerinde (config/takvim.json
# bayrak: true; takvim.milli_bayram) mağazada açılır. Mağaza kipinden bağımsızdır; sunucu satın almada in_store'a bakmaz.
TURK_BIRIMLERI = ("880", "881", "882", "885")


def tema_setlerini_ac():
    """config/tema_setleri.json'daki etkinlik setlerini mağazaya açar.

    "takvim" kipinde setler burada değil, istemciye gönderilirken o günün
    etkinliğine göre açılır (get_client_game_config).
    """
    if tema_seti_kipi() is not True:
        return
    kimlikler = {str(i) for ids in tema_setleri().values() for i in ids}
    acilan = 0
    for esya in __game_config["items"]:
        if esya["id"] in kimlikler and esya.get("in_store") != "1":
            esya["in_store"] = "1"
            acilan += 1
    print(f" * Tema setleri magazaya acildi: {acilan} esya")

print (" [+] Applying config patches and mods...")
patch_game_config()

def get_game_config() -> dict:
    return __game_config


# İstemciye gönderilen, zaman ölçeği uygulanmış config önbelleği.
__istemci_config_onbellegi = {}

# İstemcinin süre olarak okuduğu alanlar.
SURE_ALANLARI = ("activation", "expiration", "training_time", "sm_training_time")


KOMPU_DONEMI = 30 * 86400


def kompu_teklifi(simdi=None):
    """Büyücü iksirleri teklifi: her 30 günlük dönem yeni bir teklif (id = dönem no).

    Dönem dolunca oyuncu yeniden baştan iksir toplayabilir.
    """
    teklifler = __game_config.get("kompu_offers") or []
    if not teklifler:
        return None
    simdi = int(time.time()) if simdi is None else simdi
    teklif = dict(teklifler[0])
    teklif["id"] = simdi // KOMPU_DONEMI
    teklif["starts_at"] = teklif["id"] * KOMPU_DONEMI
    teklif["duration"] = KOMPU_DONEMI
    return teklif


# Sahibinin isteği (12.11.2026): mağazadaki "SINIRLI, SON 0 GÜN" öğesi süresi bitince gitsin, ertesi gün rastgele başkası
# gelsin. İstemci: ItemButtonLarge/setItem, subcategory_id == Subcat.LIMITED_EDITION (121) ise rozet çıkar ve yazı
# Base/getLimitedDaysLeft = max(0, ceil((globals.LIMITED_EDITION_EXPIRATION - lastServerTimestamp) / 86400)) olur;
# Utils$/getTimeStampFromString "YYYY-AA-GG"yi new Date(y, a - 1, g) ile oyuncunun yerel gece yarısı okur. Config'te
# tarih 2012-09-14 (hep 0 gün). Her gün havuzdan bir öğe açılır, tarih yarın olur: "SON 1 GÜN".
SINIRLI_ALTKATEGORI = "121"
SINIRLI_HAVUZ_DISI = ("Harikalar",)  # tema seti her zaman açık, sınırlı değil


def sinirli_havuz():
    """Günlük sınırlı öğe havuzu: tema setlerindeki sınırlı öğeler (Harikalar dışında) ve config'te zaten mağazada
    olan sınırlı öğe (1299 Nakit Harikası). Sıra sabit karıştırılır, her gün sıradaki gelir: iki gün üst üste aynı
    öğe gelmez, havuz bitmeden öğe tekrarlanmaz."""
    esyalar = {e["id"]: e for e in __game_config["items"]}
    kimlikler = {str(i) for ad, ids in tema_setleri().items() if ad not in SINIRLI_HAVUZ_DISI for i in ids}
    kimlikler |= {e["id"] for e in __game_config["items"]
                  if e.get("subcategory_id") == SINIRLI_ALTKATEGORI and e.get("in_store") == "1"}
    havuz = sorted((k for k in kimlikler if esyalar.get(k, {}).get("subcategory_id") == SINIRLI_ALTKATEGORI), key=int)
    random.Random(SINIRLI_ALTKATEGORI).shuffle(havuz)
    return havuz


def yerel_bugun():
    """Oyuncunun bilgisayarındaki tarih: istemci bitiş tarihini yerel gece yarısı okur (sunucu aynı cihazda)."""
    return datetime.date.today()


KAYNAK_BAYRAGI = "NUM_TREE_CLUSTERS"  # istemcide globals'tan okunan ad (oyun/swf_yama.py KAYNAK_YAMALARI)


def gunun_sinirli_esyasi(bugun=None, acik=frozenset()):
    """(eşya kimliği, bitiş tarihi "YYYY-AA-GG"): bugünün sınırlı öğesi; takvimde zaten açık olanlar atlanır."""
    bugun = bugun or yerel_bugun()
    havuz = sinirli_havuz()
    if not havuz:
        return None, (bugun + datetime.timedelta(days=1)).isoformat()
    # Takvimde zaten açık olanlar havuzdan çıkarılıp sıra kalanlarda döner: etkinlik günlerinde de her gün başka öğe
    # (açıkları atlayıp aynı sırada ilerlemek aynı öğeyi günlerce seçerdi; #81 incelemesi)
    kalan = [k for k in havuz if k not in acik] or havuz
    secilen = kalan[bugun.toordinal() % len(kalan)]
    return secilen, (bugun + datetime.timedelta(days=1)).isoformat()


ADA_ODUL_TEKLIFI = 2  # Ada Ocağı'nın boru malzemesi ve ödülü viral teklif 2'den (CollectGameManager/giveReward)


def teklif_pencereleri(seviye=None, gun=None):
    """{("ada", 1) | ("viral", no): (starts_at, duration)}: bugün açık özel teklifler (KAR-34, sahibi 12.11.2026:
    "Kademeli, 15'ten başlayıp" ve "Evet, takvime bağla"). Yalnızca config/takvim.json teklifler'de bugün süren ve
    oyuncunun seviyesinin yettiği teklif açılır (seviye bilinmiyorsa yalnızca takvim). Pencere takvim gününün Türkiye
    saatiyle başı ve sonu. İstemci: CollectGameManager/get active şimdi > starts_at ve şimdi < starts_at + duration;
    SpecialDayOfferManager/timeLeft int(starts_at + duration - şimdi) > 0. Ada açıksa ödül teklifi 2 de açılır."""
    from oyun import takvim
    pencereler = {}
    for t in takvim.teklifler(gun, ileri=0):
        if not t["aktif"] or (seviye is not None and seviye < t["seviye"]):
            continue
        bas, bit = (int(datetime.datetime.combine(datetime.date.fromisoformat(t[k]), datetime.time(),
                                                  takvim.TURKIYE).timestamp()) for k in ("baslangic", "bitis"))
        pencereler[(t["tur"], t["no"])] = (bas, bit - bas)
        if t["tur"] == "ada":
            pencereler[("viral", ADA_ODUL_TEKLIFI)] = (bas, bit - bas)
    return pencereler


def get_client_game_config(dil: str = "en", ascii_mode: bool = False, seviye: int = None,
                            kaynak_yenile: bool = True) -> dict:
    """İstemciye gönderilecek config'i döndürür.

    - `dil` "tr" ise metinler Türkçeleştirilir (ceviri/tr.json).
    - Zaman ölçeği 1.0 değilse eşyaların süre alanları ölçeğe bölünür.
    - `seviye` verilirse yalnızca o seviyeye gelmiş hedefler gider (DNT-51; istemci min_level'e bakmaz).
    - `kaynak_yenile` False ise istemci kendi köyünde ağaç, taş ve altını yenilemez (globals.NUM_TREE_CLUSTERS 0;
      oyun/swf_yama.py kaynaklari_gunde_bir). Yamalı istemci bayrağı bulamazsa yenilemez: her config onu taşır.
    Sunucunun kullandığı asıl config ve kayıtlar değiştirilmez.
    """
    olcek = zaman_olcegi()
    dil = (dil or "en").lower()[:2]
    teklif = kompu_teklifi()
    takvim_setleri = takvimdeki_setler()
    from oyun import bayram_hedefleri
    # GEC-07: metinler Türkçe yazılı; İngilizce config'e gitmez (#56 incelemesi)
    bayram = bayram_hedefleri.aktif_hedefler() if dil == "tr" else []
    from oyun import takvim
    milli = takvim.milli_bayram()
    pencere = tuple(sorted(teklif_pencereleri(seviye).items()))
    sinirli = gunun_sinirli_esyasi(acik=takvim_setleri or frozenset())
    anahtar = (dil, olcek, bool(ascii_mode), teklif and teklif["id"], takvim_setleri,
               tuple(h["id"] for h in bayram), milli, pencere, seviye, sinirli, bool(kaynak_yenile))
    if anahtar in __istemci_config_onbellegi:
        return __istemci_config_onbellegi[anahtar]

    if dil == "tr":
        kopya = turkce_uygula(__game_config)
    else:
        kopya = copy.deepcopy(__game_config)
    if bayram:  # GEC-07: süren etkinliklerin hedefleri (metinleri Türkçe yazılı; ASCII kipinde aşağıda çevrilir).
        # Resimleri goals.json'daki bir hedefinkidir; hedefleri_ekle onları zaten `images`'a koyar.
        kopya["goals"] = list(kopya.get("goals", [])) + bayram
    if seviye is not None:
        from oyun import hedef_seviye
        kopya["goals"] = hedef_seviye.seviyeye_gore(kopya.get("goals", []), seviye)
    if dil == "tr" and ascii_mode:
        kopya = ascii_uygula(kopya)
    if teklif:
        kopya["kompu_offers"] = [teklif]
    acik_teklifler = dict(pencere)
    for tur, alan in (("ada", "collect_game"), ("viral", "viral_offers")):
        for no, etkinlik in (kopya.get(alan) or {}).items():
            if isinstance(etkinlik, dict):
                etkinlik["starts_at"], etkinlik["duration"] = acik_teklifler.get((tur, int(no)), (0, 0))
    if takvim_setleri:
        for esya in kopya.get("items", []):
            if esya["id"] in takvim_setleri:
                esya["in_store"] = "1"
    sinirli_id, bitis = sinirli
    kopya.setdefault("globals", {})["LIMITED_EDITION_EXPIRATION"] = bitis
    kopya["globals"][KAYNAK_BAYRAGI] = 1 if kaynak_yenile else 0
    # Yalnızca "takvim" kipinde döner: "hepsi açık" (True) kipinde sınırlı öğeler zaten mağazada, "hiçbiri" (False)
    # kipinde tema seti öğesi mağazaya hiç açılmaz (ayarlar.json _magaza_tema_setleri; #81 incelemesi)
    if tema_seti_kipi() == "takvim":
        for esya in kopya.get("items", []):
            if esya.get("subcategory_id") != SINIRLI_ALTKATEGORI:
                continue
            if esya["id"] == sinirli_id:
                esya["in_store"] = "1"
            elif esya.get("in_store") == "1" and esya["id"] not in (takvim_setleri or ()):
                esya["in_store"] = "0"  # dünkü sınırlı öğe gider
    if milli:
        for esya in kopya.get("items", []):
            if esya["id"] in TURK_BIRIMLERI:
                esya["in_store"] = "1"

    if olcek != 1.0:
        for esya in kopya.get("items", []):
            for alan in SURE_ALANLARI:
                deger = esya.get(alan)
                if deger is None:
                    continue
                try:
                    sayi = float(deger)
                except (TypeError, ValueError):
                    continue
                if sayi > 0:
                    esya[alan] = sure_metni(olcekle(sayi, olcek))
        print(f" [+] Zaman olcegi {olcek}: uretim/insaat sureleri {olcek} kat kisaltildi")

    __istemci_config_onbellegi.clear()
    __istemci_config_onbellegi[anahtar] = kopya
    return kopya


def game_config() -> dict:
    return get_game_config()

##########
# PLAYER #
##########

# Seviye eşiklerinin tek okuması (OYN-14). İstemci (1.4.07) `levels[i].exp_required`'ı (i+1). seviyenin eşiği
# sayar: PlayerStatus/checkForLevelUp `iExperience >= arLevelList[iLevel].exp_required` ise iLevel'ı bir artırır;
# PlayerStatus/Init XP çubuğunu `arLevelList[iLevel - 1]` ile `arLevelList[iLevel]` arasında çizer ve
# `iLevel >= arLevelList.length` ise `length - 1`'e indirir. Seviyeyle XP arasında çeviri yapan her yer bu dört
# işlevi kullanır; `levels[...]` doğrudan okunmaz.

def en_yuksek_seviye() -> int:
    """İstemcinin kabul ettiği en yüksek seviye (PlayerStatus/Init: length - 1)."""
    return max(1, len(__game_config["levels"]) - 1)

def _seviye_sinirla(level) -> int:
    return max(1, min(int(level), en_yuksek_seviye()))

def get_xp_from_level(level: int) -> int:
    """Seviyenin alt eşiği: o seviyede olmak için gereken en az XP (`levels[seviye - 1]`)."""
    return int(__game_config["levels"][_seviye_sinirla(level) - 1]["exp_required"])

def seviye_araligi(level: int) -> tuple:
    """İstemcinin XP çubuğu (uiExpMin, uiExpMax): (`levels[seviye - 1]`, `levels[seviye]`)."""
    seviyeler = __game_config["levels"]
    sv = _seviye_sinirla(level)
    bas = int(seviyeler[sv - 1]["exp_required"])
    return bas, int(seviyeler[sv]["exp_required"]) if sv < len(seviyeler) else bas

def get_level_from_xp(xp: int) -> int:
    seviyeler = __game_config["levels"]
    if not seviyeler:
        return 0
    i = 0
    for lvl in seviyeler:
        if lvl["exp_required"] > int(xp):
            return i
        i += 1
    # XP tüm eşikleri aştıysa son seviye döner (eskiden 0 dönüyordu ve
    # bozuk bir XP değeri oyuncuyu 0. seviyeye düşürüyordu).
    return len(seviyeler) - 1

#########
# ITEMS #
#########

# ID

items_dict_id_to_items_index = {int(item["id"]): i for i, item in enumerate(__game_config["items"])}

def get_item_from_id(id: int) -> dict:
    items_index = items_dict_id_to_items_index[int(id)] if int(id) in items_dict_id_to_items_index else None
    return __game_config["items"][items_index] if items_index is not None else None

def get_attribute_from_item_id(id: int, attribute_name: str) -> str:
    item = get_item_from_id(id)
    return item[attribute_name] if item and attribute_name in item else None

def get_name_from_item_id(id: int) -> str:
    return get_attribute_from_item_id(id, "name")

# subcat_functional

items_dict_subcat_functional_to_items_index = {int(item["subcat_functional"]): i for i, item in enumerate(__game_config["items"])}

def get_item_from_subcat_functional(subcat_functional: int) -> dict:
    items_index = items_dict_subcat_functional_to_items_index[int(subcat_functional)] if int(subcat_functional) in items_dict_subcat_functional_to_items_index else None
    return __game_config["items"][items_index] if items_index is not None else None

############
# MISSIONS #
############

missions_dict_id_to_missions_index = {int(item["id"]): i for i, item in enumerate(__game_config["missions"])}

def get_mission_from_id(id: int) -> dict:
    items_index = missions_dict_id_to_missions_index[int(id)] if int(id) in missions_dict_id_to_missions_index else None
    return __game_config["missions"][items_index] if items_index is not None else None

def get_attribute_from_mission_id(id: int, attribute_name: str) -> str:
    mission = get_mission_from_id(id)
    return mission[attribute_name] if mission and attribute_name in mission else None