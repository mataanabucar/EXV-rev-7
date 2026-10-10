// Print the manual HTML to PDF with headless Chromium (Letter, backgrounds on, no margins: the
// pages carry their own margins). Usage: node 2026-10-10-manual-print.mjs <manual.html> <out.pdf>
import path from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright');
const [src, out] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto('file://' + path.resolve(src), { waitUntil: 'networkidle' });
await page.evaluate(() => document.fonts.ready);
await page.pdf({ path: out, width: '8.5in', height: '11in', printBackground: true, preferCSSPageSize: true,
  margin: { top: '0', right: '0', bottom: '0', left: '0' } });
await browser.close();
console.log('wrote', out);
