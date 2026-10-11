/* Has anything changed since this copy was made? The build stamps the answer as of build time (planner freshness),
   and the page shows a quiet banner only when something has. A page opened as a file reads that stamp and nothing
   else: it can touch neither the file system nor the network. Served from this machine (`planner explore --serve`),
   it also asks the helper's GET /freshness on load and again whenever the window regains focus. It reports and never
   updates: nothing here pulls, opens or replays anything. */
const Freshness = (() => {
  const MIN_GAP = 20000;  // ms between asks, so refocusing a window does not run a git fetch each time
  const st = { report: D.freshness, live: false, fetches: 0, busy: false, last: 0, error: "" };
  let fetchFn = (...a) => window.fetch(...a), servedFn = () => location.protocol === "http:" || location.protocol === "https:";
  const served = () => servedFn();
  const stamp = (r) => (r && r.checked_at ? r.checked_at.replace("T", " ").slice(0, 16) : "");

  /* The banner's words for a report, or "" when nothing has changed. */
  function words(r) {
    if (!r) return "";
    if (r.role === "reader") {
      return r.state === "newer" ? `A newer copy was published on ${r.latest && r.latest.date ? r.latest.date : "a later date"}; reopen it to update — your drafts carry over.` : "";
    }
    if (r.role !== "owner") return "";
    const parts = [];
    if (r.behind > 0) parts.push(`${plural(r.behind, "commit")} behind upstream`);
    if (r.uncommitted > 0) parts.push(`${plural(r.uncommitted, "file")} uncommitted`);
    return parts.length ? parts.join("; ") + "." : "";
  }
  function render() {
    const box = $("#fresh"), text = words(st.report);
    box.hidden = !text;
    box.textContent = "";
    if (!text) return;
    const when = st.live ? "checked just now" : st.report.checked_at ? `as of ${stamp(st.report)}, when this page was built` : "";
    box.append(h("span", { class: "fresh-text" }, text), when ? h("span", { class: "fresh-when" }, ` (${when})`) : null);
    box.title = st.error ? `The live check failed: ${st.error}` : "";
    box.dataset.state = st.report.state;
  }
  async function poll(why) {
    if (!served() || st.busy || Date.now() - st.last < MIN_GAP) return false;
    st.busy = true; st.fetches++;
    try {
      const res = await fetchFn("/freshness");
      if (!res.ok) throw new Error(`/freshness answered ${res.status}`);
      st.report = await res.json(); st.live = true; st.error = "";
    } catch (e) {
      st.error = e.message;
      console.warn(`[freshness] the ${why} check failed; the banner keeps the build-time stamp:`, e.message);
    } finally { st.busy = false; st.last = Date.now(); render(); }
    return true;
  }
  function start() {
    render();
    if (!served() || !["owner", "reader"].includes(D.role)) return;  // a file never looks: its freshness is the stamp; with no role there is nothing to check
    poll("load");
    window.addEventListener("focus", () => poll("focus"));
  }
  /* For #selftest: run the page against a fake helper, then put the real one back. */
  function use(fake, isServed) { const was = [fetchFn, servedFn, st.last]; fetchFn = fake; servedFn = isServed; st.last = 0; return () => { [fetchFn, servedFn, st.last] = was; }; }
  return { st, words, render, poll, start, use, served };
})();
