/* Optional generated art, only through the gallery's resolver (resolve.js), only by slot id.

   build.py inlines resolve.js, a bundle of the slot contract and manifests, and the chosen files as data URIs
   (assets_inline.py), so this works from file://. The page looks and works fully with none of it: every view draws
   its own marks, textures first, and an asset only replaces one when its slot resolves. Nothing here
   names a file or a provider. A failure is reported in the console and in Assets.status, never swallowed. */
const Assets = {
  R: null, status: "none", fellBack: [], listeners: new Set(),
  /* Emblem and theme slots are keyed by a box's icon kind (icons.js, chosen at build time), never by its name: the
     art is generic, so a vault's "news" app wears the news emblem whatever the app is called. */
  slotFor(prefix, key) {
    const id = `${prefix}.${Icons.name(key)}`;
    return this.R && this.R.slots().includes(id) ? id : null;
  },
  url(id) {
    if (!this.R || !id) return null;
    try {
      const resolved = this.R.get(id).url;
      const rel = resolved.replace(/^inline:\//, "");
      const file = (window.ASSET_FILES || {})[rel];
      if (!file) { console.warn(`[assets] ${id} resolved to ${rel}, which the build did not inline; the page keeps its own drawing`); return null; }
      return file;
    } catch (e) { console.warn(`[assets] ${id}: ${e.message}`); return null; }
  },
  form(id) { try { return this.R ? this.R.get(id).form : null; } catch (e) { console.warn(`[assets] ${id} has no form: ${e.message}`); return null; } },
  /* The explorer is dark, so an emblem made for a dark ground comes first; a light one would sit as a pale square. */
  emblem(key) { return this.url(this.slotFor("emblem-on-dark", key)) || this.url(this.slotFor("emblem", key)); },
  texture(name) { return this.url(this.R && this.R.slots().includes("texture." + name) ? "texture." + name : null); },
  onReady(fn) { this.listeners.add(fn); if (this.R) fn(this); },
  async load() {
    if (!window.ASSET_REPORT) { this.status = "no assets in this build: the page's own drawing only"; return; }
    if (!window.AssetResolver || !window.ASSET_BUNDLE) { this.status = "the build named assets but the resolver did not load"; console.warn("[assets] " + this.status); return; }
    try {
      // The inline:/ base cannot be fetched, so the resolver reads the inlined bundle, as it does from file://.
      this.R = await window.AssetResolver.load({ base: "inline:/", config: window.ASSET_BUNDLE.config });
      this.fellBack = window.ASSET_REPORT.fallbacks || [];  // the build checked each file; its reasons are the precise ones
      this.status = `provider "${this.R.provider}", ${this.R.slots().length} slots${this.fellBack.length ? `, ${this.fellBack.length} fell back to builtin` : ""}`;
      console.info("[assets] " + this.status);
      this.listeners.forEach((fn) => fn(this));
    } catch (e) {
      this.R = null; this.status = `assets did not load (${e.message}); the page's own drawing only`;
      console.warn("[assets] " + this.status);
    }
  },
};
