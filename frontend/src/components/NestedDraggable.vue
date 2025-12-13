<template>
    <draggable
        class="nested-draggable-area"
        :class="{ 'min-h-[40px]': level > 0 }"
        tag="div"
        :list="localItems"
        :group="{ name: 'wiki-tree' }"
        item-key="name"
        ghost-class="dragging-ghost"
        drag-class="dragging-item"
        handle=".drag-handle"
        :animation="150"
        @change="handleChange"
    >
        <template #item="{ element }">
            <div class="draggable-item">
                <!-- Node Row -->
                <div
                    class="flex items-center justify-between pr-2 py-1.5 hover:bg-surface-gray-2 group border-b border-outline-gray-1 cursor-pointer"
                    :class="{ 'bg-surface-gray-3': !element.is_group && element.name === selectedPageId }"
                    :style="{ paddingLeft: `${level * 12 + 8}px` }"
                    @click="handleRowClick(element)"
                >
                    <div class="flex items-center gap-1.5 flex-1 min-w-0">
                        <!-- Drag Handle -->
                        <button 
                            class="drag-handle p-0.5 hover:bg-surface-gray-3 rounded cursor-grab active:cursor-grabbing opacity-0 group-hover:opacity-100 transition-opacity"
                            @click.stop
                        >
                            <LucideGripVertical class="size-4 text-ink-gray-4" />
                        </button>

                        <!-- Expand/Collapse Toggle for Groups -->
                        <button 
                            v-if="element.is_group" 
                            class="p-0.5 hover:bg-surface-gray-3 rounded"
                            @click.stop="toggleExpanded(element.name)"
                        >
                            <LucideChevronRight 
                                class="size-4 text-ink-gray-5 transition-transform duration-200" 
                                :class="{ 'rotate-90': isExpanded(element.name) }"
                            />
                        </button>
                        <div v-else class="w-4" />

                        <!-- Icon -->
                        <LucideFolder v-if="element.is_group" class="size-4 text-ink-gray-5 flex-shrink-0" />
                        <LucideFileText v-else class="size-4 text-ink-gray-5 flex-shrink-0" />

                        <!-- Title -->
                        <span 
                            class="text-sm truncate" 
                            :class="(element.is_published || element.is_group) ? 'text-ink-gray-8' : 'text-ink-gray-5'"
                        >
                            {{ element.title }}
                        </span>

                        <!-- Not Published Badge (only for pages, not groups) -->
                        <Badge v-if="!element.is_group && !element.is_published" variant="subtle" theme="orange" size="sm">
                            {{ __('Not Published') }}
                        </Badge>
                    </div>

                    <!-- Actions -->
                    <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity" @click.stop>
                        <Dropdown :options="getDropdownOptions(element)">
                            <Button variant="ghost" size="sm">
                                <LucideMoreHorizontal class="size-4" />
                            </Button>
                        </Dropdown>
                    </div>
                </div>

                <!-- Children (nested draggable for groups) -->
                <div v-if="element.is_group && isExpanded(element.name)">
                    <NestedDraggable
                        :items="element.children || []"
                        :level="level + 1"
                        :parent-name="element.name"
                        :space-id="spaceId"
                        :selected-page-id="selectedPageId"
                        @create="(parent, isGroup) => emit('create', parent, isGroup)"
                        @delete="(n) => emit('delete', n)"
                        @update="handleNestedUpdate"
                    />
                </div>
            </div>
        </template>
    </draggable>
</template>

<script setup>
import { ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useStorage } from '@vueuse/core';
import { Dropdown, Badge, Button, createResource, toast } from 'frappe-ui';
import draggable from 'vuedraggable';
import LucideChevronRight from '~icons/lucide/chevron-right';
import LucideFolder from '~icons/lucide/folder';
import LucideFileText from '~icons/lucide/file-text';
import LucideMoreHorizontal from '~icons/lucide/more-horizontal';
import LucideGripVertical from '~icons/lucide/grip-vertical';

defineOptions({
    name: 'NestedDraggable',
});

const props = defineProps({
    items: {
        type: Array,
        required: true,
    },
    level: {
        type: Number,
        default: 0,
    },
    parentName: {
        type: String,
        default: null,
    },
    spaceId: {
        type: String,
        default: null,
    },
    selectedPageId: {
        type: String,
        default: null,
    },
});

const emit = defineEmits(['create', 'delete', 'update']);
const router = useRouter();

// Local copy of items for draggable to mutate
const localItems = ref([...props.items]);

// Watch for external changes to items prop
watch(() => props.items, (newItems) => {
    localItems.value = [...newItems];
}, { deep: true });

// Store expanded state in localStorage, collapsed by default
const expandedNodes = useStorage('wiki-tree-expanded-nodes', {});

function isExpanded(name) {
    return expandedNodes.value[name] === true;
}

function toggleExpanded(name) {
    expandedNodes.value[name] = !expandedNodes.value[name];
}

function handleRowClick(element) {
    if (element.is_group) {
        toggleExpanded(element.name);
    } else {
        router.push({ name: 'SpacePage', params: { spaceId: props.spaceId, pageId: element.name } });
    }
}

function handleChange(evt) {
    // Emit update event with the change information
    if (evt.added || evt.moved) {
        const item = evt.added?.element || evt.moved?.element;
        const newIndex = evt.added?.newIndex ?? evt.moved?.newIndex;
        
        emit('update', {
            item,
            newParent: props.parentName,
            newIndex,
            siblings: localItems.value,
            type: evt.added ? 'added' : 'moved',
        });
    }
}

function handleNestedUpdate(payload) {
    // Bubble up the update event
    emit('update', payload);
}

// Publish/Unpublish functionality
function createPublishResource(element) {
    return createResource({
        url: 'frappe.client.set_value',
        makeParams() {
            return {
                doctype: 'Wiki Document',
                name: element.name,
                fieldname: {
                    is_published: element.is_published ? 0 : 1,
                },
            };
        },
        onSuccess() {
            const action = element.is_published ? __('unpublished') : __('published');
            toast.success(__('Page {0}', [action]));
            emit('update', { type: 'refresh' });
        },
        onError(error) {
            toast.error(error.messages?.[0] || __('Error updating publish status'));
        },
    });
}

function getDropdownOptions(element) {
    const options = [];

    // Add child options for groups
    if (element.is_group) {
        options.push({
            group: __('Add'),
            items: [
                {
                    label: __('Page'),
                    icon: 'file-plus',
                    onClick: () => emit('create', element.name, false),
                },
                {
                    label: __('Group'),
                    icon: 'folder-plus',
                    onClick: () => emit('create', element.name, true),
                },
            ],
        });
    }

    // Publish/Unpublish option for non-groups (pages)
    if (!element.is_group) {
        options.push({
            label: element.is_published ? __('Unpublish') : __('Publish'),
            icon: element.is_published ? 'eye-off' : 'eye',
            onClick: () => {
                const resource = createPublishResource(element);
                resource.submit();
            },
        });
    }

    // Danger zone - only show delete if it's not a group with children
    const hasChildren = element.is_group && element.children?.length > 0;
    if (!hasChildren) {
        options.push({
            group: __('Danger'),
            items: [
                {
                    label: __('Delete'),
                    icon: 'trash-2',
                    theme: 'red',
                    onClick: () => emit('delete', element),
                },
            ],
        });
    }

    return options;
}
</script>

<style scoped>
.nested-draggable-area {
    min-height: 8px;
}

.dragging-ghost {
    opacity: 0.5;
    background-color: var(--surface-blue-1, #e0f2fe);
    border-radius: 4px;
}

.dragging-item {
    opacity: 0.8;
    background-color: white;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    border-radius: 4px;
}

.drag-handle:active {
    cursor: grabbing;
}
</style>
