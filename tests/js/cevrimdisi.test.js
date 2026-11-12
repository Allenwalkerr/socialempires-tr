// templates/cevrimdisi.html: indirme bitince ya da durunca "… paket iniyor..." yazısı kalmamalı (sahibinin bildirimi,
// 12.11.2026: iki çubuk dolu, "İndi" yazıyor ama altta "Tam paket iniyor..." duruyordu).
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const html = fs.readFileSync(path.join(__dirname, "..", "..", "templates", "cevrimdisi.html"), "utf8");
const betik = html.slice(html.lastIndexOf("<script>") + 8, html.lastIndexOf("</script>"));

function oge() {
  return { textContent: "", hidden: false, disabled: false, value: 0, dataset: { paket: "tam" },
           addEventListener() {}, querySelector() { return oge.alt; }, closest() { return this; } };
}

function calistir(yanitlar) {
  const ileti = oge();
  oge.alt = oge();
  const paketKutusu = oge();
  paketKutusu.querySelector = () => oge();
  const document = {
    getElementById: (ad) => (ad === "ileti" ? ileti : null),
    querySelector: () => paketKutusu,
    querySelectorAll: () => [],
  };
  let sira = 0;
  const zamanlayicilar = [];
  const baglam = {
    document, Intl, Object, FormData: function () {},
    setTimeout: (f) => { zamanlayicilar.push(f); return zamanlayicilar.length; }, clearTimeout() {},
    fetch: () => Promise.resolve({ json: () => Promise.resolve(yanitlar[Math.min(sira++, yanitlar.length - 1)]) }),
  };
  vm.runInNewContext(betik, baglam);
  return { ileti, zamanlayicilar };
}

const bekle = () => new Promise((r) => setImmediate(r));
const paketler = (inen) => ({ tam: { dosya: 10, inen_dosya: inen, bayt: 100, inen_bayt: inen * 10 } });

test("indirme bitince 'iniyor' yazısı 'İndirme bitti.' olur", async () => {
  const k = calistir([{ calisiyor: true, paket: "tam", paketler: paketler(5) },
                      { calisiyor: false, paket: "tam", paketler: paketler(10) }]);
  await bekle(); await bekle();
  assert.strictEqual(k.ileti.textContent, "Tam paket iniyor...");
  k.zamanlayicilar.shift()();
  await bekle(); await bekle();
  assert.strictEqual(k.ileti.textContent, "İndirme bitti.");
});

test("durdurulan indirmede eski yazı silinir", async () => {
  const k = calistir([{ calisiyor: true, paket: "tam", paketler: paketler(5) },
                      { calisiyor: false, paket: "tam", paketler: paketler(6) }]);
  await bekle(); await bekle();
  k.zamanlayicilar.shift()();
  await bekle(); await bekle();
  assert.strictEqual(k.ileti.textContent, "");
});
