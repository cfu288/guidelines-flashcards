// Launch a visible Chrome window for manual EPUB / file harvesting.
// Downloads go to <repo>/tmp/.
//
// Args:
//   node scripts/open_browser.js <start_url>     # opens at one URL
//   node scripts/open_browser.js                 # opens at a local launchpad page
//
// Stays alive until killed (Ctrl-C or `pkill -f open_browser.js`).
// Anything downloaded lands in tmp/ — then run import_manual_downloads.py.

const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer-core');

const REPO = path.resolve(__dirname, '..');
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const TMP_DIR = path.join(REPO, 'tmp');
const LAUNCHPAD = '/tmp/epub-launchpad.html';

(async () => {
  fs.mkdirSync(TMP_DIR, { recursive: true });

  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: false,
    defaultViewport: null,                       // full window
    args: [
      '--disable-blink-features=AutomationControlled',
      '--window-size=1400,900',
    ],
  });

  // Configure all pages to download into tmp/ via CDP
  const context = browser.defaultBrowserContext();
  // Allow downloads at all paths
  await context.overridePermissions('https://www.ahajournals.org', []);

  const page = (await browser.pages())[0] || await browser.newPage();
  const client = await page.target().createCDPSession();
  await client.send('Browser.setDownloadBehavior', {
    behavior: 'allow',
    downloadPath: TMP_DIR,
  });

  // Set up download behaviour for new pages too
  browser.on('targetcreated', async (target) => {
    if (target.type() !== 'page') return;
    const p = await target.page();
    if (!p) return;
    const c = await p.target().createCDPSession();
    await c.send('Browser.setDownloadBehavior', { behavior: 'allow', downloadPath: TMP_DIR });
  });

  const startUrl = process.argv[2] || `file://${LAUNCHPAD}`;
  await page.goto(startUrl, { waitUntil: 'domcontentloaded' }).catch(() => {});

  console.error(`\nBrowser open. Downloads → ${TMP_DIR}`);
  console.error(`Started at: ${startUrl}`);
  console.error(`Kill with: pkill -f open_browser.js\n`);

  // Keep alive
  await new Promise(() => {});
})().catch(e => {
  console.error('fatal:', e);
  process.exit(1);
});
