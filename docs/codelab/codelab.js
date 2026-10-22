/* One step on screen, routed by #step-N, with arrow keys. Without this file every step is open and the links are plain anchors. */
(function () {
  "use strict";
  var KEY = "vela-codelab-visited";
  var main = document.querySelector("main.codelab");
  var steps = Array.prototype.slice.call(document.querySelectorAll("section.step"));
  if (!main || !steps.length) return;
  var items = Array.prototype.slice.call(document.querySelectorAll(".route li"));
  var visited = [];
  try {
    visited = JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch (e) {
    console.warn("vela: visited steps not read from localStorage; starting with none", e);
    visited = [];
  }
  var current = -1;

  function save() {
    try {
      localStorage.setItem(KEY, JSON.stringify(visited));
    } catch (e) {
      console.warn("vela: visited steps not saved to localStorage; the ticks won't survive a reload", e);
    }
  }
  function fromHash() {
    var m = location.hash.match(/^#step-(\d+)$/);
    var n = m ? Number(m[1]) - 1 : 0;
    return n >= 0 && n < steps.length ? n : 0;
  }
  function show(n, scroll) {
    current = n;
    if (visited.indexOf(n) < 0) { visited.push(n); save(); }
    steps.forEach(function (s, i) { s.classList.toggle("active", i === n); });
    items.forEach(function (li, i) {
      li.classList.toggle("current", i === n);
      li.classList.toggle("done", i !== n && visited.indexOf(i) >= 0);
      var a = li.querySelector("a");
      if (i === n) a.setAttribute("aria-current", "step"); else a.removeAttribute("aria-current");
    });
    var left = steps.slice(n).reduce(function (t, s) { return t + Number(s.getAttribute("data-min")); }, 0);
    document.getElementById("timeleft").textContent = left + " min left";
    document.getElementById("bar").style.width = ((n + 1) / steps.length * 100) + "%";
    document.title = steps[n].getAttribute("data-title") + " | Plan your first initiative with vela";
    if (diagrams[n]) diagrams[n].set(0);
    if (scroll) window.scrollTo(0, 0);
  }
  function go(n) {
    if (n < 0 || n >= steps.length) return;
    location.hash = "step-" + (n + 1);
  }

  /* A sequence diagram lights one arrow at a time. The step's own Next and Back (and the arrow keys) walk its arrows before they leave the step. */
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text) n.textContent = text;
    return n;
  }
  var diagrams = steps.map(function (step) {
    var fig = step.querySelector("figure.seq");
    if (!fig) return null;
    var arrows = Array.prototype.slice.call(fig.querySelectorAll(".arrow"));
    var words = Array.prototype.slice.call(fig.querySelectorAll(".seq-list li"));
    var d = { index: 0, count: arrows.length };
    var controls = el("div", "controls");
    var back = el("button", "", "\u2190 Back");
    var fwd = el("button", "primary", "Next arrow \u2192");
    var status = el("span", "status");
    status.setAttribute("aria-live", "polite");
    back.type = "button"; fwd.type = "button";
    controls.appendChild(back); controls.appendChild(fwd); controls.appendChild(status);
    fig.insertBefore(controls, fig.firstChild);
    d.set = function (i) {
      d.index = Math.max(0, Math.min(d.count - 1, i));
      arrows.forEach(function (a, n) {
        a.classList.toggle("now", n === d.index);
        a.classList.toggle("past", n < d.index);
      });
      back.disabled = d.index === 0;
      fwd.disabled = d.index === d.count - 1;
      status.textContent = "Arrow " + (d.index + 1) + " of " + d.count + ": " + words[d.index].textContent;
    };
    d.canNext = function () { return d.index < d.count - 1; };
    d.canBack = function () { return d.index > 0; };
    back.addEventListener("click", function () { d.set(d.index - 1); });
    fwd.addEventListener("click", function () { d.set(d.index + 1); });
    fig.classList.add("js");
    d.set(0);
    return d;
  });
  function walk(direction) {
    var d = diagrams[current];
    if (d && direction > 0 && d.canNext()) { d.set(d.index + 1); return true; }
    if (d && direction < 0 && d.canBack()) { d.set(d.index - 1); return true; }
    return false;
  }

  main.classList.add("js");
  window.addEventListener("hashchange", function () { show(fromHash(), true); });
  document.addEventListener("keydown", function (e) {
    if (e.altKey || e.ctrlKey || e.metaKey || (e.target.closest && e.target.closest("input, textarea, summary"))) return;
    if (e.key === "ArrowRight" && !walk(1)) go(current + 1);
    if (e.key === "ArrowLeft" && !walk(-1)) go(current - 1);
  });
  document.querySelectorAll("a.next-step, a.prev").forEach(function (a) {
    a.addEventListener("click", function (e) {
      if (walk(a.classList.contains("prev") ? -1 : 1)) e.preventDefault();
    });
  });
  document.querySelectorAll(".code").forEach(function (box) {
    var btn = box.querySelector(".copy");
    btn.addEventListener("click", function () {
      var text = box.querySelector("pre").innerText;
      var done = function () { btn.textContent = "Copied"; setTimeout(function () { btn.textContent = "Copy"; }, 1500); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function (e) { console.warn("vela: copy failed", e); btn.textContent = "Select and copy"; });
      } else { btn.textContent = "Select and copy"; }
    });
  });
  show(fromHash(), true);
})();
