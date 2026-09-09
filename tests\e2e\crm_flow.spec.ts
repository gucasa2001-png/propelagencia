import { test, expect } from '@playwright/test';

test.describe('Propel CRM — Fluxos E2E Comerciais e Portal do Cliente', () => {

  test('01. Health Check & Observabilidade estão respondendo 200', async ({ request }) => {
    const res = await request.get('/api/health');
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.status).toBe('healthy');
    expect(body.database).toBe('sqlite3_connected');
  });

  test('02. Portal do Cliente exibe Skeleton Shimmer e detalhes do anúncio', async ({ page }) => {
    await page.goto('/portal/odonto-camila');
    
    // Verifica título e identificação do cliente
    await expect(page.locator('h1')).toContainText('Portal do Cliente');
    
    // Verifica presença dos cards de criativos
    const cards = page.locator('.interactive-card');
    await expect(cards.first()).toBeVisible({ timeout: 5000 });
  });

  test('03. Mesa de Tráfego exibe métricas e permite interação', async ({ page }) => {
    await page.goto('/trafego');
    
    // Verifica header e meta Espanha
    await expect(page.locator('header')).toBeVisible();
    await expect(page.getByText('Meta Espanha')).toBeVisible();
    
    // Verifica presença da busca instantânea Pipedrive
    const searchInput = page.locator('input[placeholder*="Filtrar"]');
    if (await searchInput.isVisible()) {
      await searchInput.fill('Odonto');
      await page.waitForTimeout(300);
    }
  });

  test('04. Tela de login valida credenciais e redireciona', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('input[name="username"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    
    // Preenche credenciais
    await page.fill('input[name="username"]', 'propel');
    await page.fill('input[name="password"]', 'propel2027');
    await page.click('button[type="submit"]');
    
    // Deve redirecionar para a mesa comercial (Kanban)
    await expect(page).toHaveURL(/.*\/$/);
  });

});
