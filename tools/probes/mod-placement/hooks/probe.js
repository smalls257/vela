// Placement probe. Throwaway: it learns where a pane docks and what `open` resolves with.
// The button is here only to see where the pane docks and whether a press lands; nothing that ships has one.
const seen = {}
const renderedIds = new Set()

export function register(on) {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'probe-pane', description: 'Open the probe pane', immediate: true })
    await $.command.register({ name: 'probe-report', description: 'Print what the probe stored' })
    $.clock.after(0, async () => {
      const result = await $.ui.open({ id: 'probe-auto', title: 'Probe (auto)' })
      await $.store.set('auto-open', JSON.stringify(result ?? 'void'))
      $.ui.invalidate('ui.render')
    })
    return next(e)
  })

  on('command.run', { command: 'probe-pane' }, async ($, e) => {
    const result = await $.ui.open({ id: 'probe-asked', title: 'Probe (asked)' })
    await $.store.set('asked-open', JSON.stringify({ result: result ?? 'void', presentation: e.presentation ?? null }))
    return {}
  })

  on('ui.render', { component: 'Pane' }, async ($, e, next) => {
    const { Box, Text, Button, Markdown, Code, Svg } = $.ui.resolve(e)
    if (!renderedIds.has(e.requestId)) {
      renderedIds.add(e.requestId)
      await $.store.set('render:' + e.requestId, JSON.stringify({
        surface: e.surface, placement: e.props.placement, bodyColumns: e.props.bodyColumns, viewport: e.viewport ?? null,
      }))
    }
    const fence = '```mermaid\nsequenceDiagram\n  A->>B: hello\n  B->>A: back\n```'
    const children = [
      Markdown({ text: 'Probe pane ' + e.requestId + '\n\n' + fence }),
      Code({ source: 'const where = "' + (e.props.placement ?? '?') + '"', language: 'js' }),
      Button({ key: 'press', label: 'Press me', onPress: () => { $.prompt.submit({ text: 'probe button pressed', asUser: true }) } }),
    ]
    if (e.surface === 'desktop') {
      children.push(Svg({ alt: 'probe rectangle', source: '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="60"><rect width="200" height="60" fill="#dde"/><text x="10" y="35">probe svg</text></svg>' }))
    }
    return Box({ flexDirection: 'column', children })
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const { Text } = $.ui.resolve(e)
    const auto = await $.store.get('auto-open')
    return Text({ children: ['probe band ' + String(auto ?? 'not opened yet')] })
  })

  on('tool.call', async ($, e, next) => {
    const result = await next(e)
    await $.store.set('tool-returned', String(Date.now()))
    $.clock.after(0, async () => {
      await $.process.run(['sleep', '2'])
      await $.store.set('process-finished', String(Date.now()))
    })
    return result
  })

  on('command.run', { command: 'probe-report' }, async ($, e) => {
    const keys = ['auto-open', 'asked-open', 'render:probe-auto', 'render:probe-asked', 'tool-returned', 'process-finished']
    const lines = []
    for (const key of keys) lines.push(key + ' = ' + String(await $.store.get(key)))
    return { text: lines.join('\n') }
  })
}
