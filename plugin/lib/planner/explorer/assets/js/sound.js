/* Sound: off by default, one switch for the whole page (S). Every voice is synthesised with Web Audio, so there is
   nothing to download. Each app has its own note, rising left to right across the map, so a message travelling
   right sounds as a rising interval; an open question sounds unsettled (a tritone). An app's theme from the asset
   resolver, if one is loaded, can mark an app coming into focus. */
const PITCH = [261.63, 293.66, 329.63, 392.0, 440.0, 523.25, 587.33, 659.25, 783.99, 880.0];
const OPEN_PITCH = 739.99;
const Sound = {
  enabled: false, ctx: null, master: null, comp: null, listeners: new Set(),
  ensure() {
    if (this.ctx) { if (this.ctx.state === "suspended") this.ctx.resume(); return this.ctx; }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) { console.warn("[sound] Web Audio is not available; sound stays off."); return null; }
    this.ctx = new AC();
    this.comp = this.ctx.createDynamicsCompressor();
    this.comp.threshold.value = -18; this.comp.ratio.value = 3;
    this.master = this.ctx.createGain();
    this.master.gain.value = 0.32;
    this.master.connect(this.comp); this.comp.connect(this.ctx.destination);
    return this.ctx;
  },
  set(on) {
    if (on && !this.ensure()) { toast("This browser has no Web Audio, so sound stays off."); on = false; }
    this.enabled = on;
    const btn = $("#sound");
    btn.setAttribute("aria-pressed", String(on));
    btn.querySelector("span").textContent = on ? "Sound on" : "Sound off";
    $("#sound-waves").setAttribute("d", on ? "M16 9.5a4 4 0 0 1 0 5M18.5 7a7.5 7.5 0 0 1 0 10" : "M17 9l4 6M21 9l-4 6");
    this.listeners.forEach((fn) => fn(on));
  },
  onChange(fn) { this.listeners.add(fn); },
  /* A plucked tone: sine body, a quiet octave partial, a fast attack and a long soft decay. */
  tone(freq, at, { gain = 0.5, dur = 1.1, type = "sine", out } = {}) {
    const ctx = this.ctx; if (!ctx || !this.enabled) return;
    const t = Math.max(at ?? ctx.currentTime, ctx.currentTime);
    const env = ctx.createGain();
    env.gain.setValueAtTime(0.0001, t);
    env.gain.exponentialRampToValueAtTime(gain, t + 0.008);
    env.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    const lp = ctx.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 2600;
    const a = ctx.createOscillator(); a.type = type; a.frequency.value = freq;
    const b = ctx.createOscillator(); b.type = "triangle"; b.frequency.value = freq * 2;
    const bg = ctx.createGain(); bg.gain.value = 0.18;
    a.connect(env); b.connect(bg); bg.connect(env); env.connect(lp); lp.connect(out || this.master);
    a.start(t); b.start(t); a.stop(t + dur + 0.05); b.stop(t + dur + 0.05);
  },
  pitchOf(laneId) { const i = LANE_INDEX[laneId]; return PITCH[(i === undefined ? 0 : i) % PITCH.length]; },
  lane(id, at, opts) { this.tone(this.pitchOf(id), at, opts); },
  /* A step's motif: departure at the sender's pitch, arrival louder at the receiver's, and an unresolved tritone
     when the step carries an open question. */
  playStep(step, D_, { at, out } = {}) {
    if (!this.enabled || !this.ensure()) return;
    const base = at ?? this.ctx.currentTime + 0.02;
    for (const { u, t0, t1 } of FlowKit.stepTiming(step, D_)) {
      if (u.kind === "msg" || u.kind === "reply") {
        this.lane(u.from, base + t0, { gain: 0.22, dur: 0.6, out });
        this.lane(u.to, base + t1, { gain: 0.5, dur: 1.2, out });
      } else if (u.kind === "self") {
        this.lane(u.lane, base + t0, { gain: 0.35, dur: 0.5, out });
        this.lane(u.lane, base + t0 + D_ * 0.45, { gain: 0.3, dur: 0.9, out });
      }
    }
    if (FlowKit.openPins(step).length) this.tone(OPEN_PITCH, base + FlowKit.travelTime(step, D_) + 0.05, { gain: 0.16, dur: 1.6, out });
  },
  /* A short click and the lane's own note: a plug went in, a strip seated. */
  click(laneId, kind = "drop") {
    if (!this.enabled || !this.ensure()) return;
    const ctx = this.ctx, t = ctx.currentTime;
    const len = Math.floor(ctx.sampleRate * 0.03), buf = ctx.createBuffer(1, len, ctx.sampleRate), ch = buf.getChannelData(0);
    for (let i = 0; i < len; i++) ch[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 4);
    const src = ctx.createBufferSource(); src.buffer = buf;
    const bp = ctx.createBiquadFilter(); bp.type = "bandpass"; bp.frequency.value = kind === "lift" ? 4200 : 2400; bp.Q.value = 1.1;
    const g = ctx.createGain(); g.gain.value = kind === "lift" ? 0.25 : 0.5;
    src.connect(bp); bp.connect(g); g.connect(this.master); src.start(t);
    if (kind === "drop" && !laneId) {
      const o = ctx.createOscillator(), og = ctx.createGain();
      o.frequency.setValueAtTime(190, t); o.frequency.exponentialRampToValueAtTime(90, t + 0.08);
      og.gain.setValueAtTime(0.0001, t); og.gain.exponentialRampToValueAtTime(0.35, t + 0.005); og.gain.exponentialRampToValueAtTime(0.0001, t + 0.12);
      o.connect(og); og.connect(this.master); o.start(t); o.stop(t + 0.14);
    }
    if (laneId) this.lane(laneId, t + 0.01, { gain: 0.3, dur: 0.5 });
  },
  verdict(kind) {
    if (!this.enabled || !this.ensure()) return;
    const t = this.ctx.currentTime + 0.01;
    if (kind === "right") { this.tone(523.25, t, { gain: 0.3, dur: 0.6 }); this.tone(659.25, t + 0.07, { gain: 0.3, dur: 0.9 }); }
    else if (kind === "near") this.tone(440, t, { gain: 0.25, dur: 0.7 });
    else this.tone(196, t, { gain: 0.28, dur: 0.9 });
  },
  /* All done: the resolver's chime.decided if assets are loaded, else a rising arpeggio. */
  chime() {
    if (!this.enabled || !this.ensure()) return;
    if (Assets.play("chime.decided", { volume: 0.6 })) return;
    const t = this.ctx.currentTime + 0.02;
    [523.25, 659.25, 783.99, 1046.5].forEach((f, i) => this.tone(f, t + i * 0.09, { gain: 0.22, dur: 1.4 }));
  },
  /* The cockpit's breath: a soft tone per light, low for overdue, high for never examined. */
  breath(level, urgency, key) {
    if (!this.enabled || !this.ensure()) return;
    const P = { warning: 293.66, caution: 440, pending: 554.37, unexamined: 659.25, override: 880 }[level];
    if (!P) return;
    this.tone(P * (1 + ((hash(key) % 5) - 2) * 0.0125), undefined, { gain: (level === "override" ? 0.02 : 0.03) + 0.06 * urgency, dur: 1.4, type: level === "warning" ? "triangle" : "sine" });
  },
  /* A station arrival on the line map: two notes at the line's own pitch. */
  arrival(order) {
    if (!this.enabled || !this.ensure()) return;
    const base = [523.25, 587.33, 659.25, 698.46, 783.99, 880][order % 6], t = this.ctx.currentTime;
    this.tone(base, t, { gain: 0.12, dur: 0.6 }); this.tone(base * 0.75, t + 0.16, { gain: 0.1, dur: 0.6 });
  },
  /* A rising bell for the garden: each further decision one step higher on a pentatonic scale. */
  bell(step = 0) {
    if (!this.enabled || !this.ensure()) return;
    const semis = [0, 2, 4, 7, 9][step % 5] + 12 * Math.floor(step / 5);
    this.tone(392 * Math.pow(2, Math.min(semis, 30) / 12), undefined, { gain: 0.16, dur: 1.4 });
  },
};
$("#sound").addEventListener("click", () => Sound.set(!Sound.enabled));
