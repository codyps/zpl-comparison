// Shared protocol driver for the Node/Wasm renderers and TypeScript port.
import fs from 'node:fs';
import {createRequire} from 'node:module';

import {dispatch} from './session.mjs';

let wasmInitialization;
async function run(args) {
  const [libraryArg, mode, file, count, output, widthArg = '400', heightArg = '300'] = args;
  if (!libraryArg?.startsWith('--library=')) throw new Error('expected --library=<renderer>');
  const library = libraryArg.slice('--library='.length);
  const [n, width, height] = [count, widthArg, heightArg].map(Number);
  if (![n, width, height].every(value => Number.isSafeInteger(value) && value > 0)) throw new Error('iterations/canvas dimensions');
  // Resolve dependencies beside each isolated adapter manifest, also after deployment.
  const require = createRequire(new URL(`../${library}/package.json`, import.meta.url));
  const input = fs.readFileSync(file);
  let parse, render;
  if (library === 'codyps-zpl-node') {
    const api = require('./index.cjs');
    const profileName = process.env.ZPL_RENDER_PROFILE ?? 'zd621-203dpi';
    // The public Node API cannot override individual ZD621 preview flags.
    const profile = {'zd621-203dpi': 'zd621', 'zd621-preview-203dpi': 'zd621',
      'zq610-plus-203dpi': 'zq610-plus'}[profileName];
    if (!profile) throw new Error(`unknown ZPL_RENDER_PROFILE: ${profileName}`);
    const options = {format: 'png', width, height, dpi: 203, profile};
    if (process.env.ZPL_FONT_DIR) {
      const directory = process.env.ZPL_FONT_DIR;
      const font0 = fs.readFileSync(`${directory}/0.ttf`);
      const swiss = fs.readFileSync(`${directory}/Swiss.ttf`);
      options.resolveFont = name => {
        if (name === 'R:FC0.TTF') return font0;
        if (/^[REBA]:TT0003M_\.TTF$/.test(name)) return swiss;
        return api.resolveRomFont(name);
      };
      // Only controlled runs need room for the verified bitmap preamble.
      options.limits = {inputBytes: Math.max(1024 * 1024, input.length)};
    }
    render = () => {
      const result = api.render(input, options);
      if (result.labels !== 1) throw new Error(`expected one label, got ${result.labels}`);
      return result.data;
    };
  } else if (library === 'zpl-renderer-js') {
    const api = require('zpl-renderer-js/external');
    wasmInitialization ??= api.init({wasmBytes: fs.readFileSync(require.resolve('zpl-renderer-js/wasm'))});
    await wasmInitialization;
    // This API accepts text only. Do not silently replace arbitrary binary bytes.
    let source, decodingError;
    try {
      source = new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(input);
    } catch (error) {
      decodingError = error;
    }
    render = async () => {
      if (decodingError) throw decodingError;
      const labels = await api.zplToBase64MultipleAsync(source, width / 8, height / 8, 8,
        {enableInvertedLabels: true, grayscaleOutput: false});
      if (!labels.length) return null;
      if (labels.length !== 1) throw new Error(`expected one label, got ${labels.length}`);
      return Buffer.from(labels[0], 'base64');
    };
  } else if (library === 'zebrash-ts') {
    const api = await import('../zebrash-ts/api.mjs');
    parse = () => new api.Parser().parse(input);
    render = async () => {
      const labels = parse();
      if (!labels.length) return null;
      if (labels.length !== 1) throw new Error(`expected one label, got ${labels.length}`);
      return new api.Drawer().drawLabelAsPng(labels[0], {
        labelWidthMm: width / 8, labelHeightMm: height / 8, dpmm: 8,
        enableInvertedLabels: true, grayscaleOutput: false,
      });
    };
  } else {
    throw new Error(`unknown renderer: ${library}`);
  }
  if (mode === 'probe-parse' || mode === 'probe-render') {
    let result;
    let verdict = 'accepted';
    try {
      if (mode === 'probe-parse') {
        if (!parse) throw new Error('adapter does not expose parsing');
        parse();
      } else {
        result = await render();
        if (!result?.length) verdict = 'accepted-empty';
      }
    } catch (error) {
      console.error(error.stack ?? String(error));
      verdict = 'rejected';
    }
    if (result?.length) fs.writeFileSync(output, result);
    console.log(verdict);
    return;
  }
  async function operation() {
    if (mode === 'parse') {
      if (!parse) throw new Error('adapter does not expose parsing');
      return parse();
    }
    const result = await render();
    if (!result?.length) throw new Error('renderer returned no labels');
    return result;
  }
  if (mode === 'accuracy') {
    fs.writeFileSync(output, await operation());
    return;
  }
  let sink;
  const warmup = performance.now();
  for (let i = 0; i < 3 || (process.env.ZPL_BENCH_MEMORY !== '1' && performance.now() - warmup < 250); i++) sink = await operation();
  const start = process.hrtime.bigint();
  let checksum = 0;
  for (let i = 0; i < n; i++) {
    sink = await operation();
    checksum += sink.length ?? 1;
  }
  const ns = Number(process.hrtime.bigint() - start);
  if (process.env.ZPL_BENCH_MEMORY === '1') sink = await operation();
  fs.writeFileSync(output, mode === 'parse' ? JSON.stringify(sink) : sink);
  console.log(JSON.stringify({ns, iterations: n, checksum}));
  return;
}

await dispatch(run, process.argv.slice(2));
