"""Yol haritası 2 için ölçümler: her sayı bu betikten gelir (docs/YOL_HARITASI_2.md).

Hiçbir dosya yazmaz; geçici bir kayıt dizininde (SE_KAYIT_DIZINI) yeni bir köy açıp sunucunun uçlarını çağırır.

    python araclar/yol_haritasi_olcum.py [istemci.swf] [--json]

İstemci verilmezse download_assets/assets/flash/SocialEmpires1.4.07sec_fixed.swf okunur.

Bölümler (YOL_HARITASI_2.md §1 ile aynı sıra):
 1. komut kapsamı: istemcinin addCommand ile gönderdiği komutlar (araclar/komut_imzalari.py) ve çalışan sunucunun
    KOMUTLAR sözlüğü (oyun/komutlar.py @komut; aynı ad iki kez kaydedilirse SONUNCUSU geçer: KOMUTLAR[ad] = fonksiyon).
    "boş" = işleyicinin gövdesi belge dizesi dışında yalnızca pass/return; bilinmeyen komut do_command'da günlüğe düşer.
 2. ayrı HTTP uçları: istemcinin dize havuzundaki .php ve app.php/... yolları ile Flask kuralları; eşleşen uç test
    istemcisiyle çağrılır, cevap boyutu ve biçimi yazılır.
 3. kapalı sistemler: istemcinin Base.Items.globals'tan okuduğu anahtarlar (getproperty globals ardından gelen ad) ile
    istemciye giden config'in globals'ı; Config sınıfının false olan özellik bayrakları.
 4. varlık tamlığı: istemci dizelerindeki dosya yolları; download_assets/assets altında ve config/onindirme.tsv'de olup
    olmadığı. Birleştirilerek kurulan yollar düz dize olmadığı için sayılmaz (sınır).
 5. döngü: dünya simülasyonunun ayarları (ayarlar.json dunya) ve kaynak giriş-çıkışı.
 6. ekonomi: config eşyalarının collect/activation değerleri, zaman ölçeğiyle saatlik verim; seviye xp tablosu.
 7. kendi sistemlerimizin sağlığı: modül başına test sayısı ve açık bulgular.
"""

import ast
import inspect
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
sys.path.insert(0, os.path.join(KOK, "araclar"))
os.environ.setdefault("SE_KAYIT_DIZINI", tempfile.mkdtemp(prefix="se-olcum-"))

import abc_okur  # noqa: E402
import komut_imzalari  # noqa: E402

VARSAYILAN_SWF = os.path.join(KOK, "download_assets", "assets", "flash", "SocialEmpires1.4.07sec_fixed.swf")


def _sessiz():
    """Sunucu içe aktarılırken bastığı satırları bastır."""
    import contextlib
    import io
    return contextlib.redirect_stdout(io.StringIO())


def abc_listesi(veri):
    return list(abc_okur.swf_abc(veri))


# --------------------------------------------------------------------------- 1. komutlar

def _bos_mu(fonksiyon):
    try:
        kaynak = inspect.getsource(fonksiyon)
    except (OSError, TypeError):
        return False
    agac = ast.parse(inspect.cleandoc("\n" + kaynak) if kaynak.startswith((" ", "\t")) else kaynak)
    islev = next(d for d in ast.walk(agac) if isinstance(d, ast.FunctionDef))
    govde = [d for d in islev.body
             if not (isinstance(d, ast.Expr) and isinstance(getattr(d, "value", None), ast.Constant)
                     and isinstance(d.value.value, str))]
    return all(isinstance(d, ast.Pass) or (isinstance(d, ast.Return) and d.value is None) for d in govde)


def _kayit_tekrarlari():
    """oyun/*.py'de @komut(...) ile kaydedilen adların kaç kez geçtiği (AST)."""
    sayac = Counter()
    yerler = defaultdict(list)
    dizin = os.path.join(KOK, "oyun")
    for ad in sorted(os.listdir(dizin)):
        if not ad.endswith(".py"):
            continue
        yol = os.path.join(dizin, ad)
        agac = ast.parse(open(yol, encoding="utf-8").read())
        for d in ast.walk(agac):
            if isinstance(d, ast.FunctionDef):
                for s in d.decorator_list:
                    if isinstance(s, ast.Call) and getattr(s.func, "id", None) == "komut":
                        for a in s.args:
                            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                                sayac[a.value] += 1
                                yerler[a.value].append(f"oyun/{ad}:{d.lineno} {d.name}")
    return {k: yerler[k] for k, n in sayac.items() if n > 1}


def komut_kapsami(veri):
    sonuc = komut_imzalari.istemci_komutlari(veri)
    istemci, cozulemeyen = sonuc["komutlar"], sonuc["cozulemeyen"]
    with _sessiz():
        import oyun.sunucu  # noqa: F401  (bütün @komut modülleri yüklenir)
        from oyun import komutlar
    gercek, bos, yok = [], [], []
    for ad in sorted(istemci):
        f = komutlar.KOMUTLAR.get(ad)
        if f is None:
            yok.append(ad)
        elif _bos_mu(f):
            bos.append((ad, f.__name__))
        else:
            gercek.append(ad)
    fazla = sorted(set(komutlar.KOMUTLAR) - set(istemci))
    return {"istemci_komut": len(istemci), "cozulemeyen_cagri": len(cozulemeyen), "gercek": len(gercek),
            "bos": bos, "isleyicisi_yok": yok, "sunucuda_fazla": fazla, "sunucu_kayit": len(komutlar.KOMUTLAR),
            "kayit_tekrari": _kayit_tekrarlari()}


# --------------------------------------------------------------------------- 2. HTTP uçları

UC_DESENI = re.compile(r"(?:[A-Za-z0-9_]+\.php(?:/[A-Za-z0-9_/]*)?)$|(?:^|/)(?:pvp|tournaments?|pool)/[A-Za-z0-9_/]+$")


def istemci_uclari(abcler):
    uclar = set()
    for a in abcler:
        for d in a.dizeler[1:]:
            if d and len(d) < 120 and " " not in d and UC_DESENI.search(d):
                uclar.add(d)
    return sorted(uclar)


def http_uclari(abcler):
    with _sessiz():
        from oyun import sunucu
        from oyun.kayit import new_village
        uid = new_village()
    app = sunucu.app
    from oyun.istemci import DINAMIK
    eslestir = app.url_map.bind("localhost")
    istemci = istemci_uclari(abcler)
    tarayici = app.test_client()
    with _sessiz():
        tarayici.post("/", data={"USERID": uid, "GAMEVERSION": "SocialEmpires1.4.07sec_fixed.swf"})
    sonuc = []
    for u in istemci:
        adres = DINAMIK + "/" + u.lstrip("/")
        try:
            kural, _ = eslestir.match(adres, method="POST", return_rule=True)
            es = kural.rule
        except Exception:
            es = None
        satir = {"uc": u, "sunucu": es}
        if es:
            with _sessiz():
                r = tarayici.post(adres, data={"USERID": uid, "user_id": uid})
            govde = r.get_data().decode("utf-8", "replace")
            if re.match(r"^[0-9a-f]{64};", govde):  # imzalı cevap: "<sha256>;<json>" (oyun/istemci.py imzali)
                govde = govde[65:]
            try:
                veri_ = json.loads(govde) if govde else None
            except ValueError:
                veri_ = govde
            # tür: "bos" (gövde yok, 4xx), "onay" (yalnızca sonuç: data {}, OK, true/false/0), "veri"
            ic = veri_.get("data", veri_) if isinstance(veri_, dict) else veri_
            if isinstance(ic, dict) and set(ic) == {"result"}:
                ic = ic["result"]
            if not govde or r.status_code >= 400:
                tur = "bos"
            elif ic in ({}, [], None, True, False, 0, "OK", "NOK", "NOTEAM", "success") or (
                    isinstance(veri_, dict) and set(veri_) == {"result"} and veri_["result"] in ("success", "ok")):
                tur = "onay"
            else:
                tur = "veri"
            satir.update(durum=r.status_code, bayt=len(govde), tur=tur, ornek=govde[:70])
        sonuc.append(satir)
    return {"istemci_uc": len(istemci), "eslesen": sum(1 for s in sonuc if s["sunucu"]),
                    "eslesmeyen": [s["uc"] for s in sonuc if not s["sunucu"]], "uclar": sonuc}


# --------------------------------------------------------------------------- 3. kapalı sistemler

def globals_okumalari(abcler):
    """{anahtar: {yöntem adı}}: kodda `getproperty globals` ardından gelen `getproperty X`."""
    okunan = defaultdict(set)
    boyut = {}
    for a in abcler:
        adlar = a.yontem_adlari()
        for i, g in a.govdeler.items():
            try:
                islemler = a.coz(g)
            except Exception:
                continue
            sira = [islemler[o] for o in sorted(islemler)]
            for k in range(len(sira) - 1):
                if sira[k].ad == "getproperty" and a.ad(sira[k].isl[0]) == "globals" and sira[k + 1].ad == "getproperty":
                    ad = a.ad(sira[k + 1].isl[0])
                    if ad not in ("*", "[]"):
                        okunan[ad].add(adlar.get(i, "yontem%d" % i))
                        boyut[adlar.get(i, "yontem%d" % i)] = len(g.kod)
    return okunan, boyut


def kapali_sistemler(abcler):
    okunan, boyut = globals_okumalari(abcler)
    with _sessiz():
        from oyun.config import get_client_game_config
        g = get_client_game_config("tr").get("globals", {})
    eksik = {}
    yanlis = {}
    for anahtar, yontemler in sorted(okunan.items()):
        siniflar = sorted({y.split("/")[0] for y in yontemler})
        bilgi = {"siniflar": siniflar, "yontem": len(yontemler), "kod_bayt": sum(boyut.get(y, 0) for y in yontemler)}
        if anahtar not in g:
            eksik[anahtar] = bilgi
        elif g[anahtar] in (0, False, "", None, [], {}, "0", "false"):
            yanlis[anahtar] = dict(bilgi, deger=g[anahtar])
    bayraklar = {}
    for a in abcler:
        try:
            sabit = a.sabitler("Config")
        except Exception:
            continue
        for k, v in sabit.items():
            if isinstance(v, bool) and re.search(r"ACTIV|ENABLE|FEATURE|SHOW|USE_|HAS_|ALLOW", k):
                bayraklar[k] = v
    return {"okunan_anahtar": len(okunan), "configte_yok": eksik, "configte_kapali": yanlis,
            "config_bayraklari_false": sorted(k for k, v in bayraklar.items() if v is False),
            "config_bayraklari_true": sorted(k for k, v in bayraklar.items() if v is True)}


# --------------------------------------------------------------------------- 3b. sistem envanteri

# (ad, istemci sınıf deseni, komutlar, config alanları, arşivdeki varlık klasörü deseni)
SISTEMLER = (
    ("PvP saldırı ve kalkan", r"^(PVPManager|Assault|ShieldManager|PopupAttackLog|PopupBuyShields|PvpPlayerManager)",
     "begin_attack_new end_attack end_attack_new get_enemy_new attack_player reply_attack buy_shield reset_shield "
     "buy_attacks_pack buy_spyings_pack spy_player clean_attack_log clean_attacks set_attack_team", "pvp_shields honor_levels",
     r"PopupBuyShields|PopupPVPFinished"),
    ("Turnuva", r"^(Tournament|PopupTournament)", "end_tournament_match tournament_refund_resources "
     "tournament_substract_resources", "tournament_type tournament_formations", r"tournament"),
    ("Görev adaları (seferler)", r"^(Quest\$?$|QuestBase|QuestIsla|QuestBoss|QuestShip|QuestZeppelin|PopupQuest|PopupIslandQuestsManager|NewQuestIsland|CQuest|CustomQuest)", "start_quest start_quest_new "
     "end_quest set_quest_var", "map_prices", r"^quests/"),
    ("Kendi adasındaki hikâye görevi", r"^QuestsInMap", "collect_treasure", "", r"^$"),
    ("Hayatta kalma", r"^(Survival|PopupSurvival|QuestSurvival)", "start_survival end_survival add_survival_vida_extra "
     "buy_survival_map", "", r"survival"),
    ("Ağır kuşatma", r"^(HeavySiege|PopupHeavySiege)", "start_heavy_siege reset_heavy_siege", "", r"siege"),
    ("Ejderha, canavar, binici, tapınak adımları", r"^(Dragon|Monster|Rider|Temple|Popup(Dragon|Monster|Rider|Temple))",
     "activate_dragon desactivate_dragon next_dragon finish_dragon_help activate_monster desactivate_monster next_monster "
     "next_monster_step next_step buy_step_cash buy_monster_step_cash rider_buy_step_cash rider_next_step rider_select "
     "next_temple_step buy_temple_step_cash reset_temple", "", r"dragon|monster|rider|temple"),
    ("Ruh Kazanı", r"^(SoulMixer|PopupSoulMixer)", "", "", r"SoulMixer"),
    ("Mezarlık ve kahraman", r"^(Graveyard|PopupGraveyard|Hero)", "put_graveyard resurrect_hero graveyard_buy_potions "
     "buy_graveyard_capacity reset_potions_received", "", r"graveyard"),
    ("Birim paketleri", r"^(UnitPack|PopupShowPack|PopupUnitPack)", "buy_unit_pack", "unit_packs", r"UnitPacks"),
    ("Ada etkinliği (collect game)", r"^(CollectGame|IslandForge|PopupCollectGame)", "collect_game_add_item "
     "collect_game_buy_all collect_game_reward_given collect_game_speed_up collect_game_update_timestamp",
     "collect_game collect_game_items", r"IslandForge"),
    ("Koleksiyonlar", r"^(UnitCollectionsManager|popupCollections|PanelCollection|ItemsCollection|PopUpCollectionComplete|CollectableManager)", "finish_collection unit_collections_completed",
     "units_collections_categories", r"collection"),
    ("Dart", r"^(Darts|PopupDarts)", "darts_new_free darts_reset darts_shoot_balloon", "darts_items", r"darts"),
    ("Zaman makinesi", r"^(PopupSelectTime|TimeMachine|PopupHelpTimeMachine)", "buy_time_packet time_ff", "",
     r"TimeMachine"),
    ("Pazar", r"^(Market|PopupMarket)", "trade_resource_b set_resource_allies", "", r"market"),
    ("Depo", r"^(PopupUnitWarehouse|UnitWarehouseCard|InfoButtonUnitWarehouse)", "add_unit_warehouse place_warehoused_item reset_warehouse "
     "buy_warehouse_capacity_single store_item store_add_items place_stored_item sell_stored_item", "", r"warehouse"),
    ("Simyacı (kompu)", r"^(Kompu|PopupKompu)", "", "kompu_offers", r"kompu"),
    ("Teklifler", r"^(Offer|Viral|PromotionPacks|FirstPurchase|PopupOffer|PopupViral)", "buy_offer_pack "
     "buy_super_offer_pack buy_viral_offer_all buy_viral_offer_friend reward_viral_offer buy_first_purchase "
     "set_first_purchase_timestamp", "offer_packs viral_offers viral_icons", r"viral_buttons"),
    ("Günlük, haftalık, dönüş ödülleri", r"^(DailyBonus|PopupDailyBonus|Comeback|MondayBonus|WeeklyReward)",
     "comeback_reward weekly_reward win_bonus", "daily_bonus", r"DailyBonus"),
    ("Komşular ve yardım", r"^(Neighbo|Assist|PopupNeighbo|SocialItem|Recruitment)", "assist_neighbor "
     "assist_neighbor_new assist_receive assist_send_feed set_help_map finish_si finish_si_recruitment buy_si_help "
     "accept_collect_help set_fake_neighbors", "neighbor_assists social_items recruitment_prices", r"Recruitment"),
    ("Büyüler", r"^(Magic|PopupMagic|SelectedMagic)", "buy_magic use_magic buy_mana_new", "magics", r"magic"),
    ("Dünya haritası", r"^(World_|ExplorationWorld|StateWorld|PopupWorld|Continent)", "modify_position_univers buy_pvp_territory "
     "reset_world_change", "", r"world"),
    ("İkinci kasaba", r"^(TownManager|PopupNewTown)", "buy_map name_map set_skin unlock_skin", "town_prices",
     r"PopupNewTown"),
    ("Seviye ödülü ve sıralama", r"^(PopupLevelUp|LevelRanking)", "rt_level_up apply_rewards_ranking",
     "level_ranking_reward level_up_tips", r"PopupLevelUp"),
)


def sistem_envanteri(abcler):
    with _sessiz():
        from oyun import komutlar
        from oyun.config import get_client_game_config
        cfg = get_client_game_config("tr")
    yontemler = []
    for a in abcler:
        for i, ad in a.yontem_adlari().items():
            g = a.govdeler.get(i)
            yontemler.append((ad.split("/")[0], len(g.kod) if g else 0))
    paket = [s.split("\t")[0] for s in open(os.path.join(KOK, "config", "onindirme.tsv"), encoding="utf-8")
             if not s.startswith("#") and s.strip()]
    sonuc = []
    for ad, desen, kmt, alan, varlik in SISTEMLER:
        r = re.compile(desen)
        siniflar = {s for s, _ in yontemler if r.search(s)}
        bayt = sum(b for s, b in yontemler if s in siniflar)
        kmtler = kmt.split()
        gercek = [k for k in kmtler if k in komutlar.KOMUTLAR and not _bos_mu(komutlar.KOMUTLAR[k])]
        bos = [k for k in kmtler if k in komutlar.KOMUTLAR and _bos_mu(komutlar.KOMUTLAR[k])]
        yok = [k for k in kmtler if k not in komutlar.KOMUTLAR]
        alanlar = {f: (len(cfg.get(f)) if isinstance(cfg.get(f), (list, dict)) else cfg.get(f)) for f in alan.split()}
        vr = re.compile(varlik, re.I)
        varliklar = sum(1 for y in paket if vr.search(y)) if varlik != r"^$" else None
        sonuc.append({"sistem": ad, "sinif": len(siniflar), "kod_bayt": bayt, "komut": len(kmtler),
                      "gercek": len(gercek), "bos": bos, "yok": yok, "config": alanlar, "arsiv_varlik": varliklar})
    return sonuc


# --------------------------------------------------------------------------- 4. varlıklar

YOL_DESENI = re.compile(r"^[A-Za-z0-9_\-./]+\.(?:swf|png|jpg|jpeg|mp3|gif|xml)$", re.I)


def varlik_tamligi(abcler):
    yollar = set()
    for a in abcler:
        for d in a.dizeler[1:]:
            if d and YOL_DESENI.match(d) and "/" in d:
                yollar.add(d.lstrip("/"))
    kok = os.path.join(KOK, "download_assets", "assets")
    paket = set()  # config/onindirme.tsv: indirilebilir arşivin tam listesi (araclar/onindirme_listesi.py)
    with open(os.path.join(KOK, "config", "onindirme.tsv"), encoding="utf-8") as f:
        for satir in f:
            if satir.startswith("#") or not satir.strip():
                continue
            paket.add(satir.split("\t")[0])
    sonlar = defaultdict(set)
    for y in paket:
        parca = y.split("/")
        for i in range(1, len(parca)):
            sonlar["/".join(parca[i:])].add(y)

    def arsivde(y):
        # istemci yolu çoğu zaman önek olmadan yazılır (externalized/, swf/...): tam eşleşme ya da bir önekin ardı
        return y in paket or bool(sonlar.get(y))

    gruplar = defaultdict(lambda: Counter())
    for y in sorted(yollar):
        grup = y.split("/")[0] if not y.startswith("externalized/") else "/".join(y.split("/")[:2])
        gruplar[grup]["yol"] += 1
        gruplar[grup]["arsivde"] += int(arsivde(y))
    eksik = sorted(y for y in yollar if not arsivde(y))
    yerel_dosya = sum(len(fs) for _, _, fs in os.walk(kok)) if os.path.isdir(kok) else 0
    return {"istemci_yol": len(yollar), "arsivde": len(yollar) - len(eksik), "eksik": eksik,
            "gruplar": {k: dict(v) for k, v in sorted(gruplar.items())}, "paket_satiri": len(paket),
            "yerel_varlik_dosyasi": yerel_dosya}


# --------------------------------------------------------------------------- 5-6. döngü ve ekonomi

def ekonomi():
    with _sessiz():
        from oyun.config import get_game_config
        from oyun.zaman import zaman_olcegi
        c = get_game_config()
    olcek = zaman_olcegi()
    ayar = json.load(open(os.path.join(KOK, "ayarlar.json"), encoding="utf-8"))
    tablo = []
    for e in c["items"]:
        try:
            topla, sure, xp = float(e.get("collect") or 0), float(e.get("activation") or 0), float(e.get("collect_xp") or 0)
        except ValueError:
            continue
        if e.get("type") != "b" or topla <= 0 or sure <= 0 or str(e.get("in_store")) != "1":
            continue
        saat = sure / olcek / 3600
        tablo.append({"id": e["id"], "ad": e["name"], "tur": e.get("collect_type"), "seviye": int(e.get("min_level") or 0),
                      "toplama": topla, "sure_sn": sure, "saatte": round(topla / saat, 1), "xp_saatte": round(xp / saat, 2)})
    en_iyi = {}
    for sev in (1, 10, 20, 30, 40, 50):
        for tur in ("g", "f", "w", "s"):
            adaylar = [t for t in tablo if t["tur"] == tur and t["seviye"] <= sev]
            if adaylar:
                b = max(adaylar, key=lambda t: t["saatte"])
                en_iyi[f"{sev}:{tur}"] = (b["ad"], b["saatte"], b["sure_sn"])
    seviyeler = [int(s["exp_required"]) for s in c["levels"]]
    return {"zaman_olcegi": olcek, "dunya": ayar.get("dunya", {}), "uretim_binasi": len(tablo), "en_iyi": en_iyi,
            "seviye_xp": {n: seviyeler[n - 1] for n in (2, 5, 10, 15, 20, 30, 40, 50, 60, 70, 80, 90, 100)
                          if n <= len(seviyeler)},
            "seviye_sayisi": len(seviyeler)}


# --------------------------------------------------------------------------- 7. kendi sistemlerimiz

KENDI_SISTEMLER = ("dunya", "diyar", "turnuva", "elo", "yokken", "bildirim", "tasima", "onindirme", "bot_koy",
                   "bot_yardim", "takvim", "bayram_hedefleri", "kayit_yedek", "ev_agi", "hile", "gunluk_odul",
                   "pvp", "pvp_yeni", "ada", "profil", "swf_yama", "fx_yama", "denge")


def saglik():
    testler = {}
    tdizin = os.path.join(KOK, "tests")
    kaynaklar = {}
    for ad in os.listdir(tdizin):
        if ad.startswith("test_") and ad.endswith(".py"):
            kaynaklar[ad] = open(os.path.join(tdizin, ad), encoding="utf-8").read()
    for sistem in KENDI_SISTEMLER:
        if not os.path.exists(os.path.join(KOK, "oyun", sistem + ".py")):
            continue
        desen = re.compile(r"\b%s\b" % re.escape(sistem))
        sayi = 0
        for ad, metin in kaynaklar.items():
            if desen.search(metin):
                sayi += len(re.findall(r"^\s+def test_", metin, re.M))
        satir = sum(1 for _ in open(os.path.join(KOK, "oyun", sistem + ".py"), encoding="utf-8"))
        testler[sistem] = {"satir": satir, "test_dosyalarindaki_test": sayi}
    b = json.load(open(os.path.join(KOK, "docs", "gorev", "BULGULAR.json"), encoding="utf-8"))
    acik = Counter(m["durum"] for m in b["maddeler"])
    acik_liste = [(m["id"], m["durum"], m["baslik"][:90]) for m in b["maddeler"]
                  if m["durum"] in ("acik", "onay_bekliyor", "dogrulandi", "ci_bekliyor", "engelli", "ertelendi")]
    return {"sistemler": testler, "bulgu_durumlari": dict(acik), "acik_maddeler": acik_liste}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    json_cikti = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    yol = argv[0] if argv else VARSAYILAN_SWF
    veri = open(yol, "rb").read()
    abcler = abc_listesi(veri)
    sonuc = {"istemci": os.path.basename(yol), "komutlar": komut_kapsami(veri), "uclar": http_uclari(abcler),
             "kapali": kapali_sistemler(abcler), "sistemler": sistem_envanteri(abcler),
             "varliklar": varlik_tamligi(abcler), "ekonomi": ekonomi(),
             "saglik": saglik()}
    if json_cikti:
        print(json.dumps(sonuc, ensure_ascii=False, indent=1, default=list))
        return
    k = sonuc["komutlar"]
    print(f"1. KOMUTLAR: istemci {k['istemci_komut']}, gerçek işleyici {k['gercek']}, boş {len(k['bos'])}, "
          f"işleyicisi yok {len(k['isleyicisi_yok'])}; sunucu kaydı {k['sunucu_kayit']}, sunucuda fazla "
          f"{len(k['sunucuda_fazla'])}, çözülemeyen çağrı {k['cozulemeyen_cagri']}")
    print("   boş:", ", ".join(f"{a}({f})" for a, f in k["bos"]))
    print("   yok:", ", ".join(k["isleyicisi_yok"]) or "-")
    print("   kayıt tekrarı (sonuncusu geçer):", k["kayit_tekrari"] or "-")
    u = sonuc["uclar"]
    print(f"2. UÇLAR: istemci {u['istemci_uc']}, sunucuda eşleşen {u['eslesen']}")
    for s in u["uclar"]:
        print("  ", s["uc"], "|", s.get("durum"), s.get("bayt"), s.get("tur"), (s.get("ornek") or "")[:60].replace("\n", " "))
    print("   tür sayıları:", dict(Counter(s.get("tur") for s in u["uclar"])),
          "| not: command.php gövdesiz POST'ta 400 verir (komut paketi gerekir; komutlar bölüm 1'de)")
    c = sonuc["kapali"]
    print(f"3. KAPALI: istemcinin globals'tan okuduğu anahtar {c['okunan_anahtar']}, config'te yok "
          f"{len(c['configte_yok'])}, config'te kapalı (0/false/boş) {len(c['configte_kapali'])}")
    for ad, b in c["configte_yok"].items():
        print("   yok:", ad, b)
    for ad, b in c["configte_kapali"].items():
        print("   kapalı:", ad, b)
    print("   Config false bayrakları:", ", ".join(c["config_bayraklari_false"]))
    print("3b. SİSTEM ENVANTERİ (sınıf, istemci kodu bayt, komut: gerçek/toplam, boş, yok, config alanı, arşiv varlığı)")
    for s in sonuc["sistemler"]:
        print(f"   {s['sistem']}: sınıf {s['sinif']}, {s['kod_bayt']} bayt, komut {s['gercek']}/{s['komut']}"
              f"{' boş ' + ','.join(s['bos']) if s['bos'] else ''}{' YOK ' + ','.join(s['yok']) if s['yok'] else ''}, "
              f"config {s['config']}, varlık {s['arsiv_varlik']}")
    v = sonuc["varliklar"]
    print(f"4. VARLIK: istemci dizelerinde yol {v['istemci_yol']}, arşivde {v['arsivde']}, eksik {len(v['eksik'])}; "
          f"yerel varlık dosyası {v['yerel_varlik_dosyasi']}, paket satırı {v['paket_satiri']}")
    for g, b in v["gruplar"].items():
        if b["yol"] != b["arsivde"]:
            print("  ", g, b)
    print("   eksik:", ", ".join(v["eksik"][:60]))
    e = sonuc["ekonomi"]
    print(f"5-6. EKONOMİ: zaman ölçeği {e['zaman_olcegi']}, mağazadaki üretim binası {e['uretim_binasi']}, "
          f"seviye {e['seviye_sayisi']}; dünya ayarı {e['dunya']}")
    for anahtar, b in e["en_iyi"].items():
        print("  ", anahtar, b)
    print("   seviye xp:", e["seviye_xp"])
    s = sonuc["saglik"]
    print("7. SAĞLIK:", s["bulgu_durumlari"])
    for ad, b in s["sistemler"].items():
        print("  ", ad, b)
    for m in s["acik_maddeler"]:
        print("   açık:", *m)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
