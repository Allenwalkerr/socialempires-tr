# Bağımsız denetim: özet (KAR-13)

Kasım 2026. Kod altı alana bölündü. Her alana, önceki bulguları ve devir notlarını görmeyen ayrı bir denetçi baktı.
Ortak kurallar `docs/denetim/BRIEF.md`'de, raporlar `docs/denetim/<alan>.md`'de. Denetçinin her bulgusu kitaba
geçmeden önce yeniden üretildi; üretilemeyen bulgu `?` ile bekliyor.

**Sınır.** Denetçiler aynı model ailesinden; bir insan denetçi kadar bağımsız değiller. Kayıt alanının raporu yarım:
denetçi kullanım payı yüzünden durduruldu ve dört bulgudan sonrası yazılmadı.

## Sayılar

| Alan | Bulgu | Düzeltildi | Çürütüldü | Kararınızı bekliyor | Sonraki aşamada | Denenmedi |
|---|---:|---:|---:|---:|---:|---:|
| Kayıt ve göç (yarım) | 4 | 3 | 0 | 0 | 0 | 1 |
| Ekonomi ve formüller | 9 | 1 | 0 | 1 | 0 | 7 |
| Sunucu ve komutlar | 9 | 2 | 0 | 1 | 0 | 6 |
| Bot dünyası, PvP, turnuva | 9 | 0 | 1 | 2 | 2 | 4 |
| Türkçe ve arayüz | 8 | 0 | 0 | 0 | 1 | 7 |
| Dağıtım ve güvenlik | 8 | 0 | 0 | 1 | 0 | 7 |
| **Toplam** | **47** | **6** | **1** | **5** | **3** | **32** |

Önem: 3 Yüksek, 13 Orta, 31 Düşük. Üç Yüksek bulgunun üçü de düzeltildi.

## Düzeltilenler

| Bulgu | Ne oluyordu | Kitap | PR |
|---|---|---|---|
| KYG-01 | Kimliği sayı olan kayıt sunucunun açılışını çökertiyordu | DNT-05 | #45 |
| KYG-03 | Yedekten (`.bak`) geri alınan kayıt güncellenmiyordu | DNT-06 | #45 |
| KYG-02 | İçe aktarmadan önceki kayıt korunmuyordu (yalnızca `.bak`'ta kalıyor, o da eziliyordu) | DNT-07 | sıradaki |
| EKF-01 | Değirmen ve madenlerde seçilen süre yok sayılıyordu (8 saatte ekranda 900, kayıtta 300) | DNT-09 | #45 |
| SNK-01 | Seviye atlama ödülü (çoğu seviyede nakit) kayda yazılmıyordu | DNT-10 | #45 |
| SNK-02 | Bağlantı gecikince istemcinin yeniden yolladığı komut paketi iki kez uygulanıyordu | DNT-12 | sıradaki |

## Çürütülen

| Bulgu | Neden |
|---|---|
| DPT-01 (ilk hâli) | "Teslim olmak zafer sayılıyor" yanlış: istemci teslim olunca `win: 0` gönderir. Denetçinin okuma aracı (`abc_okur.cagrilar`) koşullu değeri tek sabit gibi gösteriyordu (S-63). Denetçi raporunu düzeltti. |

## Kararınızı bekleyenler

| Bulgu | Soru |
|---|---|
| DPT-02 | Bot akınında köylüler, şifacılar ve nakitle alınmış birimler de ölüyor. Hepsinin saldırı gücü var (köylü 6, şifacı 15), yani bu bir hata değil, denge kararı. Akınlarda yalnızca asker mi ölsün, yoksa böyle mi kalsın? |
| DPT-03 | Turnuva puanı istemciden olduğu gibi alınıyor. Puan ancak elle hazırlanmış bir istekle şişirilebilir; hile paneli zaten var. Bir üst sınır konulsun mu? |
| SNK-05, DGV-01 | "Ev ağı" ayarı açıkken ağdaki başka bir cihaz parolasız girip kaydı değiştirebiliyor. Bu ayar için bir parola mı istensin, yoksa bilerek açık mı kalsın? |
| EKF-03 | Sunucu kaynak yetiyor mu diye bakmıyor; yalnızca bozuk istemci komutunda bedava kaynak çıkar. Sunucu yetmeyen alımı reddetsin mi? |

## Sonraki aşamalarda ele alınacaklar

| Bulgu | Aşama |
|---|---|
| TRA-01: 206 hedefin (görev) metinleri Türkçe değil | GEC-06 (Türkçe) |
| DPT-04: sunucunun kalkanı ile istemcinin kalkanı ayrı | GEC-05 (PvP), KYT-03 |
| DPT-06: saldırı onuru config'ten farklı | GEC-05 |

## Denenmeyenler

Kalan 32 bulgunun çoğu Düşük önemde; raporlarda yerleri ve öneriyle duruyorlar. Sırayla yeniden üretilip kitaba
(`docs/gorev/BULGULAR.json`) işlenecek. Öne alınacaklar: EKF-02 (çiftlikte odun düşümü), SNK-03 (eşya yokken depoya
ekleme), KYG-04 (başka cihaza taşınan eski kayıtta görev numaraları).
