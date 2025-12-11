<template>
    <div class="p-6">
        <div class="mb-6">
            <h1 class="text-2xl font-semibold text-ink-gray-9">
                {{ space.doc?.space_name || spaceId }}
            </h1>
            <p class="text-sm text-ink-gray-6 mt-1">{{ space.doc?.route }}</p>
        </div>

        <WikiDocumentList 
            v-if="wikiTree.data" 
            :tree-data="wikiTree.data" 
            :space-id="spaceId"
            @refresh="wikiTree.reload()" 
        />
    </div>
</template>

<script setup>
import { createDocumentResource, createResource } from 'frappe-ui';
import WikiDocumentList from '../components/WikiDocumentList.vue';

const props = defineProps({
    spaceId: {
        type: String,
        required: true,
    },
});

const space = createDocumentResource({
    doctype: 'Wiki Space',
    name: props.spaceId,
});
space.reload();

const wikiTree = createResource({
    url: '/api/method/wiki.api.get_wiki_tree',
    params: { space_id: props.spaceId },
    auto: true,
});
</script>
