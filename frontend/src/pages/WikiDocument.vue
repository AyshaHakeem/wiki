<template>  
<div class="p-6">
    <div v-if="wikiDoc.doc">
        <!-- Breadcrumbs -->
        <WikiBreadcrumbs :pageId="pageId" class="mb-4" />

        <!-- Page Header -->
        <div class="flex items-center justify-between mb-6">
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

        <MilkdownProvider>
            <WikiEditor ref="editorRef" :content="wikiDoc.doc.content" :saving="wikiDoc.setValue.loading" @save="saveContent" />
        </MilkdownProvider>
    </div>
</div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { MilkdownProvider } from "@milkdown/vue";
import { createDocumentResource, createResource, Badge, Button, toast } from "frappe-ui";
import WikiEditor from '../components/WikiEditor.vue';
import WikiBreadcrumbs from '../components/WikiBreadcrumbs.vue';
import LucideExternalLink from '~icons/lucide/external-link';
import LucideEye from '~icons/lucide/eye';
import LucideEyeOff from '~icons/lucide/eye-off';
import LucideSave from '~icons/lucide/save';

const props = defineProps({
    pageId: {
        type: String,
        required: true
    }
});

const editorRef = ref(null);

const wikiDoc = createDocumentResource({
    doctype: "Wiki Document",
    name: props.pageId,
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

onMounted(() => {
    wikiDoc.reload();
});

function saveContent(content) {
    wikiDoc.setValue.submit({
        content
    });
}
</script>