<template>
    <div class="flex h-full">
        <!-- Left Sidebar -->
        <aside
            ref="sidebarRef"
            class="border-r border-outline-gray-2 flex flex-col bg-surface-gray-1 relative flex-shrink-0"
            :style="{ width: `${sidebarWidth}px` }"
        >
            <!-- Header -->
            <div class="p-4 border-b border-outline-gray-2">
                <div class="flex items-center justify-between mb-3">
                    <Button
                        variant="ghost"
                        icon-left="arrow-left"
                        :route="{ name: 'SpaceList' }"
                    >
                        {{ __('Back to Spaces') }}
                    </Button>
                    <Button
                        variant="ghost"
                        icon="settings"
                        :title="__('Settings')"
                        @click="showSettingsDialog = true"
                    />
                </div>
                <div class="flex items-center gap-2">
                    <h1 class="text-lg font-semibold text-ink-gray-9">
                        {{ space.doc?.space_name || spaceId }}
                    </h1>
                    <Button
                        v-if="space.doc?.route"
                        variant="ghost"
                        icon="external-link"
                        :title="__('View Space')"
                        :link="space.doc?.route"
                    />
                </div>
                <p class="text-sm text-ink-gray-5 mt-0.5">{{ space.doc?.route }}</p>
            </div>

            <!-- Document Tree -->
            <div v-if="space.doc && wikiTree.data" class="flex-1 overflow-auto p-2">
                <WikiDocumentList
                    :tree-data="wikiTree.data"
                    :space-id="spaceId"
                    :root-node="space.doc.root_group"
                    :selected-page-id="currentPageId"
                    @refresh="wikiTree.reload()"
                />
            </div>

            <!-- Resize Handle -->
            <div
                class="absolute top-0 right-0 w-1 h-full cursor-col-resize z-10"
                :class="sidebarResizing ? 'bg-surface-gray-4' : 'hover:bg-surface-gray-4'"
                @mousedown="startResize"
            />
        </aside>

        <!-- Right Content Panel -->
        <main class="flex-1 overflow-auto bg-surface-white min-w-0">
            <router-view
                :space-id="spaceId"
                @refresh="wikiTree.reload()"
            />
        </main>

        <!-- Settings Dialog -->
        <Dialog v-model="showSettingsDialog">
            <template #body-title>
                <h3 class="text-xl font-semibold text-ink-gray-9">
                    {{ __('Space Settings') }}
                </h3>
            </template>
            <template #body-content>
                <div class="space-y-4 py-2">
                    <!-- Feedback Collection Toggle -->
                    <div class="flex items-center justify-between p-3 rounded-lg border border-outline-gray-2 bg-surface-gray-1">
                        <div class="flex-1 mr-4">
                            <p class="text-sm font-medium text-ink-gray-9">
                                {{ __('Enable Feedback Collection') }}
                            </p>
                            <p class="text-xs text-ink-gray-5 mt-0.5">
                                {{ __('Show a feedback widget on wiki pages to collect user reactions') }}
                            </p>
                        </div>
                        <Switch
                            v-model="enableFeedbackCollection"
                            :disabled="updatingFeedbackSetting"
                            @update:modelValue="updateFeedbackSetting"
                        />
                    </div>
                </div>
            </template>
            <template #actions="{ close }">
                <div class="flex justify-end">
                    <Button variant="outline" @click="close">{{ __('Close') }}</Button>
                </div>
            </template>
        </Dialog>
    </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useRoute } from 'vue-router';
import { createDocumentResource, createResource, Button, Dialog, Switch } from 'frappe-ui';
import WikiDocumentList from '../components/WikiDocumentList.vue';
import LucideSettings from '~icons/lucide/settings';
import { useSidebarResize } from '../composables/useSidebarResize';

const props = defineProps({
    spaceId: {
        type: String,
        required: true,
    },
});

const route = useRoute();

// Settings dialog state
const showSettingsDialog = ref(false);

// Feedback collection setting
const enableFeedbackCollection = ref(false);
const updatingFeedbackSetting = ref(false);

// Sidebar resize
const sidebarRef = ref(null);
const { sidebarWidth, sidebarResizing, startResize } = useSidebarResize(sidebarRef);

// Compute current page from route params
const currentPageId = computed(() => route.params.pageId || null);

const space = createDocumentResource({
    doctype: 'Wiki Space',
    name: props.spaceId,
    auto: true
});

// Sync enableFeedbackCollection with space doc when it loads
watch(() => space.doc, (doc) => {
    if (doc) {
        enableFeedbackCollection.value = Boolean(doc.enable_feedback_collection);
    }
}, { immediate: true });

// Update feedback setting
async function updateFeedbackSetting(value) {
    updatingFeedbackSetting.value = true;
    try {
        await space.setValue.submit({
            enable_feedback_collection: value ? 1 : 0
        });
    } catch (error) {
        console.error('Failed to update feedback setting:', error);
        // Revert on error
        enableFeedbackCollection.value = !value;
    } finally {
        updatingFeedbackSetting.value = false;
    }
}

const wikiTree = createResource({
    url: '/api/method/wiki.api.get_wiki_tree',
    params: { space_id: props.spaceId },
    auto: true,
});
</script>
