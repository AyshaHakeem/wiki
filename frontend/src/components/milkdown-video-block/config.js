/**
 * Video Block Configuration
 *
 * Provides configuration options for the video block component.
 */

import { $ctx } from '@milkdown/kit/utils';

/**
 * Default configuration for the video block
 */
export const defaultVideoBlockConfig = {
	// Placeholder text when no video is loaded
	placeholderText: 'Video',
	// Whether to show controls on the video player
	showControls: true,
	// Whether to autoplay (usually disabled for UX)
	autoplay: false,
	// Whether to loop the video
	loop: false,
	// Whether to mute the video by default
	muted: false,
	// Maximum width of the video player (CSS value)
	maxWidth: '100%',
};

/**
 * Video block configuration context
 */
export const videoBlockConfig = $ctx(
	defaultVideoBlockConfig,
	'videoBlockConfigCtx',
);
