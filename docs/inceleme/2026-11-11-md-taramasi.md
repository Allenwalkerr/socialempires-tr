# .md taraması (11 Kasım 2026): yapılacak ama kitapta görünmeyen işler

> Bu rapor taramanın ham hâlidir. Bulguların hepsi aynı gün `docs/gorev/BULGULAR.json`'a işlendi (DNT-25 … DNT-40,
> TST-06, OYN-29 … OYN-32, KYN-07, BLG-01) ya da belgelerde düzeltildi; güncel durum için kitaba bakın.

Tarih: 11 Kasım 2026. Salt okunur tarama; depoya hiçbir şey yazılmadı. Kaynak: istenen bütün .md dosyaları baştan sona
okundu (devlog 10 dosya, inceleme 9 .md, denetim 7 + DENETIM.md, FAZ0, TEST_OLCUMU, RESIM_KAYNAKLARI, README, ANDROID,
LINUX, FLASH, CONTRIBUTING, SECURITY, RELEASES, GELISTIRME). `1407-*.json` ve `0926-komutlar.json` veri dosyası olduğu
için satır satır okunmadı. Kitap karşılığı `docs/gorev/BULGULAR.json`'dan (158 madde: 98 düzeltildi, 26 karar_verildi,
11 açık, 10 onay_bekliyor, 6 doğrulandı, 4 çürütüldü, 2 ci_bekliyor, 1 ertelendi) arandı; kod `grep`/okumayla denendi.
Hiçbir test koşturulmadı (yazma/`__pycache__` riski). İşaret: ✔ kodda/kitapta doğrudan gördüm, ◐ dolaylı, ? doğrulayamadım.

Sınıflar: A yapılmış ve kitapta kapalı; B yapılmış ama kitapta açık/eksik; C yapılmamış ve kitapta açık; D yapılmamış ve
kitapta yok; E belge çelişkisi/bayat bilgi.

---

## D. Yapılmamış ve kitapta HİÇ olmayan işler

Denetimin (KAR-13) 47 bulgusundan 17'si hâlâ "denenmedi" ve BULGULAR'da karşılığı yok (kimlik araması: 0 sonuç). 11.11
itibarıyla gerçek dağılım: 26 düzeltildi, 3 karar (DPT-02, DPT-03, SNK-08 via DNT-04), 1 çürütüldü (DPT-01), 17 denenmedi.
`docs/DENETIM.md` hâlâ "17 / 1 / 2 / 3 / 24" yazıyor (E-1 bkz.). Kitapta olmayan 15 bulgu (KYG-04 = DNT-08 zaten açık, TRA-03 yapılmış: B'de; 15+2 = 17):

| Bulgu | Rapor | Özet | Kodda kanıt |
|---|---|---|---|
| EKF-04 | denetim/ekonomi-formuller.md | `TIME_SCALE` yalnız 4 süre alanını ölçekliyor; ölçek 100'de 457 süre alanı <1 sn, ölçek 0,1'de `1.728e+06` biçimi. Sayfadaki hız seçici (ONR-01) artık 10 kata kadar çıkıyor, `COLLECT_MINUTES`, `COLLECT_HELP_SECONDS`, PvP hakkı ölçeklenmiyor | ✔ `oyun/config.py:235` hâlâ `f"{sayi / olcek:.6g}"`, en az 1 sn kıskacı yok |
| EKF-08 | aynı | `upgrade` = `sell`+`buy`; istemci eski binanın XP'sini geri alıyor olabilir, sunucu `sell`de XP geri almıyor (yeniden yüklemede seviye atlama) | ? bayt kodu hiç okunmamış (rapor da "?" diyor); `oyun/komutlar.py:396` `upgrade` yalnız seviye +1 |
| EKF-09 | aynı | PvP sabitleri üç yerde elle kopya, config `globals`'a bağlı değil | ✔ `oyun/denge.py:11-12` ve `oyun/pvp.py:28-29` aynı `3` / `6*3600` |
| SNK-06 | denetim/sunucu-komutlar.md | `orient`/`upgrade`/`push_unit`/`pop_unit` binayı yalnızca (x,y) ile buluyor, bina türü tercih edilmiyor | ✔ `oyun/komutlar.py:101` `esya_bul(h,x,y,esya_id=None)` |
| SNK-07 | aynı | Açık kasaba bellekte; sunucu yeniden başlarsa kasaba numarasız komutlar (`push_queue_unit`, `buy_first_purchase`...) kasaba 0'a gider; `harita()` geçersiz kasabayı sessizce 0 yapıyor | ✔ `oyun/oyuncu.py:21,24` `_acik_kasabalar = {}` |
| DPT-05 | denetim/dunya-pvp-turnuva.md | Turnuva `_bitir`/`_odul_ver` ve haftalık ödül oyuncu kaydını `save_lock` dışında (yalnız `turnuva.KILIT`) değiştiriyor | ✔ `grep save_lock oyun/turnuva.py oyun/diyar.py` boş |
| DPT-07 | aynı | Oyuncuya bot akınında toplam kayıp/sıklık sınırı yok (yalnız 10 dk aralık); KAR-15 yalnız DPT-02'yi (kimler ölür) kapsıyor, sıklık kararı yok | ✔ `ayarlar.json` `oyuncu_saldiri_araligi: 600`, oyuncu için 6 saat/3 hak kuralı yok |
| DPT-08 | aynı | Profil resmi kayıtta base64 (≤~400 KB); her komutta bütün kayıt `fsync`le yeniden yazılıyor, Android pil/depolama | ✔ `oyun/profil.py:58` `kayit["profil_resmi"]` |
| DPT-09 | aynı | `_lonca` binanın bütün `attrs`ini (`bq`, `cp`, `hc`...) `{"workers","hired","guild"}` ile eziyor | ✔ `oyun/dunya.py:380-385` `esya[7] = {...}` |
| TRA-02 | denetim/turkce-arayuz.md | İstemci `toUpperCase` ile bina/metin büyütüyor: "Değirmen" -> "DEĞIRMEN" (İ/ı bozulur), `passFilter` küçük harfte arama | ◐ yamada ya da testte karşılığı yok (`grep toUpperCase oyun/` boş) |
| TRA-04 | aynı | `docs/RESIM_KAYNAKLARI.md` depoda olmayan (silinmiş) görselleri sayıyor; `templates/img/` dosyalarının oyundaki kaynağı hiçbir yerde yazılı değil | ✔ belge hiçbir yerden bağlı değil; `templates/img/gift.png`, `knight.png`, `sword.png`, `villager.png` hiçbir şablonda/kodda kullanılmıyor (gift.png hediye sandığından kalma) |
| TRA-05 | aynı | Curse Casual JVE, Freestyle Script ve Arial Narrow gömülü yazı tiplerinde `ç Ç ğ Ğ ı İ ş Ş` yok; o yazı tipli alanlar çevrilirse boş görünür | ◐ `tests/test_swf_yama.py` yalnız el yapımı yazı tiplerini sınıyor; CEV-04 sonrası bu 6 alanın durumu denetlenmemiş (GEC-06 kapanışı ekran denetimini yazıyor, yazı tipi harf denetimini yazmıyor) |
| TRA-06 | aynı | `download_assets/tr/*.tr-<özet>.swf` birikiyor (her sözlük değişiminde +4 MB), eskisini silen kod yok; tarayıcı 1 gün eski çeviriyi saklıyor | ✔ `oyun/swf_yama.py:327` yalnız yazıyor; `oyun/sunucu.py:120` `SEND_FILE_MAX_AGE_DEFAULT = 86400` |
| TRA-08 | aynı | `turkce.dogrula` yalnız `#n#`, etiket, satır sonunu denetliyor; `%s`/`{0}` kaybı geçer | ✔ `oyun/turkce.py:185-194` |
| EKF-07 | denetim/ekonomi-formuller.md | `docs/inceleme/1407-config-hatti.md` bayat (bkz. E-6) | ✔ tablodaki yamalar `config/patch/`'te yok |

Bunların dışında kitaba hiç yazılmamış, belgelerde geçen işler:

- **D-1. Soru işareti taşıyan sahip eylemi: GitHub Environment (imza sırları).** `docs/DENETIM.md` ("Sizin yapmanız gereken tek ayar"),
  devlog 11-11 "Sonraki adım", DNT-17 notu. BULGULAR'da `açık`/`onay_bekliyor` madde yok; yalnız DNT-17 notunda ve
  `devam_noktasi`'nda düz metin. Yapılınca iş akışına bir satır eklenecek (kodda: `.github/workflows/android.yml` değişmedi, ◐).
- **D-2. Ada Ocağı (`collect_game`) ve viral tekliflerin "açılması" kararı.** `docs/inceleme/1407-formuller.md` ("Açılması ayrı
  karar" iki yerde), devlog 11-05 "Sahibinden beklenenler". Yalnız GEC-03 notunda düz metin; ayrı madde/karar yok. Config'te
  `starts_at`/`duration` 0 (✔ formül defteri), yani komutlar yazıldı ama özellik oyuncuya kapalı.
- **D-3. İstemcide "görsel denetim yapılmadı" borçları (S-35).** BULGULAR'da GEC-02, GEC-03, GOR-01, KYT-01, KAR-10 notları
  "İstemcide görsel denetim yapılmadı" der (yüksek seviyeli hesap SV59, birlik paketi penceresi, eğitim kuyruğu, ilk alım
  teklifi, koleksiyon ödülü "oyunda denenmedi" devlog 11-05, mezarlık/diriltme, Ada Ocağı). Hiçbiri `açık` madde değil.
  GEC-09 (açık) bunları kapsayabilir ama `docs/YOL_HARITASI_1407.md` okunmadığı için kapsamını doğrulayamadım (?).
- **D-4. Kayıt-göç denetim alanı yarım.** `docs/denetim/kayit-goc.md` başlığı "Yarım rapor... dört bulgudan sonrası yazılmadı";
  `docs/DENETIM.md` "Sınır"da söylüyor, KAR-13 notu "altı alanın raporu tamam" diyor. `surum.py` göç adımları, `tasima.py`,
  `kayit_yedek.py` tam denetlenmedi (denetçi 4. bulgudan sonra durdu). Kitapta "alan tamamlanmadı" maddesi yok.
- **D-5. TST (mutasyon) açık uçları.** `docs/TEST_OLCUMU.md` §8: `tests/js` ve istemci ölçülmedi; §12: kalan 534 mutantın
  (komutlar 180, dunya 83) çoğu "tek tek okunmadı"; komutlar oranı %62,4 -> %60,8 (anlamsız fark) ve en geniş kalan havuz.
  TST-02 yalnız testsiz komutları kapsıyor; bu iki iş kitapta yok.
- **D-6. Denge sabitleri sahip kararı bekliyor** (TST-04 notunda düz metin, durum "düzeltildi"): `denge.GANIMET_ORANI 0,10`,
  `GANIMET_TAVANI 50000`, `YENI_OYUNCU_KALKANI 24 sa`, `pvp.GALIBIYET_ASGARI_ALTIN 25`, `XP_PAYI 150`, elo `K 32/16`,
  `BASLANGIC 1500`, `HAFTALIK_MAC 3`, `turnuva.TAKIM_BOYU 20`, bot ağırlıkları, bot aynı hedef 6 sa (istemci 4 sa). KAR-20/OYN-19
  onur için `globals`'a geçti; kalanların kararı için ayrı madde yok. (Not: onur tavanı 10 maddesi OYN-19 ile kapandı, ◐.)
- **D-7. Upstream veri düzeltmelerini "tek tek değerlendir"** (`2026-10-30-upstream-tarama2.md` §6(a) 4. madde ve tarama1 §6
  "0926b'yi de ilgilendiren hata düzeltmeleri": efb753b, 1a51219, ba02772, a437e92, 6f9d792 Konak ev sınırı, e989ba1 ejderha
  yuvası istismarı, 2d39fb4/d76d1ae baskın köylüleri). BULGULAR'da bu commit kimliklerinin hiçbiri yok. 1.4.07 geçişiyle
  `1-mega_patch`/`2-unit_patch` 54df29e'den olduğu gibi alındı (README), yani veri düzeltmeleri büyük olasılıkla zaten içeride
  (B olabilir, ?); ama hiç kontrol/kayıt yok. Davranış düzeltmeleri (e989ba1, 2d39fb4) sunucu koduna ait ve bizim `komutlar.py`
  için değerlendirilmedi (?).
- **D-8. `end_attack_new` indeks 11-12 (kurbana kalkan bayrağı, yıkım yüzdesi) kullanılmıyor.** `docs/inceleme/1407-pvp.md` §3 ve §10
  ("kurbana verilen kalkanın süresi ve koşulu istemcide yok"). Kodda: `oyun/pvp.py:137-200` `yeni_sonuc` `args[11]`/`args[12]`
  okumuyor (✔). Kurbanlar bot olduğu için etkisi küçük olabilir ama karar/not yok.
- **D-9. Olası "öneri akışı" işi: PR incelemesi talimat daraltma** (devlog 11-01 "Sıradaki adım": "ilk birkaç incelemenin yorumları
  okunur; gereksiz uyarı çoksa talimat daraltılır"). Kitapta yok; DAG-13 yalnız tur sınırı ve token yenileme (Kasım 2027) yazıyor.
  Kasım 2027 token yenileme hatırlatıcısı da yalnız DAG-13 notunda (açık madde/rutin yok).
- **D-10. Katkı süreci belgeleri.** CLAUDE.md "Her PR devir notunu günceller" kuralı `CONTRIBUTING.md` ve
  `.github/PULL_REQUEST_TEMPLATE.md`'de yok (şablon yalnız `unittest` ve "Oyun içinde denendi"; `node --test` ve devir notu yok) (✔).
- **D-11. `FAZ0_OLCUMLER.md` §1 son cümle:** "Köylü yürütme ve mağazadan alınan evi yere bırakma bu turda ayrı ayrı sınanmadı."
  F0-01 notu aynısını söylüyor, `açık` değil; GEC-09 "uçtan uca oynanış betiği" ile örtüşür ama açıkça adı geçmiyor (?).
- **D-12. GPLv3 atıf eksiği (düşük).** `2026-10-30-upstream-tarama2.md` §7: `araclar/make_se_unit_patch.py`, `se_unit_patch.csv`,
  `unit_templates.json` upstream 0.04a ile aynı blob; README'nin atıf paragrafı yalnız dört config dosyasını sayıyor
  (`villages/`, `game_config_*.json`, 11 `templates/img` dosyası da 0.04a ile aynı, tarama1 §1). Atıf genel cümleyle var,
  dosya listesi eksik (◐).
- **D-13. Konak/Mağaza rotasyonu, Dart rotasyonu** (tarama1 §2.2, §6 A; tarama2 §4.2): "alınabilir" denmiş, kitapta yok.
  1.4.07'ye geçildiği için Dart (yalnız 0926 ve öncesi) büyük olasılıkla geçersiz (◐); mağaza rotasyonu `takvim` ile örtüşüyor.
  Yine de karar kaydı yok.

---

## E. Belgeler arası çelişki ve güncelliğini yitirmiş bilgi

| # | Yer | Alıntı / sorun | Kodda/kitapta kanıt |
|---|---|---|---|
| E-1 | `docs/DENETIM.md:20,30,33,75` | Sayılar "17 düzeltildi / 1 / 2 / 3 / 24 denenmedi"; "KYG-02, SNK-02 ... sıradaki"; "Kalan 32 bulgu" | ✔ DNT-07 ve DNT-12 #46'da birleşti (devlog 11-11); EKF-02 (DNT-19) ve SNK-03 (DNT-20) #47'de; "Öne alınacaklar: EKF-02, SNK-03" yerine geldi. Gerçek: 26/3/1/17 (yukarıda) |
| E-2 | `docs/GELISTIRME.md:142-144` | "Ruffle'da yere tıklama işlenmiyor ... Saldırı ve turnuva savaşları Ruffle'da oynanamıyor" | ✔ F0-01 çürütüldü (`docs/FAZ0_OLCUMLER.md` §1: harita tıklaması çalışıyor). `docs/GELISTIRME.md` bu bölümü hiç güncellemedi (KYN-04 yalnız fx_yama satırını düzeltti) |
| E-3 | `docs/GELISTIRME.md:146` | "Haftalık turnuva (tür 8) kapalı" | ✔ `config/patch/turnuva.json:2` `TOURNAMENT_ACTIVATED=1` (KNF-04); `docs/denetim/dunya-pvp-turnuva.md` DPT-03 tür 8 turnuvasını açıp bitirdi. Çelişki |
| E-4 | `docs/GELISTIRME.md:145` | "Oyuncu fotoğrafları boş görünür" | ✔ OYN-05: `/profil` fotoğrafı, `playerInfo.pic` doldurulur (kısmen: yalnız oyuncunun kendisi) |
| E-5 | `docs/GELISTIRME.md:24,39` | Komut protokolü "`SocialEmpires0926bsec.swf`" bytecode'undan; `tests/test_komutlar.py` içindeki `test_istemcinin_tum_komutlari_karsilaniyor` | ✔ Bu adlı test yok (`grep` boş). Kapı artık `tests/test_komut_imzalari.py` (`test_1407_*`, `EKSIK_1407 = set()`) ve istemci 1.4.07 (`docs/inceleme/1407-komutlar.md`: G=158, H=159). GELISTIRME.md'de `araclar/abc_okur.py` ve `komut_imzalari.py` hiç anılmıyor |
| E-6 | `docs/inceleme/1407-config-hatti.md` (ve EKF-07) | "bu dosya `araclar/config_hatti.py` ile üretilir; elle düzenlenmez"; `graveyard`, `level_up_tips`, `mission_goals`, `new_daily_bonus`, `viral_*`, `unit_collections`, `soulmixer_temp`, `missions_0_1` yamalarını ölçüyor, `kompu` "çatışır" | ✔ GEC-02 sonrası `config/patch/` = `0-language_en`, `1-mega_patch`, `2-unit_patch`, `kompu`, `turnuva`, `yeni_icerik`; tablo geçişten önceki 13 yamayı anlatıyor. Belge geçmiş ölçümü gösteriyor ama üstünde "güncel değil" notu yok; araç upstream klasörü gerektirdiği için yeniden üretilemiyor |
| E-7 | `docs/TEST_OLCUMU.md:123` (§7 tablo) | Koleksiyon ödülü satırı: "Açık (BULGULAR)" | ✔ BULGULAR KMT-05 `duzeltildi` (PR #37, devlog 11-05); §7 hiç güncellenmedi. Ayrıca §6 madde 4 "teste yazılmadı (§8)" ve §8 "kaynak olmadan beklenen değer yazılmaz" eski; §12'de `test_denge`/`test_dunya` eklendi |
| E-8 | `README.md:48`, `ANDROID.md:10,33,35,9` | "temel ~175 MB, tam ~1,1 GB"; ANDROID "ilk açılışta ~60 MB"; "~250 MB boş yer" | ✔ BULGULAR GEC-08: liste 4751 dosya, temel 210 MB (tam 1110 MB). 210 MB temel paket + APK varken "250 MB boş yer" sınırda |
| E-9 | `README.md:56-75`, `ANDROID.md:19-21` | "Sürümler sayfasından en yeni `SocialEmpiresTR-...-windows.zip`/`-android.apk` indirin" | ✔ `git tag` boş; v0.1.0 yayınlanmadı (GEC-09 açık, sahibin onayını bekliyor). ANDROID.md yayınsız PR APK'sını da anlatıyor (doğru), README yalnız release diyor |
| E-10 | `README.md:26` | "50 bot köyü: gerçek portreler" | ✔ OYN-04: gerçek kişi fotoğrafları silindi; botlar oyunun birim resmini taşıyor. "Gerçek portre" yanlış |
| E-11 | `README.md:37` ve `templates/login.html:17`, `templates/oyun.html:18` yorumları | "Güneş'in gerçek konumuna göre boyanan gökyüzü"; HTML yorumu "gökyüzünün rengi Güneş'in konumuna göre değişir" | ✔ OYN-09: CSS gökyüzü/`gokyuzu.js` kaldırıldı (`templates/js/` yalnız `oyun.js`); gökyüzü oyunun resmi |
| E-12 | `README.md:44` | "istemcinin gönderdiği 120'den fazla komutun tamamını" | ✔ G=158, H=159 (`docs/inceleme/1407-komutlar.md`); sayı eski (128, 0926 dönemi) |
| E-13 | `README.md:86`, `README.md:79` | "Gerekli Python paketleri (`flask`, `jsonpatch`) eksikse otomatik kurulur"; "Python 3.12+" | ✔ `baslat.bat:11` `import flask, jsonpatch, waitress` ve `pip install -r requirements.txt` (waitress, brotli, hijridate de var); Android Python 3.11 (ANDROID/Chaquopy). README özellik listesi ONR-01/02/04, bayram hedefleri, ev ağı parolası, günlük/profil güvenliğini hiç anmıyor (düşük) |
| E-14 | `README.md` "Proje yapısı" tablosu | `oyun/` modülleri eksik: `pvp_yeni.py`, `hiz.py`, `yokken.py`, `bayram_hedefleri.py`, `profil.py` (adı var), `ev_agi.py`, `kaynaklar.py`, `kayit_semasi.py`, `komut_imzalari`... | ✔ `ls oyun/` |
| E-15 | `ANDROID.md:72` | "Sunucu yalnızca cihazın kendisine açıktır (`127.0.0.1:5050`); evdeki başka cihazlar bağlanamaz" | ✔ aynı dosyada "Wi-Fi ile taşı" anlatılıyor; `oyun/tasima.py:93` `create_server(host="0.0.0.0", port=5051)` 10 dk açık (DGV-02/DNT-18). İç çelişki; belgede 5051 geçici gönderici anılmıyor |
| E-16 | `docs/RESIM_KAYNAKLARI.md` bütün dosya | Wikimedia kulüp logoları (Fenerbahçe, Galatasaray, Beşiktaş, Muşspor), fotoğraflar "özgür lisanslı bot profil resimleri" diye sayılıyor | ✔ bu görseller silindi (`oyun/bot_kimlik.py:13` `SILINEN_PORTRELER`); `templates/img/profile/` yalnız `1025.png`. Belge CLAUDE.md "yalnızca oyunun kendi resimleri" kuralına aykırı bir kaynak politikasını anlatıyor, hiçbir belgeden bağlı değil. **Kurala aykırı, yapılmaz; belge silinmeli ya da "kaldırıldı" notu almalı** |
| E-17 | `docs/inceleme/ceviri-kapsami.md:18` | "Kapı: ilk beş satırın hepsinde T = 1" | ◐ tabloda sabit yazılar 44/46 (0,957) ve AS3 213/219 (0,973) ≠ 1; GEC-06 kapanışı bunu "iki kanıtlı istisna" diye kapatıyor (BULGULAR) ama belgede istisna ifadesi "kapı" cümlesiyle çelişik duruyor (araç metni sabit) |
| E-18 | `docs/inceleme/1407-mezarlik.md:60-61` vs `1407-pvp.md:148` | Savunmacı kurtarmada biri "yalnız `protect==1` kurtarılabilir", ötekisi "`protect==1` düşülmez (hep kurtarılır)"; araştırma "yön tersi gibi (?), bu sorunun dışı" | ◐ çözülmemiş çelişki; kodda `oyun/pvp.py`/`oyun/dunya.py`'de `protect` geçmiyor (✔ `grep`), savunmacı kaybı `0.45` sabit oranla. Doğru yön bayt kodundan okunmadı |
| E-19 | `docs/inceleme/2026-10-30-upstream-tarama1.md` §2.5, §6 ve `-tarama2.md` §6 | "0926'da kal (A) önerilen yol" | ✔ KAR-08 ile geçersiz; yalnız `-1407-gecis-plani.md` §4 "Geçersiz" etiketi taşıyor, tarama1/tarama2 üstünde "karar KAR-08 ile değişti" notu yok. KYN-01 (karar_verildi) kitapta düzeltmiş |
| E-20 | `RELEASES.md` (bütün dosya), `LINUX.md`, `FLASH.md` | İngilizce upstream kopyası; RELEASES tablosu 0.01a-0.04a bağlantıları `../../releases/download/0.04a/...` bu depoda yok; LINUX/FLASH yalnız Flash Player'dan söz ediyor, Ruffle'dan hiç | ✔ `git tag` boş; README FLASH.md/LINUX.md'ye "Ayrıntılar" diye bağlıyor ama Ruffle kurulumunu anlatmıyor. RELEASES.md hiçbir yerden bağlı değil |
| E-21 | `docs/DENETIM.md` (Kararlarınız) vs KAR-17 | Doğru; ama "Sonraki aşamalar" tablosunda TRA-01/DPT-04/DPT-06 "düzeltildi" yazıyor, BULGULAR'da bu üç kimlik yok (CEV-03, KYT-03, OYN-19 karşılığı) | ◐ DPT-04 = KYT-03 (kod `oyun/kayit.py:288-291`, `pvp_yeni.py:51`), DPT-06 = OYN-19; denetim kimliğinden kitaba çapraz bağ yok (kitap "kanit"ında DPT-04/06 geçmiyor) |

---

## B. Yapılmış ama kitapta açık / eksik kayıtlı

| Madde | Neden B | Kanıt |
|---|---|---|
| KYN-02 (açık) Mağazadaki Soul Mixer 0926'da işlevsiz | Soul Mixer artık 1.4.07'de çalışıyor; `soulmixer_temp.json` silindi (GEC-02). Madde hâlâ `acik` | ✔ `config/patch/` içinde yok; `buy_powerups`, `push_queue_unit` Soul Mixer'ı destekliyor |
| KYN-04 (açık) Ölü yamalar + bayat belgeler | Üç belge düzeltildi (#19, notta), yamalar KNF-01/GEC-02 ile ayrıştırıldı ve silindi/kapsandı; durum yine `acik` | ✔ `config/patch/` 6 dosya; KNF-01 `dogrulandi` |
| KYT-02 (açık) Yeni alanlar yokken özellikler kapalı | Kuyruk (#26), Ada Ocağı, mezarlık (#28/#37/#51: OYN-25 `resurrectableUnits`), ilk alım (KAR-10) açıldı; günlük ödül (OYN-11) hâlâ açık. Madde başlığı bayat | ✔ `oyun/komutlar.py` işleyicileri; `kayit_semasi.py` |
| TRA-03 | `docs/inceleme/ceviri-kapsami.md` yeniden üretildi (1976/1976, 4567/4567); denetim kimliği kitapta yok | ✔ belge güncel; kitapta karşılık yok |
| DPT-04, DPT-06 | Düzeltildi (KYT-03, OYN-19) ama BULGULAR'da denetim kimliğiyle işaretli değil | ✔ bkz. E-21 |
| SNK-08 | "Giriş sayfası her çağrıda yeniden yüklüyor" DNT-04(6)'da "kalır" kararı var ama denetim kimliği geçmiyor | ✔ `oyun/sunucu.py:198` hâlâ `load_saved_villages()` |
| DENETIM.md "Düzeltilenler" PR sütunu | KYG-02/SNK-02 "sıradaki": #46'da birleşti | ✔ devlog 11-11 |
| FAZ0_OLCUMLER.md "Tek eksik dosya: fx/p.miniFireball2.swf (404)" | VAR-01 duzeltildi; belge cümlesi kendi içinde "sonradan kapandı" diyor (tutarlı) ama GELISTIRME `Bilinen eksikler` hâlâ var | ✔ `oyun/fx_yama.py` |
| 1407-hedefler.md §7 önerileri (id blokları, `orders:-1`, önbellek anahtarı, `reward_mission`) | Uygulandı (GEC-07, `oyun/bayram_hedefleri.py:66` `orders: -1`); GEC-07 `◐`: "`orders -1` gerçek sıralamasını çalıştırarak doğrulamadım (?)" kapanmamış | ✔ kod; sıralama ? |
| 1407-mezarlik.md "Sunucu önerisi" 1-6 | Uygulandı (OYN-25..28); madde 4 kapasite sınırı "◐ karar" olarak bırakılmıştı | ✔ `oyun/komutlar.py:1569 mezarliga_ekle`, 1619 diriltme |
| 1407-pvp.md §9 liste (get_enemy_new, begin/end_attack_new, buy_shield, reset_shield, reply_attack, clean_attack_log, end_tournament_match) | Hepsi yazıldı (GEC-05, #49-#52); `attacksLost` sayacı da (`oyun/pvp.py:156`) | ✔ `oyun/pvp_yeni.py`, `komutlar.py:2171-2219` |
| Tarama1 "VAR-01 bayat belgeler" | Düzeltildi (#19) | ✔ |
| Tarama2 §6(a) 1. (varlık kaynağını sabitle) | Yapıldı (KYN-03, DNT-16) | ✔ `oyun/kaynaklar.py` |

---

## C. Yapılmamış, kitapta açık madde olarak var (yalnız kimlik)

- Durum `acik` (11): OYN-11, OYN-12, OYN-13, OYN-15, KYN-02*, KYN-04*, KYT-02*, GEC-09, ONR-03, TST-02, DNT-08.
  (* yukarıda B: iş bitmiş, durum bayat.)
- `onay_bekliyor` (10): DAG-04, DAG-05, OYN-05, DAG-12, DNT-02, OYN-07, OYN-08, VAR-03, KMT-08, KMT-09.
- `ci_bekliyor` (2): ONR-01, ONR-02. `ertelendi` (1): HIZ-02.
- Karar bekleyen/sahip işi, durumu `karar_verildi` ama iş yapılacak: KAR-09 (imza anahtarı en son iş), DNT-17 notundaki GitHub Environment.
- Doğrulananlar (`dogrulandi`) kalan iş içerenler: GEC-03 (◐, "istemcide görsel denetim yok"), KMT-01 (0926 komutları; bugün 1.4.07'de konu kapalı, B olabilir), CEV-01 (0926 AS3 dizeleri; 1.4.07'de CEV-04 ile kapandı, B), TST-03.
- Kodla doğruladıklarım: OYN-15 hâlâ açık (✔ `oyun/turnuva.py:218` `"tournament_reward_id": {str(k): 0 ...}`, `turnuva.py:239` `reward_id = random.randrange(...)`; notta "GEC-05'te okunacak" deniyor ama GEC-05 bunu yapmadan kapandı, not bayat).

---

## A. Yapılmış ve kitapta kapalı

Yaklaşık 70 aday iş (elle sayım, kesin değil): devlog "Sıradaki adım" maddelerinin çoğu (GEC-01..08, KAR-10..22, ONR-01/02/04 hariç
olanlar), denetimin 26 düzeltilen bulgusu, `1407-pvp`/`mezarlik`/`hedefler`/`formuller` önerilerinin uygulananları,
bot adları/portre sorunu (OYN-04), Android alt maddeleri (DAG-05..12 kod kısmı), TST-01/03/04/05, DNT-05..24.

---

## Kurala aykırı öneriler (iş sayılmaz)

- `docs/RESIM_KAYNAKLARI.md` (E-16): internetten/Wikimedia'dan görsel (kulüp logosu, fotoğraf) kullanımı; CLAUDE.md "Görseller"
  kuralına aykırı, kaldırıldı (OYN-04); yapılmaz.
- Devlog 10-30-2: sahibi "ünlü adları ve internetten fotoğrafları" önce istedi, sonra bıraktı; depoya girmedi. İş değil.
- DGV-01/SNK-05 "jeton/parola" önerileri, tarama2 (d) "upstream'e katkı": kurala aykırı değil ama çok oyunculu değil; iş sayılmadı (parola DNT-13 ile yapıldı).
- `KMT-09` Asker Toplama için "arkadaş daveti" gerektiriyor: çok oyunculu davet eklenmez (kural); "bot yardımcılarıyla açma" ayrı karar olarak kitapta duruyor, iş sayılmadı.
- Aykırı öneri bulunmadı: tek kişilik/çevrimdışı kuralına, günlük ödül kuralına ya da CSS/emoji figür kuralına aykırı yeni bir öneri yok (denetim `BRIEF.md` bunları kapsam dışı ilan etmiş).
