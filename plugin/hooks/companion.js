// The companion mod: draws what `vela companion session` wrote, beside the transcript or as one line above the prompt.
//
// The panel only shows. It holds no plan rule and no panel wording: the band, the pane's title and every block (its
// words, marks and tones) come from vela's own JSON (Infected Core ruled out on this side). The mod only maps blocks
// to Ink elements and tones to colors, so the terminal, the desktop pane and the HTML panel draw one vocabulary
// without drifting (Distributed Monolith ruled out). It sends nothing back to Claude (the owner's rule for every
// companion); its one kind of button folds a section, which changes only what the panel shows.
//
// It never holds the chat. A tool.call hook that waited for vela would hold back the tool's result, and so Claude, so
// the hook returns the result at once and schedules one refresh 400 ms later; a burst of writes costs one run, and
// drawing reads only what the last refresh stored.
const SESSION_PANE = 'vela-session'
const PLAN_PANE = 'vela-plan'
const REFRESH_AFTER_MS = 400
const VELA_TIMEOUT_MS = 5000
const WRITES_PLAN = /scripts\/(run-)?vela\b/
const EXPLAINS_PLAN = /companion explain/
// A mod's process.run looks no command up on PATH (Claude Code refuses a bare `sh` as "not found or in an unsafe
// location"), so the shell is named by its full path; /bin/sh is on every Mac and Linux.
const SHELL = '/bin/sh'

// What the last refresh stored. Drawing reads these and starts nothing.
let session = null
let plan = null
let problem = ''
let timer = null
let planWanted = false  // keep the plan panel's text current
let planNeedsOpen = false  // open its pane once, when the person asks; a person's close ends it until they ask again
let toldNotPlaced = false
let startCwd = ''
let inVault // undefined = not looked at yet, true or false once looked at; a vela tool call clears it
let sessionOpened = false
let shown = { session: false, plan: false }
let views = { session: null, plan: null }
const folded = new Set()  // `<pane>:<section key>` of the sections the person folded; lives as long as the mod does

// Tone -> Ink text props, the one table; vela names the tone, the mod only colors it. `dim` and `strong` are weights,
// not colors, so a theme's own dim and bold apply.
const TONES = {
  plain: {},
  dim: { dimColor: true },
  strong: { weight: 'bold' },
  info: { color: '#5aa8ff' },
  good: { color: 'green' },
  warn: { color: '#e5a50a' },
  bad: { color: 'red' },
  accent: { color: 'yellow' },
  new: { color: 'magenta' },
  id: { color: 'cyan' },
}
const BAR_CELLS = 20  // the contract's bar width
const BAR_FULL = '█'
const BAR_REST = '░'
const OPEN_MARK = '▾'
const FOLDED_MARK = '▸'

// vela's JSON, or { unreadable: why } when what it printed isn't JSON: said, never read as an empty panel.
function jsonOf(text) {
  let found = null
  try {
    found = JSON.parse(text)
  } catch (error) {
    found = { unreadable: String(error && error.message ? error.message : error) }
  }
  return found !== null && typeof found === 'object' ? found : { unreadable: 'not an object' }
}

async function runVela($, args) {
  const done = await $.process.run([SHELL, `${$.plugin.root}/scripts/run-vela`, 'companion', ...args, '--json', '--find-up'], { timeoutMs: VELA_TIMEOUT_MS })
  const parsed = jsonOf(done.stdout)
  const why = parsed.unreadable ? (String(done.stderr || '').trim().split('\n')[0] || parsed.unreadable) : ''  // vela says why on stderr
  return { code: done.exitCode, text: done.stdout, found: parsed.unreadable ? null : parsed, why }
}

// What the pane draws, from the JSON vela printed (nothing read from disk, nothing made here).
function viewOf(found) {
  const diagram = found.diagram || null
  return {
    blocks: Array.isArray(found.blocks) ? found.blocks : [],
    vault: found.vault || '',
    diagramSvg: diagram ? diagram.svg : '',
    title: found.session ? found.session.title : '',
  }
}

const toneProps = (tone) => TONES[tone] || TONES.plain
const cells = (n) => Math.max(0, Math.round(n))
const padTo = (text, width) => text + ' '.repeat(Math.max(0, width - text.length))

// A page link: the vault's file, so a click opens it where the terminal opens files.
const pageHref = (vault, page) => encodeURI(`file://${vault}/${page}`)

function spanOf(el, span, vault) {
  if (span.page && vault) return el.Link({ href: pageHref(vault, span.page), label: span.t })
  return el.Text({ ...toneProps(span.tone), children: [span.t] })
}

function barOf(el, done, total) {
  const filled = total > 0 ? cells((done / total) * BAR_CELLS) : 0
  return [
    el.Text({ color: TONES.good.color, children: [BAR_FULL.repeat(filled)] }),
    el.Text({ dimColor: true, children: [BAR_REST.repeat(BAR_CELLS - filled)] }),
  ]
}

// One Line: spans and bar items on one row.
function lineOf(el, line, vault) {
  const parts = (line || []).flatMap((item) => (item.bar ? barOf(el, item.bar[0], item.bar[1]) : [spanOf(el, item, vault)]))
  return el.Text({ children: parts.length > 0 ? parts : [' '] })
}

function toggleFold(key, redraw) {
  if (folded.has(key)) folded.delete(key)
  else folded.add(key)
  redraw()
}

// A header the person can fold: the only button the mod draws.
function foldHeader(el, fold, key, title, right) {
  const id = `${fold.pane}:${key}`
  const mark = folded.has(id) ? FOLDED_MARK : OPEN_MARK
  return el.Box({
    justifyContent: 'space-between',
    children: [
      el.Button({ key: `fold:${id}`, plain: true, onPress: () => toggleFold(id, fold.redraw), children: [`${mark} `, el.Text({ weight: 'bold', children: [title] })] }),
      el.Text({ dimColor: true, children: [right || ' '] }),
    ],
  })
}

// Ink's border has no title slot, so the title is the box's first row.
function cardOf(el, block, vault) {
  const head = el.Box({
    justifyContent: 'space-between',
    children: [el.Text({ weight: 'bold', children: [block.title] }), el.Text({ dimColor: true, children: [block.right || ' '] })],
  })
  const body = (block.lines || []).map((line) => lineOf(el, line, vault))
  return el.Box({ borderStyle: 'round', borderColor: toneProps(block.tone).color || undefined, borderDimColor: block.tone === 'dim', paddingX: 1, flexDirection: 'column', children: [head, ...body] })
}

function nextOf(el, block) {
  const top = el.Text({
    children: [
      el.Text({ inverse: true, ...TONES.accent, children: [` ${block.chip} `] }),
      ' ',
      el.Text({ ...TONES.accent, weight: 'bold', children: [block.text] }),
      block.id ? '  ' : '',
      block.id ? el.Text({ ...TONES.id, children: [block.id] }) : '',
    ],
  })
  return el.Box({ flexDirection: 'column', children: block.note ? [top, el.Text({ dimColor: true, children: [`  ${block.note}`] })] : [top] })
}

// Names and ids are padded to the section's widest, so the columns line up as in the mockup.
function rowsOf(el, rows, vault) {
  const nameWidth = Math.max(0, ...rows.map((r) => (r.name || '').length))
  const idWidth = Math.max(0, ...rows.map((r) => (r.id || '').length))
  return rows.map((row) => {
    const name = row.page && vault ? el.Link({ href: pageHref(vault, row.page), label: padTo(row.name || '', nameWidth) }) : padTo(row.name || '', nameWidth)
    const main = el.Text({
      children: [
        '  ',
        el.Text({ ...toneProps(row.tone), children: [row.mark || ' '] }),
        ' ',
        name,
        '  ',
        el.Text({ ...TONES.id, children: [padTo(row.id || '', idWidth)] }),
        row.chip ? ' ' : '',
        row.chip ? el.Text({ inverse: true, ...toneProps(row.chip.tone), children: [` ${row.chip.t} `] }) : '',
        row.note ? ' ' : '',
        row.note ? el.Text({ dimColor: true, children: [row.note] }) : '',
      ],
    })
    if (!row.sub) return main
    return el.Box({ flexDirection: 'column', children: [main, el.Text({ children: ['    ', lineOf(el, row.sub, vault)] })] })
  })
}

function sectionOf(el, block, vault, fold) {
  const titled = Boolean(block.title)
  const isFolded = titled && folded.has(`${fold.pane}:${block.key}`)
  const head = titled ? [foldHeader(el, fold, block.key, block.title, block.count)] : []
  const rows = isFolded ? [] : rowsOf(el, block.rows || [], vault)
  return el.Box({ flexDirection: 'column', children: [...head, ...rows] })
}

function barsOf(el, block, fold) {
  const labelWidth = Math.max(0, ...block.rows.map((r) => r.label.length))
  const rows = block.rows.map((row) => {
    const filled = row.max > 0 ? Math.min(BAR_CELLS, Math.max(row.value > 0 ? 1 : 0, cells((row.value / row.max) * BAR_CELLS))) : 0
    return el.Text({
      children: ['  ', el.Text({ dimColor: true, children: [padTo(row.label, labelWidth)] }), ' ', el.Text({ ...toneProps(row.tone), children: [BAR_FULL.repeat(filled)] }), ' ', row.text],
    })
  })
  const key = `bars:${block.title}`
  const head = block.title ? [foldHeader(el, fold, key, block.title, '')] : []
  return el.Box({ flexDirection: 'column', children: [...head, ...(folded.has(`${fold.pane}:${key}`) ? [] : rows)] })
}

// The widest drawing that fits the pane; the narrowest when none does.
function drawingFor(drawings, columns) {
  const widths = Object.keys(drawings || {}).map(Number).sort((a, b) => a - b)
  if (widths.length === 0) return []
  const fits = widths.filter((w) => w <= columns - 2)
  return drawings[String(fits.length > 0 ? fits[fits.length - 1] : widths[0])]
}

function diagramOf(el, block, columns, surface, svg, fold) {
  const key = 'diagram'
  const head = foldHeader(el, fold, key, block.title, block.id)
  if (folded.has(`${fold.pane}:${key}`)) return el.Box({ flexDirection: 'column', children: [head] })
  const picture = surface === 'desktop' && svg
    ? [el.Svg({ source: svg, alt: block.alt || block.title })]
    : drawingFor(block.drawings, columns).map((line) => lineOf(el, line, ''))
  return el.Box({ flexDirection: 'column', children: [head, ...picture] })
}

function blockOf(el, block, view, columns, surface, fold) {
  switch (block.type) {
    case 'card': return cardOf(el, block, view.vault)
    case 'next': return nextOf(el, block)
    case 'section': return sectionOf(el, block, view.vault, fold)
    case 'bars': return barsOf(el, block, fold)
    case 'diagram': return diagramOf(el, block, columns, surface, view.diagramSvg, fold)
    case 'lines': return el.Box({ flexDirection: 'column', children: (block.lines || []).map((line) => lineOf(el, line, view.vault)) })
    default: return null  // a block this mod doesn't know is left out, not guessed at
  }
}

// The pane's body: vela's blocks, a blank row between them. `fold` = { pane, redraw }.
function drawBlocks(view, el, bodyColumns, surface, fold) {
  const drawn = view.blocks.map((block) => blockOf(el, block, view, bodyColumns, surface, fold)).filter(Boolean)
  const spaced = drawn.flatMap((node, at) => (at === 0 ? [node] : [el.Text({ children: [' '] }), node]))
  return el.Box({ flexDirection: 'column', children: spaced })
}

function firstLine(done) {
  if (done.found && Array.isArray(done.found.warnings) && done.found.warnings.length > 0) return done.found.warnings[0]
  if (done.found && typeof done.found.message === 'string') return done.found.message
  return done.why || done.text.split('\n')[0]
}

async function refreshSession($) {
  const done = await runVela($, ['session'])
  if (done.code === 0 && done.found) {
    session = done.found
    views.session = viewOf(done.found)
    problem = ''
    if (!sessionOpened) {
      sessionOpened = true
      const placed = await $.ui.open({ id: SESSION_PANE, title: views.session.title })
      shown.session = placed.isPlaced
      if (!placed.isPlaced) notePanelIsHidden($)
    }
    return
  }
  if (done.code === 1) {
    session = null
    views.session = null
    problem = ''
    await $.ui.close({ id: SESSION_PANE })
    shown.session = false
    sessionOpened = false
    return
  }
  problem = firstLine(done)
  if (done.code === 2 && done.found && done.found.files) {
    session = done.found
    views.session = viewOf(done.found)
  }
}

async function refreshPlan($) {
  if (!planWanted) return
  const done = await runVela($, ['explain', '--last'])
  if (done.code === 0 && done.found && done.found.files) {
    plan = done.found
    views.plan = viewOf({ ...done.found, session: { title: done.found.copy ? done.found.copy.title : '' } })
    if (planNeedsOpen) {
      planNeedsOpen = false
      const placed = await $.ui.open({ id: PLAN_PANE, title: views.plan.title })
      shown.plan = placed.isPlaced
      if (!placed.isPlaced) notePanelIsHidden($)
    }
  }
}

// A pane that could not be placed (a narrow terminal, the desktop app) must not leave the panel silently absent.
function notePanelIsHidden($) {
  if (toldNotPlaced) return
  toldNotPlaced = true
  $.ui.toast('The panel is ready: type /vela-companion to open it.')
}

// Is there a plan at or above the folder the session started in? Looked at once, not on every turn: Python starts
// only in a folder that holds a vela plan.
async function findVault($) {
  if (!startCwd) return true  // can't tell where we are; vela itself answers "no plan here"
  let dir = startCwd
  for (;;) {
    if (await $.fs.exists(`${dir}/.vela.yaml`)) return true
    const parent = dir.replace(/\/[^/]*$/, '')
    if (!parent || parent === dir) return false
    dir = parent
  }
}

async function refresh($) {
  timer = null
  try {
    await refreshSession($)
    await refreshPlan($)
  } catch (error) {
    problem = `vela didn't run: ${error && error.message ? error.message : error}`
  }
  $.ui.invalidate('ui.render')
}

async function scheduleIfVault($) {
  if (inVault === undefined) inVault = await findVault($)
  if (inVault) schedule($)
}

function schedule($) {
  if (timer) timer.cancel()
  timer = $.clock.after(REFRESH_AFTER_MS, () => { void refresh($) })
}

function touchesPlan(e) {
  if (e.tool === 'Bash') return WRITES_PLAN.test(e.command || '')
  if (e.tool === 'Edit' || e.tool === 'Write' || e.tool === 'MultiEdit') return String(e.file_path || '').endsWith('.md')
  return false
}

// The band as vela's colored spans; the plain sentence when vela sent none.
function bandPieces(found, Text) {
  const spans = Array.isArray(found.band_spans) ? found.band_spans : []
  if (spans.length === 0) return [found.band]
  return spans.map((span) => Text({ ...toneProps(span.tone), children: [span.t] }))
}

export function register(on) {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'vela-companion', description: "Show this session's companion", immediate: true })
    await $.command.register({ name: 'vela-plan', description: 'Show the plan companion', immediate: true })
    startCwd = e.cwd || ''
    inVault = await findVault($)
    if (inVault) $.clock.after(0, () => { void refresh($) })
    return next(e)
  })

  on('tool.call', async ($, e, next) => {
    const result = await next(e)
    if (touchesPlan(e)) {
      if (e.tool === 'Bash' && EXPLAINS_PLAN.test(e.command || '')) { planWanted = true; planNeedsOpen = true }
      inVault = undefined  // a vela call may have just made the plan
      schedule($)
    }
    return result
  })

  on('turn.complete', async ($, e, next) => {
    await scheduleIfVault($)
    return next(e)
  })

  on('ui.close', async ($, e, next) => {
    if (e.origin === 'person' && e.id === SESSION_PANE) shown.session = false
    if (e.origin === 'person' && e.id === PLAN_PANE) { shown.plan = false; planWanted = false; planNeedsOpen = false }
    return next(e)
  })

  on('command.run', { command: 'vela-companion' }, async ($) => {
    if (!views.session) await refreshSession($)
    if (views.session) {
      const placed = await $.ui.open({ id: SESSION_PANE, title: views.session.title })
      shown.session = placed.isPlaced
    }
    return {}
  })

  on('command.run', { command: 'vela-plan' }, async ($) => {
    planWanted = true
    planNeedsOpen = true
    await refreshPlan($)
    return {}
  })

  on('ui.render', { component: 'Pane' }, async ($, e, next) => {
    if (e.requestId !== SESSION_PANE && e.requestId !== PLAN_PANE) return next(e)
    const view = e.requestId === SESSION_PANE ? views.session : views.plan
    const el = $.ui.resolve(e)
    if (!view) return el.Box({ children: [el.Text({ children: [problem || ' '] })] })
    return drawBlocks(view, el, e.props.bodyColumns, e.surface, { pane: e.requestId, redraw: () => $.ui.invalidate('ui.render') })
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)  // a survey holds the band; a hook yields to it
    const { Text } = $.ui.resolve(e)
    if (problem) return Text({ children: [problem] })
    if (session && session.band && !shown.session) return Text({ children: bandPieces(session, Text) })
    return next(e)
  })
}
