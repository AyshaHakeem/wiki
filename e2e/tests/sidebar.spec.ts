import { expect, test } from '@playwright/test';

/**
 * Tests for the public-facing wiki sidebar.
 * These tests verify that the sidebar correctly displays only published pages
 * and that client-side navigation works properly.
 */
test.describe('Public Sidebar', () => {
	test.describe('Published Pages Visibility', () => {
		test('should only display published pages in the public sidebar', async ({
			page,
		}) => {
			await page.setViewportSize({ width: 1100, height: 900 });

			// Navigate to wiki and click first space
			await page.goto('/wiki');
			await page.waitForLoadState('networkidle');

			const spaceLink = page.locator('a[href*="/wiki/spaces/"]').first();
			await expect(spaceLink).toBeVisible({ timeout: 5000 });
			await spaceLink.click();
			await page.waitForLoadState('networkidle');

			// Create a published page inside the space
			const createFirstPage = page.locator(
				'button:has-text("Create First Page")',
			);
			const newPageButton = page.locator('button[title="New Page"]');

			const publishedPageTitle = `Published Page ${Date.now()}`;

			if (
				await createFirstPage.isVisible({ timeout: 2000 }).catch(() => false)
			) {
				await createFirstPage.click();
			} else {
				await newPageButton.click();
			}

			await page.getByLabel('Title').fill(publishedPageTitle);
			await page
				.getByRole('dialog')
				.getByRole('button', { name: 'Create' })
				.click();
			await page.waitForLoadState('networkidle');

			// Wait for editor and add content
			const editor = page.locator('.ProseMirror, [contenteditable="true"]');
			await expect(editor).toBeVisible({ timeout: 10000 });
			await editor.click();
			await page.keyboard.type('This is published content.');

			// Save the page
			await page.click('button:has-text("Save")');
			await page.waitForLoadState('networkidle');

			// Publish the page
			await page
				.locator(
					'button:has-text("Save") ~ button, button:has-text("Save") + * button',
				)
				.first()
				.click();
			await page.waitForSelector('[role="menuitem"]', {
				state: 'visible',
				timeout: 5000,
			});
			await page.getByRole('menuitem', { name: 'Publish' }).click();
			await page.waitForLoadState('networkidle');
			await expect(page.locator('text=Published').first()).toBeVisible({
				timeout: 10000,
			});

			// Create an unpublished page
			const unpublishedPageTitle = `Unpublished Page ${Date.now()}`;
			await page.locator('button[title="New Page"]').click();
			await page.getByLabel('Title').fill(unpublishedPageTitle);
			await page
				.getByRole('dialog')
				.getByRole('button', { name: 'Create' })
				.click();
			await page.waitForLoadState('networkidle');

			// Wait for editor and add content
			await expect(editor).toBeVisible({ timeout: 10000 });
			await editor.click();
			await page.keyboard.type('This is unpublished content.');

			// Save but do NOT publish
			await page.click('button:has-text("Save")');
			await page.waitForLoadState('networkidle');
			await page.waitForTimeout(1000);

			// Go back to the published page in the sidebar
			const publishedPageInSidebar = page
				.locator('aside')
				.locator(`text=${publishedPageTitle}`)
				.first();
			await publishedPageInSidebar.click();
			await page.waitForLoadState('networkidle');

			// Click View Page to go to public route
			const viewPageButton = page.locator('button:has-text("View Page")');
			await expect(viewPageButton).toBeVisible({ timeout: 5000 });

			const [publicPage] = await Promise.all([
				page.context().waitForEvent('page'),
				viewPageButton.click(),
			]);

			await publicPage.waitForLoadState('networkidle');
			await publicPage.setViewportSize({ width: 1100, height: 900 });

			// Verify the sidebar is visible on the public page
			const sidebar = publicPage.locator('.wiki-sidebar');
			await expect(sidebar).toBeVisible({ timeout: 10000 });

			// Verify the published page appears in the sidebar
			const publishedLink = sidebar.locator(
				`.wiki-link:has-text("${publishedPageTitle}")`,
			);
			await expect(publishedLink).toBeVisible({ timeout: 5000 });

			// Verify the unpublished page does NOT appear in the sidebar
			const unpublishedLink = sidebar.locator(
				`.wiki-link:has-text("${unpublishedPageTitle}")`,
			);
			await expect(unpublishedLink).not.toBeVisible();

			await publicPage.close();
		});
	});

	test.describe('Sidebar Navigation', () => {
		test('should update content, URL, active state, and metadata when clicking sidebar links', async ({
			page,
		}) => {
			await page.setViewportSize({ width: 1100, height: 900 });

			// Navigate to wiki and click first space
			await page.goto('/wiki');
			await page.waitForLoadState('networkidle');

			const spaceLink = page.locator('a[href*="/wiki/spaces/"]').first();
			await expect(spaceLink).toBeVisible({ timeout: 5000 });
			await spaceLink.click();
			await page.waitForLoadState('networkidle');

			// Create first published page
			const firstPageTitle = `First Nav Page ${Date.now()}`;
			const createFirstPage = page.locator(
				'button:has-text("Create First Page")',
			);
			const newPageButton = page.locator('button[title="New Page"]');

			if (
				await createFirstPage.isVisible({ timeout: 2000 }).catch(() => false)
			) {
				await createFirstPage.click();
			} else {
				await newPageButton.click();
			}

			await page.getByLabel('Title').fill(firstPageTitle);
			await page
				.getByRole('dialog')
				.getByRole('button', { name: 'Create' })
				.click();
			await page.waitForLoadState('networkidle');

			// Add content and save
			const editor = page.locator('.ProseMirror, [contenteditable="true"]');
			await expect(editor).toBeVisible({ timeout: 10000 });
			await editor.click();
			await page.keyboard.type('First page content here.');
			await page.click('button:has-text("Save")');
			await page.waitForLoadState('networkidle');

			// Publish first page
			await page
				.locator(
					'button:has-text("Save") ~ button, button:has-text("Save") + * button',
				)
				.first()
				.click();
			await page.waitForSelector('[role="menuitem"]', {
				state: 'visible',
				timeout: 5000,
			});
			await page.getByRole('menuitem', { name: 'Publish' }).click();
			await page.waitForLoadState('networkidle');
			await expect(page.locator('text=Published').first()).toBeVisible({
				timeout: 10000,
			});

			// Create second published page
			const secondPageTitle = `Second Nav Page ${Date.now()}`;
			await page.locator('button[title="New Page"]').click();
			await page.getByLabel('Title').fill(secondPageTitle);
			await page
				.getByRole('dialog')
				.getByRole('button', { name: 'Create' })
				.click();
			await page.waitForLoadState('networkidle');

			// Add different content and save
			await expect(editor).toBeVisible({ timeout: 10000 });
			await editor.click();
			await page.keyboard.type('Second page different content.');
			await page.click('button:has-text("Save")');
			await page.waitForLoadState('networkidle');

			// Publish second page
			await page
				.locator(
					'button:has-text("Save") ~ button, button:has-text("Save") + * button',
				)
				.first()
				.click();
			await page.waitForSelector('[role="menuitem"]', {
				state: 'visible',
				timeout: 5000,
			});
			await page.getByRole('menuitem', { name: 'Publish' }).click();
			await page.waitForLoadState('networkidle');
			await expect(page.locator('text=Published').first()).toBeVisible({
				timeout: 10000,
			});

			// Go to the first page and open public view
			const firstPageInSidebar = page
				.locator('aside')
				.locator(`text=${firstPageTitle}`)
				.first();
			await firstPageInSidebar.click();
			await page.waitForLoadState('networkidle');

			const viewPageButton = page.locator('button:has-text("View Page")');
			await expect(viewPageButton).toBeVisible({ timeout: 5000 });

			const [publicPage] = await Promise.all([
				page.context().waitForEvent('page'),
				viewPageButton.click(),
			]);

			await publicPage.waitForLoadState('networkidle');
			await publicPage.setViewportSize({ width: 1100, height: 900 });

			// Verify initial state on first page
			const pageTitle = publicPage.locator('#wiki-page-title');
			await expect(pageTitle).toHaveText(firstPageTitle, { timeout: 10000 });

			const pageContent = publicPage.locator('#wiki-content');
			await expect(pageContent).toContainText('First page content');

			const initialUrl = publicPage.url();

			// Verify first page link is active
			const sidebar = publicPage.locator('.wiki-sidebar');
			const firstPageLink = sidebar.locator(
				`.wiki-link:has-text("${firstPageTitle}")`,
			);
			await expect(firstPageLink).toHaveAttribute('aria-current', 'page', {
				timeout: 5000,
			});

			// Verify last updated timestamp is visible
			const lastUpdated = publicPage.locator('#wiki-last-updated');
			await expect(lastUpdated).toBeVisible();
			await expect(lastUpdated).toContainText('Last updated');

			// Get initial edit link href
			const editLinks = publicPage.locator('#wiki-edit-link');
			const initialEditHref = await editLinks.first().getAttribute('href');

			// Click the second page link in sidebar
			const secondPageLink = sidebar.locator(
				`.wiki-link:has-text("${secondPageTitle}")`,
			);
			await expect(secondPageLink).toBeVisible({ timeout: 5000 });
			await secondPageLink.click();
			await publicPage.waitForTimeout(500);

			// Verify content updated
			await expect(pageTitle).toHaveText(secondPageTitle, { timeout: 10000 });
			await expect(pageContent).toContainText('Second page different content');

			// Verify URL updated (client-side navigation)
			expect(publicPage.url()).not.toEqual(initialUrl);

			// Verify second page link is now active
			await expect(secondPageLink).toHaveAttribute('aria-current', 'page', {
				timeout: 5000,
			});

			// Verify first page link is no longer active
			const firstPageAriaCurrent =
				await firstPageLink.getAttribute('aria-current');
			expect(firstPageAriaCurrent).not.toBe('page');

			// Verify edit link updated
			const updatedEditHref = await editLinks.first().getAttribute('href');
			expect(updatedEditHref).not.toEqual(initialEditHref);

			// Verify last updated is still visible
			await expect(lastUpdated).toBeVisible();
			await expect(lastUpdated).toContainText('Last updated');

			await publicPage.close();
		});
	});
});
