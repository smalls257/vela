import { expect, mock, test } from 'claude-code/testing'

const SESSION = {
  kind: 'session', capture: 14, notes: 'read', vault: '/plan',
  band: 'Grill: hold, pay, confirm · 2 decided · 1 open · next: Pricing runtime · /vela-companion to open',
  session: { title: 'Grill: hold, pay, confirm' }, files: { md: '.vela/companion/session.md' },
  diagram: { svg: '', text: '1. Find a crossing' }, warnings: [],
}
const ran = (stdout: unknown, exitCode = 0) => ({ exitCode, stdout: JSON.stringify(stdout), stderr: '', isStdoutTruncated: false, isStderrTruncated: false })
const WRITE = { tool: 'Bash', command: 'sh /p/scripts/run-vela decide CON-007 --yes ^c12' } as never

test('vela is started through the shell by its full path, never a bare name', async ($, on) => {
  const clock = mock.clock(on)
  const argvs: string[][] = []
  on('process.run', (_$, e) => { argvs.push([...(e as { argv: string[] }).argv]); return { value: ran(SESSION) } })
  on('fs.read', () => ({ value: '# This session' }))
  on('tool.call', () => ({ result: 'ok' }))
  await $.tool.call(WRITE)
  await clock.advance(500)
  expect(argvs.length).toBe(1)
  expect(argvs[0][0]).toBe('/bin/sh')
})

test("when vela can't start, the band says vela's own reason", async ($, on) => {
  const clock = mock.clock(on)
  on('process.run', () => ({ value: { exitCode: 2, stdout: '', stderr: 'vela: no Python 3.9 or later found as python3, python or py on the PATH.\n', isStdoutTruncated: false, isStderrTruncated: false } }))
  on('tool.call', () => ({ result: 'ok' }))
  await $.tool.call(WRITE)
  await clock.advance(1000)
  const band = await $.ui.mount({ plugin: 'vela', surface: 'terminal', component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 10 } as never })
  expect(await band.find({ type: 'Text', text: 'vela: no Python 3.9 or later found as python3, python or py on the PATH.' })).toBeDefined()
})

test("a vela call's result comes back before vela's refresh finishes", async ($, on) => {
  const clock = mock.clock(on)
  let release: (v: unknown) => void = () => {}
  let started = 0
  on('process.run', () => { started += 1; return new Promise((resolve) => { release = (v) => resolve({ value: v }) }) })
  on('tool.call', () => ({ result: 'ok' }))
  const answered = await $.tool.call(WRITE)
  expect(answered).toEqual({ result: 'ok' })      // resolved while no refresh has even started
  expect(started).toBe(0)
  await clock.advance(500)
  expect(started).toBe(1)                          // the refresh runs later, and is still pending here
  release(ran(SESSION))
})

test('a burst of writes costs one vela run', async ($, on) => {
  const clock = mock.clock(on)
  let runs = 0
  on('process.run', () => { runs += 1; return { value: ran(SESSION) } })
  on('fs.read', () => ({ value: '# This session' }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('tool.call', () => ({ result: 'ok' }))
  for (const n of [1, 2, 3]) await $.tool.call({ tool: 'Bash', command: `sh /p/scripts/run-vela record add x${n}` } as never)
  await clock.advance(1000)
  expect(runs).toBe(1)
})

test('other commands never run vela', async ($, on) => {
  const clock = mock.clock(on)
  let runs = 0
  on('process.run', () => { runs += 1; return { value: ran({}) } })
  on('tool.call', () => ({ result: 'ok' }))
  await $.tool.call({ tool: 'Bash', command: 'ls -la' } as never)
  await clock.advance(1000)
  expect(runs).toBe(0)
})

test("vela's own failure line is shown in the band, never hidden", async ($, on) => {
  const clock = mock.clock(on)
  const why = "I can't read this session's notes on this machine."
  on('process.run', () => ({ value: ran({ notes: 'unreadable', warnings: [why] }, 2) }))
  on('tool.call', () => ({ result: 'ok' }))
  await $.tool.call(WRITE)
  await clock.advance(1000)
  const band = await $.ui.mount({ plugin: 'vela', surface: 'terminal', component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 10 } as never })
  expect(await band.find({ type: 'Text', text: why })).toBeDefined()
})

test('the band is the text vela wrote when no pane is showing', async ($, on) => {
  const clock = mock.clock(on)
  on('process.run', () => ({ value: ran(SESSION) }))
  on('fs.read', () => ({ value: '# This session' }))
  on('ui.open', () => ({ value: { isPlaced: false, reason: 'unasked below 144 columns' } }))
  on('tool.call', () => ({ result: 'ok' }))
  await $.tool.call(WRITE)
  await clock.advance(1000)
  const band = await $.ui.mount({ plugin: 'vela', surface: 'terminal', component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 10 } as never })
  expect(await band.find({ type: 'Text', text: SESSION.band })).toBeDefined()
})

test('the pane draws the Markdown vela wrote and has no buttons', async ($, on) => {
  const clock = mock.clock(on)
  on('process.run', () => ({ value: ran(SESSION) }))
  on('fs.read', () => ({ value: '# This session\n\nHold, pay, confirm' }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('tool.call', () => ({ result: 'ok' }))
  await $.tool.call(WRITE)
  await clock.advance(1000)
  const pane = await $.ui.mount({ plugin: 'vela', surface: 'terminal', component: 'Pane', requestId: 'vela-session', props: { title: 'x', isFocused: false, bodyColumns: 60, placement: 'dock' } as never })
  expect(await pane.find({ type: 'Markdown', text: 'Hold, pay, confirm' })).toBeDefined()
  expect(await pane.findAll({ type: 'Button' })).toHaveLength(0)
})

const PLAN = { kind: 'explain', vault: '/plan', files: { md: '.vela/companion/explain.md' }, copy: { title: 'Harborline' }, diagram: null, warnings: [] }
const START = (cwd: string) => ({ cwd, surface: 'terminal' } as never)
const DONE = { reason: 'answer', answer: 'done', turnId: 't1', durationMs: 1000 } as never
function bare(on: (...a: never[]) => unknown, onToast: () => void = () => {}) {
  const hook = on as unknown as (name: string, fn: (...input: never[]) => unknown) => void
  hook('command.register', () => ({ value: undefined }))
  hook('session.start', (_h: never, e: never) =>  ({ cwd: (e as { cwd: string }).cwd }))
  hook('turn.complete', () => ({ text: 'done' }))
  hook('ui.toast', () => { onToast(); return { value: undefined } })
}

test('the plan pane opens when the person asks and is not reopened by later turns', async ($, on) => {
  const clock = mock.clock(on)
  let opens = 0
  bare(on)
  on('fs.exists', () => ({ value: true }))
  on('process.run', () => ({ value: ran(PLAN) }))
  on('fs.read', () => ({ value: '# The plan' }))
  on('ui.open', (_h: never, input: never) => { if ((input as unknown as { id: string }).id === 'vela-plan') opens += 1; return { value: { isPlaced: true } } })
  await $.session.start(START('/plan'))
  await $.command.run({ command: 'vela-plan', args: '' } as never)
  expect(opens).toBe(1)
  for (let n = 0; n < 3; n += 1) {
    await $.turn.complete(DONE)
    await clock.advance(1000)
  }
  expect(opens).toBe(1)
})

test('a folder with no plan above it never starts vela, on a turn or at the start', async ($, on) => {
  const clock = mock.clock(on)
  let runs = 0
  bare(on)
  on('fs.exists', () => ({ value: false }))
  on('process.run', () => { runs += 1; return { value: ran({}) } })
  await $.session.start(START('/work/other/deep'))
  await clock.advance(1000)
  await $.turn.complete(DONE)
  await clock.advance(1000)
  expect(runs).toBe(0)
})

test('a folder with a plan above it refreshes after a turn', async ($, on) => {
  const clock = mock.clock(on)
  let runs = 0
  const looked: string[] = []
  bare(on)
  on('fs.exists', (_h: never, input: never) => { const path = (input as unknown as { path: string }).path; looked.push(path); return { value: path === '/work/.vela.yaml' } })
  on('process.run', () => { runs += 1; return { value: ran(SESSION) } })
  on('fs.read', () => ({ value: '# This session' }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  await $.session.start(START('/work/plan/sub'))
  await clock.advance(1000)
  const atStart = runs
  await $.turn.complete(DONE)
  await clock.advance(1000)
  expect(atStart).toBe(1)
  expect(runs).toBe(2)
  expect(looked).toContain('/work/.vela.yaml')
})

test('a survey keeps the band', async ($, on) => {
  const clock = mock.clock(on)
  bare(on)
  on('ui.render', (h: never, input: never) => { const { Box, Text } = (h as { ui: { resolve: (e: never) => { Box: (p: unknown) => unknown, Text: (p: unknown) => unknown } } }).ui.resolve(input); return Box({ children: [Text({ children: ['the engine band'] })] }) })
  on('process.run', () => ({ value: ran(SESSION) }))
  on('fs.read', () => ({ value: '# This session' }))
  on('ui.open', () => ({ value: { isPlaced: false, reason: 'unasked below 144 columns' } }))
  on('tool.call', () => ({ result: 'ok' }))
  await $.tool.call(WRITE)
  await clock.advance(1000)
  const band = await $.ui.mount({ plugin: 'vela', surface: 'terminal', component: 'AbovePrompt', props: { hasSurvey: true, isWorking: false, maxRows: 10 } as never })
  expect(await band.findAll({ type: 'Text', text: SESSION.band })).toHaveLength(0)
})

test('a pane that cannot be placed says once that the panel is ready, never silently absent', async ($, on) => {
  const clock = mock.clock(on)
  let toasts = 0
  bare(on, () => { toasts += 1 })
  on('process.run', () => ({ value: ran(SESSION) }))
  on('fs.read', () => ({ value: '# This session' }))
  on('ui.open', () => ({ value: { isPlaced: false, reason: 'this surface has no pane' } }))
  on('tool.call', () => ({ result: 'ok' }))
  await $.tool.call(WRITE)
  await clock.advance(1000)
  await $.tool.call(WRITE)
  await clock.advance(1000)
  expect(toasts).toBe(1)
})
