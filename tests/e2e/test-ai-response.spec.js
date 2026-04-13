const { test, expect } = require('@playwright/test');
test('Check orcamento', async ({ page }) => {
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  await page.goto('http://localhost:8000/app/test-ai-orcamento.html');
});
