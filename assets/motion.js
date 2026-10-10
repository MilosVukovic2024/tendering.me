/* Tendering.me — animacije (jedan izvor za cijeli sajt, bez biblioteka). Pravila i klase: assets/motion.css, README → Animacije.
   Moduli: traka navigacije, mobilni meni, ulazak pri skrolu, brojači, linija koraka, linija čitanja (fallback). */
(function () {
  "use strict";
  var d = document, html = d.documentElement, w = window;
  var reduced = !!(w.matchMedia && w.matchMedia("(prefers-reduced-motion: reduce)").matches);
  var hasIO = "IntersectionObserver" in w;
  html.classList.add("motion");

  // Greška u ovom fajlu ne smije sakriti sadržaj: skini prekidače, sve postaje vidljivo.
  function fail() {
    html.classList.remove("motion", "js");
    $$(".a-menu").forEach(function (m) { m.removeAttribute("inert"); m.classList.remove("open"); });
    $$(".a-steps").forEach(function (b) { b.classList.remove("is-live"); });
    $$(".is-armed").forEach(function (m) { m.classList.remove("is-armed"); });
  }
  w.addEventListener("error", function (e) { if (e && e.filename && e.filename.indexOf("/assets/motion.js") > -1) fail(); });
  function safe(fn) { return function () { try { fn.apply(this, arguments); } catch (err) { fail(); if (w.console) console.error(err); } }; }

  // Kriva sajta cubic-bezier(0.16, 1, 0.3, 1) za animacije koje vodi JS (brojači).
  function bezier(x1, y1, x2, y2) {
    var cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx, cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    function sx(t) { return ((ax * t + bx) * t + cx) * t; }
    return function (x) {
      if (x <= 0) return 0;
      if (x >= 1) return 1;
      var lo = 0, hi = 1, t = x;
      for (var i = 0; i < 24; i++) { var v = sx(t); if (Math.abs(v - x) < 1e-5) break; if (v < x) lo = t; else hi = t; t = (lo + hi) / 2; }
      return ((ay * t + by) * t + cy) * t;
    };
  }
  var ease = bezier(0.16, 1, 0.3, 1);
  function vh() { return w.innerHeight || html.clientHeight; }
  function $$(sel, root) { return Array.prototype.slice.call((root || d).querySelectorAll(sel)); }

  /* ── Traka navigacije: .is-scrolled poslije 8 px (IO sentinel, bez scroll listenera) ── */
  function initBar() {
    var bars = $$(".a-bar");
    if (!bars.length || !hasIO) return;
    var s = d.createElement("div");
    s.setAttribute("aria-hidden", "true");
    s.style.cssText = "position:absolute;top:0;left:0;width:1px;height:8px;pointer-events:none;visibility:hidden";
    d.body.insertBefore(s, d.body.firstChild);
    new IntersectionObserver(function (es) {
      var scrolled = !es[es.length - 1].isIntersecting;
      bars.forEach(function (b) { b.classList.toggle("is-scrolled", scrolled); });
    }).observe(s);
  }

  /* ── Mobilni meni: [data-menu-toggle] + aria-controls; fokus ostaje u meniju; Esc, klik van, prelaz na desktop ── */
  function initMenu() {
    var tg = d.querySelector("[data-menu-toggle]");
    var panel = tg && d.getElementById(tg.getAttribute("aria-controls"));
    if (!panel || !html.classList.contains("js")) return;
    var mq = w.matchMedia("(max-width: 900px)");
    function isOpen() { return panel.classList.contains("open"); }
    function set(open, focusToggle) {
      panel.classList.toggle("open", open);
      tg.setAttribute("aria-expanded", open ? "true" : "false");
      if (mq.matches) { if (open) panel.removeAttribute("inert"); else panel.setAttribute("inert", ""); }
      if (!open && focusToggle) tg.focus();
    }
    function sync() {
      if (mq.matches) { if (!isOpen()) panel.setAttribute("inert", ""); }
      else { panel.classList.remove("open"); panel.removeAttribute("inert"); tg.setAttribute("aria-expanded", "false"); }
    }
    tg.addEventListener("click", function () { set(!isOpen()); });
    panel.addEventListener("click", function (e) { if (e.target.closest("a")) set(false); });
    d.addEventListener("click", function (e) { if (isOpen() && !panel.contains(e.target) && !tg.contains(e.target)) set(false); });
    d.addEventListener("keydown", function (e) {
      if (!isOpen()) return;
      if (e.key === "Escape") { set(false, true); return; }
      if (e.key !== "Tab") return;
      var f = [tg].concat($$("a[href], button:not([disabled])", panel)), i = f.indexOf(d.activeElement);
      if (e.shiftKey && i <= 0) { e.preventDefault(); f[f.length - 1].focus(); }
      else if (!e.shiftKey && (i === f.length - 1 || i < 0)) { e.preventDefault(); f[0].focus(); }
    });
    if (mq.addEventListener) mq.addEventListener("change", sync); else mq.addListener(sync);
    w.addEventListener("pagehide", function () { if (isOpen()) set(false); });
    sync();
  }

  /* ── Ulazak pri skrolu ───────────────────────────────────────────────────────
     Jedinica = .a-reveal | .a-stagger | .a-group, ili sekcija markdown strane (h2 + blokovi do sljedećeg h2).
     Skriva se (is-armed) tek kad je ispod vidnog polja i u pojasu 25 % ispod njega; otkriva se (is-in) kad pređe 90 % visine.
     Šta je vidljivo pri učitavanju, posle skoka na #sidro ili povratka nazad — nikad se ne skriva. */
  var units = [], byHead = new Map(), byMember = new Map(), armIO, inIO, endIO;

  function addUnit(head, members) {
    if (!head || byHead.has(head)) return;
    var u = { head: head, members: members, state: 0 }; // 0 neodlučeno, 1 skriveno, 2 gotovo
    units.push(u); byHead.set(head, u);
    if (armIO) armIO.observe(head);
  }
  function arm(u) {
    u.state = 1;
    u.members.forEach(function (m) { m.classList.add("is-armed"); byMember.set(m, u); inIO.observe(m); });
    inIO.observe(u.head);
  }
  function reveal(u, instant, offset) {
    if (u.state === 2) return;
    var wasArmed = u.state === 1;
    u.state = 2;
    armIO.unobserve(u.head); inIO.unobserve(u.head);
    if (!wasArmed) return;
    u.members.forEach(function (m) {
      inIO.unobserve(m);
      if (instant) m.classList.add("a-instant");
      if (offset) m.style.setProperty("--rb", offset + "ms");
      m.classList.add("is-in");
      m.classList.remove("is-armed");
    });
    // a-instant samo za ovaj prelaz; poslije toga hover i ostale mikrointerakcije rade normalno
    if (instant) requestAnimationFrame(function () { requestAnimationFrame(function () {
      u.members.forEach(function (m) { m.classList.remove("a-instant"); });
    }); });
  }
  function revealAll(instant) { units.forEach(function (u) { reveal(u, instant); }); }

  function sectionsOf(article) {
    // Djeca članka; omotači .a-steps su providni. h1 + prvi pasus pripadaju heroju (CSS).
    var kids = [];
    Array.prototype.forEach.call(article.children, function (c) {
      if (c.classList.contains("a-steps")) Array.prototype.forEach.call(c.children, function (x) { if (!x.classList.contains("a-steps-line")) kids.push(x); });
      else kids.push(c);
    });
    var groups = [], cur = null;
    kids.forEach(function (el, i) {
      if (el.matches(".a-progress, h1") || (i === 1 && el.tagName === "P" && kids[0].tagName === "H1")) return;
      if (el.tagName === "H2" || !cur) { cur = { head: el, items: [] }; groups.push(cur); }
      if (/^(UL|OL)$/.test(el.tagName)) Array.prototype.forEach.call(el.children, function (li) { cur.items.push(li); });
      else cur.items.push(el);
    });
    groups.forEach(function (g) {
      g.items.forEach(function (el, k) { el.classList.add("a-sec"); el.style.setProperty("--rd", Math.min(k, 6) * 60 + "ms"); });
      addUnit(g.head, g.items);
    });
  }

  function scanUnits(root) {
    $$(".a-reveal, .a-stagger, .a-group", root).forEach(function (el) { addUnit(el, [el]); });
    $$('article[data-motion="flow"]', root).forEach(sectionsOf);
  }

  function initReveal() {
    if (reduced || !hasIO) return;
    armIO = new IntersectionObserver(function (es) {
      var limit = vh();
      es.forEach(function (e) {
        var u = byHead.get(e.target);
        if (!u || u.state || !e.isIntersecting) return;
        armIO.unobserve(e.target);
        if (e.boundingClientRect.top >= limit) arm(u); else u.state = 2;
      });
    }, { rootMargin: "0px 0px 25% 0px" });
    inIO = new IntersectionObserver(function (es) {
      var seen = [];
      es.filter(function (e) { return e.isIntersecting; })
        .sort(function (a, b) { return a.boundingClientRect.top - b.boundingClientRect.top || a.boundingClientRect.left - b.boundingClientRect.left; })
        .forEach(function (e) { var u = byHead.get(e.target) || byMember.get(e.target); if (u && u.state === 1 && seen.indexOf(u) < 0) seen.push(u); });
      seen.forEach(function (u, i) { reveal(u, false, Math.min(i, 4) * 60); });
    }, { rootMargin: "0px 0px -10% 0px" });
    // Kraj dokumenta: ono što ne može preći 90 % visine (dno strane) otkriva se kad se stigne do kraja.
    var end = d.createElement("div");
    end.setAttribute("aria-hidden", "true");
    end.style.cssText = "height:1px;margin-top:-1px;pointer-events:none";
    d.body.appendChild(end);
    endIO = new IntersectionObserver(function (es) { if (es[es.length - 1].isIntersecting) units.forEach(function (u) { if (u.state === 1) reveal(u); }); });
    endIO.observe(end);
    scanUnits(d);
    // Fokus tastaturom na skrivenom elementu → odmah vidljivo.
    d.addEventListener("focusin", function (e) {
      units.forEach(function (u) { if (u.state === 1 && u.members.some(function (m) { return m.contains(e.target); })) reveal(u, true); });
    });
    // Skok na #sidro: ciljna sekcija odmah vidljiva.
    function hash() {
      var id = location.hash.slice(1), t = null;
      try { t = id && d.getElementById(decodeURIComponent(id)); } catch (err) { t = null; }
      if (!t) return;
      units.forEach(function (u) { if (u.state === 1 && (t.contains(u.head) || u.head.contains(t))) reveal(u, true); });
    }
    w.addEventListener("hashchange", hash);
    w.addEventListener("load", hash);
    w.addEventListener("beforeprint", function () { revealAll(true); });
  }

  /* ── Brojač: .a-count[data-to] (data-dec, data-prefix, data-suffix); 1,2 s, kriva sajta ── */
  function fmt(n, dec, en) {
    var p = n.toFixed(dec).split(".");
    p[0] = p[0].replace(/\B(?=(\d{3})+(?!\d))/g, en ? "," : ".");
    return p.join(en ? "." : ",");
  }
  function count(el) {
    if (el.dataset.counted) return;
    el.dataset.counted = "1";
    var to = parseFloat(el.dataset.to), dec = parseInt(el.dataset.dec || "0", 10);
    var en = /^en/i.test(html.lang), pre = el.dataset.prefix || "", suf = el.dataset.suffix || "";
    var real = d.createElement("span"), anim = d.createElement("span");
    real.className = "a-count-real"; anim.className = "a-count-anim"; anim.setAttribute("aria-hidden", "true");
    while (el.firstChild) real.appendChild(el.firstChild);
    el.appendChild(real); el.appendChild(anim);
    el.style.display = getComputedStyle(el).display === "inline" ? "inline-grid" : "grid";
    el.classList.add("is-counting");
    var t0 = performance.now(), done = false;
    function finish() { if (done) return; done = true; el.classList.remove("is-counting"); anim.remove(); el.style.display = ""; }
    setTimeout(finish, 1300); // završava i ako pregledač privremeno ne crta kadrove (rAF stoji)
    (function tick(now) {
      if (done) return;
      var p = Math.min(1, (now - t0) / 1200);
      anim.textContent = pre + fmt(to * ease(p), dec, en) + suf;
      if (p < 1) requestAnimationFrame(tick); else finish();
    })(t0);
  }
  function initCount() {
    var els = $$(".a-count[data-to]");
    if (reduced || !els.length || !hasIO) return;
    var fcp = (performance.getEntriesByName && performance.getEntriesByName("first-contentful-paint")[0] || {}).startTime;
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        io.unobserve(e.target);
        count(e.target);
      });
    }, { rootMargin: "0px 0px -15% 0px" });
    // Bez čitanja geometrije (nema forsiranog layouta pri učitavanju): brojke na vrhu strane se odlučuju po vremenu, ostale preko IO.
    els.forEach(function (el) {
      if (el.closest(".a-hero")) {
        // Hero: brojanje kreće kad se brojka pojavi (CSS kašnjenje ulaska); ako je skripta zakasnila, ostaje statično.
        var host = el.closest(".a-after") || el, delay = parseFloat(getComputedStyle(host).animationDelay) * 1000 || 0;
        var elapsed = fcp ? performance.now() - fcp : 0;
        if (elapsed <= delay + 120) setTimeout(function () { count(el); }, Math.max(0, delay - elapsed));
        return;
      }
      // Odmah ispod naslova članka: broji od nule samo ako ništa još nije prikazano (bez skoka konačno → 0).
      if (el.closest("article > h1 + p")) { if (!fcp) count(el); return; }
      io.observe(el);
    });
  }

  /* ── Linija koraka (.a-steps): prati skrol samo dok je blok vidljiv; ne vraća se; korak se pali kad ga linija stigne ── */
  function initSteps() {
    if (reduced || !hasIO) return;
    $$(".a-steps").forEach(function (box) {
      var line = box.querySelector(".a-steps-line");
      if (!line) { line = d.createElement("span"); line.className = "a-steps-line"; line.setAttribute("aria-hidden", "true"); box.insertBefore(line, box.firstChild); }
      box.classList.add("is-live");
      var max = 0, raf = 0, on = false, done = false;
      function items() { return $$(".step-card, li", box).filter(function (x) { return !x.classList.contains("is-on") && !x.dataset.pending; }); }
      function update() {
        raf = 0;
        var r = box.getBoundingClientRect(), head = vh() * 0.6;
        var p = Math.max(0, Math.min(1, (head - r.top) / r.height));
        if (p > max) { max = p; line.style.transform = "scaleY(" + max.toFixed(4) + ")"; }
        // Korak se pali kad linija stigne do njegovog broja (kartica: .a-num; lista: vrh stavke, gdje je oznaka).
        function top(x) { return (x.querySelector(".a-num") || x).getBoundingClientRect().top; }
        var lit = items().filter(function (x) { return top(x) < head; })
          .sort(function (a, b) { return top(a) - top(b) || a.getBoundingClientRect().left - b.getBoundingClientRect().left; });
        lit.forEach(function (x, i) { x.dataset.pending = "1"; setTimeout(function () { x.classList.add("is-on"); delete x.dataset.pending; }, i * 60); });
        if (max >= 1 && !items().length) { done = true; stop(); }
      }
      function onScroll() { if (!raf) raf = requestAnimationFrame(update); }
      function start() { if (on || done) return; on = true; w.addEventListener("scroll", onScroll, { passive: true }); w.addEventListener("resize", onScroll); onScroll(); }
      function stop() { if (!on) return; on = false; w.removeEventListener("scroll", onScroll); w.removeEventListener("resize", onScroll); }
      new IntersectionObserver(function (es) { if (es[es.length - 1].isIntersecting) start(); else stop(); }).observe(box);
    });
  }

  /* ── Sjaj (.a-sheen): jednom, kad je element bar do pola u vidnom polju ── */
  function initSheen() {
    var els = $$(".a-sheen");
    if (reduced || !els.length || !hasIO) return;
    els.forEach(function (el) {
      var bar = d.createElement("span");
      bar.className = "a-sheen-bar"; bar.setAttribute("aria-hidden", "true");
      el.insertBefore(bar, el.firstChild);
    });
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("is-shine"); io.unobserve(e.target); } });
    }, { threshold: 0.5 });
    els.forEach(function (el) { io.observe(el); });
  }

  /* ── Linija čitanja: CSS animation-timeline gdje postoji, inače rAF ── */
  function initProgress() {
    var bar = d.querySelector(".a-progress");
    if (!bar || (w.CSS && CSS.supports && CSS.supports("animation-timeline: view()"))) return;
    var art = bar.closest("article") || d.querySelector("article"), raf = 0;
    function up() {
      raf = 0;
      var r = art.getBoundingClientRect(), p = Math.max(0, Math.min(1, -r.top / Math.max(1, r.height - vh())));
      bar.style.transform = "scaleX(" + p.toFixed(4) + ")";
    }
    function req() { if (!raf) raf = requestAnimationFrame(up); }
    w.addEventListener("scroll", req, { passive: true });
    w.addEventListener("resize", req);
    req();
  }

  w.Motion = { reduced: reduced, ease: ease, refresh: function (root) { if (armIO) scanUnits(root || d); } };

  // Poslije skripti strane (njihov DOMContentLoaded je registrovan ranije), da animacije vide konačni DOM.
  // defer skripta se izvršava prije DOMContentLoaded (readyState je tada već "interactive").
  function init() { [initBar, initMenu, initReveal, initCount, initSteps, initSheen, initProgress].forEach(function (f) { safe(f)(); }); }
  var nav = performance.getEntriesByType && performance.getEntriesByType("navigation")[0];
  if (d.readyState === "complete" || (nav && nav.domContentLoadedEventStart > 0)) init();
  else d.addEventListener("DOMContentLoaded", init);
})();
