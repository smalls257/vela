/* Asset resolver. A page loads this file, then:
 *
 *   const assets = await AssetResolver.load();          // slot contract and builtin art beside this file; assets.config.json
 *                                                       // and the provider's folder from data-providers (default: beside this file)
 *   img.src = assets.url('emblem.learning');             // any image or loop slot
 *   const h = assets.play('chime.decided');             // audio slot: file or Web Audio recipe, same call
 *   h.stop();
 *   assets.report();                                    // which slots fell back to builtin, and why
 *
 * Pages name slots (slots.json), never files or providers. The builtin provider must fill every slot; any slot the
 * chosen provider lacks, or whose file is missing, falls back to builtin and is logged with the reason (never silently).
 * Fetch needs http(s). Over file:// the resolver uses window.ASSET_BUNDLE (assets.bundle.js, rebuilt by
 * build_index.py) if a page has loaded it, and says so in the console.
 */
(function (global) {
  "use strict";
  const HERE = (document.currentScript && new URL(".", document.currentScript.src).href) || "./";
  // The slot contract and builtin art live with this file, the one canonical copy. A page whose provider art
  // (ComfyUI renders, assets.config.json) sits elsewhere says where, with a data-providers attribute on the script tag that loads this file (e.g. data-providers="../assets/").
  const PROVIDERS = (document.currentScript && document.currentScript.dataset.providers &&
    new URL(document.currentScript.dataset.providers, document.baseURI).href) || HERE;

  async function fetchJson(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
    return r.json();
  }

  async function fileExists(url) {
    try { return (await fetch(url, { method: "HEAD" })).ok; } catch (e) { console.warn(`[assets] could not check whether ${url} exists: ${e.message}`); return false; }
  }

  async function readSources(base, providers, configOverride) {
    // When inlining assets into a page, the base is "inline:/" which cannot be fetched from. Skip to the bundle immediately.
    if (base && base.startsWith("inline:")) {
      const b = global.ASSET_BUNDLE;
      if (!b) throw new Error(`[assets] cannot read asset config from inline:// URL. The page must have loaded ASSET_BUNDLE.`);
      const config = configOverride || b.config;
      const provider = config.provider === "builtin" ? null : b.providers[config.provider] || null;
      const providerError = config.provider !== "builtin" && !provider ? `bundle has no ${config.provider} manifest` : null;
      return { config, slots: b.slots, builtin: b.providers.builtin, provider, providerError, recipes: b.recipes, checkFiles: false };
    }
    try {
      const config = configOverride || await fetchJson(providers + "assets.config.json");
      const slots = await fetchJson(base + "slots.json");
      const builtin = await fetchJson(base + "builtin/manifest.json");
      let provider = null, providerError = null;
      if (config.provider !== "builtin") {
        try { provider = await fetchJson(`${providers}${config.provider}/manifest.json`); }
        catch (e) { providerError = `could not read ${config.provider}/manifest.json (${e.message})`; }
      }
      return { config, slots, builtin, provider, providerError, recipes: null, checkFiles: true };
    } catch (e) {
      const b = global.ASSET_BUNDLE;
      if (!b) throw new Error(`[assets] cannot read asset config (${e.message}). Serve over http, e.g. "python3 -m http.server" in the folder that holds the asset config, or load assets/assets.bundle.js first.`);
      console.warn(`[assets] fetch failed (${e.message}); using assets.bundle.js snapshot built ${b.built}. Rebuild it after changing config.`);
      const config = configOverride || b.config;
      const provider = config.provider === "builtin" ? null : b.providers[config.provider] || null;
      const providerError = config.provider !== "builtin" && !provider ? `bundle has no ${config.provider} manifest` : null;
      return { config, slots: b.slots, builtin: b.providers.builtin, provider, providerError, recipes: b.recipes, checkFiles: false };
    }
  }

  async function load(opts = {}) {
    const base = opts.base || HERE;
    const providers = opts.providers || (opts.base ? base : PROVIDERS);
    const src = await readSources(base, providers, opts.config);
    const table = {}, fallbacks = [];
    const recipeCache = src.recipes || {};

    await Promise.all(src.slots.slots.map(async (slot) => {
      const b = src.builtin.slots[slot.id];
      if (!b) throw new Error(`[assets] builtin provider has no entry for slot ${slot.id}; the slot contract is broken`);
      const p = src.provider && src.provider.slots && src.provider.slots[slot.id];
      let chosen = null, why = null;
      if (src.config.provider === "builtin") chosen = null;
      else if (src.providerError) why = src.providerError;
      else if (!p) why = `${src.config.provider} has no file for this slot`;
      else if (src.checkFiles && !(await fileExists(`${providers}${src.config.provider}/${p.file}`))) why = `${src.config.provider}/${p.file} is missing`;
      else chosen = p;

      const entry = chosen || b;
      const provider = chosen ? src.config.provider : "builtin";
      const resolved = { slot: slot.id, kind: slot.kind, provider, form: entry.form, url: `${provider === "builtin" ? base : providers}${provider}/${entry.file}`, meta: entry };
      if (entry.form === "recipe") {
        const key = `${provider}/${entry.file}`;
        resolved.recipe = recipeCache[key] || (recipeCache[key] = await fetchJson(resolved.url));
      }
      table[slot.id] = resolved;
      if (why) fallbacks.push({ slot: slot.id, fellBackTo: "builtin", because: why });
    }));

    if (fallbacks.length) console.warn(`[assets] provider "${src.config.provider}": ${fallbacks.length} slot(s) fell back to builtin`, fallbacks);

    function get(id) {
      const r = table[id];
      if (!r) throw new Error(`[assets] unknown slot "${id}". Known: ${Object.keys(table).sort().join(", ")}`);
      return r;
    }
    return {
      provider: src.config.provider,
      get,
      url: (id) => get(id).url,
      play: (id, o) => playSlot(get(id), o),
      report: () => fallbacks.slice(),
      slots: () => Object.keys(table).sort(),
    };
  }

  function playSlot(r, o = {}) {
    if (r.kind !== "audio") throw new Error(`[assets] slot ${r.slot} is ${r.kind}, not audio`);
    if (r.form === "recipe") return Synth.play(r.recipe, o);
    const el = new Audio(r.url);
    el.loop = !!(o.loop ?? r.meta.loop);
    el.volume = o.volume ?? 1;
    el.play().catch((e) => console.error(`[assets] could not play ${r.slot} (${r.url}):`, e));
    return { stop: () => { el.pause(); el.currentTime = 0; }, element: el };
  }

  /* ---- Web Audio recipe synth (format web-audio-recipe/1) ----
   * notes: [beat, note | [notes], beats, velocity, voice]
   * voice: {wave, partials:[[ratio, amp]], tilt, noise, env:{a,d,s,r}, filter:{type,hz,q,env_hz,env_d}, lfo:{hz,depth}, trem:{hz,depth}, gain, send:{reverb,delay}}
   */
  const Synth = (function () {
    let ctx = null, noiseBuf = null;
    const NOTE = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };

    function context() {
      if (!ctx) ctx = new (global.AudioContext || global.webkitAudioContext)();
      if (ctx.state === "suspended") ctx.resume();
      return ctx;
    }
    function freq(name) {
      const m = /^([A-G])([#b]?)(-?\d)$/.exec(name);
      if (!m) throw new Error(`[assets] bad note name "${name}"`);
      const semis = NOTE[m[1]] + (m[2] === "#" ? 1 : m[2] === "b" ? -1 : 0) + (parseInt(m[3], 10) + 1) * 12;
      return 440 * Math.pow(2, (semis - 69) / 12);
    }
    function noise(c) {
      if (noiseBuf) return noiseBuf;
      noiseBuf = c.createBuffer(1, c.sampleRate, c.sampleRate);
      const d = noiseBuf.getChannelData(0);
      for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
      return noiseBuf;
    }
    function impulse(c, seconds, decay) {
      const len = Math.floor(c.sampleRate * seconds), buf = c.createBuffer(2, len, c.sampleRate);
      for (let ch = 0; ch < 2; ch++) {
        const d = buf.getChannelData(ch);
        for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, decay);
      }
      return buf;
    }
    function buildBus(c, recipe, out) {
      const spb = 60 / recipe.bpm, fx = recipe.fx || {}, bus = { dry: c.createGain(), sends: {} };
      bus.dry.connect(out);
      if (fx.reverb) {
        const conv = c.createConvolver(), wet = c.createGain();
        conv.buffer = impulse(c, fx.reverb.seconds, fx.reverb.decay);
        wet.gain.value = fx.reverb.mix;
        conv.connect(wet).connect(out);
        bus.sends.reverb = conv;
      }
      if (fx.delay) {
        const dl = c.createDelay(4), fb = c.createGain(), wet = c.createGain();
        dl.delayTime.value = fx.delay.beats * spb;
        fb.gain.value = fx.delay.feedback;
        wet.gain.value = fx.delay.mix;
        dl.connect(fb).connect(dl);
        dl.connect(wet).connect(out);
        if (bus.sends.reverb) wet.connect(bus.sends.reverb);
        bus.sends.delay = dl;
      }
      return bus;
    }
    function lfo(c, hz, depth, target, t0, t1) {
      const o = c.createOscillator(), g = c.createGain();
      o.frequency.value = hz; g.gain.value = depth;
      o.connect(g).connect(target);
      o.start(t0); o.stop(t1);
    }
    function playNote(c, bus, v, f, t0, t1, vel) {
      const env = v.env, peak = (v.gain ?? 0.2) * vel, end = Math.max(t1, t0 + env.a), stopAt = end + env.r * 3 + 0.05;
      const amp = c.createGain();
      amp.gain.setValueAtTime(0, t0);
      amp.gain.linearRampToValueAtTime(peak, t0 + env.a);
      amp.gain.setTargetAtTime(peak * env.s, t0 + env.a, env.d / 3);
      amp.gain.setTargetAtTime(0, end, env.r / 3);
      let node = amp;
      if (v.trem) {
        const t = c.createGain();
        t.gain.value = 1 - v.trem.depth / 2;
        lfo(c, v.trem.hz, v.trem.depth / 2, t.gain, t0, stopAt);
        amp.connect(t); node = t;
      }
      if (v.filter) {
        const fl = c.createBiquadFilter();
        fl.type = v.filter.type; fl.Q.value = v.filter.q ?? 0.7;
        fl.frequency.setValueAtTime(v.filter.hz + (v.filter.env_hz || 0), t0);
        if (v.filter.env_hz) fl.frequency.setTargetAtTime(v.filter.hz, t0, v.filter.env_d / 3);
        if (v.lfo) lfo(c, v.lfo.hz, v.lfo.depth, fl.frequency, t0, stopAt);
        node.connect(fl); node = fl;
      }
      node.connect(bus.dry);
      for (const [name, level] of Object.entries(v.send || {})) {
        const dest = bus.sends[name];
        if (!dest) continue;
        const s = c.createGain(); s.gain.value = level;
        node.connect(s).connect(dest);
      }
      if (v.noise) {
        const src = c.createBufferSource();
        src.buffer = noise(c); src.loop = true;
        src.connect(amp); src.start(t0, Math.random() * 0.5); src.stop(stopAt);
        return;
      }
      for (const [ratio, a] of v.partials || [[1, 1]]) {
        const o = c.createOscillator(), g = c.createGain();
        o.type = v.wave || "sine"; o.frequency.value = f * ratio;
        g.gain.setValueAtTime(a, t0);
        if (v.tilt && ratio > 1) g.gain.setTargetAtTime(0, t0, env.d / (v.tilt * ratio));
        o.connect(g).connect(amp);
        o.start(t0); o.stop(stopAt);
      }
    }
    function scheduleCycle(c, bus, recipe, start) {
      const spb = 60 / recipe.bpm;
      for (const [beat, n, beats, vel, voiceName] of recipe.notes) {
        const v = recipe.voices[voiceName];
        if (!v) throw new Error(`[assets] recipe ${recipe.slot} uses unknown voice "${voiceName}"`);
        const t0 = start + beat * spb, t1 = t0 + beats * spb;
        for (const name of Array.isArray(n) ? n : [n]) playNote(c, bus, v, freq(name), t0, t1, vel);
      }
    }
    function play(recipe, o = {}) {
      const c = context(), master = c.createGain();
      master.gain.value = o.volume ?? 0.8;
      master.connect(c.destination);
      const bus = buildBus(c, recipe, master), cycle = recipe.length_beats * 60 / recipe.bpm;
      let next = c.currentTime + 0.05, timer = null;
      scheduleCycle(c, bus, recipe, next);
      if (o.loop ?? recipe.loop) {
        timer = setInterval(() => {
          if (c.currentTime > next + cycle - 2) { next += cycle; scheduleCycle(c, bus, recipe, next); }
        }, 500);
      }
      return {
        duration: cycle,
        stop(fade = 0.4) {
          clearInterval(timer);
          master.gain.setTargetAtTime(0, c.currentTime, fade / 3);
          setTimeout(() => master.disconnect(), fade * 1000 + 200);
        },
      };
    }
    return { play, freq };
  })();

  global.AssetResolver = { load, Synth };
})(window);
