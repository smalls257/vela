/* How vela thinks: the interactive parts. Without this file every page still reads straight through (cards and steps are all open). */
(function () {
  "use strict";
  var SVG = "http://www.w3.org/2000/svg";

  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    if (text) node.textContent = text;
    return node;
  }

  /* Links into the repository work from a checkout; served over http they go to the repository on GitHub. */
  function pointRepoLinksAtGitHub() {
    if (location.protocol !== "http:" && location.protocol !== "https:") return;
    document.querySelectorAll("a[data-repo]").forEach(function (a) {
      var path = a.getAttribute("data-repo");
      var kind = /\/$/.test(path) ? "tree" : "blob";
      a.href = "https://github.com/smalls257/vela/" + kind + "/main/" + path;
    });
  }

  /* A deck is a diagram of clickable steps. One card is open; arrow keys move along the chips. */
  function buildDeck(deck) {
    var cards = Array.prototype.slice.call(deck.querySelectorAll(".card"));
    if (!cards.length) return;
    var holder = el("div", { "class": "chip-groups" });
    var chips = [], groups = {};
    cards.forEach(function (card, index) {
      var name = card.getAttribute("data-group") || "";
      if (!groups[name]) {
        var box = el("div", { "class": "chip-group" });
        if (name) box.appendChild(el("p", { "class": "group-name" }, name));
        var list = el("ol", { "class": "chips", role: "presentation" });
        box.appendChild(list);
        holder.appendChild(box);
        groups[name] = list;
      }
      var chip = el("button", { type: "button", "class": "chip", role: "tab", id: "tab-" + card.id,
        "aria-controls": card.id, "data-kind": card.getAttribute("data-kind") || "" }, card.getAttribute("data-label"));
      var item = el("li", { role: "presentation" });
      item.appendChild(chip);
      groups[name].appendChild(item);
      chips.push(chip);
      card.setAttribute("role", "tabpanel");
      card.setAttribute("aria-labelledby", chip.id);
      chip.addEventListener("click", function () { select(index, false); });
      chip.addEventListener("keydown", function (event) { move(event, index); });
      if (index + 1 < cards.length) {
        var next = el("p", { "class": "next" });
        var go = el("button", { type: "button" }, "Next: " + cards[index + 1].getAttribute("data-label") + " →");
        go.addEventListener("click", function () { select(index + 1, true); });
        next.appendChild(go);
        card.appendChild(next);
      }
    });
    var tabs = el("div", { role: "tablist", "aria-label": deck.getAttribute("data-label") });
    tabs.appendChild(holder);
    deck.insertBefore(tabs, deck.querySelector(".deck-cards"));
    deck.classList.add("js");

    function select(index, focusCard) {
      cards.forEach(function (card, i) {
        card.hidden = i !== index;
        chips[i].setAttribute("aria-selected", i === index ? "true" : "false");
        chips[i].tabIndex = i === index ? 0 : -1;
      });
      if (focusCard) { chips[index].focus(); }
    }
    function move(event, index) {
      var step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key];
      var target = event.key === "Home" ? 0 : event.key === "End" ? cards.length - 1 : step ? index + step : null;
      if (target === null || target < 0 || target >= cards.length) return;
      event.preventDefault();
      select(target, true);
    }
    var wanted = cards.map(function (c) { return c.id; }).indexOf(location.hash.slice(1));
    select(wanted < 0 ? 0 : wanted, false);
    if (wanted >= 0) setTimeout(function () { tabs.scrollIntoView(); }, 0);  /* the browser's own jump to #id lands on the card; show the whole diagram instead */
  }

  /* A stepper shows one step at a time, with Back and Next, like the dashboard's flow player. A flow also draws its apps. */
  function buildStepper(stepper) {
    var steps = Array.prototype.slice.call(stepper.querySelectorAll(".step"));
    if (!steps.length) return;
    var nodes = stepper.getAttribute("data-nodes") ? JSON.parse(stepper.getAttribute("data-nodes")) : [];
    var current = 0, drawing = null, contractLine = null;
    var label = stepper.getAttribute("data-label");
    var controls = el("div", { "class": "controls", role: "group", "aria-label": label });
    var back = el("button", { type: "button" }, "← Back");
    var forward = el("button", { type: "button", "class": "primary" }, "Next →");
    var status = el("span", { "class": "status", "aria-live": "polite" });
    controls.appendChild(back); controls.appendChild(forward); controls.appendChild(status);
    var dots = el("div", { "class": "dots" });
    var dotButtons = steps.map(function (step, i) {
      var dot = el("button", { type: "button", "aria-label": "Step " + (i + 1) + ": " + step.querySelector("h3").textContent });
      dot.addEventListener("click", function () { show(i); });
      dots.appendChild(dot);
      return dot;
    });
    if (nodes.length) {
      drawing = drawFlow(nodes, function (nodeId) {
        for (var i = 0; i < steps.length; i++) {
          if (steps[i].getAttribute("data-from") === nodeId || steps[i].getAttribute("data-to") === nodeId) { show(i); return; }
        }
      });
      contractLine = el("p", { "class": "flow-contract" });
      stepper.insertBefore(drawing.svg, stepper.firstChild);
      stepper.insertBefore(contractLine, drawing.svg.nextSibling);
      stepper.insertBefore(controls, contractLine.nextSibling);
    } else {
      stepper.insertBefore(controls, stepper.firstChild);
    }
    stepper.insertBefore(dots, controls.nextSibling);
    stepper.classList.add("js");
    back.addEventListener("click", function () { show(current - 1); });
    forward.addEventListener("click", function () { show(current + 1); });
    stepper.addEventListener("keydown", function (event) {
      if (event.target.closest && event.target.closest("a, summary")) return;
      if (event.key === "ArrowRight") { event.preventDefault(); show(current + 1); }
      if (event.key === "ArrowLeft") { event.preventDefault(); show(current - 1); }
    });

    function show(index) {
      if (index < 0 || index >= steps.length) return;
      current = index;
      steps.forEach(function (step, i) { step.hidden = i !== index; });
      dotButtons.forEach(function (dot, i) {
        if (i === index) dot.setAttribute("aria-current", "step"); else dot.removeAttribute("aria-current");
        dot.classList.toggle("past", i < index);
      });
      back.disabled = index === 0;
      forward.disabled = index === steps.length - 1;
      status.textContent = "Step " + (index + 1) + " of " + steps.length;
      if (drawing) {
        var step = steps[index];
        drawing.draw(steps.slice(0, index + 1).map(function (s) {
          return { from: s.getAttribute("data-from"), to: s.getAttribute("data-to") };
        }));
        var contract = step.getAttribute("data-contract");
        contractLine.textContent = "";
        if (contract && contract !== "-") {
          contractLine.appendChild(document.createTextNode("Over "));
          contractLine.appendChild(el("b", {}, contract));
        }
      }
    }
    show(0);
  }

  function drawFlow(nodes, onNode) {
    var W = 420, H = 250, NW = 138, NH = 38;
    var svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.setAttribute("class", "flow-svg");
    svg.setAttribute("role", "group");
    svg.setAttribute("aria-label", "The apps in this flow. The current step is described below.");
    var defs = document.createElementNS(SVG, "defs");
    defs.innerHTML = '<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z"/></marker>';
    svg.appendChild(defs);
    var edges = document.createElementNS(SVG, "g");
    svg.appendChild(edges);
    var byId = {}, nodeEls = {};
    nodes.forEach(function (n) {
      byId[n.id] = n;
      var g = document.createElementNS(SVG, "g");
      g.setAttribute("class", "node");
      g.setAttribute("role", "button");
      g.setAttribute("tabindex", "0");
      g.setAttribute("aria-label", n.label + ": jump to its first step");
      var rect = document.createElementNS(SVG, "rect");
      rect.setAttribute("x", n.x - NW / 2); rect.setAttribute("y", n.y - NH / 2);
      rect.setAttribute("width", NW); rect.setAttribute("height", NH);
      var text = document.createElementNS(SVG, "text");
      text.setAttribute("x", n.x); text.setAttribute("y", n.y);
      text.textContent = n.label;
      g.appendChild(rect); g.appendChild(text);
      g.addEventListener("click", function () { onNode(n.id); });
      g.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onNode(n.id); } });
      svg.appendChild(g);
      nodeEls[n.id] = g;
    });
    function edgePoint(a, b) {
      var dx = b.x - a.x, dy = b.y - a.y;
      var scale = Math.min(dx ? (NW / 2 + 3) / Math.abs(dx) : Infinity, dy ? (NH / 2 + 3) / Math.abs(dy) : Infinity);
      return { x: a.x + dx * scale, y: a.y + dy * scale };
    }
    function draw(path) {
      edges.textContent = "";
      Object.keys(nodeEls).forEach(function (id) { nodeEls[id].classList.remove("on"); });
      path.forEach(function (hop, i) {
        var last = i === path.length - 1;
        var a = byId[hop.from], b = byId[hop.to];
        if (!a || !b) return;
        if (last) { nodeEls[hop.from].classList.add("on"); nodeEls[hop.to].classList.add("on"); }
        if (a === b) return;
        var start = edgePoint(a, b), end = edgePoint(b, a);
        var line = document.createElementNS(SVG, "line");
        line.setAttribute("x1", start.x); line.setAttribute("y1", start.y);
        line.setAttribute("x2", end.x); line.setAttribute("y2", end.y);
        line.setAttribute("class", "edge" + (last ? " now" : ""));
        if (last) line.setAttribute("marker-end", "url(#arrow)");
        edges.appendChild(line);
      });
    }
    return { svg: svg, draw: draw };
  }

  function start() {
    pointRepoLinksAtGitHub();
    document.querySelectorAll(".deck").forEach(buildDeck);
    document.querySelectorAll(".stepper").forEach(buildStepper);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
