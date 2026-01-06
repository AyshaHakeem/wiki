<template>
    <div class="flex h-full">
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

            <div v-if="space.doc && mergedTreeData" class="flex-1 overflow-auto p-2">
                <WikiDocumentList
                    :tree-data="mergedTreeData"
                    :space-id="spaceId"
                    :root-node="space.doc.root_group"
                    :selected-page-id="currentPageId"
                    :selected-contribution-id="currentContributionId"
                    @refresh="refreshTree"
                />
            </div>

            <div
                class="absolute top-0 right-0 w-1 h-full cursor-col-resize z-10"
                :class="sidebarResizing ? 'bg-surface-gray-4' : 'hover:bg-surface-gray-4'"
                @mousedown="startResize"
            />
        </aside>

        <main class="flex-1 overflow-auto bg-surface-white min-w-0">
            <router-view
                :space-id="spaceId"
                @refresh="refreshTree"
            />
        </main>

        <Dialog v-model="showSettingsDialog">
            <template #body-title>
                <h3 class="text-xl font-semibold text-ink-gray-9">
                    {{ __('Space Settings') }}
                </h3>
            </template>
            <template #body-content>
                <div class="space-y-4 py-2">
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
import { ref, computed, watch, toRef } from 'vue';
import { useRoute } from 'vue-router';
import { createDocumentResource, createResource, Button, Dialog, Switch } from 'frappe-ui';
import WikiDocumentList from '../components/WikiDocumentList.vue';
import { useSidebarResize } from '../composables/useSidebarResize';
import { useContributionMode, currentBatch } from '../composables/useContributionMode';

const props = defineProps({
    spaceId: {
        type: String,
        required: true,
    },
});

const route = useRoute();

const spaceIdRef = toRef(props, 'spaceId');
const {
    isContributionMode,
    contributionsResource,
    initBatch,
    loadContributions,
} = useContributionMode(spaceIdRef);

const showSettingsDialog = ref(false);

const enableFeedbackCollection = ref(false);
const updatingFeedbackSetting = ref(false);

const sidebarRef = ref(null);
const { sidebarWidth, sidebarResizing, startResize } = useSidebarResize(sidebarRef);

const currentPageId = computed(() => route.params.pageId || null);
const currentContributionId = computed(() => route.params.contributionId || null);

const space = createDocumentResource({
    doctype: 'Wiki Space',
    name: props.spaceId,
    auto: true
});

watch(() => space.doc, (doc) => {
    if (doc) {
        enableFeedbackCollection.value = Boolean(doc.enable_feedback_collection);
    }
}, { immediate: true });

watch(() => space.doc, async (doc) => {
    if (doc && isContributionMode.value) {
        // Clear shared state immediately to prevent stale data from prior space
        currentBatch.value = null;
        await initBatch();
        await loadContributions();
    }
}, { immediate: true });

async function updateFeedbackSetting(value) {
    updatingFeedbackSetting.value = true;
    try {
        await space.setValue.submit({
            enable_feedback_collection: value ? 1 : 0
        });
    } catch (error) {
        console.error('Failed to update feedback setting:', error);
        enableFeedbackCollection.value = !value;
    } finally {
        updatingFeedbackSetting.value = false;
    }
}

const wikiTree = createResource({
    url: '/api/method/wiki.api.wiki_space.get_wiki_tree',
    params: { space_id: props.spaceId },
    auto: true,
});

const mergedTreeData = computed(() => {
    const liveTree = wikiTree.data;
    if (!liveTree || !isContributionMode.value) {
        return liveTree;
    }

    const contributions = contributionsResource.data || [];
    if (contributions.length === 0) {
        return liveTree;
    }

    const mergedTree = JSON.parse(JSON.stringify(liveTree));

    const nodeMap = new Map();
    const buildNodeMap = (nodes, parent = null) => {
        for (const node of nodes) {
            node._parent = parent;
            nodeMap.set(node.name, node);
            if (node.children) {
                buildNodeMap(node.children, node);
            }
        }
    };
    buildNodeMap(mergedTree.children || []);

    const applySiblingsOrder = (siblingsOrderJson, parentContainer) => {
        if (!siblingsOrderJson || !parentContainer) return;
        try {
            const siblingsOrder = JSON.parse(siblingsOrderJson);
            for (let i = 0; i < siblingsOrder.length; i++) {
                const siblingName = siblingsOrder[i];
                const siblingNode = nodeMap.get(siblingName);
                if (siblingNode && parentContainer.includes(siblingNode)) {
                    siblingNode._draftSortOrder = i;
                }
            }
        } catch (e) {
            console.error('Failed to parse siblings_order:', e);
        }
    };

    for (const contrib of contributions) {
        if (contrib.operation === 'create') {
            const newNode = {
                name: contrib.temp_id,
                title: contrib.proposed_title,
                is_group: contrib.proposed_is_group,
                is_published: contrib.proposed_is_published,
                children: [],
                _isDraft: true,
                _contribution: contrib.name,
                _draftSortOrder: contrib.proposed_sort_order,
            };

            const parentName = contrib.parent_ref;
            let parentContainer = null;
            if (parentName === mergedTree.root_group) {
                mergedTree.children = mergedTree.children || [];
                mergedTree.children.push(newNode);
                parentContainer = mergedTree.children;
            } else if (nodeMap.has(parentName)) {
                const parent = nodeMap.get(parentName);
                parent.children = parent.children || [];
                parent.children.push(newNode);
                newNode._parent = parent;
                parentContainer = parent.children;
            }
            nodeMap.set(contrib.temp_id, newNode);

            applySiblingsOrder(contrib.siblings_order, parentContainer);

        } else if (contrib.operation === 'edit') {
            const node = nodeMap.get(contrib.target_document);
            if (node) {
                node._isModified = true;
                node._contribution = contrib.name;
                if (contrib.proposed_title) {
                    node._draftTitle = contrib.proposed_title;
                }
            }

        } else if (contrib.operation === 'delete') {
            const node = nodeMap.get(contrib.target_document);
            if (node) {
                node._isDeleted = true;
                node._contribution = contrib.name;
            }

        } else if (contrib.operation === 'move') {
            const node = nodeMap.get(contrib.target_document);
            if (node) {
                node._isMoved = true;
                node._contribution = contrib.name;

                if (node._parent) {
                    const parentChildren = node._parent.children || [];
                    const idx = parentChildren.findIndex(c => c.name === node.name);
                    if (idx !== -1) {
                        parentChildren.splice(idx, 1);
                    }
                } else {
                    // It's at root level
                    const idx = mergedTree.children.findIndex(c => c.name === node.name);
                    if (idx !== -1) {
                        mergedTree.children.splice(idx, 1);
                    }
                }

                const newParentName = contrib.new_parent_ref;
                if (newParentName === mergedTree.root_group || !newParentName) {
                    mergedTree.children = mergedTree.children || [];
                    mergedTree.children.push(node);
                    node._parent = null;
                } else if (nodeMap.has(newParentName)) {
                    const newParent = nodeMap.get(newParentName);
                    newParent.children = newParent.children || [];
                    newParent.children.push(node);
                    node._parent = newParent;
                }
            }

        } else if (contrib.operation === 'reorder') {
            const node = nodeMap.get(contrib.target_document);
            if (node) {
                node._isReordered = true;
                node._contribution = contrib.name;
                node._draftSortOrder = contrib.proposed_sort_order ?? contrib.new_sort_order;

                const parentContainer = node._parent?.children || mergedTree.children;
                applySiblingsOrder(contrib.siblings_order, parentContainer);
            }
        }
    }

    const sortChildren = (nodes) => {
        if (!nodes) return;
        nodes.sort((a, b) => {
            const orderA = a._draftSortOrder ?? a.sort_order ?? 0;
            const orderB = b._draftSortOrder ?? b.sort_order ?? 0;
            return orderA - orderB;
        });
        for (const node of nodes) {
            sortChildren(node.children);
        }
    };
    sortChildren(mergedTree.children);

    return mergedTree;
});

async function refreshTree() {
    await wikiTree.reload();
    if (isContributionMode.value) {
        await loadContributions();
    }
}
</script>
