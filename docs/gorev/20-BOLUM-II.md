# SOCIAL EMPIRES TR GÖREV KİTABI: BÖLÜM II (açık işler ve sahibinin testleri)

Önce `00-CEKIRDEK.md` dosyasını oku. Bu dosya §6 (açık işler) ve §7 (sahibinin elle yapacağı testler) bölümlerini içerir.

## 6. Açık işler

`BULGULAR.json`'da durumu `acik`, `onay_bekliyor`, `ertelendi` ya da `engelli` olan maddeler. Yeni işe başlamadan
önce buradan seç; sahibinin kararı gerekenleri ona sor.

11 Kasım 2026 durumu (.md taramasından sonra; asıl kayıt `BULGULAR.json`, çelişirse JSON geçerlidir).

| Madde | Durum | Ne gerekiyor |
| --- | --- | --- |
| GEC-09 | acik | Kabul: uçtan uca oynanış betiği, oyunda gözle bakılmamış pencereler (notunda liste), sahibinin tablet denemesi, v0.1.0 |
| ONR-02 | ci_bekliyor | "Sen yokken" özeti, #60 |
| ONR-03 | acik | Android bildirimleri; "inşaat bitti" başlamadan önce sahibine sorulur (KAR-22) |
| OYN-11, KYT-02 | acik | 1.4.07'nin 5 günlük günlük ödülü kapalı; başlığı boş pencere |
| OYN-12, OYN-13 | acik | Seviye/XP bilgisi yenilenmiyor; "Yedek yükle" klavyeyle açılmıyor (önce yeniden üretilir) |
| OYN-15 | acik | Turnuvada gösterilen ödül ile verilen farklı |
| OYN-31, OYN-32 | acik | PvP: end_attack_new 11-12. argümanlar; savunmada kurtarma yönü (bayt kodundan okunacak) |
| DNT-25 … DNT-39 | acik | Bağımsız denetimin kitaba yazılmamış 15 bulgusu (hepsi Düşük) |
| DNT-40 | acik | Kayıt göçü denetim alanı yarım |
| DNT-08 | acik | Başka cihaza taşınan 0.06a kayıtta görev numaraları (karar gerekebilir) |
| TST-02, TST-06 | acik | Testsiz komutlar; mutasyon ölçümünün açık uçları |
| KYN-07 | acik | Upstream düzeltmelerinin değerlendirilmesi |
| BLG-01 | ci_bekliyor | Bayat belgeler (bu taramanın PR'ı) |
| KMT-08, KMT-09, OYN-29, OYN-30 | onay_bekliyor | Sahibinin kararı: görev sınırı, Asker Toplama, Ada Ocağı ve viral teklifler, denge sabitleri |
| DAG-04, DAG-05, DAG-12, DNT-02, OYN-05, OYN-07, OYN-08, VAR-03 | onay_bekliyor | Sahibi 1.4.07 sürümünde tablette dener (§7.4) |
| HIZ-02 | ertelendi | Mobil LCP 3,7 sn (yavaş 4G benzetimi); ev ağında sorun beklenmiyor |
| KAR-09 | karar_verildi | En son iş: Android imza anahtarı; ayrıca GitHub Environment ayarı (`docs/DENETIM.md`) |

## 7. Sahibinin elle yapacağı testler

### 7.1 Telefon ve tablet (DAG-04)

Benzetimde (`node araclar/cihaz_denemesi.js <USERID> klasor --dokun`) iPhone, Pixel ve iPad dik/yatayda düzen
doğru; gerçek Safari ve gerçek parmakla deneme yine de gerekli.


1. Bilgisayarda `ayarlar.json` dosyasında `"ev_agi": true` yapın ve oyunu başlatın.
2. Sunucunun açılışta yazdığı `http://192.168.x.x:5050/` adresini telefonda açın (aynı Wi-Fi).
3. İmparatorluğa girin, "Krallığa Gir"e basın, bir binaya dokunun, haritayı parmakla kaydırın.
4. Oyundan çıkıp yeniden girin: yaptığınız değişiklik duruyor mu?
5. Aynısını iPad'de deneyin. Sonucu ("çalıştı" ya da gördüğünüz hata) bildirin.

### 7.2 Ateş topu efekti (VAR-01)

Ateş topu atan bir birimle saldırıya geçin ya da saldırıya uğrayın; ateş topu görünüyor mu? Görünmüyorsa ya da tuhaf
görünüyorsa bildirin.

### 7.3 Windows paketi

İlk sürümü yayınlamak için etiket gönderin (ya da bunu yapay zekâ oturumundan isteyin):

```bash
git tag v0.1.0
```

```bash
git push origin v0.1.0
```

Sürüm sayfasındaki zip'i Python kurulu olmayan bir bilgisayarda açıp `Social Empires.bat` dosyasına çift tıklayın.

### 7.4 Tablet denemesi, 1.4.07 sürümünde (GEC-09)

Sahibi PR #18 APK'sını denemeyecek, denemeyi 1.4.07'ye geçiş bitince yapacak (KAR-08). O sürümde bakılacaklar:

1. Yükleme perdesinde "Yükleniyor" yazıyor mu, "Cargando" var mı? (VAR-03)
2. Yüksek kalitede dokunulan yerde koyu yeşil iz kalıyor mu? (OYN-07)
3. Görüntü: Doldur oyunu esnetmeden ekranı kaplıyor mu? (OYN-08)
4. Geri tuşu, durum ve gezinme çubukları (DAG-12); galeriden profil resmi (OYN-05); klavye (DNT-02).

### 7.5 Android imza anahtarı (bir kez)

Sahibinin kararı (KAR-09): bütün işler bittikten sonra, **en son iş** olarak yapılır. Adımlar `ANDROID.md` "İmza
anahtarı" bölümünde. O zamana kadar her yeni APK'da yedek al, kaldır, kur, yükle gerekir.
