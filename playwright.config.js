const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests_ui',

  // Mistral-7B tourne en local sur CPU : une réponse prend 100 à 300 s.
  // Le défaut de 30 s ferait échouer tous les tests conversationnels.
  timeout: 360_000,
  expect: { timeout: 10_000 },

  use: {
    baseURL: process.env.APP_BASE_URL || 'http://127.0.0.1:8000',
    headless: true,
    viewport: { width: 1280, height: 900 },
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },

  reporter: [['list'], ['html', { open: 'never' }]],

  // Un seul worker : le modèle est chargé une fois en mémoire et ne
  // supporte pas des requêtes concurrentes sur une machine CPU.
  workers: 1,
});
