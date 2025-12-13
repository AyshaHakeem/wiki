/**
 * Video Block Schema
 *
 * Defines the ProseMirror node schema for video blocks.
 * Uses the same markdown syntax as images: ![title](url.mp4)
 */

import { $nodeSchema } from '@milkdown/kit/utils';

/**
 * Video block node schema
 *
 * Attributes:
 * - src: The URL of the video file
 * - title: Optional title/alt text for the video
 */
export const videoBlockSchema = $nodeSchema('video-block', () => ({
	group: 'block',
	atom: true,
	isolating: true,
	marks: '',
	attrs: {
		src: { default: '' },
	},
	parseDOM: [
		{
			tag: 'video[src]',
			getAttrs: (dom) => ({
				src: dom.getAttribute('src') || '',
			}),
		},
		{
			tag: 'div[data-type="video-block"]',
			getAttrs: (dom) => ({
				src: dom.getAttribute('data-src') || '',
			}),
		},
	],
	toDOM: (node) => [
		'video',
		{
			src: node.attrs.src,
			controls: 'true',
			class: 'video-block',
		},
	],
	parseMarkdown: {
		match: (node) => node.type === 'video-block',
		runner: (state, node, type) => {
			const src = node.url || '';
			state.addNode(type, { src });
		},
	},
	toMarkdown: {
		match: (node) => node.type.name === 'video-block',
		runner: (state, node) => {
			const { src } = node.attrs;
			// Output as image markdown syntax: ![](url) on its own line
			state.write(`\n![](${src})\n`);
		},
	},
}));
