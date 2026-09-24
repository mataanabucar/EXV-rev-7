// Render the EX-MA concept views to PNG with headless Chromium.
// Usage: node 2026-09-24-concept-render.mjs <build_dir> <out_dir> [view ...]
// build_dir must contain the viewer html (as index.html), data.js and three.module.js.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright');

const [buildDir, outDir, ...only] = process.argv.slice(2);
const VIEWS = ['01-full-assembly', '02-control-box', '03-control-box-cutaway', '04-arm', '05-arm-cutaway'];
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript' };

const server = http.createServer((req, res) => {
  const p = path.join(buildDir, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const port = server.address().port;

const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1800, height: 1150 } });
page.on('console', m => { if (m.type() === 'error') console.error('page:', m.text()); });
page.on('pageerror', e => console.error('pageerror:', e.message));
fs.mkdirSync(outDir, { recursive: true });
for (const v of (only.length ? only : VIEWS)) {
  await page.goto(`http://127.0.0.1:${port}/index.html?view=${v}`);
  await page.waitForFunction(() => window.READY === true, null, { timeout: 120000 });
  const out = path.join(outDir, `2026-09-24-concept-${v}.png`);
  await page.locator('#wrap').screenshot({ path: out });
  console.log('wrote', out);
}
await browser.close();
server.close();
