<template>
    <div>
        <div class="flex items-center justify-end mb-4">
            <div class="flex gap-2">
                <Button :title="__('New Group')" icon="folder-plus" variant="subtle" @click="openCreateDialog(rootNode, true)"></Button>
                <Button :title="__('New Page')" icon="file-plus" variant="subtle" @click="openCreateDialog(rootNode, false)">
                </Button>
            </div>
        </div>

        <div v-if="!treeData.children || treeData.children.length === 0"
            class="flex flex-col items-center justify-center py-16 border border-dashed border-outline-gray-2 rounded-lg">
            <LucideFileText class="size-12 text-ink-gray-4 mb-4" />
            <h3 class="text-lg font-medium text-ink-gray-7 mb-2">{{ __('No pages yet') }}</h3>
            <p class="text-sm text-ink-gray-5 mb-6">{{ __('Create your first page to get started') }}</p>
            <Button variant="solid" @click="openCreateDialog(rootNode, false)">
                <template #prefix>
                    <LucideFilePlus class="size-4" />
                </template>
                {{ __('Create First Page') }}
            </Button>
        </div>

        <div v-else class="border border-outline-gray-2 rounded-lg overflow-hidden">
            <NestedDraggable
                :key="treeKey"
                :items="treeData.children"
                :level="0"
                :parent-name="rootNode"
                :space-id="spaceId"
                :selected-page-id="selectedPageId"
                :selected-contribution-id="selectedContributionId"
                @create="openCreateDialog"
                @delete="openDeleteDialog"
                @rename="openRenameDialog"
                @update="handleTreeUpdate"
            />
        </div>

        <Dialog v-model="showCreateDialog">
            <template #body-title>
                <h3 class="text-xl font-semibold text-ink-gray-9">
                    {{ createIsGroup ? __('Create New Group') : __('Create New Page') }}
                </h3>
            </template>
            <template #body-content>
                <div class="space-y-4">
                    <FormControl v-model="createTitle" :label="__('Title')" type="text"
                        :placeholder="createIsGroup ? __('Enter group name') : __('Enter page title')" autofocus />
                </div>
            </template>
            <template #actions="{ close }">
                <div class="flex justify-end gap-2">
                    <Button variant="outline" @click="close">{{ __('Cancel') }}</Button>
                    <Button variant="solid" :loading="isContributionMode ? createContributionResource.loading : wikiDocuments.insert.loading" @click="createDocument(close)">
                        {{ isContributionMode ? __('Save Draft') : __('Create') }}
                    </Button>
                </div>
            </template>
        </Dialog>

        <Dialog v-model="showDeleteDialog">
            <template #body-title>
                <h3 class="text-xl font-semibold text-ink-gray-9">
                    {{ __('Delete') }} "{{ deleteNode?.title }}"
                </h3>
            </template>
            <template #body-content>
                <div class="space-y-4">
                    <p class="text-ink-gray-7">
                        {{ __('Are you sure you want to delete this') }}
                        {{ deleteNode?.is_group ? __('group') : __('page') }}?
                    </p>
                    <div v-if="deleteNode?.is_group && deleteChildCount > 0"
                        class="bg-surface-orange-1 border border-outline-orange-2 rounded-lg p-4">
                        <div class="flex items-start gap-3">
                            <LucideAlertTriangle class="size-5 text-ink-orange-4 flex-shrink-0 mt-0.5" />
                            <div>
                                <p class="font-medium text-ink-orange-4">{{ __('Warning') }}</p>
                                <p class="text-sm text-ink-orange-3 mt-1">
                                    {{ __('This group contains') }} {{ deleteChildCount }}
                                    {{ deleteChildCount === 1 ? __('child document') : __('child documents') }}
                                    {{ __('that will also be deleted.') }}
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </template>
            <template #actions="{ close }">
                <div class="flex justify-end gap-2">
                    <Button variant="outline" @click="close">{{ __('Cancel') }}</Button>
                    <Button variant="solid" :theme="isContributionMode ? 'gray' : 'red'" :loading="isContributionMode ? deleteContributionResource.loading : deleteDocResource?.deleteWithChildren?.loading"
                        @click="deleteDocument(close)">
                        {{ isContributionMode ? __('Save Delete Draft') : __('Delete') }}
                    </Button>
                </div>
            </template>
        </Dialog>

        <Dialog v-model="showRenameDialog">
            <template #body-title>
                <h3 class="text-xl font-semibold text-ink-gray-9">
                    {{ renameNode?.is_group ? __('Rename Group') : __('Change Title') }}
                </h3>
            </template>
            <template #body-content>
                <div class="space-y-4">
                    <FormControl v-model="renameTitle" :label="renameNode?.is_group ? __('Name') : __('Title')" type="text"
                        :placeholder="renameNode?.is_group ? __('Enter group name') : __('Enter page title')" autofocus />
                </div>
            </template>
            <template #actions="{ close }">
                <div class="flex justify-end gap-2">
                    <Button variant="outline" @click="close">{{ __('Cancel') }}</Button>
                    <Button variant="solid" :loading="renameResource.loading"
                        @click="renameDocument(close)">
                        {{ __('Save') }}
                    </Button>
                </div>
            </template>
        </Dialog>
    </div>
</template>

<script setup>
import { ref, toRef, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useStorage } from '@vueuse/core';
import { createListResource, createDocumentResource, createResource, toast, FormControl } from 'frappe-ui';
import NestedDraggable from './NestedDraggable.vue';
import { useContributionMode, useContribution, currentBatch } from '@/composables/useContributionMode';
import LucideFilePlus from '~icons/lucide/file-plus';
import LucideFileText from '~icons/lucide/file-text';
import LucideAlertTriangle from '~icons/lucide/alert-triangle';

const props = defineProps({
    treeData: {
        type: Object,
        required: true,
    },
    spaceId: {
        type: String,
        required: true,
    },
    rootNode: {
        type: String,
        required: true,
    },
    selectedPageId: {
        type: String,
        default: null,
    },
    selectedContributionId: {
        type: String,
        default: null,
    },
});

const emit = defineEmits(['refresh']);
const router = useRouter();

const treeKey = computed(() => {
    const getNodeIds = (nodes) => {
        if (!nodes) return '';
        return nodes.map(n => n.name + (n.children ? getNodeIds(n.children) : '')).join(',');
    };
    return getNodeIds(props.treeData?.children);
});

const spaceIdRef = toRef(props, 'spaceId');
const {
    isContributionMode,
    initBatch,
    loadContributions,
} = useContributionMode(spaceIdRef);

const {
    createPageContribution,
    createContributionResource,
} = useContribution();

const expandedNodes = useStorage('wiki-tree-expanded-nodes', {});

const showCreateDialog = ref(false);
const createTitle = ref('');
const createParent = ref(null);
const createIsGroup = ref(false);

const showDeleteDialog = ref(false);
const deleteNode = ref(null);
const deleteChildCount = ref(0);
const deleteDocResource = ref(null);

const showRenameDialog = ref(false);
const renameTitle = ref('');
const renameNode = ref(null);

const wikiDocuments = createListResource({
    doctype: 'Wiki Document',
    fields: ['name', 'title', 'is_group', 'route', 'is_published', 'parent_wiki_document'],
    insert: {
        onSuccess(doc) {
            toast.success(createIsGroup.value ? __('Group created') : __('Page created'));
            if (createParent.value) {
                expandedNodes.value[createParent.value] = true;
            }
            emit('refresh');
            if (!createIsGroup.value && doc.name) {
                router.push({ name: 'SpacePage', params: { spaceId: props.spaceId, pageId: doc.name } });
            }
        },
        onError(error) {
            toast.error(error.messages?.[0] || __('Error creating document'));
        },
    },
});

const reorderResource = createResource({
    url: '/api/method/wiki.api.wiki_space.reorder_wiki_documents',
    onSuccess(data) {
        if (data.is_contribution) {
            toast.success(__('Reorder saved as draft'));
            loadContributions();
        } else {
            toast.success(__('Documents reordered'));
        }
        emit('refresh');
    },
    onError(error) {
        toast.error(error.messages?.[0] || __('Error reordering documents'));
        emit('refresh');
    },
});

const deleteContributionResource = createResource({
    url: 'wiki.frappe_wiki.doctype.wiki_contribution.wiki_contribution.create_contribution',
});

const renameResource = createResource({
    url: 'frappe.client.set_value',
    onSuccess() {
        toast.success(renameNode.value?.is_group ? __('Group renamed') : __('Title updated'));
        emit('refresh');
    },
    onError(error) {
        toast.error(error.messages?.[0] || __('Error updating title'));
    },
});

function handleTreeUpdate(payload) {
    if (payload.type === 'refresh') {
        emit('refresh');
        return;
    }

    if (payload.type === 'added' || payload.type === 'moved') {
        const siblingNames = payload.siblings.map(s => s.name);
        reorderResource.submit({
            doc_name: payload.item.name,
            new_parent: payload.newParent,
            new_index: payload.newIndex,
            siblings: JSON.stringify(siblingNames),
        });
    }
}

function openCreateDialog(parentName, isGroup) {
    createParent.value = parentName;
    createIsGroup.value = isGroup;
    createTitle.value = '';
    showCreateDialog.value = true;
}

async function openDeleteDialog(node) {
    deleteNode.value = node;
    deleteChildCount.value = 0;

    deleteDocResource.value = createDocumentResource({
        doctype: 'Wiki Document',
        name: node.name,
        whitelistedMethods: {
            getChildrenCount: 'get_children_count',
            deleteWithChildren: 'delete_with_children',
        },
    });

    if (node.is_group) {
        try {
            const result = await deleteDocResource.value.getChildrenCount.submit();
            deleteChildCount.value = result;
        } catch (e) {
            deleteChildCount.value = node.children?.length || 0;
        }
    }

    showDeleteDialog.value = true;
}

async function createDocument(close) {
    if (!createTitle.value.trim()) {
        toast.warning(__('Title is required'));
        return;
    }

    if (isContributionMode.value) {
        await createDocumentAsContribution(close);
    } else {
        await createDocumentDirectly(close);
    }
}

async function createDocumentDirectly(close) {
    await wikiDocuments.insert.submit({
        title: createTitle.value.trim(),
        parent_wiki_document: createParent.value,
        is_group: createIsGroup.value ? 1 : 0,
        is_published: 0,
    });
    close();
}

async function createDocumentAsContribution(close) {
    try {
        if (!currentBatch.value) {
            await initBatch();
        }

        if (!currentBatch.value) {
            toast.error(__('Could not create contribution batch'));
            return;
        }

        await createPageContribution(
            currentBatch.value.name,
            createParent.value,
            createTitle.value.trim(),
            '', // Empty content for new page
            createIsGroup.value
        );

        toast.success(createIsGroup.value ? __('Group draft created') : __('Page draft created'));

        if (createParent.value) {
            expandedNodes.value[createParent.value] = true;
        }

        await loadContributions();
        emit('refresh');
        close();
    } catch (error) {
        console.error('Error creating contribution:', error);
        toast.error(error.messages?.[0] || __('Error creating draft'));
    }
}

async function deleteDocument(close) {
    if (isContributionMode.value) {
        await deleteDocumentAsContribution(close);
    } else {
        await deleteDocumentDirectly(close);
    }
}

async function deleteDocumentDirectly(close) {
    try {
        await deleteDocResource.value.deleteWithChildren.submit();
        toast.success(__('Document deleted'));
        emit('refresh');
        close();
    } catch (error) {
        toast.error(error.messages?.[0] || __('Error deleting document'));
    }
}

async function deleteDocumentAsContribution(close) {
    try {
        if (!currentBatch.value) {
            await initBatch();
        }

        if (!currentBatch.value) {
            toast.error(__('Could not create contribution batch'));
            return;
        }

        await deleteContributionResource.submit({
            batch: currentBatch.value.name,
            operation: 'delete',
            target_document: deleteNode.value.name,
        });

        toast.success(__('Delete saved as draft'));

        await loadContributions();
        emit('refresh');
        close();
    } catch (error) {
        console.error('Error creating delete contribution:', error);
        toast.error(error.messages?.[0] || __('Error creating draft'));
    }
}

function openRenameDialog(node) {
    renameNode.value = node;
    renameTitle.value = node.title || '';
    showRenameDialog.value = true;
}

async function renameDocument(close) {
    if (!renameTitle.value.trim()) {
        toast.warning(__('Name is required'));
        return;
    }

    await renameResource.submit({
        doctype: 'Wiki Document',
        name: renameNode.value.name,
        fieldname: {
            title: renameTitle.value.trim(),
        },
    });
    close();
}
</script>