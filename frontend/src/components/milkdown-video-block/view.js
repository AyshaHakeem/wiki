/**
 * Video Block View
 *
 * Connects the video-block schema to the Vue component for rendering.
 */

import { $view } from '@milkdown/kit/utils';
import { createApp, h, shallowRef } from 'vue';
import VideoBlockComponent from './VideoBlock.vue';
import { defaultVideoBlockConfig, videoBlockConfig } from './config.js';
import { videoBlockSchema } from './schema.js';

/**
 * Video block node view
 *
 * Creates a ProseMirror NodeView that renders the Vue component.
 */
export const videoBlockView = $view(videoBlockSchema.node, (ctx) => {
	// Get config from context, fallback to defaults
	let config = defaultVideoBlockConfig;
	try {
		config = ctx.get(videoBlockConfig.key) || defaultVideoBlockConfig;
	} catch (e) {
		// Config context not available, use defaults
	}

	return (initialNode, view, getPos) => {
		const dom = document.createElement('div');
		dom.className = 'milkdown-video-block-view';
		dom.setAttribute('data-type', 'video-block');

		// Track selection state and current node
		let selected = false;
		let currentNode = initialNode;

		// Create reactive props
		const props = shallowRef({
			src: initialNode.attrs.src || '',
			selected: false,
			config: config,
		});

		// Use Vue's createApp for rendering
		let app = null;
		let mounted = false;

		const mountComponent = () => {
			if (mounted) return;

			// Use Vue 3's render function approach
			app = createApp({
				render() {
					return h(VideoBlockComponent, {
						...props.value,
						'onUpdate:src': (newSrc) => {
							if (typeof getPos === 'function') {
								const pos = getPos();
								if (pos != null) {
									view.dispatch(
										view.state.tr.setNodeMarkup(pos, undefined, {
											...currentNode.attrs,
											src: newSrc,
										}),
									);
								}
							}
						},
					});
				},
			});
			app.mount(dom);
			mounted = true;
		};

		// Mount the component
		mountComponent();

		return {
			dom,
			update: (updatedNode) => {
				if (updatedNode.type !== currentNode.type) {
					return false;
				}
				currentNode = updatedNode;
				props.value = {
					...props.value,
					src: currentNode.attrs.src || '',
				};
				// Force re-render
				if (app) {
					app._instance?.proxy?.$forceUpdate?.();
				}
				return true;
			},
			selectNode: () => {
				selected = true;
				props.value = { ...props.value, selected: true };
				dom.classList.add('ProseMirror-selectednode');
			},
			deselectNode: () => {
				selected = false;
				props.value = { ...props.value, selected: false };
				dom.classList.remove('ProseMirror-selectednode');
			},
			destroy: () => {
				if (app) {
					app.unmount();
					app = null;
				}
				mounted = false;
			},
			stopEvent: (event) => {
				// Allow clicks on the video controls
				return event.target.tagName === 'VIDEO';
			},
			ignoreMutation: () => true,
		};
	};
});
