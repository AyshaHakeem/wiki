/**
 * Milkdown Video Block Plugin
 *
 * This plugin provides a custom video block component for Milkdown editor.
 * It transforms image syntax with video URLs (like GitHub does) into
 * an HTML5 video player in the editor.
 *
 * Markdown syntax: ![title](video-url.mp4)
 * The plugin detects video URLs by file extension and renders them as video players.
 */

import { videoBlockConfig } from './config.js';
import { remarkVideoBlockPlugin } from './remark-plugin.js';
import { videoBlockSchema } from './schema.js';
import { videoBlockView } from './view.js';

export { videoBlockConfig } from './config.js';
export { remarkVideoBlockPlugin } from './remark-plugin.js';
export { videoBlockSchema } from './schema.js';
export { videoBlockView } from './view.js';

/**
 * Video extensions that should be rendered as video players
 */
export const VIDEO_EXTENSIONS = [
	'.mp4',
	'.webm',
	'.ogg',
	'.mov',
	'.avi',
	'.mkv',
	'.m4v',
];

/**
 * Check if a URL is a video URL based on file extension
 */
export function isVideoUrl(url) {
	if (!url) return false;
	const lowerUrl = url.toLowerCase();
	return VIDEO_EXTENSIONS.some((ext) => lowerUrl.endsWith(ext));
}

/**
 * All plugins for the video block component
 * Use with: editor.use(videoBlockComponent)
 */
export const videoBlockComponent = [
	remarkVideoBlockPlugin,
	videoBlockSchema,
	videoBlockView,
	videoBlockConfig,
].flat();
