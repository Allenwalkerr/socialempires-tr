"""Bot köylerinin adı ve portresi: oyunun kendi birimlerinden.

Her bot oyundaki bir birimin oyun içindeki Türkçe adını taşır, portresi de o birimin
oyundaki resmidir (buildingthumbs, çevrimdışı temel pakette). Güçlü botlara güçlü
birimler düşer: liste birimlerin gücüne (can × saldırı) göre sıralıdır ve üretim
sırası botun başlangıç seviyesidir. Gerçek kişi adı ve fotoğrafı kullanılmaz
(sahibi, 30 Ekim 2026).
"""

PORTRE_YOLU = "/default01.static.socialpointgames.com/static/socialempires/buildingthumbs/{}.jpg"
VARSAYILAN_PORTRE = "/img/profile/1025.png"
# İlk sürümlerin bot fotoğrafları (gerçek kişiler; depodan kaldırıldı)
SILINEN_PORTRELER = ("/img/profile/bot_", "/img/profile/pp_")

# 50 bot: (oyundaki birim adı, birim resmi, birim kimliği), zayıftan güçlüye
BOTLAR = [
    ("Hafif Okçu", "arquero1", "516"), ("Mızrakçı", "infanteriaunidad1", "509"),
    ("Şifacı", "curandera", "502"), ("Keşiş", "obispo", "569"),
    ("Kılıççı", "infanteriaunidad2", "510"), ("Hafif Şövalye", "caballo1", "512"),
    ("Orta Atlı Okçu", "caballoarquero", "515"), ("Korucu", "ranger", "535"),
    ("Orta Şövalye", "caballo2", "513"), ("Seçkin Kılıççı", "unidadcastillo1", "507"),
    ("Kraliyet Okçusu", "arquero5", "609"), ("Cehennem Okçusu", "arqueroinfernounidad", "646"),
    ("Göksel Okçu", "703_angelarquero", "703"), ("Elf Druid", "628_druida", "628"),
    ("Baltalı Viking", "vikingolanzahachas", "607"), ("Atlantis Savaşçısı", "guerreroatlantis", "619"),
    ("Aztek Savaşçısı", "guerreroazteca", "578"), ("Ejder Yavrusu", "638_draggy", "638"),
    ("Güçlü Şövalye", "caballo4", "541"), ("Savaşçı Prenses", "xena", "533"),
    ("Gergedan Binicisi", "640_rinoceronte", "640"), ("Viking", "vikingo", "606"),
    ("Anubis Sureti", "guerreroegipcio1", "612"), ("Yengeç Şövalye", "cangrejo", "621"),
    ("Büyücü", "mago", "550"), ("Kraliyet Elfi", "elfoblanco", "632"),
    ("Yüce Elf", "arqueroelfo", "557"), ("Yağmacı Trol", "trol8", "564"),
    ("Ak Büyücü", "706_mage", "706"), ("Deve Binicisi", "camelloguerrero", "614"),
    ("Kızıl Büyücü", "652_magorojo", "652"), ("Elf Kaplanı", "tigreelfo", "629"),
    ("Valkür", "valkiria", "554"), ("Göksel Rahip", "699_warriorpriest", "699"),
    ("Cehennem Savaşçısı", "644_if_footman", "644"), ("Mumya", "momia", "615"),
    ("Kanatlı Paladin", "655_paladin", "655"), ("Cehennem Şövalyesi", "infernomontado", "647"),
    ("Grifon Şövalye", "700_grifo", "700"), ("Fil Binicisi", "elefante", "603"),
    ("Thor", "thor", "556"), ("Kızıl Samuray", "694_samurai", "694"),
    ("Sparta Yiğidi", "660_leonidas", "660"), ("Barbar", "661_conan", "661"),
    ("Altın Golem", "641_golem", "641"), ("Kara Yeti", "642_yeti", "642"),
    ("İblis Kıran", "654_demoniogrande", "654"), ("Balrog", "650_juggernaut", "650"),
    ("Öfkeli Ejderha", "649_dragonbigred", "649"), ("Fırtına Ejderhası", "684_dragon", "684"),
]
ISIMLER = [ad for ad, _, _ in BOTLAR]
_RESIM = {ad: resim for ad, resim, _ in BOTLAR}

# İlk sürümlerin tarihî adları, üretim sırasıyla; kayıtlı köyler aynı sıradaki yeni ada geçer
ESKI_ISIMLER = [
    "Kara Han", "Bozkurt Bey", "Demir Yay", "Gökbörü", "Alp Er Tunga",
    "Kül Tigin", "Bilge Kağan", "Tomris Hatun", "Modu Han", "Attila",
    "Balamir", "İlteriş", "Kapgan", "Suyab", "Tardu",
    "Bayan Kağan", "İstemi Yabgu", "Bilge Hatun", "Kür Şad", "Tonyukuk",
    "Vezir Nizam", "Şahin Bey", "Korkut Ata", "Dede Korkut", "Manas",
    "Cengiz Han", "Kubilay", "Timur", "Babür", "Alparslan",
    "Tuğrul Bey", "Melikşah", "Sultan Sencer", "Harzemşah", "Celaleddin",
    "Ertuğrul", "Osman Bey", "Orhan Bey", "Murat Bey", "Yıldırım",
    "Fatih", "Yavuz", "Kanuni", "Sokullu", "Kılıç Arslan",
    "Nurettin", "Selahaddin", "Baybars", "Kutuz", "Berke Han",
]
YENI_AD = dict(zip(ESKI_ISIMLER, ISIMLER))


def portre(ad):
    """Botun birim resmi; bot listede yoksa varsayılan portre."""
    resim = _RESIM.get(ad)
    return PORTRE_YOLU.format(resim) if resim else VARSAYILAN_PORTRE


def adlari_yenile(kayitlar):
    """Eski adlı bot köylerini yeni adlarına geçirir, bot portrelerini birim resmiyle tazeler.

    Raporlardaki (attacksSent/attacksReceived) eski adlar ve portreler de değişir.
    kayitlar: {uid: kayıt}; değişen kayıtların kimliklerini döndürür (kaydetmek çağıranın işi)."""
    degisen = set()
    for uid, kayit in kayitlar.items():
        if not isinstance(kayit, dict):
            continue
        pi = kayit.get("playerInfo") or {}
        if pi.get("bot"):
            ad = YENI_AD.get(pi.get("name"), pi.get("name"))
            if ad in _RESIM:
                yeni = {"name": ad, "pic": portre(ad), "map_names": [f"{ad} Kalesi"]}
                if any(pi.get(k) != v for k, v in yeni.items()):
                    pi.update(yeni)
                    degisen.add(uid)
        elif str(pi.get("pic") or "").startswith(SILINEN_PORTRELER):
            # Oyuncunun devraldığı eski bot köyü: silinen gerçek kişi fotoğrafı yerine varsayılan portre
            pi["pic"] = ""
            degisen.add(uid)
        ps = kayit.get("privateState") or {}
        for giris in (ps.get("attacksSent") or []) + (ps.get("attacksReceived") or []):
            rakip = (giris.get("description") or {}).get("oponent") if isinstance(giris, dict) else None
            if isinstance(rakip, dict) and rakip.get("name") in YENI_AD:
                rakip["name"] = YENI_AD[rakip["name"]]
                rakip["pic"] = portre(rakip["name"])
                degisen.add(uid)
    return degisen


# Profil birliği ve köy teması (sahibinin fikri, 12.11.2026: "her botun profil fotoğrafındaki birlik o bot köyünde
# yer alsın", "profil resimleri ile uygun bir şekilde dekorasyon"). Süsler yalnızca oyunun kendi süsleridir
# (config category_id 4; sprite'ı çevrimdışı pakette olanlar, config/onindirme.tsv). "kucuk": 1x1 süsler (meydanın
# köşeleri, birliğin iki yanı ve köye serpilenler); "orta": meydanın yanına konan büyük süs; "agac": ağaç öbekleri.
TEMALAR = {
    "saray": {"kucuk": [122, 126, 123, 125, 129], "orta": [178], "agac": None},  # Kral ve Asker Heykelleri, Bahçe
    "kuzey": {"kucuk": [128, 114, 118], "orta": [180], "agac": None},  # Viking Heykeli, Kurukafalar; Donmuş Mamut
    "misir": {"kucuk": [131, 117, 68], "orta": [176, 206], "agac": None},  # Antik Testi; Piramit, Timsah Çukuru
    "aztek": {"kucuk": [68, 133, 131], "orta": [1457], "agac": None},  # Maya Ateşi, Altın Totem; Yanardağ
    "elf": {"kucuk": [63, 66, 67], "orta": [207, 178], "agac": [101, 104, 105]},  # çiçekler; Hayat Ağacı, Bahçe
    "cehennem": {"kucuk": [117, 114, 68], "orta": [1457], "agac": [107]},  # İskelet Heykeli; Yanardağ; Korku Ağacı
    "ejderha": {"kucuk": [120, 1282], "orta": [1456, 434], "agac": None},  # Ejderha Heykeli, Mavi Anka Yumurtası
    "goksel": {"kucuk": [63, 129, 122], "orta": [179, 178], "agac": [100]},  # Ak Çiçek, Çeşme; Altın Çeşme
    "deniz": {"kucuk": [130, 129], "orta": [944], "agac": None},  # Su Kuyusu, Çeşme; Girdap
    "trol": {"kucuk": [353, 354, 355, 356], "orta": [288], "agac": None},  # Trol Heykelleri; Kaya Delen Kafatası
    "buyu": {"kucuk": [119, 1282], "orta": [1254], "agac": [101]},  # Minotor Heykeli; Anka Yumurtası
    "antik": {"kucuk": [115, 118, 132], "orta": [178], "agac": None},  # Roma Sütunu, Miğfer Heykeli, Truva Atı
    "dogu": {"kucuk": [121, 68], "orta": [1456], "agac": [103]},  # Moğol Heykeli; Çin Ağacı
    "altin": {"kucuk": [133, 177], "orta": [179], "agac": None},  # Altın Totem, Hazine Sandığı; Altın Çeşme
    "savan": {"kucuk": [114, 131], "orta": [206], "agac": None},  # Kurukafalar, Antik Testi; Timsah Çukuru
}
BIRIM_TEMASI = {
    "607": "kuzey", "606": "kuzey", "554": "kuzey", "556": "kuzey", "642": "kuzey",
    "612": "misir", "615": "misir", "614": "misir",
    "578": "aztek",
    "628": "elf", "632": "elf", "557": "elf", "629": "elf",
    "646": "cehennem", "644": "cehennem", "647": "cehennem", "654": "cehennem", "650": "cehennem",
    "638": "ejderha", "649": "ejderha", "684": "ejderha",
    "703": "goksel", "699": "goksel", "655": "goksel", "700": "goksel", "706": "goksel",
    "619": "deniz", "621": "deniz",
    "564": "trol",
    "550": "buyu", "652": "buyu",
    "660": "antik", "661": "antik", "533": "antik",
    "694": "dogu",
    "641": "altin",
    "640": "savan", "603": "savan",
}
_BIRIM = {ad: int(kimlik) for ad, _, kimlik in BOTLAR}


def profil_birimi(ad):
    """Botun profil resmindeki birliğin kimliği; bot listede yoksa None."""
    return _BIRIM.get(ad)


def tema(ad):
    """Botun köy teması (TEMALAR'dan); listede olmayan ya da teması yazılmamış birlikte 'saray'."""
    kimlik = _BIRIM.get(ad)
    return TEMALAR[BIRIM_TEMASI.get(str(kimlik), "saray")] if kimlik else TEMALAR["saray"]
