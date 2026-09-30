// Node-only benchmark driver; upstream APIs are linked in benchmarks/README.md.
import fs from 'node:fs';
const [library, mode, file, count, output, widthArg = "400", heightArg = "300"] = process.argv.slice(2);
const width = Number(widthArg);
const height = Number(heightArg);
if (![width, height].every(value => Number.isSafeInteger(value) && value > 0)) throw new Error("canvas dimensions");
// Match the other adapters: pass the requested canvas through the public API.
const renderOptions = { printDensity: 8, width, height };
const sourceBytes = fs.readFileSync(file);
const n = Number(count);
if (!Number.isSafeInteger(n) || n < 1) throw new Error('iterations');
const api = await import(library);
// JS strings represent raw graphic bytes as byte-valued characters, while
// ordinary source text is UTF-8. Use the library's own byte-count-aware
// tokenizer (including changed prefixes/delimiters) to locate binary spans.
function sourceString(bytes) {
  const utf8 = data => new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(data);
  if (library !== 'zplr') return utf8(bytes);
  const raw = bytes.toString('latin1');
  const document = api.parseDocument(raw);
  const commands = document.items.flatMap(item => item.kind === 'label' ? item.commands : [item]);
  const binary = commands.filter(command =>
    (command.canonical === '^GF' && ['B', 'C'].includes(command.parameters[0]?.trim().toUpperCase())) ||
    (command.canonical === '~DY' && ['B', 'C'].includes(command.parameters[1]?.trim().toUpperCase())));
  let cursor = 0;
  let result = '';
  for (const command of binary) {
    result += utf8(bytes.subarray(cursor, command.span.start));
    result += raw.slice(command.span.start, command.span.end);
    cursor = command.span.end;
  }
  return result + utf8(bytes.subarray(cursor));
}
const source = sourceString(sourceBytes);
async function operation() {
  if (library === 'jszpl') {
    const label = new api.Label();
    label.width = 50;
    label.height = 37.5;
    label.printDensity = api.PrintDensity.dpmm8;
    for (let i = 0; i < Number(source); i++) {
      const text = new api.Text();
      text.fixed = true;
      text.left = 10 + i % 4 * 95;
      text.top = 10 + Math.floor(i / 4) * 22;
      text.characterHeight = 16;
      text.text = `Item ${String(i).padStart(2, '0')}`;
      label.content.push(text);
    }
    return label.generateZPL();
  }
  if (mode === 'parse') return api.parseDocument(source);
  const pngs = await api.renderZplPNG(source, renderOptions);
  if (pngs.length !== 1) throw new Error('expected one label');
  return pngs[0];
}
if (mode === 'probe-parse' || mode === 'probe-render') {
  let result;
  let verdict = 'accepted';
  try {
    if (mode === 'probe-parse') {
      const parsed = api.parseDocument(source);
      for (const diagnostic of parsed.diagnostics) console.error(JSON.stringify(diagnostic));
      if (parsed.diagnostics.some(d => d.severity === 'error')) verdict = 'rejected';
    } else {
      const images = await api.renderZplPNG(source, renderOptions);
      result = images[0];
      if (!result) verdict = 'accepted-empty';
    }
  } catch (error) {
    console.error(error.stack ?? String(error));
    verdict = 'rejected';
  }
  if (result) fs.writeFileSync(output, result);
  console.log(verdict);
  process.exit(0);
}
if (mode === "accuracy") {
  fs.writeFileSync(output, await operation());
  process.exit(0);
}
let sink;
const warmup = performance.now();
for (let i = 0; i < 3 || (process.env.ZPL_BENCH_MEMORY !== "1" && performance.now() - warmup < 250); i++) sink = await operation();
const start = process.hrtime.bigint();
let checksum = 0;
for (let i = 0; i < n; i++) {
  sink = await operation();
  checksum += sink.length ?? 1;
}
const ns = Number(process.hrtime.bigint() - start);
fs.writeFileSync(output, mode === 'parse' ? JSON.stringify(sink) : sink);
console.log(JSON.stringify({ns, iterations: n, checksum}));
