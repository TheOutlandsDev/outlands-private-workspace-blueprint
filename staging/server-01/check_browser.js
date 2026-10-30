// Native Chromium DOM checks for the disposable fictional staging runner.
const fs = require('fs');
const { chromium } = require('playwright');

function requireCheck(condition, label) {
  if (!condition) throw new Error(label);
  process.stdout.write(`PASS ${label}\n`);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  await context.route('**/*', (route) => {
    const url = new URL(route.request().url());
    if (url.protocol === 'data:' || url.protocol === 'blob:') return route.continue();
    const host = url.hostname;
    if (host === '127.0.0.1' || host === 'localhost') return route.continue();
    return route.abort();
  });
  try {
    const catalog = await context.newPage();
    const catalogResponse = await catalog.goto('http://127.0.0.1:13003/', { waitUntil: 'domcontentloaded' });
    requireCheck(catalogResponse && catalogResponse.status() === 200, 'Homepage browser response');
    await catalog.waitForFunction(() => document.body.innerText.includes('Open WebUI') &&
      document.body.innerText.includes('Grafana'), null, { timeout: 45000 });
    const catalogText = await catalog.locator('body').innerText();
    requireCheck(catalogText.includes('Open WebUI') && catalogText.includes('Grafana'),
      'fictional Homepage cards rendered');
    requireCheck((await catalog.title()).includes('FICTIONAL CATALOG'), 'fictional Homepage title rendered');
    const catalogLinks = await catalog.locator('a').evaluateAll((nodes) => nodes.map((node) => node.href));
    requireCheck(catalogLinks.includes('https://webui.example.invalid/'),
      'WebUI card remains fictional');
    requireCheck(catalogLinks.includes('https://metrics.example.invalid/'),
      'optional Grafana card remains fictional');

    const webui = await context.newPage();
    const webuiResponse = await webui.goto('http://127.0.0.1:13001/', { waitUntil: 'domcontentloaded' });
    requireCheck(webuiResponse && webuiResponse.status() === 200, 'Open WebUI browser response');
    await webui.locator('input[type="password"]').first().waitFor({ timeout: 60000 });
    requireCheck(!(await webui.locator('body').innerText()).includes('Fixture Owner'),
      'signed-out WebUI shows no fixture owner content');

    const grafana = await context.newPage();
    const grafanaResponse = await grafana.goto('http://127.0.0.1:13002/login', { waitUntil: 'domcontentloaded' });
    requireCheck(grafanaResponse && grafanaResponse.status() === 200, 'Grafana browser response');
    await grafana.locator('input[name="user"]').waitFor({ timeout: 45000 });
    await grafana.locator('input[name="password"]').waitFor({ timeout: 45000 });
    const password = fs.readFileSync(`${process.env.STAGE_ROOT}/metrics/.secrets/grafana-admin-password`, 'utf8').trim();
    await grafana.locator('input[name="user"]').fill('admin');
    await grafana.locator('input[name="password"]').fill(password);
    await grafana.locator('button[type="submit"]').first().click();
    await grafana.waitForURL((url) => !url.pathname.endsWith('/login'), { timeout: 45000 });
    await grafana.goto('http://127.0.0.1:13002/d/outlands-synthetic-source/synthetic-source-states',
      { waitUntil: 'domcontentloaded' });
    await grafana.getByText('Synthetic source states', { exact: true }).first().waitFor({ timeout: 60000 });
    requireCheck(true, 'native Grafana synthetic dashboard rendered');
  } finally {
    await browser.close();
  }
})().catch((error) => {
  process.stderr.write(`FAIL browser staging: ${error.message}\n`);
  process.exitCode = 1;
});
