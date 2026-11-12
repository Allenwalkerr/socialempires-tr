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
