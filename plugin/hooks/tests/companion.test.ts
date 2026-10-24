import { expect, mock, test } from 'claude-code/testing'

const SESSION = {
  kind: 'session', capture: 14, notes: 'read', vault: '/plan',
  band: 'Grill: hold, pay, confirm · 2 decided · 1 open · next: Pricing runtime · /vela-companion to open',
  session: { title: 'Grill: hold, pay, confirm' }, files: { md: '.vela/companion/session.md' },
  diagram: { svg: '', text: '1. Find a crossing' }, warnings: [],
}
const ran = (stdout: unknown, exitCode = 0) => ({ exitCode, stdout: JSON.stringify(stdout), stderr: '', isStdoutTruncated: false, isStderrTruncated: false })
const WRITE = { tool: 'Bash', command: 'sh /p/scripts/run-vela decide CON-007 --yes ^c12' } as never

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
