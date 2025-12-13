<template>
    <div class="wiki-editor-container">
        <!-- Milkdown Editor -->
        <div class="wiki-milkdown-editor" @keydown="handleContentChange" @input="handleContentChange">
            <Milkdown autofocus />
        </div>
    </div>
</template>

<script setup>
import "@milkdown/crepe/theme/common/style.css";
import "@milkdown/crepe/theme/frame.css";

import { ref, onUnmounted } from "vue";
import { Crepe } from "@milkdown/crepe";
import { Milkdown, useEditor, useInstance } from "@milkdown/vue";
import { upload, uploadConfig } from "@milkdown/kit/plugin/upload";
import { useFileUpload, toast } from "frappe-ui";
import { videoBlockComponent } from "./milkdown-video-block/index.js";

const props = defineProps({
    content: {
        type: String,
        default: "",
    },
    saving: {
        type: Boolean,
        default: false,
    }
});

const emit = defineEmits(['save']);
const hasUnsavedChanges = ref(false);
const lastSavedAt = ref(null);
const lastSavedContent = ref(props.content || "");

// Autosave configuration
const AUTOSAVE_DELAY = 2000; // 3 seconds debounce
let autosaveTimer = null;

// File upload composable from frappe-ui
const fileUploader = useFileUpload();

/**
 * Upload image to Frappe and return the file URL
 * This is used by Milkdown's ImageBlock feature
 */
async function uploadImage(file) {
    try {
        const result = await fileUploader.upload(file, {
            private: false,
            optimize: true
        });
        
        toast.success('Image uploaded successfully');
        
        // Return the file URL for the editor to use
        return result.file_url;
    } catch (error) {
        console.error('Image upload failed:', error);
        toast.error('Failed to upload image');
        throw error;
    }
}

/**
 * Custom uploader for drag-and-drop file uploads
 * This is used by @milkdown/plugin-upload for handling dropped files
 */
async function dragDropUploader(files, schema) {
    const nodes = [];
    
    for (let i = 0; i < files.length; i++) {
        const file = files.item(i);
        if (!file) continue;
        
        const isImage = file.type.includes('image');
        const isVideo = file.type.includes('video');
        
        // Only handle image and video files
        if (!isImage && !isVideo) {
            toast.warning(`Skipped unsupported file: ${file.name}`);
            continue;
        }
        
        try {
            const result = await fileUploader.upload(file, {
                private: false,
                optimize: isImage // Only optimize images, not videos
            });
            
            if (isImage) {
                // Create an image node for image files
                const imageNode = schema.nodes.image.createAndFill({
                    src: result.file_url,
                    alt: file.name
                });
                
                if (imageNode) {
                    nodes.push(imageNode);
                }
            } else if (isVideo) {
                // Create a video-block node for video files
                // Uses our custom video-block schema that renders as HTML video player
                const videoNode = schema.nodes['video-block']?.createAndFill({
                    src: result.file_url
                });
                
                if (videoNode) {
                    nodes.push(videoNode);
                } else {
                    // Fallback: if video-block not available, use image node
                    // (will display as broken image but preserves the URL)
                    const imageNode = schema.nodes.image.createAndFill({
                        src: result.file_url,
                        alt: file.name
                    });
                    if (imageNode) {
                        nodes.push(imageNode);
                    }
                }
            }
            
            toast.success(`Uploaded: ${file.name}`);
        } catch (error) {
            console.error('File upload failed:', error);
            toast.error(`Failed to upload: ${file.name}`);
        }
    }
    
    return nodes;
}

const content = props.content || "";

// Store the Crepe instance for later access
let crepeInstance = null;

const editor = useEditor((root) => {
    crepeInstance = new Crepe({ 
        root, 
        defaultValue: content,
        featureConfigs: {
            [Crepe.Feature.ImageBlock]: {
                onUpload: uploadImage,
            },
        },
    });
    
    // Add the upload plugin for drag-and-drop support
    // Access the underlying Milkdown editor to add plugins
    crepeInstance.editor
        .config((ctx) => {
            ctx.update(uploadConfig.key, (prev) => ({
                ...prev,
                uploader: dragDropUploader,
            }));
        })
        .use(upload)
        .use(videoBlockComponent);
    
    return crepeInstance;
});

// Use useInstance to check if editor is ready
const [isLoading, getInstance] = useInstance();

function handleContentChange() {
    // Clear existing timer
    if (autosaveTimer) {
        clearTimeout(autosaveTimer);
    }

    // Check if content has changed
    const currentContent = crepeInstance?.getMarkdown();
    if (currentContent !== undefined && currentContent !== lastSavedContent.value) {
        hasUnsavedChanges.value = true;
        
        // Set up debounced autosave
        autosaveTimer = setTimeout(() => {
            autoSave();
        }, AUTOSAVE_DELAY);
    }
}

async function autoSave() {
    if (props.saving || isLoading.value) {
        return;
    }

    const currentContent = crepeInstance?.getMarkdown();
    if (currentContent === undefined || currentContent === lastSavedContent.value) {
        hasUnsavedChanges.value = false;
        return;
    }

    emit('save', currentContent);
    lastSavedContent.value = currentContent;
    lastSavedAt.value = new Date();
    hasUnsavedChanges.value = false;
}

function saveToDB() {
    // Clear any pending autosave
    if (autosaveTimer) {
        clearTimeout(autosaveTimer);
    }

    if (isLoading.value) {
        toast.error('Editor is still loading');
        return;
    }
    
    // Get markdown from the Crepe instance
    const markdown = crepeInstance?.getMarkdown();
    if (markdown !== undefined) {
        emit('save', markdown);
        lastSavedContent.value = markdown;
        lastSavedAt.value = new Date();
        hasUnsavedChanges.value = false;
    } else {
        toast.error('Could not get content from editor');
    }
}

// Expose saveToDB so parent component can trigger save
defineExpose({
    saveToDB,
    hasUnsavedChanges,
});

onUnmounted(() => {
    if (autosaveTimer) {
        clearTimeout(autosaveTimer);
    }
});
</script>

<style>
/* Wiki Editor Container Styles */
.wiki-editor-container {
    display: flex;
    flex-direction: column;
    height: 100%;
}

/* Milkdown Editor Wrapper - no overflow:hidden to preserve drag handles */
.wiki-milkdown-editor {
    flex: 1;
    min-height: 500px;
    border: 1px solid var(--gray-200, #e5e7eb);
    border-radius: 0.5rem;
    background-color: var(--surface-white, #ffffff);
    position: relative;
}

/* Crepe Theme Customizations for Frappe UI Integration */
.wiki-milkdown-editor .crepe .milkdown {
    /* Background Colors - matching frappe-ui surfaces */
    --crepe-color-background: var(--surface-white, #ffffff);
    --crepe-color-surface: var(--surface-gray-1, #f9fafb);
    --crepe-color-surface-low: var(--surface-gray-2, #f3f4f6);

    /* Text Colors - matching frappe-ui ink colors */
    --crepe-color-on-background: var(--ink-gray-9, #111827);
    --crepe-color-on-surface: var(--ink-gray-8, #1f2937);
    --crepe-color-on-surface-variant: var(--ink-gray-6, #4b5563);

    /* Accent Colors - using frappe-ui primary */
    --crepe-color-primary: var(--primary, #171717);
    --crepe-color-secondary: var(--surface-gray-2, #f3f4f6);
    --crepe-color-on-secondary: var(--ink-gray-9, #111827);

    /* UI Colors */
    --crepe-color-outline: var(--outline-gray-2, #e5e7eb);
    --crepe-color-inverse: var(--ink-gray-9, #111827);
    --crepe-color-on-inverse: var(--surface-white, #ffffff);
    --crepe-color-inline-code: var(--ink-red-3, #dc2626);
    --crepe-color-error: var(--ink-red-3, #dc2626);

    /* Interactive Colors */
    --crepe-color-hover: var(--surface-gray-2, #f3f4f6);
    --crepe-color-selected: var(--surface-gray-3, #e5e7eb);
    --crepe-color-inline-area: var(--surface-gray-2, #f3f4f6);

    /* Typography - matching frappe-ui fonts */
    --crepe-font-title: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --crepe-font-default: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --crepe-font-code: "Fira Code", "JetBrains Mono", Menlo, Monaco, "Courier New", monospace;

    /* Shadows - softer shadows */
    --crepe-shadow-1: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    --crepe-shadow-2: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

/* Editor content area styling */
.wiki-milkdown-editor .crepe .milkdown .editor {
    min-height: 480px;
    padding: 1.5rem;
    outline: none;
}

/* Heading styles */
.wiki-milkdown-editor .crepe .milkdown .editor .heading {
    font-weight: 600;
    line-height: 1.25;
    margin-top: 1.5rem;
    margin-bottom: 0.75rem;
}

.wiki-milkdown-editor .crepe .milkdown .editor h1 {
    font-size: 1.875rem;
}

.wiki-milkdown-editor .crepe .milkdown .editor h2 {
    font-size: 1.5rem;
}

.wiki-milkdown-editor .crepe .milkdown .editor h3 {
    font-size: 1.25rem;
}

/* Paragraph styling */
.wiki-milkdown-editor .crepe .milkdown .editor .paragraph {
    margin: 0.75rem 0;
    line-height: 1.625;
}

/* List styling */
.wiki-milkdown-editor .crepe .milkdown .editor .bullet-list,
.wiki-milkdown-editor .crepe .milkdown .editor .ordered-list {
    padding-left: 1.5rem;
    margin: 0.5rem 0;
}

.wiki-milkdown-editor .crepe .milkdown .editor .list-item {
    margin: 0.25rem 0;
}

/* Code block styling */
.wiki-milkdown-editor .crepe .milkdown .editor pre {
    background-color: var(--surface-gray-2, #f3f4f6);
    border-radius: 0.375rem;
    padding: 1rem;
    overflow-x: auto;
    font-size: 0.875rem;
    line-height: 1.5;
}

/* Inline code styling */
.wiki-milkdown-editor .crepe .milkdown .editor code:not(pre code) {
    background-color: var(--surface-gray-2, #f3f4f6);
    padding: 0.125rem 0.375rem;
    border-radius: 0.25rem;
    font-size: 0.875em;
}

/* Blockquote styling */
.wiki-milkdown-editor .crepe .milkdown .editor blockquote {
    border-left: 3px solid var(--outline-gray-3, #d1d5db);
    padding-left: 1rem;
    margin: 1rem 0;
    color: var(--ink-gray-6, #4b5563);
    font-style: italic;
}

/* Link styling */
.wiki-milkdown-editor .crepe .milkdown .editor a {
    color: var(--primary, #171717);
    text-decoration: underline;
    text-underline-offset: 2px;
}

.wiki-milkdown-editor .crepe .milkdown .editor a:hover {
    text-decoration-thickness: 2px;
}

/* Table styling */
.wiki-milkdown-editor .crepe .milkdown .editor table {
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0;
}

.wiki-milkdown-editor .crepe .milkdown .editor th,
.wiki-milkdown-editor .crepe .milkdown .editor td {
    border: 1px solid var(--outline-gray-2, #e5e7eb);
    padding: 0.5rem 0.75rem;
    text-align: left;
}

.wiki-milkdown-editor .crepe .milkdown .editor th {
    background-color: var(--surface-gray-1, #f9fafb);
    font-weight: 600;
}

/* Horizontal rule */
.wiki-milkdown-editor .crepe .milkdown .editor hr {
    border: none;
    border-top: 1px solid var(--outline-gray-2, #e5e7eb);
    margin: 1.5rem 0;
}

/* Image styling */
.wiki-milkdown-editor .crepe .milkdown .editor img {
    max-width: 100%;
    height: auto;
    border-radius: 0.375rem;
}

/* Task list styling */
.wiki-milkdown-editor .crepe .milkdown .editor .task-list-item {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
}

.wiki-milkdown-editor .crepe .milkdown .editor .task-list-item input[type="checkbox"] {
    margin-top: 0.25rem;
    accent-color: var(--primary, #171717);
}
</style>