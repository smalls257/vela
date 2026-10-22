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
    if (scroll) window.scrollTo(0, 0);
  }
  function go(n) {
    if (n < 0 || n >= steps.length) return;
    location.hash = "step-" + (n + 1);
  }

  main.classList.add("js");
  window.addEventListener("hashchange", function () { show(fromHash(), true); });
  document.addEventListener("keydown", function (e) {
    if (e.altKey || e.ctrlKey || e.metaKey || (e.target.closest && e.target.closest("input, textarea, summary"))) return;
    if (e.key === "ArrowRight") go(current + 1);
    if (e.key === "ArrowLeft") go(current - 1);
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
