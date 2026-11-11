# Denetim raporu: turkce-arayuz (TRA)

Kapsam: `oyun/turkce.py`, `swf_yama.py`, `swf_font.py`, `fx_yama.py`, `ceviri/`, `araclar/ceviri_kapsami.py`, `templates/` (HTML, CSS, JS), ilgili belgeler ve testler.
Araçlar: `is/turkce-arayuz/` (`t1.py` yer tutucu karşılaştırması, `t2.py` yamalı SWF denetimi, `t3.py` alan genişliği tahmini, `pw.js`/`pw2.js` Playwright, 360 px ve 1000 px).

### TRA-01: 1.4.07'nin "hedefler" (goals) metinleri Türkçeleşmiyor; config çevirisinde bu bölüm yok
- Önem: Orta
- İşaret: ✔
- Yer: oyun/turkce.py:36-150 (`_bolum_anahtarlari` bölümleri: `goals` yok), config/goals.json
- Kanıt: `get_game_config()['goals']` 206 hedef, 410 başlık/açıklama alanı; hiçbiri `localization_strings` anahtarı değil (ör. `id 3`: "Send villager to farm land", "Your farm land needs villagers to produce food..."). `turkce_uygula` bölümleri arasında `goals` yok, bu yüzden hepsi İngilizce gider. Projenin kendi belgesi de aynı rakamı veriyor (`docs/inceleme/ceviri-kapsami.md`: Hedefler 0/410, SWF metin alanları 404/638, AS3 dizeleri 0/219; "Kapı: T = 1" sağlanmıyor).
- Etki: 1.4.07'de oyuncunun hedef/öğretici panelinde sürekli İngilizce görür; SWF'te ~234 alan ve ~219 kod dizesi de İngilizce kalıyor.
- Öneri: `goals` için `goal:<id>:<alan>` anahtarlarını `_bolum_anahtarlari`na ekle ve çevir.

### TRA-02: İstemci yerelleştirilmiş metni Flash `toUpperCase`/`toLowerCase` ile büyütüyor; Türkçe i/ı/İ bozulur
- Önem: Düşük
- İşaret: ◐
- Yer: istemci `PopUpCollectionComplete/<kurucu>` (@50, @140), `infoFriendAssistPopup/<kurucu>` (@215), `TournamentManager$/onTournamentFinished`, `BuildingWindow/passFilter` (toLowerCase); sunucu tarafı ceviri/tr.json
- Kanıt: Bayt kodu: `PopUpCollectionComplete` kurucusu `name.toUpperCase()` ile bina adını büyütür (`buildingStringName`); `AUX_ACEPTAR` ("Kabul et") `infoFriendAssistPopup`ta büyütülür. AS3 `toUpperCase` yerele bakmaz: `i` -> `I`. tr.json'da `item:5` "Değirmen I", `item:22` "Demirci", `item:24` "Kilise" gibi adlar bu pencerede "DEĞIRMEN", "DEMIRCI", "KILISE" çıkar (doğrusu İ). Pencereyi çalıştırıp görmedim.
- Etki: Koleksiyon tamamlama penceresinde büyük harfli adlarda noktalı İ yerine noktasız I; bina listesi aramasında (`passFilter`, küçük harfe çevirme) İ/ı ile yazılan aramalar eşleşmeyebilir (?).
- Öneri: Etkilenen metinleri yamada elle büyük yazılmış hâlde ver (indexOf eşleşmesini kontrol ederek) ya da SWF yamasında `toUpperCase` çağrılarını sarmala.

### TRA-03: `docs/inceleme/ceviri-kapsami.md` güncel çeviri durumunu yansıtmıyor
- Önem: Düşük
- İşaret: ✔
- Yer: docs/inceleme/ceviri-kapsami.md (Oranlar, Config bölümleri)
- Kanıt: Belge 1.4.07 için "Config loc adları 1478/1976", "bütün metinler 4058/4561" diyor. Taban config + 0/1/2 yamaları üzerinde `turkce._bolum_anahtarlari` ile saydım (`t1.py` ve tek satırlık komut): 1979 loc adının 1979'u `ceviri/tr.json`'da; sunulan config'te (yerel yamalar dahil) 4573 anahtarın 4573'ü çevrili ve `dogrula` hiçbirini reddetmiyor. İngilizce kalan yalnızca `TUTORIAL_EI`, Arthur ve Guinevere adları.
- Etki: Çeviri durumu yanlış okunur; kalan işin (TRA-01) büyüklüğü belirsizleşir.
- Öneri: Belgeyi `araclar/ceviri_kapsami.py` ile yeniden üret.

### TRA-04: `docs/RESIM_KAYNAKLARI.md` depoda olmayan görselleri anlatıyor, depodaki görsellerin kaynağını yazmıyor
- Önem: Düşük
- İşaret: ✔
- Yer: docs/RESIM_KAYNAKLARI.md; templates/img/
- Kanıt: Belge Wikimedia'dan (kulüp logoları, fotoğraflar dahil) bot profil resimlerini "özgür lisanslı" diye sayıyor; `templates/img/profile/` içinde yalnızca `1025.png` var ve `bot_kimlik.SILINEN_PORTRELER` bu fotoğrafların depodan kaldırıldığını söylüyor. Öte yandan `templates/img/` altındaki 24 dosyanın (`logo.png`, `knight.png`, `sword.png`, `villager.png`, `Gamebar_byTrevo.png`, `simge-*.png`, `oyun/*.png`) nereden geldiği hiçbir belgede yazılı değil; "oyunun kendi görseli" olduklarını bu depodan doğrulayamadım (?).
- Etki: Kural denetimi (yalnızca oyunun resimleri) ve lisans izi yapılamıyor.
- Öneri: Belgeyi güncelle; her `templates/img` dosyası için oyundaki kaynak yolunu yaz.

### TRA-05: Türkçe harfi olmayan üç gömülü yazı tipi var (şimdilik kullanılmayan alanlarda)
- Önem: Düşük
- İşaret: ✔ (yazı tipi içeriği), ◐ (etki)
- Yer: oyun/swf_font.py, oyun/swf_yama.py:`_fontlari_tamamla`
- Kanıt: Yamalı SWF'te (`turkcelestir`, 521 değişiklik) DefineFont3: Arial Rounded MT Bold (222 glif) ve Eras Bold ITC (227) on iki Türkçe harfin hepsini içeriyor; Curse Casual JVE (166 glif) ve Freestyle Script (84) `ç Ç ğ Ğ ı İ ş Ş` harflerini, Arial Narrow (13 glif) on iki harfin hiçbirini içermiyor. Bu üç yazı tipini kullanan 6 DefineEditText ("REMAINING QUESTS: 3", "10/100", "00:00:00", "GET THE APP", "Play Dragon City on your iphone...", "SN") sözlükte yok (İngilizce), bu yüzden bugün kusursuz.
- Etki: Bu alanlar çevrilirse Türkçe harfler boş kalır; `_yazi_tipini_uydur` yalnızca Arial Narrow ve kayıtlı yazı tipi sözlüğü için çalışıyor, `HasFontClass` ile yazı tipi alan sınıflarını (`_font_konumu` None) atlıyor (bu SWF'te böyle alan yok, 0).
- Öneri: Bu alanları çevirmeden önce harf eklemeyi bu yazı tiplerine de yap ya da `_yazi_tipini_uydur` sonucunu test et.

### TRA-06: Yamalı SWF önbelleği birikiyor ve tarayıcı bir gün eski çeviriyi saklıyor
- Önem: Düşük
- İşaret: ◐
- Yer: oyun/swf_yama.py:`onbellekli_turkcelestir`, oyun/varliklar.py:196-208, oyun/sunucu.py (`SEND_FILE_MAX_AGE_DEFAULT = 86400`)
- Kanıt: Önbellek dosyası `...tr-<özet>.swf` (yaklaşık 4,3 MB); özet değişince yenisi yazılıyor, eskisini silen kod yok. SWF her zaman aynı adresten (`.../flash/SocialEmpires1.4.07sec_fixed.swf`) sunuluyor ve `send_file` bir gün `Cache-Control` veriyor.
- Etki: Sözlük güncellenince oyuncu bir gün boyunca eski çeviriyi görebilir (belgedeki "Ctrl+F5" çözümü); disk her çeviri güncellemesinde 4 MB büyür.
- Öneri: Eski `tr-*.swf` dosyalarını sil; yamalı SWF için özetli adres ya da kısa önbellek süresi kullan.

### TRA-07: Eski Flash giriş sayfası (`play.html`) boş `<img>` ve güvenliksiz dış bağlantılar içeriyor
- Önem: Düşük
- İşaret: ✔
- Yer: templates/play.html:33-36
- Kanıt: `<a ...><div><img>Oyna</div></a>`: `src` ve `alt` yok; ayrıca `target="_blank"` bağlantılarında `rel="noopener"` yok (oyun.html'deki eşi var). Bağlantılar üst proje deposuna/Discord'a gidiyor. Sayfa `/flash.html` ile sunuluyor; Playwright'ta ana sayfalar (`/play.html` oyun.html, `/gunluk`, `/profil`, `/hazine`, `/tasima`, `/cevrimdisi`, `/cheat`, `/`) 360 px genişlikte yatay kaydırma, konsol hatası, 404 ya da `alt`ı olmayan resim üretmedi.
- Etki: Çok küçük; boş resim kırık simge olarak görünebilir.
- Öneri: Boş `<img>`i kaldır, `rel="noopener"` ekle.

### TRA-08: `dogrula` yalnızca `#n#`, etiket ve satır sonunu denetliyor; kapsam aracının yer tutucu tanımı daha geniş
- Önem: Düşük
- İşaret: ✔ (şimdilik sorun yok), ? (ileri)
- Yer: oyun/turkce.py:15-17, 156-165; araclar/ceviri_kapsami.py (`_YER_TUTUCU = #\d+#|%[sd]|\{\d+\}`)
- Kanıt: `t1.py`: 4573 çevirinin tamamında `#n#`, `{...}`, `$ad`, etiket ve satır sonu İngilizce asıl ile aynı; `%` farkları yalnızca yüzde işareti (`%50`, `%100`) ve `[915]-ANAHTAR` biçimli geliştirici dolgu metinlerinde. `arayuz_tr.json` 505 girişte yer tutucu/etiket aynı; tek fark `"Throw a dart!\rline"` -> `"Dart at!"` (satır sonu kaybı). Yani bugün kayıp yok, ama `%s`/`{0}` içeren bir çeviri `dogrula`dan geçer (ayrı bir test yok).
- Etki: İleride eklenen çevirilerde sessiz yer tutucu kaybı.
- Öneri: `dogrula`da `%[sd]` ve `{n}`'i de denetle; `test_icerik` ile tr.json'ın tamamına uygula.

## Bakıldı, sorun bulunmadı

- Yamalı SWF bütünlüğü: orijinal 4 288 777 bayt CWS -> 4 291 853 bayt; etiket sayısı (4984) ve türleri aynı, dosya uzunluğu başlığı doğru, son etiket `End`. Yeniden ayrıştırıldı (`t2.py`).
- Yazı tipi tabloları: yamalı DefineFont3 beş yazı tipinde de kod tablosu sıralı ve benzersiz, ofset tablosu artan, ilk glif doğru konumda. Arial Rounded ve Eras Bold'da ç Ç ğ Ğ ı İ ö Ö ş Ş ü Ü hepsi var.
- Metin alanı `MaxLength` aşımı: 0. Sabit genişlikli, kaydırmasız alanlarda Türkçe çevirinin sığmaması tahmini (`t3.py`, yaklaşık): yalnızca bir alan sınırda (%6). Görsel doğrulama yapılmadı.
- Çeviri yer tutucuları ve HTML etiketleri: yukarıdaki TRA-08 ölçümü; `turkce_uygula` hiçbir çeviriyi reddetmedi.
- Sayfalarda kaçışsız kullanıcı verisi: şablonlarda `|safe` yok (Jinja otomatik kaçış), `tojson` yalnızca `<script>`/tek tırnaklı `flashvars` içinde ve `'` kaçışlı; `templates/js/oyun.js`daki `innerHTML` kullanımları yalnızca sayı biçimleri ve repo içi `takvim.json` metni.
- Telefon düzeni (360x740, mobil): sekiz sayfada yatay taşma yok (yalnızca bilerek taşan `.orman` arka plan katmanları), 404 ve konsol hatası yok, resimlerin hepsinde `alt` var, tıklanabilir ama klavyeyle odaklanamayan öğe yok (`cursor:pointer` taraması); etiketsiz tek kontrol gizli dosya girişi (`#dosya`, düğmeyle tetikleniyor).
- Görsel kuralı: CSS'te `radial/conic` degrade yok, `linear-gradient` yalnızca yazı boyası/maske (JS testi de bunu sınıyor); şablon/CSS/JS'te emoji, SVG, `data:` resmi ya da CSS figürü bulunmadı (yalnızca gunluk.html'de `−` yazı işareti). `url(...)` adreslerinin hepsi `/img/`, oyun varlıkları ya da `/fonts/`.
- `fx_yama`: etiket başlığı ve sınıf yeniden adlandırma mantığı okundu, 3 test geçiyor; kapsamlı SWF doğrulaması yapılmadı.
- Testler: test_swf_yama (37), test_fx_yama (3), test_ceviri_kapsami (8), test_icerik (13), `node --test tests/js` (3) geçiyor.
