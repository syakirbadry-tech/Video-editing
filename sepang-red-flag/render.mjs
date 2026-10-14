// Usage:
//   node render.mjs stills 1.5,8,16          -> frames/still_<t>.jpg
//   node render.mjs video <startFrame> <endFrame> <out.mp4>
import { chromium } from 'playwright-core';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';

const FPS = 30;
const root = path.dirname(new URL(import.meta.url).pathname);
const types = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json' };
const server = http.createServer((req, res) => {
  const p = path.join(root, decodeURIComponent(req.url.split('?')[0]));
  fs.readFile(p, (e, d) => { if (e) { res.writeHead(404); res.end(); return; } res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); res.end(d); });
}).listen(0);
const port = server.address().port;

const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-gpu-vsync'],
});
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
page.on('console', m => console.log('[page]', m.text()));
page.on('pageerror', e => console.log('[page error]', e.message));
await page.goto(`http://localhost:${port}/index.html`);
await page.waitForFunction('window.READY === true', null, { timeout: 120000 });

const grab = async t => Buffer.from((await page.evaluate(t => window.frame(t), t)).split(',')[1], 'base64');
const [mode, a, b, outFile] = process.argv.slice(2);
if (mode === 'stills') {
  fs.mkdirSync(path.join(root, 'frames'), { recursive: true });
  for (const t of a.split(',').map(Number)) {
    const s = Date.now(); const buf = await grab(t);
    fs.writeFileSync(path.join(root, 'frames', `still_${t}.jpg`), buf); console.log('still', t, Date.now() - s, 'ms');
  }
} else {
  const f0 = +a, f1 = +b;
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', outFile], { stdio: ['pipe', 'inherit', 'inherit'] });
  const s = Date.now();
  for (let f = f0; f < f1; f++) {
    if (!ff.stdin.write(await grab(f / FPS))) await once(ff.stdin, 'drain');
    if ((f - f0) % 30 === 0) console.log(`frame ${f} (${((Date.now() - s) / (f - f0 + 1)).toFixed(0)} ms/f)`);
  }
  ff.stdin.end(); await once(ff, 'close');
}
await browser.close(); server.close();
