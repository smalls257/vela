// Shared by viewer.py and the dashboard (explorer/build.py): the offline drawing rules for Mermaid diagrams.
const SVG_DROP = new Set(['script', 'image', 'foreignobject', 'iframe', 'object', 'embed', 'animate', 'set', 'animatemotion', 'animatetransform', 'video', 'audio']);
// Style text that could name an off-page resource is dropped whole. Escapes (\75rl) and
// image-set() are refused too, because deciding what such CSS means is the regex trap.
function offPageUrl(css) { return /@import|\\|image-set|cross-fade|element\(|\bsrc\(|url\(\s*(?!['"]?#)/i.test(css); }
function cleanSvgChildren(parent) {
  for (const el of [...parent.children]) {
    const tag = el.localName.toLowerCase();
    if (SVG_DROP.has(tag)) { el.remove(); continue; }
    for (const attr of [...el.attributes]) {
      const name = attr.name.toLowerCase();
      const off = (name === 'href' || name === 'xlink:href') && !attr.value.trim().startsWith('#');
      if (name.startsWith('on') || off || (name === 'style' && offPageUrl(attr.value))) el.removeAttribute(attr.name);
    }
    if (tag === 'style' && offPageUrl(el.textContent)) { el.remove(); continue; }
    cleanSvgChildren(el);
  }
}
function sanitizeSvg(svg) {
  const holder = document.createElement('template');
  holder.innerHTML = svg;
  cleanSvgChildren(holder.content);
  return holder.content;
}
// A diagram cannot carry its own configuration, and no attempt is made to clean
// it: init directives and frontmatter are refused so the reader sees why.
function hasDiagramConfig(source) { return /%%\{/.test(source) || /^\s*---/.test(source); }

// The one way a diagram is drawn in an offline page (the viewer and the dashboard): mermaid in strict mode, no
// diagram-borne configuration, and the SVG it returns cleaned by sanitizeSvg before it is shown.
function mermaidSettings(dark) {
  return {
    startOnLoad: false, theme: dark ? 'dark' : 'neutral', securityLevel: 'strict', htmlLabels: false,
    flowchart: { htmlLabels: false }, sequence: { useMaxWidth: true }, class: { htmlLabels: false }, state: { htmlLabels: false },
    secure: ['secure', 'securityLevel', 'startOnLoad', 'maxTextSize', 'maxEdges', 'themeCSS', 'themeVariables', 'htmlLabels',
      'flowchart', 'class', 'state', 'fontFamily', 'theme'],
  };
}
