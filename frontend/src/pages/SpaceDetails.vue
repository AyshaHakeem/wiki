<template>
    <div class="p-6 flex flex-col items-center">
        <div class="mb-6 w-full max-w-3xl">
            <Button 
                variant="ghost" 
                class="mb-4"
                icon-left="arrow-left"
                :route="{ name: 'SpaceList' }"
            >
                {{ __('Back to Spaces') }}
            </Button>
            <h1 class="text-2xl font-semibold text-ink-gray-9">
                {{ space.doc?.space_name || spaceId }}
            </h1>
            <p class="text-sm text-ink-gray-6 mt-1">{{ space.doc?.route }}</p>
        </div>

        <Tabs
            v-model="activeTab"
            :tabs="tabs"
            class="w-full max-w-3xl"
        >
            <template #tab-panel="{ tab }">
                <div class="py-4">
                    <WikiDocumentList 
                        v-if="tab.name === 'pages' && space.doc && wikiTree.data" 
                        :tree-data="wikiTree.data" 
                        :space-id="spaceId"
                        :root-node="space.doc.root_group"
                        @refresh="wikiTree.reload()" 
                    />
                    <SpaceSettings 
                        v-else-if="tab.name === 'settings'" 
                        :space-id="spaceId"
                    />
                </div>
            </template>
        </Tabs>
    </div>
</template>

<script setup>
import { ref, h } from 'vue';
import { createDocumentResource, createResource, Tabs, Button } from 'frappe-ui';
import WikiDocumentList from '../components/WikiDocumentList.vue';
import SpaceSettings from '../components/SpaceSettings.vue';
import LucideFileText from '~icons/lucide/file-text';
import LucideSettings from '~icons/lucide/settings';

const props = defineProps({
    spaceId: {
        type: String,
        required: true,
    },
});

const activeTab = ref(0);

const tabs = [
    {
        name: 'pages',
        label: 'Pages',
        icon: h(LucideFileText, { class: 'w-4 h-4' }),
    },
    {
        name: 'settings',
        label: 'Settings',
        icon: h(LucideSettings, { class: 'w-4 h-4' }),
    },
];

const space = createDocumentResource({
    doctype: 'Wiki Space',
    name: props.spaceId,
    auto: true
});

const wikiTree = createResource({
    url: '/api/method/wiki.api.get_wiki_tree',
    params: { space_id: props.spaceId },
    auto: true,
});
</script>
