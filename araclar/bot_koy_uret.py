# -*- coding: utf-8 -*-
"""PvP için yapay komşu köyleri üretir.

Her bot `saves/<uuid>.save.json` olarak kaydedilir ve `playerInfo.bot`
ile işaretlenir. `world.py` bu köyleri yaşayan dünya simülasyonuna dahil
eder: ekonomi, birlik üretimi, akınlar ve savunma.

Kullanım:
    python araclar\\bot_koy_uret.py [adet]      (varsayılan 50)
"""

import copy
import json
import os
import random
import sys
import time
import uuid

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from oyun.yollar import SAVES_DIR, VILLAGES_DIR  # noqa: E402
from oyun.surum import version_code  # noqa: E402
from oyun.kayit_semasi import eksikleri_tamamla  # noqa: E402
from oyun.bot_kimlik import ISIMLER, portre  # noqa: E402
from oyun import bot_koy  # noqa: E402  (yerleşim ve ordu: docs/inceleme/bot-koyleri-plani.md)

KISILIKLER = ["agresif", "savunmaci", "tuccar", "dengeli"]


def mevcut_botlari_sil():
    """Daha önce üretilmiş bot kayıtlarını siler (oyuncu kaydına dokunmaz)."""
    silinen = 0
    if not os.path.exists(SAVES_DIR):
        return 0
    for dosya in os.listdir(SAVES_DIR):
        if not dosya.endswith(".save.json"):
            continue
        yol = os.path.join(SAVES_DIR, dosya)
        try:
            with open(yol, encoding="utf-8") as f:
                kayit = json.load(f)
        except (ValueError, OSError):
            continue
        if kayit.get("playerInfo", {}).get("bot"):
            try:
                os.remove(yol)
                if os.path.exists(yol + ".bak"):
                    os.remove(yol + ".bak")
                silinen += 1
            except OSError:
                pass
    return silinen


def bot_uret(adet=50):
    with open(os.path.join(VILLAGES_DIR, "initial.json"), encoding="utf-8") as f:
        sablon = json.load(f)
    with open(os.path.join(KOK, "config", "game_config_20120826.json"), encoding="utf-8") as f:
        seviyeler = json.load(f)["levels"]

    os.makedirs(SAVES_DIR, exist_ok=True)
    eski = mevcut_botlari_sil()
    if eski:
        print(f" * {eski} eski bot kaydi silindi")

    rastgele = random.Random(20261027)
    simdi = int(time.time())

    adet = max(1, min(adet, len(ISIMLER)))
    for i in range(adet):
        isim = ISIMLER[i]
        kisi = KISILIKLER[i % len(KISILIKLER)]
        seviye = min(60, 3 + int(i * 1.15))
        pid = str(uuid.uuid4())

        kayit = copy.deepcopy(sablon)
        kayit["version"] = version_code

        pi = kayit["playerInfo"]
        pi.update({
            "pid": pid,
            "name": isim,
            "pic": portre(isim),
            "cash": 0,
            "completed_tutorial": 1,
            "default_map": 0,
            "world_id": 0,
            "last_logged_in": 0,
            "sp_ref_uid": pid,
            "bot": True,
            "bot_kisi": kisi,
            "bot_tasarim": bot_koy.TASARIM_SURUMU,
        })
        pi["map_names"] = [f"{isim} Kalesi"]
        pi["map_sizes"] = [0]

        harita = kayit["maps"][0]
        harita["level"] = seviye
        onceki = max(0, seviye - 1)
        harita["xp"] = int(seviyeler[onceki]["exp_required"]) + 1 if seviye > 0 else 0
        harita["coins"] = 300 * seviye
        harita["wood"] = 450 * seviye
        harita["stone"] = 350 * seviye
        harita["food"] = 400 * seviye
        harita["timestamp"] = simdi
        harita["resourcesTraded"] = {}
        harita["items"], harita["expansions"] = bot_koy.koy_kur(seviye, kisi, pid, simdi, ad=isim)
        harita["skin"] = bot_koy.arazi_sec(pid)

        ps = kayit["privateState"]
        ps["attacksSent"] = []
        ps["attacksReceived"] = []
        ps["teams"] = {"tournament": None}
        ps["completedMissions"] = []
        ps["rewardedMissions"] = []
        ps["gifts"] = []
        ps["unlockedQuestIndex"] = 0
        eksikleri_tamamla(ps)

        yol = os.path.join(SAVES_DIR, f"{pid}.save.json")
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(kayit, f, indent=4, ensure_ascii=False)

    print(f"[+] {adet} bot koy uretildi: {SAVES_DIR}")


if __name__ == "__main__":
    adet = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    bot_uret(adet)
