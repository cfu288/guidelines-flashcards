// Download EPUB files from publisher pages via puppeteer-core + system Chrome.
// Reads /tmp/manifest-epub-pending.json: [{ident, url, dest}]
// Writes /tmp/manifest-epub-results.json: [{ident, url, dest, status, reason}]
//
// Honors MODE env var:
//   headless (default) — runs headless
//   visible            — launches a visible browser; pauses for the user to log in
//                        when prompted; press Enter in the terminal to proceed per URL

const fs = require('fs');
const path = require('path');
const readline = require('readline');
const puppeteer = require('puppeteer-core');

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PENDING = '/tmp/manifest-epub-pending.json';
const RESULTS = '/tmp/manifest-epub-results.json';
const NAV_TIMEOUT_MS = 30000;
const MODE = process.env.MODE || 'headless';
const HEADLESS = MODE !== 'visible';

const UA =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 ' +
  '(KHTML, like Gecko) Version/17.0 Safari/605.1.15';

function isEpub(buf) {
  if (!buf || buf.length < 60) return false;
  // ZIP signature
  if (!(buf[0] === 0x50 && buf[1] === 0x4b && buf[2] === 0x03 && buf[3] === 0x04)) return false;
  // EPUB OCF requires "mimetype" file as first entry with content application/epub+zip
  const head = buf.slice(0, 200).toString('latin1');
  return head.includes('mimetype') && head.includes('application/epub+zip');
}

async function pause(prompt) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise(res => rl.question(prompt, ans => { rl.close(); res(ans); }));
}

async function downloadEpub(browser, entry) {
  const { ident, url, dest } = entry;
  const page = await browser.newPage();
  try {
    await page.setUserAgent(UA);
    await page.setExtraHTTPHeaders({ Accept: 'application/epub+zip,application/zip,*/*' });
    const resp = await page.goto(url, { waitUntil: 'load', timeout: NAV_TIMEOUT_MS });
    if (!resp) return { ...entry, status: 'failed', reason: 'no_response' };
    if (resp.status() >= 400) return { ...entry, status: 'failed', reason: `http_${resp.status()}` };

    const ct = (resp.headers()['content-type'] || '').toLowerCase();
    let buf = await resp.buffer().catch(() => null);

    // In visible mode, if the response is HTML (login wall or format-unavailable page),
    // wait for the user to do something then check again on the resulting page.
    if (!HEADLESS && (!buf || !isEpub(buf))) {
      console.error(`[${ident}] response was not EPUB (ct=${ct}). Browser is open at ${url}`);
      console.error('  → Log in / click any "Download EPUB" button, then press Enter here.');
      await pause('  pressed Enter > ');
      // Try fetching the same URL again now that cookies might be set
      const reResp = await page.goto(url, { waitUntil: 'load', timeout: NAV_TIMEOUT_MS });
      if (reResp && reResp.ok()) buf = await reResp.buffer().catch(() => null);
    }

    if (!buf || !isEpub(buf)) {
      return { ...entry, status: 'failed', reason: `not_epub (ct=${ct.split(';')[0] || '?'})` };
    }
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.writeFileSync(dest, buf);
    return { ...entry, status: 'downloaded', reason: null };
  } catch (e) {
    return { ...entry, status: 'failed', reason: `nav_error: ${String(e).slice(0, 120)}` };
  } finally {
    await page.close().catch(() => {});
  }
}

(async () => {
  const pending = JSON.parse(fs.readFileSync(PENDING, 'utf8'));
  console.error(`[${MODE}] ${pending.length} EPUB URLs to try…`);

  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: HEADLESS,
    args: HEADLESS
      ? ['--no-sandbox', '--disable-blink-features=AutomationControlled']
      : ['--disable-blink-features=AutomationControlled'],
  });

  const results = [];
  let i = 0;
  for (const entry of pending) {
    i++;
    const res = await downloadEpub(browser, entry);
    results.push(res);
    const tag = res.status === 'downloaded' ? '✓' : '✗';
    console.error(`[${i}/${pending.length}] ${tag} ${entry.ident} — ${res.reason || ''}`);
  }

  await browser.close();
  fs.writeFileSync(RESULTS, JSON.stringify(results, null, 2));
  console.error(`Wrote ${RESULTS} (${results.length} entries)`);
})().catch(e => {
  console.error('fatal:', e);
  process.exit(1);
});
