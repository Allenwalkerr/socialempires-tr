# Bot köyleri: tasarım planı (12.11.2026)

Sahibinin isteği (12.11.2026): "bot köylerinin dizaynı hepsi aynı ve çok ama çok kötü biraz estetik biraz özenli olsun
da o ruhu atmosferi hissettirsin"; "bot köylerini dizayn ederken askeri seviyelerini ayarla. Dizayn işini gerçekten
özene bezene yap. Bir plan çerçevesinde yap."

Kural (CLAUDE.md): köylerde yalnızca oyunun kendi binaları, birimleri ve süsleri; hiçbir şey çizilmez.

## 1. Bugünkü durum (araclar/bot_koy_uret.py, oyun/dunya.py)

- Binalar boyutlarına bakılmadan rastgele karoya konuyor: yalnızca sol üst köşe denetleniyor, 2×2 ev, 3×3 kışla,
  4×4 belediye üst üste biniyor.
- Surlar her köyde aynı kare (33..67), başlangıç alanının (40..59) dışına taşıyor; kapı 21. seviyede açılan Sur Kapısı
  olduğu hâlde 8. seviyeden konuyor.
- Askerler seviyeden bağımsız: 3. seviye de 60. seviye de Hafif Şövalye (512) ve üç okçudan (516, 517, 518) oluşuyor;
  dünya simülasyonu (dunya.py `_ekonomi`) da aynı dört birimi 38..62'de rastgele bir karoya ekliyor.
- Kışla türü üç kademede (I, II, III); okçu ocağı, ahır, atölye hiç yok. Kule I..III; Kule IV, V hiç yok.
- Süs yalnızca 0-2 Kral Heykeli; ağaç, çiçek, bayrak, çeşme yok. 50 köyün dördü dört kişilikten biri; düzen hep aynı.

## 2. Oyunun kendi verisi (config, 1.4.07 istemcisi)

- Harita 100×100 karo, 20×20'lik büyük karolardan 5×5 ızgara (Config EI_MAP_WIDTH 100, EI_TILES_IN_BIGTILE 20).
  Genişleme kimliği `satır·5 + sütun + 1`: 13 = başlangıç (40..59), 3×3 = 7, 8, 9, 12, 13, 14, 17, 18, 19 (20..79).
  Büyük karo başına en çok 10 kule (MAX_TOWERS_PER_BIGTILE).
- Askeri binalar ve açılış seviyeleri (mağazada, kategori 3):
  - Kışla I 1 (Mızrakçı), II 8 (Kılıççı), III 16 (Uzun Kılıççı), IV 28 (Güçlü Kılıççı), V 37 (Kraliyet Kılıççısı)
  - Okçu Ocağı I 3, II 10, III 18, IV 30, V 42 (Hafif, Orta, Ağır, Güçlü, Kraliyet Okçu)
  - Ahır I 5, II 12, III 20, IV 32, V 46 (Hafif, Orta, Ağır, Güçlü, Kraliyet Şövalye); Atlı Okçu Ahırı 24; Fil Ahırı 27
  - Atölye I 7 (Koçbaşı), II 14 (Akrep), III 22 (Mancınık), IV 26 (Top); Kule Atölyesi 22 (Yürüyen Kule)
- Savunma: Kule I 2, II 8, III 14, IV 23, V 33; Sur I 3, II 9, III 17, IV 25, V 34; Sur Kapısı 21 (3×3);
  Kale I (4×4) 0, II 10, III 27.
- Ekonomi: Belediye I 1, II 12, III 25, IV 35 (4×4); Ev I..V 1, 7, 19, 31, 36; Değirmen I..IV 1, 11, 23, 32;
  Tarla 1; Altın Ocağı I..IV 4, 13, 24, 38; Marangozhane I..IV 5, 15, 27, 35; Taş Ocağı I..IV 6, 17, 29, 41;
  Koyun Ağılı (4×4) 2, 14, 24; İnek Ağılı (4×4) 5, 17, 26; Pazar 5, 11, 25 (4×4); Kilise 19, Tapınak 18, Katedral 23.
- Süs (kategori 4): ağaçlar (Yeşil 0, Mavi 2, Mor 8, Turuncu 10, Kızıl 12), çiçekler (Sarı 0 ... Yeşil 10), heykeller
  (Kral, Asker, Viking 1; İskelet 5; Minotor 10; Ejderha 15), Çeşme 6, Maya Ateşi 1, bayraklar (Türkiye 174, Kartallı 12,
  Yeşil 15, Turuncu 5).

## 3. Plan

### 3.1 Askeri seviye (her köy oyuncunun o seviyede kurabileceği orduyla)

- Bot yalnızca kendi seviyesinde açılmış binaları ve birimleri kullanır (`min_level <= seviye`).
- Ordu, sahip olduğu askeri binaların ürettiği birimlerden oluşur: her kol (piyade, okçu, süvari, kuşatma) o kolun
  açık en yüksek iki kademesinden (çoğu en yüksekten). Kışla türü de o kolun en yüksek kademesi.
- Ordu büyüklüğü seviyeyle artar: `8 + seviye` (en çok 60); kişilik bölüşümü değiştirir:
  - **agresif**: süvari ve piyade ağırlıklı, 2 kışla + ahır, daha az kule.
  - **savunmacı**: okçu ağırlıklı, en çok kule (büyük karo başına 10'u aşmadan), çift sur.
  - **tüccar**: küçük ordu, çok üretim binası ve pazar, az kule.
  - **dengeli**: dört kol eşit.
- Dünya simülasyonu bota yeni birim katarken aynı kuralı kullanır (seviyesine uygun, ordu alanında boş bir karo) ve
  ordu `8 + seviye` sınırını aşmaz (bugün 700 öğeye kadar büyüyordu).

### 3.2 Yerleşim (dört düzen, her köy kendi tohumuyla)

Her bina kendi boyutuyla (width × height) yer kaplar; hiçbir şey üst üste binmez, hepsi köyün açık büyük karolarında
kalır. Belediye ortada bir meydanın başında; ana yol çevresinde evler sıra sıra; tarlalar ve ağıllar dışarıda bir
"çiftlik kuşağında"; askeri binalar kapıya yakın bir "ordugâh"ta; kuleler surların köşelerinde ve kapının iki
yanında; süsler meydanda (çeşme, heykel), yol kenarında (çiçek) ve sur dışında (ağaç kümeleri).

1. **Kale köyü** (savunmacı): tam sur halkası (14. seviyeden çift halka), dört köşe kulesi, kapı önünde ordugâh.
2. **Çarşı köyü** (tüccar): meydanda pazar ve çeşme, iki sıra ev arasında çarşı yolu, kuzeyde tarlalar.
3. **Ordugâh** (agresif): kışla, ahır, atölye meydanın çevresinde; ordu talim alanında düzenli sıralar.
4. **Çiftlik köyü** (dengeli): geniş tarla ve ağıl kuşağı, ağaçlıklı kenarlar, küçük sur.

- Seviye büyüdükçe köy büyür: 1-14 başlangıç büyük karosu (40..59); 15-29 artı iki büyük karo; 30+ 3×3 (20..79).
  `expansions` buna göre yazılır.
- Süs ve bayrak seçimi köyün seviyesine göre (örneğin Ejderha Heykeli 15'ten); bazı köylerde Türkiye Bayrağı.

### 3.3 Denetim (testler, tests/test_bot_koy.py)

Beklenen değerlerin kaynağı config ve Config sabitleri; üreticinin kendi çıktısı beklenen değer yapılmaz.
- Hiçbir öğe başka öğenin karolarına binmez (config width/height); hepsi açık genişlemelerin içinde.
- Her öğenin `min_level`'ı botun seviyesini aşmaz; büyük karo başına en çok 10 kule.
- Ordu gücü (config attack × life toplamı) seviyeyle artar; yüksek seviyede en az bir 4. ya da 5. kademe birim.
- 50 köyün düzenleri birbirinden farklı (aynı karo deseni iki köyde yok); dört düzenin dördü de kullanılıyor.
- Dünya simülasyonunun kattığı birim seviyeye uygun ve boş bir karoda.
- Görsel denetim: dört düzenden birer köy Ruffle'da açılıp ekran görüntüsüyle bakılır.

## 4. Kapsam dışı

- Yeni bina, birim ya da süs çizilmez; mağazada olmayan (in_store 0) ya da nakitle alınan özel binalar kullanılmaz
  (Kale I-III hariç: oyunun kendi savunma binası).
- Var olan bot kayıtları: üretici `mevcut_botlari_sil` ile yalnızca botları yeniler; oyuncu kaydına dokunmaz.

## 5. Sürüm 2: Arthur köyleri örnek (12.11.2026)

Sahibi ilk sonucu "çok bot gibi, çok yapay" buldu: "Arthur'un köyüne bak, hakikaten güzel; birebir yapma". Oyunun
kendi Arthur köyleri (villages/Arthur30, 31, 32.json) incelendi:

- Hangisinin görüneceğini istemci seçer (FriendButton/mouseUsed): oyuncu seviyesi ≤ 10 → 100000030, ≤ 20 → 100000031,
  öteki her seviye → 100000032. Çubukta Arthur'un seviyesi oyuncunun seviyesi × 1,2 (FriendsWindow/<kurucu>); köyün
  kendisi yalnızca bu üç aşamada değişir. SWF'deki öteki 1000000xx kimlikleri görev ve hayatta kalma haritalarıdır.
- Arthur30: iki büyük karo (20×40 dikdörtgen); Arthur31: L; Arthur32: 40×40.
- Sur köyün kenarında; köşelerde kule öbekleri, sur boyunca kule dizileri; kapı bir boşluk, iki yanında kule, içeri
  ağaçlı yol. Evler, bostanlar, kışlalar sura yaslı boşluksuz şeritler ve sık bloklar; belediyenin çevresi çiçek;
  askerler düzensiz kümeler; aralarda çimen.

Uygulama (oyun/bot_koy.py, tasarım sürümü 4): köy seviyeyle büyür (1-9: 1 büyük karo, 10-19: 2 (dikdörtgen),
20-29: 3 (L), 30+: 4 (2×2)); sur alanın kenarından geçer; her dış köşede kule; kapı boşluğu ve ağaçlı yol; her dış
kenarda kişiliğin sırasıyla bir mahalle şeridi; her büyük karonun ortasında 10×10'luk blok; meydan çiçek halısıyla;
ordu 2-4 toplu manga. Denetim tests/test_bot_koy.py ArthurDuzeni (genişleme eksenleri Arthur30 dosyasıyla, aşamalar,
sur kenarda ve köşelerde kule, askerler küme küme).
