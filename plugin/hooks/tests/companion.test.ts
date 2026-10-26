import { expect, mock, test } from 'claude-code/testing'

const BAND = 'Grill: hold, pay, confirm · 2 decided · 1 open · next: Pricing runtime · /vela-companion to open'
const SESSION = {
  version: 2, kind: 'session', capture: 14, notes: 'read', vault: '/plan', blocks: [],
  band_spans: [{ t: BAND, tone: 'plain' }], out_of_date: 'This panel is out of date. Ask again.',
  session: { title: 'Grill: hold, pay, confirm' }, diagram: null, warnings: [],
}
const line = (t: string, tone = 'plain') => [{ t, tone }]
const DRAW = (w: number) => [[{ t: `drawn at ${w}`, tone: 'info' }]]
const BLOCKS = [
  { type: 'card', title: 'Grill: hold, pay, confirm', right: '14 notes · 10:11', tone: 'info', lines: [line('Settle how a crossing is held.', 'dim'), [{ t: 'Agenda  ', tone: 'plain' }, { bar: [3, 4] }, { t: '  3 of 4 done', tone: 'dim' }]] },
  { type: 'next', chip: 'NEXT', text: 'Pricing runtime', id: 'RUN-pricing', note: 'last item on the agenda' },
  { type: 'section', key: 'decided', title: 'Decided this session', count: '2', rows: [
    { mark: '✔', tone: 'good', name: 'Hold, pay, confirm', id: 'FLO-001', note: 'was assumption', chip: null, sub: null, page: 'flows/FLO-001.md' },
    { mark: '?', tone: 'new', name: 'Tidepay outcome wording', id: 'UNK-009', note: 'Booking senior', chip: { t: 'NEW', tone: 'new' }, sub: [{ t: 'held by ', tone: 'dim' }, { t: 'Tidepay outcome wording', tone: 'info', page: 'x/11-unknowns.md' }], page: null },
  ] },
  { type: 'bars', title: 'Waiting', rows: [{ label: 'Booking senior', value: 19, max: 19, tone: 'bad', text: '19' }, { label: 'Finance', value: 5, max: 19, tone: 'warn', text: '5' }] },
  { type: 'diagram', title: 'Flow: Hold, pay, confirm', id: 'FLO-001', alt: 'a flow', svg: true, folded: { '48': 'five apps are shown as one lane' }, drawings: { '48': DRAW(48), '60': DRAW(60), '72': DRAW(72), '96': DRAW(96) } },
  { type: 'lines', lines: [line('Pages changed FLO-001')] },
]
const RICH = { ...SESSION, blocks: BLOCKS, band_spans: [{ t: 'Grill', tone: 'strong' }, { t: ' · 1 open', tone: 'warn' }] }
let processRuns = 0  // every answer a test gives to process.run goes through `ran`, so this counts the processes vela was asked to start
const ran = (stdout: unknown, exitCode = 0) => (processRuns += 1, { exitCode, stdout: JSON.stringify(stdout), stderr: '', isStdoutTruncated: false, isStderrTruncated: false })
const WRITE = { tool: 'Bash', command: 'sh /p/scripts/run-vela decide CON-007 --yes ^c12' } as never

test('vela is started through the shell by its full path, never a bare name', async ($, on) => {
  const clock = mock.clock(on)
  const argvs: string[][] = []
  on('process.run', (_$, e) => { argvs.push([...(e as { argv: string[] }).argv]); return { value: ran(SESSION) } })
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
  on('ui.open', () => ({ value: { isPlaced: false, reason: 'unasked below 144 columns' } }))
  on('tool.call', () => ({ result: 'ok' }))
  await $.tool.call(WRITE)
  await clock.advance(1000)
  const band = await $.ui.mount({ plugin: 'vela', surface: 'terminal', component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 10 } as never })
  expect(await band.find({ type: 'Text', text: BAND })).toBeDefined()
})

type Found = { type: string, props: Record<string, unknown>, text: string }
type Mounted = { find: (q: unknown) => Promise<Found | undefined>, findAll: (q: unknown) => Promise<Found[]>, press: (a: unknown) => Promise<void> }
// find matches by inclusion, so an outer Text holding the words matches first; the leaf is the one that shows exactly them.
const leaf = async (m: Mounted, text: string) => (await m.findAll({ type: 'Text', text })).find((n) => n.text === text)
const PANE_PROPS = (cols: number) => ({ title: 'x', isFocused: false, bodyColumns: cols, placement: 'dock' }) as never

async function paneAfterWrite($: never, on: never, found: unknown = RICH, surface: 'terminal' | 'desktop' = 'terminal', cols = 64) {
  const d = $ as never as { tool: { call: (e: never) => Promise<unknown> }, ui: { mount: (a: never) => Promise<never> } }
  const hook = on as never as (n: string, f: (...a: never[]) => unknown) => void
  hook('process.run', () => ({ value: ran(found) }))
  hook('ui.open', () => ({ value: { isPlaced: true } }))
  hook('tool.call', () => ({ result: 'ok' }))
  await d.tool.call(WRITE)
  return { mount: () => d.ui.mount({ plugin: 'vela', surface, component: 'Pane', requestId: 'vela-session', props: PANE_PROPS(cols) } as never) }
}

test('the pane draws the card, the next chip, section rows and bars from the blocks', async ($, on) => {
  const clock = mock.clock(on)
  const { mount } = await paneAfterWrite($ as never, on as never)
  await clock.advance(1000)
  const pane = await mount() as never as Mounted
  const card = (await pane.findAll({ type: 'Box' })).find((b) => b.props.borderStyle === 'round')
  expect(card?.props.borderColor).toBe('#5aa8ff')
  expect((await leaf(pane, 'Grill: hold, pay, confirm'))?.props.weight).toBe('bold')
  expect((await leaf(pane, ' NEXT '))?.props.inverse).toBe(true)
  expect(await leaf(pane, 'FLO-001')).toBeDefined()
  expect((await leaf(pane, ' NEW '))?.props.color).toBe('magenta')
  expect((await leaf(pane, '✔'))?.props.color).toBe('green')
  expect((await leaf(pane, '█'.repeat(20)))?.props.color).toBe('red')                  // the 19-of-19 bar
  expect((await leaf(pane, '█'.repeat(5)))?.props.color).toBe('#e5a50a')               // 5 of 19, scaled to 20 cells
  expect((await leaf(pane, '█'.repeat(15)))?.props.color).toBe('green')                // the agenda: 3 of 4 done
  expect((await leaf(pane, '░'.repeat(5)))?.props.dimColor).toBe(true)
  expect(await pane.find({ type: 'Link', text: /Hold, pay, confirm/ })).toBeDefined()  // a row's page is a link
})

test('the diagram is the widest drawing that fits the pane', async ($, on) => {
  const clock = mock.clock(on)
  const { mount } = await paneAfterWrite($ as never, on as never, RICH, 'terminal', 64)
  await clock.advance(1000)
  const wide = await mount() as never as { find: (q: unknown) => Promise<unknown> }
  expect(await wide.find({ type: 'Text', text: 'drawn at 60' })).toBeDefined()
  expect(await wide.find({ type: 'Text', text: 'drawn at 72' })).toBeUndefined()
})

test('the diagram falls back to 48 columns in a narrow pane', async ($, on) => {
  const clock = mock.clock(on)
  const { mount } = await paneAfterWrite($ as never, on as never, RICH, 'terminal', 50)
  await clock.advance(1000)
  const narrow = await mount() as never as { find: (q: unknown) => Promise<unknown> }
  expect(await narrow.find({ type: 'Text', text: 'drawn at 48' })).toBeDefined()
})

test('the desktop draws the picture vela wrote instead of the characters', async ($, on) => {
  const clock = mock.clock(on)
  const withSvg = { ...RICH, diagram: { svg: '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>' } }
  const { mount } = await paneAfterWrite($ as never, on as never, withSvg, 'desktop')
  await clock.advance(1000)
  const pane = await mount() as never as Mounted
  expect(await pane.find({ type: 'Svg' })).toBeDefined()
  expect(await pane.find({ type: 'Text', text: 'drawn at 60' })).toBeUndefined()
})

test('its only buttons fold sections; a press hides the rows and sends nothing', async ($, on) => {
  const clock = mock.clock(on)
  const sent: string[] = []
  ;(on as never as (n: string, f: (...a: never[]) => unknown) => void)('prompt.submit', () => { sent.push('prompt'); return {} })
  const { mount } = await paneAfterWrite($ as never, on as never)
  await clock.advance(1000)
  const pane = await mount() as never as Mounted
  const keys = (await pane.findAll({ type: 'Button' })).map((b) => b.props.key)
  expect(keys.every((k) => String(k).startsWith('fold:'))).toBe(true)
  expect(await leaf(pane, 'UNK-009')).toBeDefined()
  const runsBefore = sent.length
  const processBefore = processRuns
  await pane.press({ key: 'fold:vela-session:decided' })
  expect(await leaf(pane, 'UNK-009')).toBeUndefined()
  expect(await leaf(pane, 'Decided this session')).toBeDefined()  // the header stays, to open it again
  expect(sent.length).toBe(runsBefore)
  expect(processRuns).toBe(processBefore)  // a press starts no process either
})

test('the band draws vela\'s spans in their tones', async ($, on) => {
  const clock = mock.clock(on)
  on('process.run', () => ({ value: ran(RICH) }))
  on('ui.open', () => ({ value: { isPlaced: false, reason: 'unasked below 144 columns' } }))
  on('ui.toast', () => ({ value: undefined }))
  on('tool.call', () => ({ result: 'ok' }))
  await $.tool.call(WRITE)
  await clock.advance(1000)
  const band = await $.ui.mount({ plugin: 'vela', surface: 'terminal', component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 10 } as never }) as never as Mounted
  expect((await leaf(band, ' · 1 open'))?.props.color).toBe('#e5a50a')
  expect((await leaf(band, 'Grill'))?.props.weight).toBe('bold')
})

const PLAN = { version: 2, kind: 'explain', view: 'none', vault: '/plan', blocks: [], band_spans: [], copy: { title: 'Harborline' }, diagram: null, warnings: [] }
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
  on('ui.open', () => ({ value: { isPlaced: false, reason: 'unasked below 144 columns' } }))
  on('tool.call', () => ({ result: 'ok' }))
  await $.tool.call(WRITE)
  await clock.advance(1000)
  const band = await $.ui.mount({ plugin: 'vela', surface: 'terminal', component: 'AbovePrompt', props: { hasSurvey: true, isWorking: false, maxRows: 10 } as never })
  expect(await band.findAll({ type: 'Text', text: BAND })).toHaveLength(0)
})

test('a pane that cannot be placed says once that the panel is ready, never silently absent', async ($, on) => {
  const clock = mock.clock(on)
  let toasts = 0
  bare(on, () => { toasts += 1 })
  on('process.run', () => ({ value: ran(SESSION) }))
  on('ui.open', () => ({ value: { isPlaced: false, reason: 'this surface has no pane' } }))
  on('tool.call', () => ({ result: 'ok' }))
  await $.tool.call(WRITE)
  await clock.advance(1000)
  await $.tool.call(WRITE)
  await clock.advance(1000)
  expect(toasts).toBe(1)
})

// --- the explain pane, a stale file, links and wide names ---------------------------------------------------------------

const STUCK = {
  version: 2, kind: 'explain', view: 'stuck', vault: '/Users/x/My Plan #1', out_of_date: 'This panel is out of date. Ask again.',
  copy: { title: 'Unified Booking' }, diagram: null, band_spans: [], warnings: [],
  blocks: [
    { type: 'card', title: "What's stuck?", right: '', tone: 'bad', lines: [line('2 things are stuck.', 'strong')] },
    { type: 'section', key: 'group:Platform lead', title: 'Platform lead', count: '1', rows: [{ mark: '■', tone: 'bad', name: 'Finance on Booking events', id: '', note: '', chip: { t: '17 days', tone: 'bad' }, sub: [{ t: 'ask by the first of next month', tone: 'dim' }], page: null }] },
    { type: 'section', key: 'group:Solution lead', title: 'Solution lead', count: '1', rows: [{ mark: '■', tone: 'warn', name: 'Review of the customer data', id: '', note: '', chip: { t: '0 days', tone: 'warn' }, sub: null, page: null }] },
    { type: 'section', key: 'items', title: '', count: '', rows: [{ mark: '○', tone: 'dim', name: 'An untitled row', id: '', note: '', chip: null, sub: null, page: null }] },
    { type: 'lines', lines: [[{ t: 'Also ask  ', tone: 'dim' }, { t: "what's left?", tone: 'info' }], [{ t: 'Full picture  ', tone: 'dim' }, { t: 'dashboard.html in this folder', tone: 'info', page: 'dashboard.html#asks' }]] },
  ],
}

async function planPane($: never, on: never, found: unknown, code = 0, cols = 64) {
  const d = $ as never as { command: { run: (a: never) => Promise<unknown> }, ui: { mount: (a: never) => Promise<never> } }
  const hook = on as never as (n: string, f: (...a: never[]) => unknown) => void
  hook('process.run', () => ({ value: ran(found, code) }))
  hook('ui.open', () => ({ value: { isPlaced: true } }))
  await d.command.run({ command: 'vela-plan', args: '' } as never)
  return d.ui.mount({ plugin: 'vela', surface: 'terminal', component: 'Pane', requestId: 'vela-plan', props: PANE_PROPS(cols) } as never) as never as Promise<Mounted>
}

test('the plan pane draws the red card, untitled rows, a fold button per holder and the dashboard link', async ($, on) => {
  bare(on)
  const pane = await planPane($ as never, on as never, STUCK)
  const card = (await pane.findAll({ type: 'Box' })).find((b) => b.props.borderStyle === 'round')
  expect(card?.props.borderColor).toBe('red')
  const keys = (await pane.findAll({ type: 'Button' })).map((b) => b.props.key)
  expect(keys).toEqual(['fold:vela-plan:group:Platform lead', 'fold:vela-plan:group:Solution lead'])
  expect(await leaf(pane, 'An untitled row' + '')).toBeUndefined()  // padded to the section's width, still drawn
  expect(await pane.find({ type: 'Text', text: /An untitled row/ })).toBeDefined()
  expect(await pane.find({ type: 'Text', text: "what's left?" })).toBeDefined()
  const links = await pane.findAll({ type: 'Link' })
  expect(links.map((l) => l.props.href)).toEqual(['file:///Users/x/My%20Plan%20%231/dashboard.html#asks'])
})

test('a path with a hash, a question mark, a space and a percent sign stays one path', async ($, on) => {
  bare(on)
  const odd = { ...STUCK, vault: '/Users/x/100% #1 ?/plan' }
  const pane = await planPane($ as never, on as never, odd)
  const links = await pane.findAll({ type: 'Link' })
  expect(links[0].props.href).toBe('file:///Users/x/100%25%20%231%20%3F/plan/dashboard.html#asks')
})

test('a JSON of another version is never a blank pane: vela\'s sentence is shown', async ($, on) => {
  const clock = mock.clock(on)
  const logs: string[] = []
  ;(on as never as (n: string, f: (...a: never[]) => unknown) => void)('ui.log', (_h: never, e: never) => { logs.push((e as unknown as { text: string }).text); return { value: undefined } })
  on('process.run', () => ({ value: ran({ ...SESSION, version: 1, blocks: undefined }) }))
  on('tool.call', () => ({ result: 'ok' }))
  await $.tool.call(WRITE)
  await clock.advance(1000)
  const band = await $.ui.mount({ plugin: 'vela', surface: 'terminal', component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 10 } as never }) as never as Mounted
  expect(await band.find({ type: 'Text', text: SESSION.out_of_date })).toBeDefined()
  expect(logs.some((l) => l.includes('version 1'))).toBe(true)
})

test("a plan question vela can't answer shows vela's message in the plan pane", async ($, on) => {
  bare(on)
  const pane = await planPane($ as never, on as never, { message: 'The last answer was written by an older vela and can\'t be redrawn. Ask the question again.' }, 1)
  expect(await pane.find({ type: 'Text', text: /older vela/ })).toBeDefined()
})

test('a block type the mod does not know is skipped and logged once', async ($, on) => {
  const clock = mock.clock(on)
  const logs: string[] = []
  ;(on as never as (n: string, f: (...a: never[]) => unknown) => void)('ui.log', (_h: never, e: never) => { logs.push((e as unknown as { text: string }).text); return { value: undefined } })
  const odd = { ...RICH, blocks: [{ type: 'hologram' }, ...BLOCKS] }
  const { mount } = await paneAfterWrite($ as never, on as never, odd)
  await clock.advance(1000)
  const pane = await mount() as never as Mounted
  await pane.press({ key: 'fold:vela-session:decided' })  // a redraw
  await pane.press({ key: 'fold:vela-session:decided' })
  expect(await leaf(pane, 'FLO-001')).toBeDefined()
  expect(logs.filter((l) => l.includes('hologram'))).toHaveLength(1)
})

test('names in wide characters are padded by cells, and the link holds no blanks', async ($, on) => {
  const clock = mock.clock(on)
  const rows = [
    { mark: '✔', tone: 'good', name: '漢字', id: '', note: '', chip: null, sub: null, page: 'a.md' },
    { mark: '✔', tone: 'good', name: 'abcd', id: '', note: 'x', chip: null, sub: null, page: null },
  ]
  const wideRows = { ...RICH, blocks: [{ type: 'section', key: 'k', title: 'T', count: '2', rows }] }
  const { mount } = await paneAfterWrite($ as never, on as never, wideRows)
  await clock.advance(1000)
  const pane = await mount() as never as Mounted
  const link = await pane.find({ type: 'Link' })
  expect(link?.props.label).toBe('漢字')                                   // two wide characters are four cells, as wide as abcd: no padding
  expect(await pane.find({ type: 'Text', text: /abcd/ })).toBeDefined()
})

test('the folded-lane words show under the drawing that folded them', async ($, on) => {
  const clock = mock.clock(on)
  const { mount } = await paneAfterWrite($ as never, on as never, RICH, 'terminal', 50)
  await clock.advance(1000)
  const pane = await mount() as never as Mounted
  expect(await pane.find({ type: 'Text', text: 'five apps are shown as one lane' })).toBeDefined()
})

test('the lit map has no drawing, so the terminal says it in words and the desktop draws the picture', async ($, on) => {
  const clock = mock.clock(on)
  const map = { type: 'diagram', title: 'Where the questions sit', id: '', alt: 'Apps with open questions: Booking (warning).', svg: true, drawings: {}, folded: {} }
  const found = { ...RICH, blocks: [map], diagram: { kind: 'map', svg: '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"></svg>' } }
  const term = await paneAfterWrite($ as never, on as never, found)
  await clock.advance(1000)
  const pane = await term.mount() as never as Mounted
  expect(await pane.find({ type: 'Text', text: 'Apps with open questions: Booking (warning).' })).toBeDefined()
  expect(await pane.find({ type: 'Svg' })).toBeUndefined()
})
