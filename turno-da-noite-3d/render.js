// Uso: node render.js preview 3,15,22 | node render.js frames [workers]
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const FPS = 24, DUR = 70, root = __dirname;
const types = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript' };
const server = http.createServer((req, res) => {
  const p = path.join(root, decodeURIComponent(req.url.split('?')[0]).replace(/^\/$/, '/index.html'));
  fs.readFile(p, (e, d) => { if (e) { res.writeHead(404); res.end(); return; } res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); res.end(d); });
});
async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 720, height: 1280 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('PAGEERR', e.message));
  page.on('console', m => { if (m.type() === 'error') console.error('CONSOLE', m.text()); });
  await page.goto(`http://localhost:${server.address().port}/index.html`);
  await page.waitForFunction('window.ready === true', null, { timeout: 120000 });
  return page;
}
(async () => {
  await new Promise(r => server.listen(0, r));
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--use-gl=angle'] });
  const mode = process.argv[2];
  if (mode === 'preview') {
    const ts = process.argv[3].split(',').map(Number);
    const page = await openPage(browser);
    fs.mkdirSync(path.join(root, 'preview'), { recursive: true });
    for (const t of ts) {
      const t0 = Date.now();
      await page.evaluate(t => window.renderAt(t), t);
      await page.screenshot({ path: path.join(root, 'preview', `t${t}.png`) });
      console.log('t', t, Date.now() - t0, 'ms');
    }
  } else {
    const N = +(process.argv[3] || 4), total = FPS * DUR;
    fs.mkdirSync(path.join(root, 'frames'), { recursive: true });
    await Promise.all(Array.from({ length: N }, async (_, w) => {
      const page = await openPage(browser);
      for (let i = w; i < total; i += N) {
        await page.evaluate(t => window.renderAt(t), i / FPS);
        await page.screenshot({ path: path.join(root, 'frames', `f${String(i).padStart(5, '0')}.jpg`), type: 'jpeg', quality: 90 });
        if (i % 120 === w) console.log('frame', i, '/', total);
      }
    }));
  }
  await browser.close(); server.close();
})();
