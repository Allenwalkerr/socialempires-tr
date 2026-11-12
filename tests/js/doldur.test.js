// Doldur görünümü (sahibinin bildirimi 12.11.2026: "doldur yapınca oyunun arayüzü mahvoluyor").
// Kaynak, 1.4.07 bayt kodu: Base/getStageDimensions sahne boyunu yalnızca displayState == FULL_SCREEN iken
// (fullScreenWidth/Height) okur, öteki her durumda Config.STAGE_WIDTH/HEIGHT (760×600) verir; menüler yalnızca
// StateNormal/onFullScreenChange → setFullScreen/setNormalScreen ile yeniden dizilir. Ruffle noScale ile sahneyi
// büyütmek bu olayı tetiklemez; Doldur oyunun kendi tam ekranını (Ruffle oyuncusunun enterFullscreen'i) kullanır.
// Tarayıcı tam ekranı yalnızca kullanıcı dokunuşuyla açar (pointerup etkinleştirir).
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const js = fs.readFileSync(path.join(__dirname, "..", "..", "templates", "js", "oyun.js"), "utf8");
const bas = js.indexOf("var oyuncu = ruffle.createPlayer();");
const son = js.indexOf('oyuncu.addEventListener("pointerup", tamEkranaGec, true);', bas);
assert.ok(bas > 0 && son > bas, "Doldur bölümü oyun.js'te bulunamadı");
const bolum = js.slice(bas + "var oyuncu = ruffle.createPlayer();".length, js.indexOf("}", son) + 1);

function kur(doldur) {
  const dinleyiciler = [];
  const oyuncu = {
    acilis: 0,
    enterFullscreen() { this.acilis += 1; },
    addEventListener(ad, f, yakala) { dinleyiciler.push({ ad, f, yakala }); },
    removeEventListener(ad, f) { const i = dinleyiciler.findIndex((d) => d.ad === ad && d.f === f); if (i >= 0) dinleyiciler.splice(i, 1); },
  };
  const document = { body: { classList: { contains: (s) => doldur && s === "ekran-doldur" } }, fullscreenElement: null };
  vm.runInNewContext(bolum, { oyuncu, document });
  const bas = (ad) => dinleyiciler.filter((d) => d.ad === ad).forEach((d) => d.f());
  return { oyuncu, dinleyiciler, bas, document };
}

test("Doldur: ilk dokunuşta oyunun kendi tam ekranı bir kez açılır", () => {
  const k = kur(true);
  assert.strictEqual(k.oyuncu.acilis, 0);  // dokunuş olmadan açılmaz (tarayıcı izin vermez)
  k.bas("pointerup");
  assert.strictEqual(k.oyuncu.acilis, 1);
  k.bas("pointerup");
  assert.strictEqual(k.oyuncu.acilis, 1);  // Esc ile çıkan oyuncuyu yeniden tam ekrana zorlamaz
});

test("Sığdır: tam ekran kendiliğinden açılmaz", () => {
  const k = kur(false);
  assert.strictEqual(k.dinleyiciler.length, 0);
});

test("Doldur sahneyi noScale ile esnetmez (menüler 760×600 köşede kalıyordu)", () => {
  assert.ok(!/config\.scale\s*=\s*"noScale"/.test(js));
});

// Tam Ekran düğmesi (#81 incelemesi). Fullscreen belirtimi: başarılı requestFullscreen kullanıcı etkinleşmesini
// tüketir; aynı tıklamada ikinci istek reddedilebilir. Doldur'da tıklama başına tek istek: oyuncunun tam ekranı.
const bas2 = js.indexOf("var UYGULAMA = /SocialEmpiresTR-Android/");
const son2 = js.indexOf("  if (UYGULAMA) {", bas2);
assert.ok(bas2 > 0 && son2 > bas2, "oyun modu bölümü oyun.js'te bulunamadı");
const modBolumu = js.slice(bas2, son2);

function sayfa(doldur) {
  const dinle = {}, siniflar = new Set(doldur ? ["ekran-doldur"] : []);
  const k = { sayfaIstek: 0, oyuncuIstek: 0 };
  const oyuncu = { focus() {}, enterFullscreen() { k.oyuncuIstek += 1; } };
  const document = {
    fullscreenElement: null,
    body: { classList: { toggle: (s, a) => (a ? siniflar.add(s) : siniflar.delete(s)), contains: (s) => siniflar.has(s) } },
    documentElement: { requestFullscreen() { k.sayfaIstek += 1; return Promise.resolve(); } },
    exitFullscreen() { return Promise.resolve(); },
    querySelector: (s) => (s === "ruffle-player" ? oyuncu : null),
    getElementById: (id) => (dinle[id] = dinle[id] || { hidden: true, addEventListener(ad, f) { this[ad] = f; } }),
    addEventListener(ad, f) { dinle["belge-" + ad] = f; },
  };
  vm.runInNewContext(modBolumu, { document, navigator: { userAgent: "Chrome" }, localStorage: { setItem() {} },
                                  panelleriTazele() {} });
  return { k, dinle, document, oyuncu, siniflar };
}

test("Doldur: Tam Ekran düğmesi tek istek yapar (oyuncunun tam ekranı), Esc oyun modunu kapatır", () => {
  const s = sayfa(true);
  s.dinle["tam-ekran"].click();
  assert.deepStrictEqual(s.k, { sayfaIstek: 0, oyuncuIstek: 1 });
  assert.ok(s.siniflar.has("oyun-modu"));
  s.document.fullscreenElement = s.oyuncu;
  s.dinle["belge-fullscreenchange"]();
  s.document.fullscreenElement = null;  // Esc
  s.dinle["belge-fullscreenchange"]();
  assert.ok(!s.siniflar.has("oyun-modu"));
});

test("Sığdır: Tam Ekran düğmesi sayfanın tam ekranını ister, oyuncununkini istemez", () => {
  const s = sayfa(false);
  s.dinle["tam-ekran"].click();
  assert.deepStrictEqual(s.k, { sayfaIstek: 1, oyuncuIstek: 0 });
});
