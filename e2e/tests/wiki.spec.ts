import { expect, test } from '@playwright/test';

test.describe('Wiki E2E Tests', () => {
	test('should display wiki spaces list', async ({ page }) => {
		await page.goto('/wiki');
		await page.waitForLoadState('networkidle');

		// Should be on wiki page, not redirected to login
		await expect(page).not.toHaveURL(/.*login.*/);

		// Should show the spaces list view with at least one space or the empty state
		const spacesContainer = page.locator(
			'[data-testid="wiki-spaces"], .wiki-spaces-list, a[href*="/wiki/spaces/"]',
		);
		await expect(spacesContainer.first()).toBeVisible();
	});

	test('should create a new wiki space via UI', async ({ page }) => {
		await page.goto('/wiki');
		await page.waitForLoadState('networkidle');

		// Click create new space button
		await page.click('button:has-text("New"), button:has-text("Create")');

		// Fill in space details in the dialog
		await page.waitForSelector('[role="dialog"], .modal', { state: 'visible' });

		const spaceName = `Test Space ${Date.now()}`;
		await page.fill('input[type="text"]', spaceName);

		// Submit the form
		await page.click('button:has-text("Create"), button[type="submit"]');

		// Wait for the dialog to close and page to update
		await page.waitForLoadState('networkidle');

		// Verify the space was created: check URL changed and space name visible in heading
		await expect(page).toHaveURL(/\/wiki\/spaces\//, { timeout: 10000 });
		await expect(page.getByRole('heading', { name: spaceName })).toBeVisible();
	});

	test('should navigate to space and create a wiki page', async ({ page }) => {
		await page.goto('/wiki');
		await page.waitForLoadState('networkidle');

		// Click on first available space - fail fast if no spaces exist
		const spaceLink = page.locator('a[href*="/wiki/spaces/"]').first();
		await expect(spaceLink).toBeVisible({
			timeout: 5000,
		});
		await spaceLink.click();
		await page.waitForLoadState('networkidle');

		// Should be in the space detail view with sidebar
		await expect(page.locator('aside')).toBeVisible();

		// Look for add/create page button in sidebar
		const addButton = page
			.locator(
				'button:has-text("Create First Page"), button:has-text("New Page")',
			)
			.first();
		await expect(addButton).toBeVisible({
			timeout: 5000,
		});
		await addButton.click();

		// Fill in the page title dialog
		const titleInput = page.getByLabel('Title');
		await expect(titleInput).toBeVisible({ timeout: 5000 });
		const pageTitle = `Test Page ${Date.now()}`;
		await titleInput.fill(pageTitle);

		// Click Create button in dialog (use role to be more specific)
		await page
			.getByRole('dialog')
			.getByRole('button', { name: 'Create' })
			.click();
		await page.waitForLoadState('networkidle');

		// Verify we're now in page editing mode - editor should be visible
		await expect(
			page.locator('.ProseMirror, [contenteditable="true"]'),
		).toBeVisible({ timeout: 10000 });

		// Verify page title is shown
		await expect(page.getByText(pageTitle).first()).toBeVisible();
	});

	test('should have New Page button in space sidebar', async ({ page }) => {
		// Navigate to wiki and click first space
		await page.goto('/wiki');
		await page.waitForLoadState('networkidle');

		const spaceLink = page.locator('a[href*="/wiki/spaces/"]').first();
		await expect(spaceLink).toBeVisible({ timeout: 5000 });
		await spaceLink.click();
		await page.waitForLoadState('networkidle');

		// Should have sidebar with space management buttons
		await expect(page.locator('aside')).toBeVisible();

		// Should have either "Create First Page" (empty space) or icon buttons for New Group/Page
		// The "New Page" button has title="New Page" and icon="file-plus"
		const createFirstPage = page.locator(
			'button:has-text("Create First Page")',
		);
		const newPageButton = page.locator('button[title="New Page"]');

		const hasCreateFirst = await createFirstPage
			.isVisible({ timeout: 2000 })
			.catch(() => false);
		const hasNewPage = await newPageButton
			.isVisible({ timeout: 2000 })
			.catch(() => false);

		expect(hasCreateFirst || hasNewPage).toBe(true);
	});

	test('should open wiki editor when clicking page in sidebar', async ({
		page,
	}) => {
		// Navigate to wiki and click first space
		await page.goto('/wiki');
		await page.waitForLoadState('networkidle');

		const spaceLink = page.locator('a[href*="/wiki/spaces/"]').first();
		await expect(spaceLink).toBeVisible({ timeout: 5000 });
		await spaceLink.click();
		await page.waitForLoadState('networkidle');

		// Check if there's an existing page (indicated by "Not Published" badge in tree)
		// or if we need to create one
		const pageTreeRow = page
			.locator('aside')
			.locator('.cursor-pointer')
			.first();
		const createFirstPage = page.locator(
			'button:has-text("Create First Page")',
		);

		if (await createFirstPage.isVisible({ timeout: 2000 }).catch(() => false)) {
			// No pages - create one
			await createFirstPage.click();
			await page.getByLabel('Title').fill(`Test Page ${Date.now()}`);
			await page
				.getByRole('dialog')
				.getByRole('button', { name: 'Create' })
				.click();
			await page.waitForLoadState('networkidle');
		} else {
			// Pages exist - click on first tree row
			await pageTreeRow.click();
			await page.waitForLoadState('networkidle');
		}

		// Editor should be visible (clicking a page opens it in edit mode)
		await expect(
			page.locator('.ProseMirror, [contenteditable="true"]'),
		).toBeVisible({ timeout: 10000 });

		// Verify save button is present (indicates edit mode)
		await expect(page.locator('button:has-text("Save")')).toBeVisible();
	});
});
