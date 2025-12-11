<template>
    <div>
        <!-- Header with Add buttons -->
        <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-medium text-ink-gray-8">{{ __('Pages') }}</h2>
            <div class="flex gap-2">
                <Button variant="subtle" @click="openCreateDialog(rootNode, true)">
                    <template #prefix>
                        <LucideFolderPlus class="size-4" />
                    </template>
                    {{ __('New Group') }}
                </Button>
                <Button variant="solid" @click="openCreateDialog(rootNode, false)">
                    <template #prefix>
                        <LucideFilePlus class="size-4" />
                    </template>
                    {{ __('New Page') }}
                </Button>
            </div>
        </div>

        <!-- Empty State -->
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

        <!-- Tree View -->
        <div v-else class="border border-outline-gray-2 rounded-lg overflow-hidden">
            <div v-for="node in treeData.children" :key="node.name">
                <WikiTreeNode 
                    :node="node" 
                    :level="0"
                    @create="openCreateDialog"
                    @delete="openDeleteDialog"
                    @refresh="emit('refresh')"
                />
            </div>
        </div>

        <!-- Create Dialog -->
        <Dialog v-model="showCreateDialog">
            <template #body-title>
                <h3 class="text-xl font-semibold text-ink-gray-9">
                    {{ createIsGroup ? __('Create New Group') : __('Create New Page') }}
                </h3>
            </template>
            <template #body-content>
                <div class="space-y-4">
                    <FormControl
                        v-model="createTitle"
                        :label="__('Title')"
                        type="text"
                        :placeholder="createIsGroup ? __('Enter group name') : __('Enter page title')"
                        autofocus
                    />
                </div>
            </template>
            <template #actions="{ close }">
                <div class="flex justify-end gap-2">
                    <Button variant="outline" @click="close">{{ __('Cancel') }}</Button>
                    <Button 
                        variant="solid" 
                        :loading="wikiDocuments.insert.loading"
                        @click="createDocument(close)"
                    >
                        {{ __('Create') }}
                    </Button>
                </div>
            </template>
        </Dialog>

        <!-- Delete Confirmation Dialog -->
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
                    <Button 
                        variant="solid" 
                        theme="red"
                        :loading="deleteDocResource?.deleteWithChildren?.loading"
                        @click="deleteDocument(close)"
                    >
                        {{ __('Delete') }}
                    </Button>
                </div>
            </template>
        </Dialog>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { createListResource, createDocumentResource, toast } from 'frappe-ui';
import WikiTreeNode from './WikiTreeNode.vue';
import LucideFolderPlus from '~icons/lucide/folder-plus';
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
});

const emit = defineEmits(['refresh']);
const router = useRouter();

// Create Dialog State
const showCreateDialog = ref(false);
const createTitle = ref('');
const createParent = ref(null);
const createIsGroup = ref(false);

// Delete Dialog State
const showDeleteDialog = ref(false);
const deleteNode = ref(null);
const deleteChildCount = ref(0);
const deleteDocResource = ref(null);

// Wiki Document List Resource for insert
const wikiDocuments = createListResource({
    doctype: 'Wiki Document',
    fields: ['name', 'title', 'is_group', 'route', 'is_published', 'parent_wiki_document'],
    insert: {
        onSuccess(data) {
            toast.success(createIsGroup.value ? __('Group created') : __('Page created'));
            
            // Navigate to edit page for new pages (not groups)
            if (!createIsGroup.value && data.name) {
                router.push({ name: 'WikiDocument', params: { pageId: data.name } });
            } else {
                emit('refresh');
            }
        },
        onError(error) {
            toast.error(error.messages?.[0] || __('Error creating document'));
        },
    },
});

function openCreateDialog(parentName, isGroup) {
    createParent.value = parentName;
    createIsGroup.value = isGroup;
    createTitle.value = '';
    showCreateDialog.value = true;
}

async function openDeleteDialog(node) {
    deleteNode.value = node;
    deleteChildCount.value = 0;
    
    // Create a document resource for this specific node
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

    await wikiDocuments.insert.submit({
        title: createTitle.value.trim(),
        parent_wiki_document: createParent.value,
        is_group: createIsGroup.value ? 1 : 0,
        is_published: 0,
    });
    
    close();
}

async function deleteDocument(close) {
    try {
        await deleteDocResource.value.deleteWithChildren.submit();
        toast.success(__('Document deleted'));
        emit('refresh');
        close();
    } catch (error) {
        toast.error(error.messages?.[0] || __('Error deleting document'));
    }
}
</script>