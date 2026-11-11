# Bağımsız denetim: özet (KAR-13)

Kasım 2026. Kod altı alana bölündü. Her alana, önceki bulguları ve devir notlarını görmeyen ayrı bir denetçi baktı.
Ortak kurallar `docs/denetim/BRIEF.md`'de, raporlar `docs/denetim/<alan>.md`'de. Denetçinin her bulgusu kitaba
geçmeden önce yeniden üretildi; üretilemeyen bulgu `?` ile bekliyor.

**Sınır.** Denetçiler aynı model ailesinden; bir insan denetçi kadar bağımsız değiller. Kayıt alanının raporu yarım:
denetçi kullanım payı yüzünden durduruldu ve dört bulgudan sonrası yazılmadı.

## Sayılar

11 Kasım 2026 durumu (her bulgu `docs/gorev/BULGULAR.json`'daki karşılığıyla yeniden sayıldı):

| Alan | Bulgu | Düzeltildi | Çürütüldü | Karar: böyle kalır | Açık (kitapta) |
|---|---:|---:|---:|---:|---:|
| Kayıt ve göç (yarım) | 4 | 3 | 0 | 0 | 1 |
| Ekonomi ve formüller | 9 | 5 | 0 | 0 | 4 |
| Sunucu ve komutlar | 9 | 6 | 0 | 1 | 2 |
| Bot dünyası, PvP, turnuva | 9 | 2 | 1 | 2 | 4 |
| Türkçe ve arayüz | 8 | 3 | 0 | 0 | 5 |
| Dağıtım ve güvenlik | 8 | 8 | 0 | 0 | 0 |
| **Toplam** | **47** | **27** | **1** | **3** | **16** |

Açık 16 bulgunun kitaptaki karşılıkları: KYG-04 → DNT-08; EKF-04, EKF-07, EKF-08, EKF-09, SNK-06, SNK-07, DPT-05,
DPT-07, DPT-08, DPT-09, TRA-02, TRA-04, TRA-05, TRA-06, TRA-08 → DNT-25 … DNT-39 (11.11.2026'ya kadar kitaba hiç
yazılmamışlardı; .md taramasında bulundu). Karar: SNK-08 (giriş sayfasında yeniden okuma kalır, DNT-04),
DPT-02 (KAR-15), DPT-03 (KAR-16). Yarım kalan kayıt alanı: DNT-40.

Önem: 3 Yüksek, 13 Orta, 31 Düşük. Üç Yüksek bulgunun üçü de düzeltildi.

## Düzeltilenler

| Bulgu | Ne oluyordu | Kitap | PR |
|---|---|---|---|
| KYG-01 | Kimliği sayı olan kayıt sunucunun açılışını çökertiyordu | DNT-05 | #45 |
| KYG-03 | Yedekten (`.bak`) geri alınan kayıt güncellenmiyordu | DNT-06 | #45 |
| KYG-02 | İçe aktarmadan önceki kayıt korunmuyordu (yalnızca `.bak`'ta kalıyor, o da eziliyordu) | DNT-07 | #46 |
| EKF-01 | Değirmen ve madenlerde seçilen süre yok sayılıyordu (8 saatte ekranda 900, kayıtta 300) | DNT-09 | #45 |
| SNK-01 | Seviye atlama ödülü (çoğu seviyede nakit) kayda yazılmıyordu | DNT-10 | #45 |
| SNK-02 | Bağlantı gecikince istemcinin yeniden yolladığı komut paketi iki kez uygulanıyordu | DNT-12 | #46 |

## Çürütülen

| Bulgu | Neden |
|---|---|
| DPT-01 (ilk hâli) | "Teslim olmak zafer sayılıyor" yanlış: istemci teslim olunca `win: 0` gönderir. Denetçinin okuma aracı (`abc_okur.cagrilar`) koşullu değeri tek sabit gibi gösteriyordu (S-63). Denetçi raporunu düzeltti. |

## Kararlarınız (11 Kasım 2026)

| Bulgu | Karar |
|---|---|
| DPT-02 | Karar verildi (KAR-15): bot akınları böyle kalır. |
| DPT-03 | Karar verildi (KAR-16): turnuva puanına sınır konmaz. |
| SNK-05, DGV-01 | Karar verildi (KAR-17): ev ağı parola ister. Düzeltildi: DNT-13. |
| EKF-03 | Karar verildi (KAR-18): kaynak yetmezse alım reddedilir. Düzeltildi: DNT-14. |

## Güvenlik düzeltmeleri (KAR-17: "güvenlikle ilgili ne varsa hallet")

| Bulgu | Ne yapıldı | Kitap |
|---|---|---|
| DGV-01, SNK-05 | Ev ağı açıkken her cihaz parola girer; parola açılışta konsola yazılır | DNT-13 |
| DGV-02 | Wi-Fi taşımada kod başlıkta; tek cihaz yanlış denemelerle aktarımı kapatamaz | DNT-18 |
| DGV-03 | CI imza sırları yalnızca ana dalda ve etiketlerde; eylemler SHA'ya sabit | DNT-17 |
| DGV-04, DGV-05 | İndirilen her varlık sabit commit'in özetiyle denetlenir; uydurma adlar indirilmez | DNT-16 |
| DGV-06, DGV-07 | Android: hata ayıklama yalnızca sınama yapısında; yedek yalnızca uygulamanın sunucusundan; bulut yedeğine günlük ve ayar girmez | DNT-17 |
| DGV-08, SNK-09 | Bağımlılıklar sabit; gömülü Python özetle denetlenir; günlükler sınırlı; oturum anahtarı yalnızca sahibine okunur | DNT-15, DNT-17 |

**Sizin yapmanız gereken tek ayar:** GitHub'da depo ayarlarından (Settings → Environments) bir "Environment"
açıp imza sırlarını (`ANDROID_IMZA`, `ANDROID_IMZA_SIFRESI`) oraya taşımak ve yalnızca `master` ile `v*`
etiketlerine izin vermek. Bunu yalnızca depo sahibi yapabilir; yapılınca iş akışına bir satır eklenir.

## Sonraki aşamalarda ele alınacaklar

| Bulgu | Aşama |
|---|---|
| TRA-01: 206 hedefin (görev) metinleri Türkçe değil | GEC-06 (Türkçe): düzeltildi, CEV-03 (410/410) |
| DPT-04: sunucunun kalkanı ile istemcinin kalkanı ayrı | GEC-05 (PvP), KYT-03: düzeltildi, #49 |
| DPT-06: saldırı onuru config'ten farklı | GEC-05: düzeltildi, OYN-19 (#50; onur globals HONOR_POINT_PVP_*) |

## Denenmeyenler

Bu bölüm 11.11.2026'da kapandı: denenmeyen bulguların hepsi kitapta açık madde (yukarıdaki "Sayılar"). Öne
alınanlardan EKF-02 (DNT-19) ve SNK-03 (DNT-20) #47'de düzeltildi; KYG-04 DNT-08'de açık. Ayrıca düzeltilenler:
EKF-03 (DNT-14), EKF-05 (DNT-22), EKF-06 (DNT-23), SNK-04 (DNT-24), TRA-03 (`docs/inceleme/ceviri-kapsami.md`
GEC-06'da yeniden üretildi), TRA-07 (DNT-21), DGV-01 … DGV-08 ve SNK-05, SNK-09 (DNT-13 … DNT-18).
