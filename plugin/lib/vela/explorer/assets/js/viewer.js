/* Who is viewing: the one answer the whole page gives to "who is this for?". Needs you, the "N for you" badge, Grills
   waiting ("Mine") and the "Waiting on you" filter all ask here and nowhere else.

   The Violation this prevents is a Distributed Monolith in the browser: when the grills view had its own person menu and
   the question list its own role match, picking someone in one changed nothing in the others, and the badge, the block
   and the grills could each name a different person. A single "You are" picker later writes `set()` and every reader
   follows without a rework. Nothing else on the page is a person picker; the grills menu is a second face on `set()`.

   Who counts, in this order (viewer() returns the first that applies):
   - a person picked here, or named in a link (#s=grills&as=agent-lead): "pick" ("everyone" when the pick is nobody on purpose)
   - the handle this page was built for (D.me; the shared page carries nobody's): "page"
   - the people the plan records under the role in Viewing as (D.onboard.roles): "role"; a role nobody is recorded under
     still counts as a role, and questions match it by the words of who was asked ("the product owner")
   - nobody. The page then never says "you". */
const Viewer = (() => {
  const KEY = `explorer.viewer.${D.vaultId}`;
  const EVERYONE = "*";
  const st = { as: Settings.read(KEY) || "" };  // "" nobody picked, "*" everyone on purpose, else a handle
  const lower = (t) => String(t || "").toLowerCase();
  const handleOf = (t) => { const x = String(t || "").trim(); return x && x !== EVERYONE && !x.startsWith("@") ? "@" + x : x; };
  const ROLE_WORDS = { exec: /exec|ceo|cio|cto|ciso|chief|sponsor|director/i, product: /product/i, qa: /\bqa\b|test|quality/i, eng: /engineer|tech|architect|develop/i, mgr: /manager|delivery|program/i };

  function viewer() {
    const role = typeof Onboard !== "undefined" ? Onboard.myRole().role : "";  // the role someone chose or the plan records; "" when neither
    if (st.as === EVERYONE) return { handle: "", handles: [], role: "", source: "everyone" };
    if (st.as) return { handle: st.as, handles: [st.as], role, source: "pick" };
    if (D.me && D.me.handle) return { handle: "@" + D.me.handle, handles: ["@" + D.me.handle], role, source: "page" };
    const recorded = Object.entries((D.onboard && D.onboard.roles) || {}).filter(([, r]) => r === role).map(([hd]) => handleOf(hd));
    return { handle: recorded[0] || "", handles: recorded, role, source: role ? "role" : "" };
  }
  /* Known: the page can tell which rows are theirs, by a handle or by a role whose words match (the lead role has none). */
  const known = () => { const v = viewer(); return v.handles.length > 0 || !!ROLE_WORDS[v.role]; };
  const hasPerson = () => viewer().handles.length > 0;
  const handleSet = () => new Set(viewer().handles.map(lower));
  const isYou = (handle) => handleSet().has(lower(handle));
  /* A line (or any row) is for the viewer when it names one of their handles, or, for a viewer known only by their role, when who
     it was asked of reads as that role (a door is a kind of reader, not a person, so the match is by what they are called). `words` is that name as the plan gives it; rows with none match by handle alone. */
  function isFor(row) {
    const v = viewer();
    if ((row.for || []).some(isYou)) return true;
    if (row.named && v.handles.some((handle) => lower(personName(handle)) === row.named)) return true;  // "Booking senior" written where a handle could be
    return v.source === "role" && !!ROLE_WORDS[v.role] && !!row.words && ROLE_WORDS[v.role].test(row.words);
  }
  const name = () => { const v = viewer(); return v.handle ? personName(v.handle) : v.role ? "this role" : "Everyone"; };

  function afterChange() {
    if (typeof renderMasters === "function") renderMasters();
    if (typeof Nav !== "undefined") Nav.refresh();
    if (App.view === "role") rerender();
  }
  /* The one way to change who is viewing. A handle is kept in this browser; "" forgets it; "*" is everyone on purpose. */
  function set(handle) {
    st.as = handle === EVERYONE ? EVERYONE : handleOf(handle);
    if (st.as) Settings.write(KEY, st.as); else { try { localStorage.removeItem(KEY); } catch (e) { console.warn("[viewer] this browser keeps no settings:", e.message); } }
    afterChange();
  }
  /* A link names someone for this visit only; it is not saved, so a shared link never changes the reader's own pick. */
  function fromLink(value) { st.as = value === "everyone" ? EVERYONE : handleOf(value); }
  const pick = () => st.as;
  if (HASH.has("as")) fromLink(HASH.get("as"));  // #role=exec&as=agent-lead: a link can say who is looking, for this visit only
  return { viewer, known, hasPerson, isYou, isFor, name, set, fromLink, pick, EVERYONE, ROLE_WORDS, handleOf };
})();
