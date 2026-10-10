// Render the manual's 3D figures with headless Chromium.
// Usage: node 2026-10-10-manual-figures.mjs <figures.json> <scene_dir> <out_dir> [figure id ...]
// THREE_DIR: folder holding three's package (default: ./node_modules/three next to the cwd).
// Writes <out_dir>/<id>.png (transparent background) and <out_dir>/<id>.json (callout anchors,
// arrows and scale, in output pixels) for 2026-10-10-build-manual.py.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright');
const HERE = path.dirname(fileURLToPath(import.meta.url));
const [figFile, sceneDir, outDir, ...only] = process.argv.slice(2);
const THREE_DIR = process.env.THREE_DIR || path.resolve('node_modules/three');
const ROUTES = [
  ['/index.html', path.join(HERE, '2026-10-10-manual-render.html')],
  ['/three.module.js', path.join(THREE_DIR, 'build/three.module.js')],
  ['/addons/', path.join(THREE_DIR, 'examples/jsm') + '/'],
  ['/scene/', path.resolve(sceneDir) + '/'],
];
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json' };
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  let file = null;
  for (const [k, v] of ROUTES) {
    if (k.endsWith('/') ? u.startsWith(k) : u === k) { file = k.endsWith('/') ? v + u.slice(k.length) : v; break; }
  }
  if (!file || !fs.existsSync(file)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const port = server.address().port;

const figs = JSON.parse(fs.readFileSync(figFile, 'utf8')).filter(f => !only.length || only.includes(f.id));
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
  '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
page.on('console', m => { if (m.type() === 'error') console.error('page:', m.text()); });
page.on('pageerror', e => console.error('pageerror:', e.message));
await page.goto(`http://127.0.0.1:${port}/index.html`);
await page.waitForFunction(() => window.READY === true, null, { timeout: 60000 });
const n = await page.evaluate(() => window.loadScene('/scene'));
console.log(`scene: ${n} objects`);
fs.mkdirSync(outDir, { recursive: true });
for (const f of figs) {
  const t0 = Date.now();
  try {
    const res = await page.evaluate(spec => window.renderFigure(spec), f);
    fs.writeFileSync(path.join(outDir, `${f.id}.png`), Buffer.from(res.png.split(',')[1], 'base64'));
    delete res.png;
    fs.writeFileSync(path.join(outDir, `${f.id}.json`), JSON.stringify(res));
    console.log(`${f.id}: ${((Date.now() - t0) / 1000).toFixed(1)} s`);
  } catch (e) {
    console.error(`${f.id}: FAILED ${e.message}`);
    process.exitCode = 1;
  }
}
await browser.close();
server.close();
