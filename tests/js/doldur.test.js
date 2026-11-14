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
  vm.runInNewContext(bolum, { oyuncu, document, oyunTamEkrani: (o) => o.enterFullscreen() });
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

function sayfa(doldur, buyukEkran = true) {
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
                                  panelleriTazele() {}, oyunTamEkrani: (o) => o.enterFullscreen(),
                                  oyunTamEkraniSigarMi: () => buyukEkran, window: {},
                                  kutuBoyunuSifirla() { if (oyuncu.style) { oyuncu.style.width = ""; oyuncu.style.height = ""; } } });
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

// DNT-70. Sahibi (14.11.2026): tam ekranda arayüz ekranla oranlı büyüyor; eski videoda (acidcaos, gerçek Flash,
// allowFullScreen="true", oyunun kendi tam ekranı) büyümüyor. 1.4.07: Base/init@128 EXACT_FIT; yalnızca tam ekran
// olayında StateNormal/setFullScreen@51 NO_SCALE. Sayfanın tam ekranı bu olayı tetiklemez. Ruffle'da (14.11.2026)
// Sığdır + Tam Ekran: arayüz kendi boyunda, çubuklar ekranın kenarlarında.
test("Sığdır, büyük ekran: Tam Ekran oyunun kendi tam ekranını ister (arayüz gerilmez)", () => {
  const s = sayfa(false);
  s.dinle["tam-ekran"].click();
  assert.deepStrictEqual(s.k, { sayfaIstek: 0, oyuncuIstek: 1 });
});

test("Sığdır, 760×600'den küçük ekran: sayfanın tam ekranı (NO_SCALE menüleri keserdi)", () => {
  const s = sayfa(false, false);
  s.dinle["tam-ekran"].click();
  assert.deepStrictEqual(s.k, { sayfaIstek: 1, oyuncuIstek: 0 });
});

// Ruffle tam ekran olayını kutu büyümeden gönderir; oyun menüleri o anki sahne boyuna dizer. Kutu önce ekran boyuna
// getirilmeli, istek ondan sonra (Ruffle'da kutu büyütülmeden menüler 877×693'lük kutuda kaldı).
test("oyunTamEkrani: önce kutu ekran boyuna, sonra tam ekran isteği; çıkışta boy geri gelir", () => {
  const bas3 = js.indexOf("  function kutuBoyunuSifirla() {");
  const son3 = js.indexOf("  function doldurulsunMu() {", bas3);
  assert.ok(bas3 > 0 && son3 > bas3);
  const sira = [];
  const oyuncu = { style: {}, enterFullscreen() { sira.push("istek " + this.style.width + "x" + this.style.height); } };
  const zamanlayici = [];
  const belge = { fullscreenElement: null, querySelector: () => oyuncu };
  const ctx = { window: { screen: { width: 1920, height: 1080 } }, setTimeout: (f) => zamanlayici.push(f), oyuncu,
                document: belge };
  vm.runInNewContext(js.slice(bas3, son3) + "\noyunTamEkrani(oyuncu);", ctx);
  assert.deepStrictEqual(sira, []);  // istek hemen değil
  assert.deepStrictEqual(oyuncu.style, { width: "1920px", height: "1080px" });
  zamanlayici[0]();
  assert.deepStrictEqual(sira, ["istek 1920pxx1080px"]);
  belge.fullscreenElement = oyuncu;  // istek kabul edildi: boy kalır
  zamanlayici[1]();
  assert.deepStrictEqual(oyuncu.style, { width: "1920px", height: "1080px" });
  const s = sayfa(false);
  const o = s.oyuncu; o.style = { width: "1920px", height: "1080px" };
  s.dinle["belge-fullscreenchange"]();  // fullscreenElement null: çıkış
  assert.deepStrictEqual(o.style, { width: "", height: "" });
});

// Oyunun kendi tam ekran düğmesi (dişli menüsü, GuiManager/toggleFullscreen: stage.displayState = FULL_SCREEN) Ruffle'da
// allowFullscreen olmadan sessizce yok sayılır (Ruffle 0.7.1 varsayılanı allowFullscreen:!1; acidcaos play.html gerçek
// Flash'ta allowFullScreen="true").
test("Ruffle ayarı: oyunun kendi tam ekranına izin var", () => {
  assert.ok(/allowFullscreen:\s*true/.test(js));
});

test("Tam ekran isteği reddedilirse kutu eski boyuna döner (#85 incelemesi)", () => {
  const bas3 = js.indexOf("  function kutuBoyunuSifirla() {");
  const son3 = js.indexOf("  function doldurulsunMu() {", bas3);
  const oyuncu = { style: {}, enterFullscreen() {} };
  const zamanlayici = [];
  const belge = { fullscreenElement: null, querySelector: () => oyuncu };
  vm.runInNewContext(js.slice(bas3, son3) + "\noyunTamEkrani(oyuncu);",
                     { window: { screen: { width: 1920, height: 1080 } }, setTimeout: (f) => zamanlayici.push(f), oyuncu, document: belge });
  zamanlayici.forEach((f) => f());  // istek gitti ama tam ekran olmadı
  assert.deepStrictEqual(oyuncu.style, { width: "", height: "" });
  const s = sayfa(false);
  s.oyuncu.style = { width: "1920px", height: "1080px" };
  s.dinle["belge-fullscreenerror"]();
  assert.deepStrictEqual(s.oyuncu.style, { width: "", height: "" });
});

test("Oyunun dişli menüsündeki tam ekran düğmesi sayfanın yolunu kullanır (window.toggleFullscreen)", () => {
  assert.ok(/window\.toggleFullscreen = function/.test(modBolumu));
  const ctx = {};
  const dinle = {};
  const siniflar = new Set();
  const k = { sayfaIstek: 0, oyuncuIstek: 0, cikis: 0 };
  const oyuncu = { focus() {}, style: {}, enterFullscreen() { k.oyuncuIstek += 1; } };
  const document = {
    fullscreenElement: null,
    body: { classList: { toggle: (c, a) => (a ? siniflar.add(c) : siniflar.delete(c)), contains: (c) => siniflar.has(c) } },
    documentElement: { requestFullscreen() { k.sayfaIstek += 1; return Promise.resolve(); } },
    exitFullscreen() { k.cikis += 1; return Promise.resolve(); },
    querySelector: (q) => (q === "ruffle-player" ? oyuncu : null),
    getElementById: (id) => (dinle[id] = dinle[id] || { hidden: true, addEventListener(ad, f) { this[ad] = f; } }),
    addEventListener() {},
  };
  const pencere = {};
  vm.runInNewContext(modBolumu, { document, navigator: { userAgent: "Chrome" }, localStorage: { setItem() {} },
                                  panelleriTazele() {}, oyunTamEkrani: (o) => o.enterFullscreen(),
                                  oyunTamEkraniSigarMi: () => true, window: pencere, kutuBoyunuSifirla() {} });
  pencere.toggleFullscreen();
  assert.deepStrictEqual(k, { sayfaIstek: 0, oyuncuIstek: 1, cikis: 0 });
  document.fullscreenElement = oyuncu;
  pencere.toggleFullscreen();
  assert.strictEqual(k.cikis, 1);
});
