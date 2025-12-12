<template>  
<div class="p-6">
    <div v-if="wikiDoc.doc">
        <!-- Breadcrumbs -->
        <WikiBreadcrumbs :pageId="pageId" class="mb-4" />

        <!-- Page Header -->
        <div class="flex items-center justify-between mb-6">
            <h1 class="text-2xl font-semibold text-ink-gray-9">{{ wikiDoc.doc.title }}</h1>
            <div class="flex items-center gap-2">
                <Badge v-if="!wikiDoc.doc.is_published" variant="subtle" theme="orange" size="sm">
                    {{ __('Unpublished') }}
                </Badge>
                <Button 
                    variant="subtle" 
                    :href="`/${wikiDoc.doc.route}`"
                    target="_blank"
                >
                    <template #prefix>
                        <LucideExternalLink class="size-4" />
                    </template>
                    {{ __('View Page') }}
                </Button>
            </div>
        </div>

        <MilkdownProvider>
            <WikiEditor :content="wikiDoc.doc.content" :saving="wikiDoc.setValue.loading" @save="saveContent" />
        </MilkdownProvider>
    </div>
</div>
</template>

<script setup>
import { onMounted } from 'vue';
import { MilkdownProvider } from "@milkdown/vue";
import { createDocumentResource, Badge } from "frappe-ui";
import WikiEditor from '../components/WikiEditor.vue';
import WikiBreadcrumbs from '../components/WikiBreadcrumbs.vue';
import LucideExternalLink from '~icons/lucide/external-link';

const props = defineProps({
    pageId: {
        type: String,
        required: true
    }
});

const wikiDoc = createDocumentResource({
    doctype: "Wiki Document",
    name: props.pageId,
});

onMounted(() => {
    wikiDoc.reload();
});

function saveContent(content) {
    wikiDoc.setValue.submit({
        content
    });
}
</script>