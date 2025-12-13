/**
 * Remark Plugin for Video Block
 *
 * Transforms image nodes with video URLs into video-block nodes
 * during markdown parsing.
 */

import { $remark } from '@milkdown/kit/utils';
import { visit } from 'unist-util-visit';

/**
 * Video extensions that should be rendered as video players
 */
const VIDEO_EXTENSIONS = [
	'.mp4',
	'.webm',
	'.ogg',
	'.mov',
	'.avi',
	'.mkv',
	'.m4v',
];

/**
 * Check if a URL points to a video file
 */
function isVideoUrl(url) {
	if (!url || typeof url !== 'string') return false;
	const lowerUrl = url.toLowerCase();
	return VIDEO_EXTENSIONS.some((ext) => lowerUrl.endsWith(ext));
}

/**
 * Remark plugin that transforms image nodes with video URLs
 * into video-block nodes.
 *
 * This allows using the standard image syntax for videos:
 * ![My Video](./path/to/video.mp4)
 */
export const remarkVideoBlockPlugin = $remark(
	'remarkVideoBlockPlugin',
	() => () => (tree) => {
		visit(tree, 'image', (node, index, parent) => {
			if (!node.url || !isVideoUrl(node.url)) {
				return;
			}

			// Transform the image node into a video-block node
			node.type = 'video-block';
			node.data = {
				hName: 'video-block',
			};
		});
	},
);
