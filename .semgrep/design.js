async function f() {
  // ruleid: js-empty-catch
  try { await load(); } catch (e) {}
  // ok: js-empty-catch
  try { await load(); } catch (e) { console.warn(`[assets] ${e.message}`); }
}
