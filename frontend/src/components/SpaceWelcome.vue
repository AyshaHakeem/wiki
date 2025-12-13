<template>
    <div class="flex flex-col items-center justify-center h-full py-16">
        <LucideFileText class="size-16 text-ink-gray-3 mb-6" />
        <h2 class="text-xl font-medium text-ink-gray-7 mb-2">
            {{ __('Select a page') }}
        </h2>
        <p class="text-ink-gray-5 text-center max-w-md">
            {{ __('Choose a page from the sidebar to view and edit, or create a new page to get started.') }}
        </p>
    </div>
</template>

<script setup>
import LucideFileText from '~icons/lucide/file-text';
</script>
