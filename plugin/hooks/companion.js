// The companion mod: draws what `vela companion session` wrote, beside the transcript or as one line above the prompt.
//
// The panel only shows. It holds no plan rule and no panel wording: the band, the pane's title, the text and the
// diagram all come from vela's own files (Infected Core ruled out on this side). It only shows: it sends nothing back
// to Claude (the owner's rule for every companion).
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

// The panel's own text and diagram, from the files vela wrote beside its JSON (never made here).
async function viewOf($, found) {
  const text = await $.fs.read(`${found.vault}/${found.files.md}`)
  const diagram = found.diagram || null
  return { text, diagramText: diagram ? diagram.text : '', diagramSvg: diagram ? diagram.svg : '', title: found.session ? found.session.title : '' }
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
    views.session = await viewOf($, done.found)
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
    views.session = await viewOf($, done.found)
  }
}

async function refreshPlan($) {
  if (!planWanted) return
  const done = await runVela($, ['explain', '--last'])
  if (done.code === 0 && done.found && done.found.files) {
    plan = done.found
    views.plan = await viewOf($, { ...done.found, session: { title: done.found.copy ? done.found.copy.title : '' } })
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
    const { Box, Text, Markdown, Code, Svg } = $.ui.resolve(e)
    if (!view) return Box({ children: [Text({ children: [problem || ' '] })] })
    const children = [Markdown({ text: view.text })]
    if (e.surface === 'desktop' && view.diagramSvg) {
      children.push(Svg({ source: view.diagramSvg, alt: view.title }))
    } else if (view.diagramText) {
      children.push(Code({ source: view.diagramText }))
    }
    return Box({ flexDirection: 'column', children })
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)  // a survey holds the band; a hook yields to it
    const { Text } = $.ui.resolve(e)
    if (problem) return Text({ children: [problem] })
    if (session && session.band && !shown.session) return Text({ children: [session.band] })
    return next(e)
  })
}
