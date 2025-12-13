<script setup>
/**
 * VideoBlock Component
 * 
 * Renders a video with HTML5 video player in the Milkdown editor.
 * Supports common video formats: mp4, webm, ogg, mov, avi, mkv, m4v
 */

import { computed } from 'vue'

const props = defineProps({
    src: {
        type: String,
        default: '',
    },
    selected: {
        type: Boolean,
        default: false,
    },
    config: {
        type: Object,
        default: () => ({}),
    },
})

const emit = defineEmits(['update:src'])

// Get video MIME type from extension
const videoType = computed(() => {
    const url = props.src.toLowerCase()
    if (url.endsWith('.mp4') || url.endsWith('.m4v')) return 'video/mp4'
    if (url.endsWith('.webm')) return 'video/webm'
    if (url.endsWith('.ogg')) return 'video/ogg'
    if (url.endsWith('.mov')) return 'video/quicktime'
    if (url.endsWith('.avi')) return 'video/x-msvideo'
    if (url.endsWith('.mkv')) return 'video/x-matroska'
    return 'video/mp4' // Default fallback
})

const showControls = computed(() => props.config.showControls !== false)
const autoplay = computed(() => props.config.autoplay === true)
const loop = computed(() => props.config.loop === true)
const muted = computed(() => props.config.muted === true || props.config.autoplay === true)
const maxWidth = computed(() => props.config.maxWidth || '100%')
</script>

<template>
    <div
        class="video-block-wrapper"
        :class="{ 'is-selected': selected }"
        contenteditable="false"
    >
        <div v-if="!src" class="video-placeholder">
            <div class="placeholder-content">
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                >
                    <polygon points="23 7 16 12 23 17 23 7" />
                    <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
                </svg>
                <span>{{ config.placeholderText || 'Video' }}</span>
            </div>
        </div>
        <div v-else class="video-container" :style="{ maxWidth }">
            <video
                :src="src"
                :controls="showControls"
                :autoplay="autoplay"
                :loop="loop"
                :muted="muted"
                preload="metadata"
                class="video-player"
            >
                <source :src="src" :type="videoType" />
                Your browser does not support the video tag.
            </video>
        </div>
    </div>
</template>

<style scoped>
.video-block-wrapper {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin: 1rem 0;
    padding: 0.5rem;
    border-radius: 8px;
    transition: background-color 0.2s ease;
}

.video-block-wrapper.is-selected {
    background-color: rgba(59, 130, 246, 0.1);
    outline: 2px solid rgba(59, 130, 246, 0.5);
}

.video-placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    min-height: 200px;
    background-color: #f3f4f6;
    border: 2px dashed #d1d5db;
    border-radius: 8px;
    cursor: pointer;
}

.placeholder-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    color: #6b7280;
}

.placeholder-content svg {
    width: 48px;
    height: 48px;
    opacity: 0.5;
}

.video-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100%;
}

.video-player {
    width: 100%;
    max-width: 100%;
    border-radius: 8px;
    background-color: #000;
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
    .video-placeholder {
        background-color: #374151;
        border-color: #4b5563;
    }

    .placeholder-content {
        color: #9ca3af;
    }
}
</style>
