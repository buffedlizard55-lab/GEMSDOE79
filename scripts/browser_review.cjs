/* Optional browser QA. npm ci --prefix tools/browser-qa --ignore-scripts */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const assert = require('assert/strict');
const {chromium: playwright} = require('../tools/browser-qa/node_modules/playwright-core');
const {default: chromium, setupLambdaEnvironment} = require('../tools/browser-qa/node_modules/@sparticuz/chromium/build/index.js');
const {inflate} = require('../tools/browser-qa/node_modules/@sparticuz/chromium/build/lambdafs.js');
const root = path.resolve(__dirname, '..');
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:8080';
const sha = (buffer) => crypto.createHash('sha256').update(buffer).digest('hex');
(async () => {
  // Use npm-bundled support libraries; no OS package download or security bypass.
  await inflate(path.join(root, 'tools/browser-qa/node_modules/@sparticuz/chromium/bin/al2023.tar.br'));
  setupLambdaEnvironment(path.join(require('os').tmpdir(), 'al2023/lib'));
  const args = chromium.args.filter(a => !['--disable-web-security', '--allow-running-insecure-content', '--disable-site-isolation-trials'].includes(a));
  const browser = await playwright.launch({args, executablePath: await chromium.executablePath(), headless: true});
  const context = await browser.newContext({viewport: {width: 1440, height: 1050}, acceptDownloads: true});
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('response', (response) => { if (response.status() >= 400) errors.push(response.status() + ' ' + response.url()); });
  const siteManifest = JSON.parse(fs.readFileSync(path.join(root, 'docs/evidence/site_manifest.json'), 'utf8'));
  const pages = siteManifest.pages;
  const cases = [];
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({width, height: width > 680 ? 1050 : 900});
    for (const filename of pages) {
      const response = await page.goto(base + '/' + filename, {waitUntil: 'networkidle'});
      assert.equal(response.status(), 200);
      const dimensions = await page.evaluate(() => ({width: innerWidth, scroll: document.documentElement.scrollWidth}));
      assert(dimensions.scroll <= dimensions.width + 1, filename + ' horizontally overflows at ' + width);
      assert.equal(await page.locator('h1').count(), 1);
      cases.push({page: filename, viewport_width: width, http: response.status(), horizontal_overflow: false});
    }
    await page.goto(base + '/index.html', {waitUntil: 'networkidle'});
    fs.mkdirSync(path.join(root, '.cache/screenshots'), {recursive: true});
    await page.screenshot({path: path.join(root, '.cache/screenshots/home-' + width + '.png'), fullPage: true});
  }
  for (const [alias, target] of [['EXECUTIVE_SUMMARY.html', 'executive-summary.html'], ['PROJECT_BRIEF.html', 'research.html']]) {
    await page.goto(base + '/' + alias);
    await page.waitForURL('**/' + target);
  }
  const card = JSON.parse(fs.readFileSync(path.join(root, 'run_card.json')));
  await page.setViewportSize({width: 1440, height: 1050});
  await page.goto(base + '/index.html');
  const expectedVerdictBanner = card.ok_to_submit === true && card.verdict === 'promote'
    ? /OK TO SUBMIT: YES/
    : /OK TO SUBMIT: NO/;
  assert.match(await page.locator('.download-warning, .download-ready, main').first().innerText(), expectedVerdictBanner);
  await page.locator('[data-copy="submission-note"]').click();
  await page.waitForFunction(() => document.getElementById('toast').textContent.startsWith('Copied.'));
  assert.equal(await page.evaluate(() => navigator.clipboard.readText()), card.submission_note);
  const downloaded = page.waitForEvent('download');
  await page.locator('a[download][href$=".tif"]').first().click();
  const download = await downloaded;
  const dest = path.join(root, '.cache/browser-downloaded.tif');
  await download.saveAs(dest);
  assert.equal(sha(fs.readFileSync(dest)), card.raster_sha256);
  await page.goto(base + '/executive-summary.html', {waitUntil: 'networkidle'});
  const identityRequests = [];
  const recordIdentityRequest = request => identityRequests.push(request.url());
  page.on('request', recordIdentityRequest);
  const input = page.locator('#download-file');
  const result = page.locator('[data-download-result]');
  for (const field of ['submission_file', 'zip_file']) {
    await input.setInputFiles(path.join(root, card[field]));
    await page.waitForFunction(() => document.querySelector('[data-download-result]').dataset.state === 'match');
    assert.match(await result.innerText(), /grants no submission permission/);
    assert.match(await page.locator('.download-warning').first().innerText(), expectedVerdictBanner);
  }
  const altered = Buffer.from(fs.readFileSync(path.join(root, card.submission_file)));
  altered[500] ^= 1;
  await input.setInputFiles({name: 'altered.tif', mimeType: 'image/tiff', buffer: altered});
  await page.waitForFunction(() => document.querySelector('[data-download-result]').dataset.state === 'unknown');
  assert.match(await result.innerText(), /No format or submission approval/);
  await input.setInputFiles([]);
  await page.waitForFunction(() => document.querySelector('[data-download-result]').dataset.state === 'idle');
  assert.equal(await page.locator('[data-download-manifest]').getAttribute('aria-busy'), 'false');
  page.off('request', recordIdentityRequest);
  assert.deepEqual(identityRequests, [], 'Local identity checking must not upload or fetch data');
  await page.goto(base + '/sources.html', {waitUntil: 'networkidle'});
  await page.waitForFunction(() => document.querySelectorAll('#health-rows tr').length > 0);
  assert.match(await page.locator('#feed-observation').innerText(), /Not this candidate/);
  assert.match(await page.locator('#feed-status').innerText(), /Scientific claims last reviewed/);
  await page.goto(base + '/history.html', {waitUntil: 'networkidle'});
  const all = await page.locator('[data-search-row]:visible').count();
  await page.locator('#history-search').fill('h33');
  const filtered = await page.locator('[data-search-row]:visible').count();
  assert(filtered > 0 && filtered < all);
  await page.locator('#history-search').fill('not-a-real-candidate-name-g79');
  assert.equal(await page.locator('[data-search-row]:visible').count(), 0);
  assert.deepEqual(errors, [], 'Browser or HTTP errors');
  const report = {reviewed_utc: new Date().toISOString(), browser: await browser.version(), cases,
    downloaded_tiff_sha256: card.raster_sha256, clipboard_verified: true, download_identity_verified: {tiff: true, zip: true, altered_bytes_refused: true, reset: true, network_requests: 0}, feed_rendered: true, legacy_redirects_verified: 2,
    history_filter_verified: true, browser_errors: errors, passed: true,
    scope: 'Local HTTP/static website QA only; not organizer acceptance or geological evaluation.'};
  const reportRel = process.env.QA_REPORT_PATH || 'evidence/browser_review.json';
  const reportPath = path.isAbsolute(reportRel) ? reportRel : path.join(root, reportRel);
  fs.mkdirSync(path.dirname(reportPath), {recursive: true});
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
  await browser.close();
  console.log(JSON.stringify({passed: true, rendered_cases: cases.length, download_sha256: card.raster_sha256}, null, 2));
})().catch((error) => {console.error(error); process.exit(1);});
