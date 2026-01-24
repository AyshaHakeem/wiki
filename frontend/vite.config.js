import path from 'node:path';
import vue from '@vitejs/plugin-vue';
import { defineConfig } from 'vite';

/**
 * Custom plugin to handle TipTap v3 shimming for frappe-ui compatibility
 *
 * Problems solved:
 * 1. @tiptap/vue-3 no longer exports BubbleMenu/FloatingMenu (moved to /menus subpath)
 * 2. @tiptap/extension-table no longer has default export (now named export)
 *
 * Solution: Use ?original suffix to bypass alias and resolve to actual node_modules package.
 */
function tiptapShimsPlugin() {
	const shimDir = path.resolve(__dirname, 'src/lib/tiptap-shims');
	const vue3ShimPath = path.resolve(__dirname, 'src/lib/tiptap-vue-3-shim.js');
	const tableShimPath = path.resolve(shimDir, 'extension-table.js');

	// All shim files that should bypass the aliasing
	const shimFiles = [
		vue3ShimPath,
		tableShimPath,
		path.resolve(shimDir, 'extension-table-cell.js'),
		path.resolve(shimDir, 'extension-table-header.js'),
		path.resolve(shimDir, 'extension-table-row.js'),
	];

	return {
		name: 'tiptap-shims',
		enforce: 'pre',
		async resolveId(source, importer, options) {
			// Handle ?original imports - bypass alias and resolve to node_modules
			if (source.includes('?original')) {
				const packageName = source.replace('?original', '');
				const resolved = await this.resolve(packageName, importer, {
					...options,
					skipSelf: true,
				});
				return resolved;
			}

			// Don't apply aliases when importing from shim files themselves
			if (importer && shimFiles.includes(importer)) {
				return null;
			}

			// Alias exact @tiptap/vue-3 to our shim (not subpaths like /menus)
			if (source === '@tiptap/vue-3') {
				return vue3ShimPath;
			}

			// Alias @tiptap/extension-table to our shim (provides default export)
			if (source === '@tiptap/extension-table') {
				return tableShimPath;
			}

			return null;
		},
	};
}

// Conditionally import frappe-ui plugin
async function getFrappeUIPlugin(isDev) {
	if (isDev) {
		try {
			const module = await import(
				path.resolve(__dirname, '../../frappe-ui/vite/index.js')
			);
			return module.default;
		} catch (error) {
			console.warn(
				'Local frappe-ui not found, falling back to npm package:',
				error.message,
			);
			// Fall back to npm package if local import fails
			const module = await import('frappe-ui/vite');
			return module.default;
		}
	}
	const module = await import('frappe-ui/vite');
	return module.default;
}

// https://vitejs.dev/config/
export default defineConfig(async ({ command, mode }) => {
	const isDev = process.env.NODE_ENV !== 'production';
	const frappeui = await getFrappeUIPlugin(isDev);

	const config = {
		plugins: [
			tiptapShimsPlugin(),
			frappeui({
				frappeProxy: {
					port: 8080,
					source: '^/(app|login|api|assets|files|private|razorpay_checkout)',
				},
				jinjaBootData: true,
				lucideIcons: true,
				buildConfig: {
					indexHtmlPath: '../wiki/www/wiki.html',
					emptyOutDir: true,
					sourcemap: true,
				},
			}),
			vue(),
		],
		build: {
			chunkSizeWarningLimit: 1500,
			outDir: '../wiki/public/frontend',
			emptyOutDir: true,
			target: 'es2015',
			sourcemap: true,
		},
		resolve: {
			alias: {
				'@': path.resolve(__dirname, 'src'),
				'tailwind.config.js': path.resolve(__dirname, 'tailwind.config.js'),
				// Note: @tiptap/vue-3 shimming is handled by tiptapVue3ShimPlugin above
				// Shims for TipTap v3 table extensions (frappe-ui expects default exports)
				'@tiptap/extension-table-cell': path.resolve(
					__dirname,
					'src/lib/tiptap-shims/extension-table-cell.js',
				),
				'@tiptap/extension-table-header': path.resolve(
					__dirname,
					'src/lib/tiptap-shims/extension-table-header.js',
				),
				'@tiptap/extension-table-row': path.resolve(
					__dirname,
					'src/lib/tiptap-shims/extension-table-row.js',
				),
			},
		},
		optimizeDeps: {
			include: ['feather-icons', 'highlight.js/lib/core', 'interactjs'],
			exclude: ['@tiptap/vue-3'],
		},
		server: {
			allowedHosts: true,
		},
	};

	// Add local frappe-ui alias only in development if the local frappe-ui exists
	if (isDev) {
		try {
			// Check if the local frappe-ui directory exists
			const fs = await import('node:fs');
			const localFrappeUIPath = path.resolve(__dirname, 'frappe-ui');
			if (fs.existsSync(localFrappeUIPath)) {
				config.resolve.alias['frappe-ui'] = localFrappeUIPath;
			} else {
				console.warn('Local frappe-ui directory not found, using npm package');
			}
		} catch (error) {
			console.warn(
				'Error checking for local frappe-ui, using npm package:',
				error.message,
			);
		}
	}

	return config;
});
