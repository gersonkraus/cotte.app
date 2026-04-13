import { chromium } from '@playwright/test';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));

  await page.goto('http://localhost:8000/app/assistente-ia.html');
  await page.waitForLoadState('networkidle');

  await page.fill('#messageInput', 'crie um orcamento para Maria no valor de 500 reais para serviço de pintura');
  await page.click('#sendButton');

  await page.waitForTimeout(10000);

  await browser.close();
})();
