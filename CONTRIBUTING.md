# Katkı Rehberi

## Gereksinimler

- Windows (desteklenen), Python 3.12+, `requirements.txt` (testler için `requirements-test.txt`)
- Tarayıcı (oyun Ruffle 0.7.1 ile açılır)

## Kurulum

```bat
baslat.bat
```

Sunucu hazır olduğunda <http://127.0.0.1:5050/> açılır. Sağlık kontrolü:
<http://127.0.0.1:5050/saglik>

## Testler

```bat
python -m unittest discover -s tests
```

```bat
node --test tests/js/*.test.js
```

- `test_komutlar.py`: oyun komutları, kayıt, PvP, ekonomi, turnuva, ada.
- `test_http.py`: Flask uçtan uca uçlar (canlı kayıtları yazmaz).
- `test_komut_imzalari.py`: istemcinin (1.4.07) gönderdiği her komutun işleyicisi var.
- `test_gorev.py`: görev kitabının (`docs/gorev/BULGULAR.json`) biçimi.
- Yeni test, koruduğu kod bozulunca düşmelidir; beklenen değerin kaynağı (istemci bayt kodu, belge) yazılır
  (`docs/TEST_OLCUMU.md`).

## Değişiklik gönderme

1. `master` üzerinden yeni bir dal açın.
2. Değişikliği küçük ve odaklı tutun.
3. Testleri çalıştırın; kırılan test varsa PR açmayın.
4. Açıklamada neyin değiştiğini ve nasıl doğrulandığını yazın.
5. Kullanıcıya ait `saves/` dosyalarını, logları veya tokenları commit etmeyin.
6. İlgili `docs/gorev/BULGULAR.json` maddelerini ve o günün devir notunu (`docs/devlog/`) güncelleyin.

## Kod stili

- Python 3.12, 4 boşluk, UTF-8.
- Kullanıcıya görünen metinler Türkçe; oyun içi metinler `ceviri/` üzerinden.
- Yeni oyun içeriği `config/patch/` altında RFC 6902 JSON yaması olarak eklenir.

## Güvenlik

Açıkları herkese açık issue olarak açmayın; [SECURITY.md](SECURITY.md) izleyin.
