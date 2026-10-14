// Parse mermaid blocks with the pinned mermaid.min.js, in node, with no browser.
//
//   node mermaid-parse.js <mermaid.min.js>   reads a JSON list of diagram sources on stdin and writes a JSON list on
//   stdout, one entry per source: null when mermaid parses it, else {message, token, text, expected}.
//
// The grammar is mermaid's own, so this check cannot disagree with the viewer about what draws. The page objects
// below are only what the bundle touches while it loads. `document.nodeType` 9 with no `implementation` puts the
// bundled DOMPurify in its documented unsupported mode, where sanitize returns its input unchanged: labels are not
// cleaned, which a parse does not need, and nothing here is ever drawn.
"use strict";
const fs = require("fs");

function noop() {}
const stubElement = () => ({ setAttribute: noop, appendChild: noop, style: {} });
globalThis.window = globalThis;
globalThis.addEventListener = noop;
globalThis.Element = function Element() {};
globalThis.document = {
  nodeType: 9, compatMode: "CSS1Compat", readyState: "complete", body: { appendChild: noop },
  createElement: stubElement, querySelector: () => null, querySelectorAll: () => [], addEventListener: noop,
};

function load(path) {
  const module = { exports: {} };
  new Function("module", "exports", fs.readFileSync(path, "utf8"))(module, module.exports);
  const mermaid = module.exports.default || module.exports;
  if (typeof mermaid.parse !== "function") throw new Error(`${path} has no mermaid.parse`);
  mermaid.initialize({ startOnLoad: false, securityLevel: "strict" });
  return mermaid;
}

function verdict(error) {
  const hash = (error && error.hash) || {};
  return {
    message: String((error && error.message) || error),
    token: hash.token == null ? null : String(hash.token),
    text: hash.text == null ? null : String(hash.text),
    expected: Array.isArray(hash.expected) ? hash.expected.map(String) : [],
  };
}

async function main() {
  // mermaid logs each failure itself; the verdicts on stdout are the only output this script means.
  console.error = console.warn = console.log = console.info = console.debug = noop;
  const mermaid = load(process.argv[2]);
  const sources = JSON.parse(fs.readFileSync(0, "utf8"));
  const out = [];
  for (const source of sources) {
    try {
      await mermaid.parse(source);
      out.push(null);
    } catch (error) {
      out.push(verdict(error));
    }
  }
  process.stdout.write(JSON.stringify(out));
}

main().catch((error) => {
  process.stderr.write(String((error && error.stack) || error));
  process.exit(2);
});
