const { test, expect } = require('@playwright/test');

/**
 * Couche interface — tests end-to-end.
 *
 * Périmètre : cette suite vérifie que l'UTILISATEUR peut interagir avec
 * l'assistant. Elle ne juge PAS la justesse des réponses : une réponse
 * fausse mais correctement affichée doit faire passer ces tests. La
 * qualité du contenu relève de la couche tests_ai/.
 *
 * Adaptations liées au backend réel (Mistral-7B en local sur CPU) :
 *   - les réponses prennent 100 à 300 s : les tests conversationnels
 *     utilisent des délais explicites (voir ANSWER_TIMEOUT)
 *   - aucune assertion sur le CONTENU de la réponse : le modèle est
 *     génératif, sa formulation varie d'une exécution à l'autre
 *   - ciblage par data-testid plutôt que par classes CSS, pour que les
 *     tests survivent aux évolutions de style
 */

const ANSWER_TIMEOUT = 300_000;

test.describe('Interface — scénarios sans appel au modèle (rapides)', () => {
  test('état initial : historique vide, bouton désactivé', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByTestId('message-input')).toBeVisible();
    await expect(page.getByTestId('empty-state')).toBeVisible();
    await expect(page.getByTestId('send-button')).toBeDisabled();
  });

  test('le bouton s’active dès qu’une question est saisie', async ({ page }) => {
    await page.goto('/');
    await page.getByTestId('message-input').fill('How do I list the accounts of a bank?');
    await expect(page.getByTestId('send-button')).toBeEnabled();
  });

  test('validation : espaces seuls, message long, caractères spéciaux', async ({ page }) => {
    await page.goto('/');
    const input = page.getByTestId('message-input');
    const button = page.getByTestId('send-button');

    await expect(button).toBeDisabled();

    await input.fill('   ');
    await expect(button).toBeDisabled();

    await input.fill('A'.repeat(5000));
    await expect(button).toBeEnabled();

    await input.fill('💡 <b>test</b> & special');
    await expect(button).toBeEnabled();
  });

  test('gestion d’erreur : message clair si le backend échoue', async ({ page }) => {
    // La route est interceptée : aucun appel réel au modèle, test rapide.
    await page.route('**/api/chat', (route) =>
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Service temporarily unavailable. Please try again.' }),
      }),
    );

    await page.goto('/');
    await page.getByTestId('message-input').fill('Question triggering an error');
    await page.getByTestId('send-button').click();

    await expect(page.getByTestId('message-error')).toContainText(/unavailable|error/i);
  });

  test('l’état vide disparaît dès le premier message', async ({ page }) => {
    await page.route('**/api/chat', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ answer: 'Stubbed answer', sources: [] }),
      }),
    );

    await page.goto('/');
    await page.getByTestId('message-input').fill('First question');
    await page.getByTestId('send-button').click();

    await expect(page.getByTestId('empty-state')).toHaveCount(0);
    await expect(page.getByTestId('message-question')).toContainText('First question');
  });

  test('historique : plusieurs échanges conservés dans l’ordre', async ({ page }) => {
    await page.route('**/api/chat', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ answer: 'Stubbed answer', sources: [] }),
      }),
    );

    await page.goto('/');
    const input = page.getByTestId('message-input');
    const button = page.getByTestId('send-button');

    await input.fill('First question');
    await button.click();
    await expect(page.getByTestId('message-question')).toHaveCount(1);

    await input.fill('Second question');
    await button.click();

    const questions = page.getByTestId('message-question');
    await expect(questions).toHaveCount(2);
    await expect(questions.nth(0)).toContainText('First question');
    await expect(questions.nth(1)).toContainText('Second question');
  });
});

test.describe('Interface — parcours complet avec le modèle réel (lent)', () => {
  test.describe.configure({ timeout: ANSWER_TIMEOUT + 60_000 });

  test('parcours nominal : question envoyée, réponse affichée avec ses sources', async ({ page }) => {
    await page.goto('/');

    await page.getByTestId('message-input').fill('How do I list the accounts of a bank?');
    await page.getByTestId('send-button').click();

    // Pendant la génération : indicateur visible, champ vidé et désactivé
    await expect(page.getByTestId('loading-indicator')).toBeVisible();
    await expect(page.getByTestId('message-input')).toHaveValue('');
    await expect(page.getByTestId('message-input')).toBeDisabled();

    // Une réponse NON VIDE doit apparaître. Son contenu n'est pas évalué ici.
    const answer = page.getByTestId('message-answer');
    await expect(answer).toBeVisible({ timeout: ANSWER_TIMEOUT });
    await expect(answer).not.toBeEmpty();

    // Traçabilité : les endpoints utilisés sont affichés à l'utilisateur
    await expect(page.getByTestId('message-sources')).toBeVisible();

    // Retour à l'état interactif
    await expect(page.getByTestId('loading-indicator')).toBeHidden();
    await expect(page.getByTestId('message-input')).toBeEnabled();
  });
});
