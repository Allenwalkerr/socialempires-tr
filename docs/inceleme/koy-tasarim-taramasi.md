# Social Empires köy tasarımları: internet taraması (12.11.2026)

Sahibinin isteği: "İnternette YouTube'da, forumlarda popüler dillerde Social Empires köyleri için tarama yap; görsel
bulursan kesin bak; en az 10 dilde." Amaç bot köylerinin (oyun/bot_koy.py) gerçek oyuncu köylerine benzemesi.

## Nasıl tarandı

- Web araması 15 dilde: İngilizce, İspanyolca, Portekizce, Almanca, Fransızca, İtalyanca, Rusça, Lehçe, Türkçe,
  Arapça, Endonezce, Vietnamca, Çince, Macarca, Rumence. Köy tasarımı üzerine yazılı rehber ya da forum başlığı
  bulunmadı; çıkanlar genel tanıtım ve inceleme (gamepressure, gamezebo, gameyum, supercheats, gry-online).
- YouTube araması 12 sorguyla (village, my empire, base defense, level 100, imperio, aldeia, köy, империя, villaggio,
  dorf, قرية, kingdom tour): yaklaşık 80 video, başlığından 52'si Social Empires. Köy gösteren 16 videonun kapak
  resmi ve YouTube'un kendiliğinden ürettiği üç karesi (i.ytimg.com/vi/<kimlik>/{hqdefault,1,2,3}.jpg) indirildi
  ve tek tek bakıldı (görseller depoya konmadı).

## Görülen desenler (videodaki kare)

| Video | Seviye/başlık | Görülen |
|---|---|---|
| [90FRPhab6s0](https://www.youtube.com/watch?v=90FRPhab6s0) | My Social Empire (Level 58) | Kare köy; dışta beyaz-kırmızı sur, içte kalın kule sırası (çift sur); içerisi aynı binaların sık, düzgün sıraları; ayrı bir avluda kırmızı döşemeli meydan ve belediye |
| [E8MQzwt2mAg](https://www.youtube.com/watch?v=E8MQzwt2mAg) | My Social Empire Level 69 | Simetrik baklava/artı düzeni: köşeleriyle birbirine bağlı kare avlular, her avlu surla çevrili, içlerinde kırmızı çatılı ev sıraları |
| [3K_YbEsuJN4](https://www.youtube.com/watch?v=3K_YbEsuJN4) | Ataques a Imperios 01 | Artı (+) biçimli imparatorluk, beyaz surlar; ayrıca karlı (buz arazisi) bir imparatorluk |
| [DRF5mhGf25c](https://www.youtube.com/watch?v=DRF5mhGf25c) | My Empire Level 55 | Surlu avluda askerler düzgün aralıklı sıralar hâlinde (geçit töreni gibi) |
| [7QxXUizrP9g](https://www.youtube.com/watch?v=7QxXUizrP9g) | O melhor império | Kahverengi zemin, çok sık bina ızgarası, avluları bölen iç surlar |
| [1yqhaac5TXg](https://www.youtube.com/watch?v=1yqhaac5TXg) | My Empire - Paknot8 | Kahverengi zemin, surla bölünmüş odalar, ejderha meydanı |
| [DIrxtY32BRA](https://www.youtube.com/watch?v=DIrxtY32BRA) | social empire | Altın renkli surlarla labirent, altın tarlalar |
| [D1dIdXX-Hos](https://www.youtube.com/watch?v=D1dIdXX-Hos) | Social Empire 2024 | Daha serbest köy: ev kümeleri, tapınak, kenarda sur |
| [Gc2fAWRau2g](https://www.youtube.com/watch?v=Gc2fAWRau2g) | The Old Days | Karlı zemin, Yuvarlak Masa, sık köy |
| [-MyGzJ9QMiY](https://www.youtube.com/watch?v=-MyGzJ9QMiY), [3Vsg-FvgPuI](https://www.youtube.com/watch?v=3Vsg-FvgPuI), [EYmA7AMPE78](https://www.youtube.com/watch?v=EYmA7AMPE78) | Başlangıç köyleri | Ahşap sur, ortada belediye, tarla sıraları |

Ortak desenler: (1) simetri (kare, artı, baklava); (2) çift sur ve kalın kule sıraları; (3) aynı binanın sık ve
düzgün ızgaraları, iç surlarla odalara bölünmüş avlular; (4) avluda düzgün sıralı asker geçidi; (5) arazi türü
(kahverengi maden, kar, çöl).

## Arazi türü oyunda var (bayt koduyla doğrulandı)

Kahverengi ve karlı zemin oyunun kendi arazi türleri: haritanın `skin` alanı (Base/_parseLoadedInfo: map.skin →
skinMap) arka plan rengini (Config.BG_SKIN_COLORS) ve genişleme arazisini seçer; arazi öğesi `1000 + skinMap`
(Base/addExpandedTileBuilding). Config: 1000 Expandable Land (çimen), 1001 Desierto (çöl), 1002 Ice (buz), 1003 Sea,
1004 Mineral (kahverengi), 1005 Selva (orman), 1006 Cloud. Sunucuda `set_skin` komutu var (oyun/komutlar.py). Çizimleri
(buildingsprites/terreno*.swf) çevrimdışı paketin 2. önceliğinde, temel pakette değil.

## Bot köylerine önerilenler

1. Yüksek seviyede simetrik düzen (artı/baklava avlular) ve iç surlarla bölünmüş avlular.
2. Çift sur: dışta sur, içte kule sırası (büyük karo başına 10 kule sınırı içinde).
3. Asker geçidi: bir avluda düzgün aralıklı sıralar (bugün düzensiz mangalar).
4. Bazı botlara arazi türü (çöl, buz, maden, orman); çizimleri temel pakete alınırsa çevrimdışı da görünür.
