<template>
    <div class="h-full flex flex-col">
        <div v-if="wikiDoc.doc" class="h-full flex flex-col">
            <!-- Page Header (Sticky) -->
            <div class="flex items-center justify-between p-6 pb-4 bg-surface-white shrink-0">
                <!-- Title with Badge -->
                <div class="flex items-center gap-2">
                    <h1 class="text-2xl font-semibold text-ink-gray-9">{{ wikiDoc.doc.title }}</h1>
                    <Badge v-if="wikiDoc.doc.is_published" variant="subtle" theme="green" size="sm">
                        {{ __('Published') }}
                    </Badge>
                    <Badge v-else variant="subtle" theme="orange" size="sm">
                        {{ __('Not Published') }}
                    </Badge>
                </div>

                <!-- Actions -->
                <div class="flex items-center gap-2">
                    <Button
                        variant="outline"
                        :loading="publishResource.loading"
                        @click="togglePublish"
                    >
                        <template #prefix>
                            <component :is="wikiDoc.doc.is_published ? LucideEyeOff : LucideEye" class="size-4" />
                        </template>
                        {{ wikiDoc.doc.is_published ? __('Unpublish') : __('Publish') }}
                    </Button>
                    <Button
                        variant="outline"
                        :link="`http://wiki.localhost:8000/${wikiDoc.doc.route}`"
                        target="_blank"
                    >
                        <template #prefix>
                            <LucideExternalLink class="size-4" />
                        </template>
                        {{ __('View Page') }}
                    </Button>
                    <Button
                        variant="solid"
                        :loading="wikiDoc.setValue.loading"
                        @click="saveFromHeader"
                    >
                        <template #prefix>
                            <LucideSave class="size-4" />
                        </template>
                        {{ __('Save') }}
                    </Button>
                </div>
            </div>

            <!-- Editor Content (Scrollable) -->
            <div class="flex-1 overflow-auto px-6 pb-6">
                <MilkdownProvider v-if="editorKey" :key="editorKey">
                    <WikiEditor ref="editorRef" :content="wikiDoc.doc.content" :saving="wikiDoc.setValue.loading" @save="saveContent" />
                </MilkdownProvider>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { MilkdownProvider } from "@milkdown/vue";
import { createDocumentResource, createResource, Badge, Button, toast } from "frappe-ui";
import WikiEditor from './WikiEditor.vue';
import LucideExternalLink from '~icons/lucide/external-link';
import LucideEye from '~icons/lucide/eye';
import LucideEyeOff from '~icons/lucide/eye-off';
import LucideSave from '~icons/lucide/save';

const props = defineProps({
    pageId: {
        type: String,
        required: true
    },
    spaceId: {
        type: String,
        required: false
    }
});

const emit = defineEmits(['refresh']);
const editorRef = ref(null);

const wikiDoc = createDocumentResource({
    doctype: "Wiki Document",
    name: props.pageId,
    auto: true,
});

// Watch for pageId changes and reload document
watch(() => props.pageId, (newPageId) => {
    if (newPageId) {
        wikiDoc.name = newPageId;
        wikiDoc.reload();
    }
});

// Key that changes only when the document for the current page is loaded
// This prevents the editor from rendering with stale content
const editorKey = computed(() => {
    if (wikiDoc.doc?.name === props.pageId) {
        return `${props.pageId}-${wikiDoc.doc.modified || 'new'}`;
    }
    return null;
});

// Publish/Unpublish Resource
const publishResource = createResource({
    url: 'frappe.client.set_value',
    makeParams() {
        return {
            doctype: 'Wiki Document',
            name: props.pageId,
            fieldname: {
                is_published: wikiDoc.doc?.is_published ? 0 : 1,
            },
        };
    },
    onSuccess() {
        const action = wikiDoc.doc?.is_published ? __('unpublished') : __('published');
        toast.success(__('Page {0}', [action]));
        wikiDoc.reload();
        emit('refresh'); // Refresh sidebar tree
    },
    onError(error) {
        toast.error(error.messages?.[0] || __('Error updating publish status'));
    },
});

async function togglePublish() {
    await publishResource.submit();
}

function saveFromHeader() {
    editorRef.value?.saveToDB();
}

function saveContent(content) {
    wikiDoc.setValue.submit({
        content
    });
}
</script>
