// Bot yardımı kancaları (KAR-26, KAR-27; #67 incelemesi): oyunun ExternalInterface ile çağırdığı sayfa işlevleri.
// Beklenen davranışın kaynağı (1.4.07 bayt kodu, docs/inceleme/1407-asker-ada.md):
// - PopupRecruitment/onFindFriend: showPopupSEHelpSocialItem(tx, ty, kasaba, bina, si, ad); bot yalnızca Asker Toplama (387).
// - showPopupSEHelpOffer(no): viral teklif ve Ada'nın boru malzemesi.
// - Liste sunucuda dolar; oyun yeni durumu ancak forceReloadInfo geri çağrısıyla (Base/init addCallback) okur,
//   bu yüzden yalnızca başarıda çağrılır.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const js = fs.readFileSync(path.join(__dirname, "..", "..", "templates", "js", "oyun.js"), "utf8");
const bas = js.indexOf("var etkinOyuncu = null;");
const son = js.indexOf("\n", js.indexOf("window.showPopupSEHelpOffer = function"));
assert.ok(bas > 0 && son > bas, "kanca bölümü oyun.js'te bulunamadı");
const bolum = js.slice(bas, son) + "\nwindow.oyuncuAta = function (o) { etkinOyuncu = o; };";

function kur(yanit) {
  const k = { istekler: [], uyarilar: [], yenileme: 0 };
  const window = {};
  const fetch = (adres, ayar) => {
    k.istekler.push({ adres, ayar, govde: JSON.parse(ayar.body) });
    return Promise.resolve({ ok: yanit.ok, json: () => Promise.resolve(yanit.v) });
  };
  vm.runInNewContext(bolum, { window, fetch, alert: (m) => k.uyarilar.push(m) });
  window.oyuncuAta({ forceReloadInfo: () => { k.yenileme += 1; } });
  k.window = window;
  return k;
}
const bekle = () => new Promise((r) => setImmediate(r));

test("Asker Toplama: istek gider, başarıda oyun bilgisini yeniden okur", async () => {
  const k = kur({ ok: true, v: { bot: "5ab" } });
  k.window.showPopupSEHelpSocialItem("40", "41", "0", "387", [], "Asker");
  await bekle();
  assert.strictEqual(k.istekler.length, 1);
  assert.strictEqual(k.istekler[0].adres, "/yardim/bot");
  assert.strictEqual(k.istekler[0].ayar.method, "POST");
  assert.deepStrictEqual(k.istekler[0].govde, { tur: "sosyal", tx: 40, ty: 41, town: 0, id: 387 });
  assert.strictEqual(k.yenileme, 1);
  assert.deepStrictEqual(k.uyarilar, []);
});

test("387 dışındaki binada istek yok", async () => {
  const k = kur({ ok: true, v: {} });
  k.window.showPopupSEHelpSocialItem(1, 2, 0, 234, [], "x");
  await bekle();
  assert.strictEqual(k.istekler.length, 0);
  assert.strictEqual(k.yenileme, 0);
});

test("hata yanıtında oyun yenilenmez, sunucunun iletisi gösterilir", async () => {
  const k = kur({ ok: false, v: { hata: "Bugün bir bot yardım etti; yarın yeni biri gelir.", yarin: true } });
  k.window.showPopupSEHelpOffer("2");
  await bekle();
  assert.deepStrictEqual(k.istekler[0].govde, { tur: "teklif", no: 2 });
  assert.strictEqual(k.yenileme, 0);
  assert.deepStrictEqual(k.uyarilar, ["Bugün bir bot yardım etti; yarın yeni biri gelir."]);
});
