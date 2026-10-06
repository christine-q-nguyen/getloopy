/* christine.nguyen — site.js
   No dependencies. Nine jobs:
   1. reveal-on-scroll for .rv elements (IntersectionObserver; everything shows immediately without JS or under reduced motion)
   2. copy-to-clipboard on [data-copy-email] (progressive: falls through to mailto: when the Clipboard API is missing)
   3. mark the current page in the nav (aria-current) when the HTML didn't already
   4. sketch layer: honour ?sketch=0, inject the #sketch filter, let diagram strokes draw themselves in on reveal
   5. trace: the orange dot travels every svg[data-trace] loop and leaves a trace that fades back to hairline
   6. runners: one orange dot on each outer grid line (the two middle lines stay quiet)
   7. play: [data-anim] elements animate only while they are in view
   8. draw: a [data-draw] portrait draws its lines in once, with a brief line boil, then the shading settles over them
   Everything in 4–8 is decoration: it is skipped under prefers-reduced-motion and absent without JS. */
(function () {
  var d = document, html = d.documentElement;
  html.classList.remove("no-js");
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var hasIO = "IntersectionObserver" in window;
  var each = function (list, fn) { Array.prototype.forEach.call(list, fn); };

  // 1. reveal
  var items = d.querySelectorAll(".rv");
  if (!hasIO || reduce) {
    each(items, function (el) { el.classList.add("in"); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
    each(items, function (el) { io.observe(el); });
  }

  // 2. copy email
  d.addEventListener("click", function (e) {
    var el = e.target.closest && e.target.closest("[data-copy-email]");
    if (!el) return;
    if (!(navigator.clipboard && navigator.clipboard.writeText)) return;
    e.preventDefault();
    var email = el.getAttribute("data-copy-email");
    if (!el.dataset.originalText) el.dataset.originalText = el.textContent;
    navigator.clipboard.writeText(email).then(function () {
      el.textContent = "Copied";
      el.setAttribute("aria-live", "polite");
      setTimeout(function () { el.textContent = el.dataset.originalText; }, 1600);
    });
  });

  // 3. current page in nav
  var here = location.pathname.split("/").pop() || "index.html";
  each(d.querySelectorAll(".nav li a"), function (a) {
    var target = (a.getAttribute("href") || "").split("/").pop();
    if (target === here && !a.hasAttribute("aria-current")) a.setAttribute("aria-current", "page");
  });

  // 4. sketch
  var params = new URLSearchParams(location.search);
  if (params.get("sketch") === "0") html.classList.remove("sketch");
  if (html.classList.contains("sketch")) {
    d.body.insertAdjacentHTML("afterbegin",
      '<svg width="0" height="0" aria-hidden="true" focusable="false" style="position:absolute"><defs>' +
      '<filter id="sketch" filterUnits="userSpaceOnUse" x="-10%" y="-10%" width="120%" height="120%" color-interpolation-filters="sRGB">' +
      '<feTurbulence type="fractalNoise" baseFrequency=".035" numOctaves="2" seed="7" result="n"/>' +
      '<feDisplacementMap in="SourceGraphic" in2="n" scale="2.4" xChannelSelector="R" yChannelSelector="G"/>' +
      '</filter></defs></svg>');
    if (hasIO && !reduce) {
      each(d.querySelectorAll(".diagram svg, .tile .art > svg"), function (svg) {
        each(svg.querySelectorAll(".dg-line, .dg-line path, .dg-box, .dg-box rect, .dg-arrow"), function (el) {
          if (/^(path|rect|circle|ellipse|line|polyline|polygon)$/i.test(el.tagName)) el.setAttribute("pathLength", "1");
        });
        svg.classList.add("draw");
      });
    }
  }

  // 5. trace
  function trace(svg) {
    var base = svg.querySelector(".loop-base"), dot = svg.querySelector(".trace-dot");
    if (!base || !base.getTotalLength) return;
    var L = base.getTotalLength();
    var dur = (parseFloat(svg.getAttribute("data-trace")) || 14) * 1000;
    var after = dot && dot.parentNode === base.parentNode ? dot : base.nextSibling;
    var trails = [0.32, 0.18, 0.07].map(function (f, i) {
      var p = base.cloneNode(false);
      p.setAttribute("class", "trail t" + (i + 1));
      p.removeAttribute("id");
      p.style.strokeDasharray = (f * L) + " " + L;
      base.parentNode.insertBefore(p, after);
      return { el: p, T: f * L };
    });
    var phase = parseFloat(svg.getAttribute("data-trace-phase")) || 0;
    var t0 = null, raf = 0, visible = true;
    function frame(ts) {
      if (t0 === null) t0 = ts - phase;
      var s = (((ts - t0) % dur) / dur) * L;
      for (var i = 0; i < trails.length; i++) trails[i].el.style.strokeDashoffset = trails[i].T - s;
      if (dot) {
        var pt = base.getPointAtLength(s);
        dot.setAttribute("cx", pt.x.toFixed(2));
        dot.setAttribute("cy", pt.y.toFixed(2));
      }
      raf = visible ? requestAnimationFrame(frame) : 0;
    }
    function start() { if (!raf) raf = requestAnimationFrame(frame); }
    if (hasIO) {
      new IntersectionObserver(function (entries) {
        visible = entries[0].isIntersecting;
        if (visible) start(); else { cancelAnimationFrame(raf); raf = 0; }
      }).observe(svg);
    } else start();
  }
  if (!reduce) each(d.querySelectorAll("svg[data-trace]"), trace);

  // 6. runners
  var grid = d.querySelector(".grid-lines");
  if (grid && !reduce) {
    [[0, 31, -6, 0], [3, 37, -22, 1]].forEach(function (r) {
      var b = d.createElement("b");
      b.className = "run" + (r[3] ? " up" : "");
      b.setAttribute("data-line", r[0]);
      b.style.setProperty("--dur", r[1] + "s");
      b.style.setProperty("--delay", r[2] + "s");
      grid.appendChild(b);
    });
  }

  // 6b. runners fade while they cross text, so the motion never fights legibility
  if (grid && !reduce) {
    var runs = grid.querySelectorAll(".run");
    var textSel = "main p, main li, main h1, main h2, main h3, main td, main th, main dt, main dd, main figcaption, main blockquote, main .tag, main .lbl, main .proof";
    var fadeTick = function () {
      if (d.hidden) return;
      var vh = window.innerHeight, boxes = [];
      each(d.querySelectorAll(textSel), function (el) {
        var r = el.getBoundingClientRect();
        if (r.bottom > 0 && r.top < vh && r.width > 0 && el.textContent.trim()) boxes.push(r);
      });
      each(runs, function (b) {
        var r = b.getBoundingClientRect(), hit = false;
        for (var i = 0; i < boxes.length && !hit; i++) {
          var t = boxes[i];
          hit = r.left < t.right && r.right > t.left && r.top < t.bottom && r.bottom > t.top;
        }
        b.classList.toggle("fade", hit);
      });
    };
    setInterval(fadeTick, 400);
  }

  // 7. play
  var anim = d.querySelectorAll("[data-anim]");
  if (anim.length && !reduce) {
    if (hasIO) {
      var pio = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) { e.target.classList.toggle("play", e.isIntersecting); });
      }, { threshold: 0.15 });
      each(anim, function (el) { pio.observe(el); });
    } else each(anim, function (el) { el.classList.add("play"); });
  }

  // 8. draw
  each(d.querySelectorAll("[data-draw]"), function (fig) {
    var lines = fig.querySelector(".portrait-lines"), tone = fig.querySelector(".portrait-tone");
    var noise = fig.querySelector("feTurbulence");
    var strokes = Array.prototype.map.call(fig.querySelectorAll("[data-at]"), function (p) {
      return { el: p, at: parseFloat(p.getAttribute("data-at")), dur: parseFloat(p.getAttribute("data-for")) };
    });
    if (reduce || !hasIO || !lines || !tone || !strokes.length) return;
    var linesEnd = Math.max.apply(null, strokes.map(function (s) { return s.at + s.dur; }));
    var toneAt = linesEnd * 0.6, toneFor = 1.8, end = toneAt + toneFor;
    var clamp = function (x) { return x < 0 ? 0 : x > 1 ? 1 : x; };
    var ease = function (x) { return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
    strokes.forEach(function (s) { s.el.setAttribute("stroke-dasharray", "1 1"); s.el.setAttribute("stroke-dashoffset", "1"); });
    tone.style.opacity = "0";
    fig.classList.add("drawing");
    new IntersectionObserver(function (entries, obs) {
      if (!entries[0].isIntersecting) return;
      obs.disconnect();
      if (noise) lines.setAttribute("filter", "url(#" + noise.parentNode.id + ")");
      var t0 = null, beat = -1;
      requestAnimationFrame(function frame(ts) {
        if (t0 === null) t0 = ts;
        var t = (ts - t0) / 1000;
        strokes.forEach(function (s) { s.el.setAttribute("stroke-dashoffset", (1 - ease(clamp((t - s.at) / s.dur))).toFixed(4)); });
        tone.style.opacity = ease(clamp((t - toneAt) / toneFor)).toFixed(3);
        lines.style.opacity = (1 - ease(clamp((t - toneAt - toneFor / 2) / (toneFor / 2)))).toFixed(3);
        if (noise && t < linesEnd) {
          var b = Math.floor(t / 0.11);
          if (b !== beat) { beat = b; noise.setAttribute("seed", String(b % 5 + 1)); }
        } else if (lines.hasAttribute("filter")) lines.removeAttribute("filter");
        if (t < end) return requestAnimationFrame(frame);
        fig.classList.remove("drawing");
        tone.style.opacity = lines.style.opacity = "";
      });
    }, { threshold: 0.2 }).observe(fig);
  });
})();
