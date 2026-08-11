const { test, expect } = require('@playwright/test');

test('parcours nominal : question visible et réponse affichée', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByTestId('message-input')).toBeVisible();

  await page.getByTestId('message-input').fill('Quel est le rôle d’un endpoint OBP ?');
  await page.getByRole('button', { name: 'Envoyer' }).click();

  await expect(page.locator('.message.user')).toContainText('Quel est le rôle d’un endpoint OBP ?');
  await expect(page.locator('.message.assistant')).toContainText(/Voici une réponse|documentation OBP/i);
});

test('interface : bouton désactivé, indicateur de chargement et champ vidé', async ({ page }) => {
  await page.goto('/');
  const input = page.getByTestId('message-input');
  const button = page.getByRole('button', { name: 'Envoyer' });

  await expect(button).toBeDisabled();
  await input.fill('Test de chargement');
  await expect(button).toBeEnabled();

  await button.click();
  await expect(page.locator('#typingIndicator')).toBeVisible();
  await expect(input).toHaveValue('');
  await expect(page.locator('.message.user')).toContainText('Test de chargement');
});

test('validation des entrées : champ vide, message long, caractères spéciaux', async ({ page }) => {
  await page.goto('/');
  const input = page.getByTestId('message-input');
  const button = page.getByRole('button', { name: 'Envoyer' });

  await expect(button).toBeDisabled();
  await input.fill('   ');
  await expect(button).toBeDisabled();

  const longMessage = 'A'.repeat(5000);
  await input.fill(longMessage);
  await expect(button).toBeEnabled();

  await input.fill('💡 <b>test</b> & spécial');
  await button.click();
  await expect(page.locator('.message.user')).toContainText('💡 <b>test</b> & spécial');
});

test('gestion d’erreur : message clair si le backend échoue', async ({ page }) => {
  await page.route('**/api/chat', route => route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ error: 'Le service est indisponible pour le moment.' }) }));
  await page.goto('/');
  await page.getByTestId('message-input').fill('Question qui déclenche une erreur');
  await page.getByRole('button', { name: 'Envoyer' }).click();

  await expect(page.locator('.message.error')).toContainText(/indisponible|erreur/i);
});

test('persistance de l’historique : plusieurs questions gardées dans l’ordre', async ({ page }) => {
  await page.goto('/');
  const input = page.getByTestId('message-input');
  await input.fill('Première question');
  await page.getByRole('button', { name: 'Envoyer' }).click();
  await expect(page.locator('.message.user')).toContainText('Première question');

  await input.fill('Deuxième question');
  await page.getByRole('button', { name: 'Envoyer' }).click();

  const userMessages = page.locator('.message.user');
  await expect(userMessages).toHaveCount(2);
  await expect(userMessages.nth(0)).toContainText('Première question');
  await expect(userMessages.nth(1)).toContainText('Deuxième question');
});
