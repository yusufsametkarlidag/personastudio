// PersonaStudio — Flow projesindeki "Görsel #N" adli tum gorselleri orijinal (1K) kalitede indirir.
// Flow sekmesinde DevTools Console'a yapistir. Sayfayi kendisi kaydirir; ayni numaranin en yenisini alir.
// Chrome "birden fazla dosya indirme" izni sorarsa izin ver.
(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const done = new Set();
  const label = t => (t.innerText || "").split("\n").map(x => x.trim()).filter(Boolean).pop() || "";
  const scroller = [...document.querySelectorAll("main *")].find(e => e.scrollHeight > e.clientHeight + 50 &&
    /(auto|scroll)/.test(getComputedStyle(e).overflowY)) || document.scrollingElement;
  scroller.scrollTop = 0;
  let still = 0, lastTop = -1;
  while (still < 3) {
    for (const t of document.querySelectorAll("main flow-image-tile")) {
      const m = label(t).match(/^Görsel #(\d+)$/), im = t.querySelector("img");
      if (!m || !im || done.has(m[1])) continue;
      const b = await (await fetch(im.src)).blob();
      const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(b), download: `Görsel_#${m[1]}_flow.jpg` });
      document.body.appendChild(a); a.click(); a.remove(); done.add(m[1]);
      await sleep(350);
    }
    scroller.scrollTop += scroller.clientHeight * 0.8;
    await sleep(1500);
    still = scroller.scrollTop === lastTop ? still + 1 : 0;
    lastTop = scroller.scrollTop;
  }
  console.log(`İndirilen ${done.size} görsel:`, [...done].sort((a, b) => a - b).join(", "));
  alert(`Bitti: ${done.size} görsel indirildi. Uygulamada "Flow indirilenlerini al"a bas.`);
})();
