// Node-only benchmark driver; upstream APIs are linked in benchmarks/README.md.
import fs from 'node:fs';
const [library, mode, file, count, output] = process.argv.slice(2);
const source = fs.readFileSync(file, 'utf8');
const n = Number(count);
if (!Number.isSafeInteger(n) || n < 1) throw new Error('iterations');
const api = await import(library);
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
  const pngs = await api.renderZplPNG(source, { printDensity: 8 });
  if (pngs.length !== 1) throw new Error('expected one label');
  return pngs[0];
}
if (mode === "accuracy") {
  fs.writeFileSync(output, await operation());
  process.exit(0);
}
let sink;
const warmup = performance.now();
for (let i = 0; i < 3 || performance.now() - warmup < 250; i++) sink = await operation();
const start = process.hrtime.bigint();
let checksum = 0;
for (let i = 0; i < n; i++) {
  sink = await operation();
  checksum += sink.length ?? 1;
}
const ns = Number(process.hrtime.bigint() - start);
fs.writeFileSync(output, mode === 'parse' ? JSON.stringify(sink) : sink);
console.log(JSON.stringify({ns, iterations: n, checksum}));
