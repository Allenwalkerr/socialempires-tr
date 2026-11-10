# Denetim raporu: dagitim-guvenlik (DGV)

Kapsam: `android/`, `.github/workflows/`, `araclar/windows_paketi.py`, `android_paketi.py`, `baslat.bat`, `server.py`, `varliklari_indir.py`, `oyun/varliklar.py`, `kaynaklar.py`, `onindirme.py`, `ruffle.py`, `ayarlar.py`, `hile.py`, `tasima.py`, `kayit_yedek.py`, `sunucu.py` (ağ/oturum/statik), `requirements*.txt`, `SECURITY.md`.
Araçlar: `is/dagitim-guvenlik/` (`g1.py` LAN senaryosu, `g2.py` yol geçişi). Testler: test_android (12), test_onindirme (10), test_http (20) geçiyor.

### DGV-01: `ev_agi` açıkken ağdaki herhangi bir cihaz parolasız oyuncu olabilir, kaydı indirir ve ezer (SNK-05'in derinleştirilmesi)
- Önem: Orta (yalnızca `ayarlar.json` `ev_agi: true` iken; varsayılan false)
- İşaret: ✔
- Yer: oyun/sunucu.py:87-110, 186-205 (`login`), oyun/kayit_yedek.py:103-130, oyun/istemci.py `command.php`
- Kanıt: `g1.py`, Flask test istemcisi, `REMOTE_ADDR=192.168.1.77`, `Host: 192.168.1.10:5050` (LAN istemcisi): `GET /` oyuncu kimliklerini listeledi (kimlik sayfada var: True) -> `POST / USERID=<kimlik>` 302 (parola yok) -> `GET /kayit/indir` 200 (2983 bayt kayıt) -> kayıt JSON'u düzenlenip SHA-256'sı yeniden hesaplanarak `POST /kayit/yukle` 200 `{"durum":"ok"}`; sonuç `coins = 999999999`. `get_player_info.php` da 200. Engellenenler: `/cheat` 403 (yalnızca loopback), `Origin: http://kotu.site` ya da `Sec-Fetch-Site: cross-site` 403, loopback'ten gelen `Host: kotu.site` 403 (DNS yeniden bağlama savunması çalışıyor).
- Etki: Aynı Wi-Fi'daki herkes bütün imparatorlukları okuyabilir, değiştirebilir, silebilir ya da yedekle ezebilir. `ayarlar.json` uyarısı bunu söylüyor, ama Android yedeği `ayarlar.json`ı da taşıyor (DGV-07), yani seçenek yeni cihaza sessizce geçer.
- Öneri: `ev_agi` kipinde oyun uçları için ilk girişte üretilen bir jeton/çerez iste (Android'deki `SE_UYGULAMA_JETONU` mantığı masaüstüne de açılabilir).

### DGV-02: Wi-Fi taşıma gönderici sunucusu her arayüzde, düz HTTP ile ve 6 haneli kodla açılıyor
- Önem: Düşük
- İşaret: ◐
- Yer: oyun/tasima.py:60-110 (`gonderimi_baslat`, `_kod_dogru`, `_getir`)
- Kanıt: `create_server(gonderici, host="0.0.0.0", port=5051)` `ev_agi` ayarından bağımsız; kod `?kod=` sorgu dizesinde düz HTTP ile gider, yanıt bütün kayıt zarfıdır. Kod yanlış deneme sayacı gönderen için toplam 10 ile sınırlı: 10 yanlışta kod iptal olur (tahmin ihtimali 10/10^6), ama aynı sayaç ağdaki herkesin elinde bir "durdur" düğmesidir (10 yanlış istek aktarımı kapatır). Alan cihaz SSRF'i `_ev_agi_adresi` (özel IPv4, döngü adresi/link-local yok, yönlendirme izlenmez, yalnızca 5051) ile sınırlı: sorun bulunmadı.
- Etki: Aynı ağda dinleyen biri 10 dakikalık pencerede kodu ve kaydı düz metin görür; ağdaki biri aktarımı sürekli bozabilir.
- Öneri: Kodu istek gövdesine/başlığa al, kısa süreli HTTPS ya da kodla türetilmiş şifreleme düşün; yanlış denemeyi IP başına say.

### DGV-03: Sır taşıyan iş akışları PR koduyla çalışıyor; eylemler etiketle, SHA ile değil sabitlenmiş; etiket adı betiğe girmeden enjekte ediliyor
- Önem: Düşük
- İşaret: ◐
- Yer: .github/workflows/android.yml (`pull_request`, "İmza anahtarı", "APK"), windows.yml, tests.yml; android.yml:33-52
- Kanıt: `android.yml` `pull_request` ile (yol süzgeciyle) çalışır; aynı depodan açılan PR'larda `secrets.ANDROID_IMZA` ve `ANDROID_IMZA_SIFRESI` ortama girer ve PR'ın kendi `araclar/`, `android/`, gradle ve iş akışı dosyası çalıştırılır: depoya yazma izni olan biri iş akışını değiştirip anahtarı çıkarabilir (fork PR'larında sır gelmez; `claude-inceleme.yml` fork'u ve Dependabot'u açıkça dışlıyor, doğru). `permissions: contents: read` her yerde, `surum` işlerinde yalnızca etiketle `contents: write`: iyi. `pull_request_target` yok. Üçüncü taraf eylemler (`actions/*@v7`, `gradle/actions/setup-gradle@v6`, `reactivecircus/android-emulator-runner@v2`) yalnızca etiketli; yalnızca `claude-inceleme.yml` SHA'ya sabitli. `npm install playwright-core@1.63.0` kilit dosyası olmadan. `windows.yml:41` ve `android.yml:82-83`te `${{ steps.ad.outputs.ad }}` doğrudan kabuk metnine yerleşir; `ad` etiket adından (`GITHUB_REF_NAME`) türer, git etiket adları `$`, `(`, `;`, `` ` `` içerebilir (yalnızca yazma izni olan biri etiket atabilir).
- Etki: Yazma izni olanlar için imza anahtarı sızdırma ve etiket adıyla komut enjeksiyonu yolu; üçüncü taraf eylem etiketi kaydırılırsa derleme zinciri değişir.
- Öneri: İmza adımını yalnızca etiket/ana dalda, bir "ortam" (onaylı) altında çalıştır; eylemleri SHA'ya sabitle; `${{ }}` değerlerini `env:` üzerinden ver.

### DGV-04: Yalnızca istemci SWF'sinin özeti denetleniyor; öteki indirilen SWF/ses/görsel dosyaları yalnızca "boş ya da HTML değil" denetiminden geçiyor
- Önem: Düşük
- İşaret: ✔ (kod), ◐ (etki)
- Yer: oyun/varliklar.py:30-45 (`_gecerli_dosya`), :60-85 (`VARLIK_KAYNAKLARI`, `_indir_dene`), :96-110 (`OZETLER`), oyun/onindirme.py, config/onindirme.tsv
- Kanıt: `OZETLER` yalnızca `flash/SocialEmpires1.4.07sec_fixed.swf`ü (SHA-256) içeriyor. Öteki ~4800 varlığın (efekt, arayüz, ses SWF'leri dahil: Ruffle bunları oyunla aynı kökenden çalıştırır) tek denetimi boyut ≥ 64 bayt ve ilk bayt `<` değil. Birincil kaynak `raw.githubusercontent.com/AcidCaos/socialemperors/<COMMIT>/` (commit'e sabit: iyi), ikincisi `static.socialpointgames.com` (sabitlenmemiş, özetsiz). `config/onindirme.tsv` boyutları tutuyor ama indirmede doğrulanmıyor. Tamamlanmamış indirme `.tmp` + `os.replace` ile yarım sunulmuyor; `Content-Length` olmayan bir yanıt kesilirse eksik dosya geçerli sayılır.
- Etki: Kaynak ele geçirilir ya da ikinci kaynak farklı içerik verirse, oyun kökeninde çalışan kod (AS3) kayıt API'lerine ulaşabilir.
- Öneri: Commit'e sabit ağaç özetlerini (git blob/SHA-256) listeye ekle; ikinci kaynağı kaldır ya da özetsiz kullanma; indirilen boyutu listeyle karşılaştır.

### DGV-05: Yerel istekler sunucuyu keyfi adlı varlıklar için dışarıya indirmeye zorlayabilir
- Önem: Düşük
- İşaret: ◐
- Yer: oyun/varliklar.py (`statik_varlik`, `varlik_yolu`, `_indir`, `_basarisiz`), oyun/sunucu.py (`_koken_denetimi`: GET serbest)
- Kanıt: Statik yol GET'i `Origin` denetimine takılmaz; geçerli karakterli her yeni yol için sunucu en çok iki kaynaktan 15 sn'lik indirme dener (başarısızlık 10 dakika önbelleğe alınır, ama yol başına: `_basarisiz` sözlüğü sınırsız büyür). Ziyaret edilen bir web sayfası `<img src="http://127.0.0.1:5050/default01.../static/socialempires/x/N.png">` ile binlerce benzersiz yol isteyebilir ve 8 iş parçacığını meşgul eder (oyunun komutları bekler). Yanıtları okuyamaz.
- Etki: Yerel hizmet reddi; ağ çıkışı.
- Öneri: İndirmeyi yalnızca `onindirme.tsv`/bilinen listedeki yollarla sınırla; `_basarisiz`ı sınırla.

### DGV-06: Android: dışa açık etkinlik, hata ayıklama anahtarını herhangi bir uygulamanın açmasına izin veriyor; indirme işleyicisi adres denetlemiyor
- Önem: Düşük
- İşaret: ◐
- Yer: android/app/src/main/AndroidManifest.xml (`exported="true"` `MainActivity`), MainActivity.java (`getIntent().getBooleanExtra("sinama")`; `yedekIndir`)
- Kanıt: Etkinlik açıktır ve `sinama` ek değeri `WebView.setWebContentsDebuggingEnabled(true)` açar; bu, CI kabul sınaması içindir ama herhangi bir uygulama `am start --ez sinama true` benzeri bir niyetle aynı anahtarı çevirebilir. WebView hata ayıklama kanalına yalnızca aynı UID/shell erişebilir (Chromium kuralı, doğrulamadım), bu yüzden etkisi düşük. `yedekIndir` `DownloadListener`dan gelen adresi şemasına/ana bilgisayarına bakmadan `HttpURLConnection`a verir (`file:` ise `ClassCastException` ile iş parçacığı çöker) ve cevabı sınırsız belleğe okur (en çok 32 MB yedek beklenir). Olumlu: `setAllowFileAccess(false)`, `addJavascriptInterface` yok, dış bağlantılar tarayıcıya gidiyor, şifresiz HTTP yalnızca 127.0.0.1'e açık, `se_uygulama` çerezi `HttpOnly; SameSite=Strict` ve süreç başına rastgele (SecureRandom 24 bayt), sunucu jetonsuz istekleri `/saglik`, `/ruffle/`, statik yollar dışında 403'e çeviriyor.
- Etki: Çok sınırlı.
- Öneri: `sinama` yalnızca debug yapıda; indirme adresini `127.0.0.1` ve `http` ile sınırla.

### DGV-07: Android bulut yedeği `saves/` içindeki sınırsız büyüyen günlükleri de alıyor
- Önem: Düşük
- İşaret: ◐
- Yer: android/app/src/main/res/xml/yedek.xml, yedek_eski.xml; oyun/komutlar.py `_gunluge_yaz`, oyun/istemci.py `_http_gunlugune_yaz`
- Kanıt: Yedek kuralı `socialempires/saves/` klasörünü bütünüyle içerir, yalnızca `saves/backups/` ve `saves/gunluk_yedek/` dışarıda. Aynı klasöre `komut_gunlugu.jsonl`, `http_gunlugu.jsonl`, `istemci_hatalari.jsonl`, `sunucu_hatalari.log` yazılır ve hiçbiri döndürülmüyor (SNK-09). Şema yorumu zaten "25 MB sınırını aşınca bütün yedek düşüyor" diyor. `ayarlar.json` (içinde `ev_agi`) de yedeğe giriyor; `allowBackup="true"`.
- Etki: Zamanla kayıt yedeği sınırı aşar ve kayıtlar bulutta hiç yedeklenmez; `ev_agi` yeni cihaza taşınır.
- Öneri: Günlükleri `saves/` dışına koy ya da yedekten dışla; `ayarlar.json`ı yedeğe alma.

### DGV-08: Bağımlılıklar sabitlenmemiş; Windows paketi ve Android derlemesi o gün çıkan sürümü içine alıyor
- Önem: Düşük
- İşaret: ✔
- Yer: requirements.txt (`flask`, `jsonpatch`, `waitress`, `brotli`), araclar/windows_paketi.py:`tekerlekler`, android/app/build.gradle.kts (`install("flask")` vb.)
- Kanıt: Dosyalarda sürüm ve özet yok; `pip download --only-binary` özetsiz çalışıyor, gömülü Python `https://www.python.org/ftp/python/3.12.10/...-embed-amd64.zip` özet denetimi olmadan alınıp pakete konuyor. Test bağımlılığı `hypothesis` ise sabit. Oturum anahtarı `.oturum_anahtari` 0644 izinle yazılıyor (bu kopyada `stat`: 644); paylaşımlı bilgisayarda başka kullanıcı okuyabilir (anahtarla yalnızca oturumun `USERID`si taklit edilir ve parola yok, etkisi sınırlı).
- Etki: Aynı sürüm iki farklı zamanda farklı bağımlılıkla çıkar; tedarik zinciri saldırısı sessizce pakete girer.
- Öneri: `requirements.txt`yi sürüm ve özetle sabitle, `pip download --require-hashes`; gömülü Python özetini koda yaz.

## Bakıldı, sorun bulunmadı

- Yol geçişi: statik varlık, `/img`, `/css`, `/js`, `/fonts`, `/ruffle/<sürüm>/<dosya>`, `/profil/resim/<uid>.jpg` için `..`, `%2f`, `%5c`, `%00`, mutlak yol, çifte eğik çizgi denendi (`g2.py`): hepsi 404/308, depo dışı dosya sunulmadı. `varlik_yolu` karakter beyaz listesi, `..` reddi, `safe_join`; `gecerli_uid` kimlik beyaz listesi.
- Dinleme adresi: varsayılan `127.0.0.1:5050`; `0.0.0.0` yalnızca `ev_agi` açıkken (DGV-01) ve taşıma gönderici sunucusu için (DGV-02).
- CSRF/DNS yeniden bağlama: `_koken_denetimi` (Host yerel ad, `Origin`, `Sec-Fetch-Site`) çalışıyor (`g1.py`); hile ucu ek olarak JSON (`request.is_json`) ve loopback istiyor, taşıma uçları POST + `yerel_mi`. GET'ler yalnızca durum okur (istisna: `get_continent_ranking.php` GET `worldChange/relocate`, kimlik gerekir).
- Oturum gizli anahtarı: `secrets.token_hex(32)` ile ilk açılışta üretilip saklanıyor, `SE_SECRET_KEY` ile geçersiz kılınabiliyor; sabit/tahmin edilebilir değil.
- Ruffle: npm paketi SHA-512 ile doğrulanıyor, tar çıkarma düz dosyalarla sınırlı (alt klasör, bağlantı, `.map` atlanıyor). Yalnızca `/ruffle-deneme.html` (isteğe bağlı) `unpkg…@nightly` yükler.
- Windows paketi: başlatıcı `cd /d "%~dp0"`, tırnaklı `python.exe` yolu, `chcp 65001`, `PYTHONUTF8`; boşluk/Türkçe harfli klasörde sorun beklenmez (çalıştırmadım, ?). Pakete `saves`, `.oturum_anahtari`, `assets/` (fontlar hariç) girmiyor; `.sha256` üretiliyor ve CI'da denetleniyor.
- Android: `allowFileAccess` kapalı, JavaScript arayüzü yok, şifresiz trafik yalnızca 127.0.0.1, `targetSdk 35`, imza anahtarı depoda yok (CI sırrı), hata ayıklama imzası yalnızca sır yokken.
- `claude-inceleme.yml`: `pull_request` (hedef değil), fork ve Dependabot dışlı, eylemler SHA'ya sabit, `persist-credentials: false`, araç listesi dar.
- `SECURITY.md`'deki iddialar (CODEOWNERS, dependabot.yml, `gecerli_uid`, atomik yazım) depoda var; CodeQL/secret scanning depo ayarı olduğundan doğrulanamadı (?).
