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
                <div
                    class="flex items-center justify-between pr-2 py-1.5 hover:bg-surface-gray-2 group border-b border-outline-gray-1"
                    :class="getRowClasses(element)"
                    :style="{ paddingLeft: `${level * 12 + 8}px` }"
                    @click="handleRowClick(element)"
                >
                    <div class="flex items-center gap-1.5 flex-1 min-w-0">
                        <button 
                            class="drag-handle p-0.5 hover:bg-surface-gray-3 rounded cursor-grab active:cursor-grabbing opacity-0 group-hover:opacity-100 transition-opacity"
                            @click.stop
                        >
                            <LucideGripVertical class="size-4 text-ink-gray-4" />
                        </button>

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

                        <LucideFolder v-if="element.is_group" class="size-4 text-ink-gray-5 flex-shrink-0" />
                        <LucideFileText v-else class="size-4 text-ink-gray-5 flex-shrink-0" />

                        <span
                            class="text-sm truncate"
                            :class="getTitleClass(element)"
                        >
                            {{ element._draftTitle || element.title }}
                        </span>

                        <Badge v-if="element._isDraft" variant="subtle" theme="blue" size="sm">
                            {{ __('New') }}
                        </Badge>
                        <Badge v-else-if="element._isDeleted" variant="subtle" theme="red" size="sm">
                            {{ __('Deleted') }}
                        </Badge>
                        <Badge v-else-if="element._isMoved" variant="subtle" theme="purple" size="sm">
                            {{ __('Moved') }}
                        </Badge>
                        <Badge v-else-if="element._isModified" variant="subtle" theme="blue" size="sm">
                            {{ __('Modified') }}
                        </Badge>
                        <Badge v-else-if="element._isReordered" variant="subtle" theme="gray" size="sm">
                            {{ __('Reordered') }}
                        </Badge>
                        <Badge v-else-if="!element.is_group && !element.is_published" variant="subtle" theme="orange" size="sm">
                            {{ __('Not Published') }}
                        </Badge>
                    </div>

                    <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity" @click.stop>
                        <Dropdown :options="getDropdownOptions(element)">
                            <Button variant="ghost" size="sm">
                                <LucideMoreHorizontal class="size-4" />
                            </Button>
                        </Dropdown>
                    </div>
                </div>

                <div v-if="element.is_group" v-show="isExpanded(element.name)">
                    <NestedDraggable
                        :items="element.children || []"
                        :level="level + 1"
                        :parent-name="element.name"
                        :space-id="spaceId"
                        :selected-page-id="selectedPageId"
                        :selected-contribution-id="selectedContributionId"
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
import { ref, watch, computed } from 'vue';
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
    selectedContributionId: {
        type: String,
        default: null,
    },
});

const emit = defineEmits(['create', 'delete', 'update']);
const router = useRouter();

const localItems = ref([...props.items]);

watch(() => props.items, (newItems) => {
    localItems.value = [...newItems];
}, { deep: true });

const storageKey = computed(() => `wiki-tree-expanded-nodes-${props.spaceId || 'default'}`);
const expandedNodes = useStorage(storageKey, {});

function isExpanded(name) {
    return expandedNodes.value[name] === true;
}

function toggleExpanded(name) {
    expandedNodes.value[name] = !expandedNodes.value[name];
}

function handleRowClick(element) {
    if (element._isDeleted) {
        return;
    }

    if (element._isDraft) {
        if (element.is_group) {
            // Draft groups can still be expanded/collapsed
            toggleExpanded(element.name);
        } else {
            router.push({
                name: 'DraftContribution',
                params: { spaceId: props.spaceId, contributionId: element._contribution }
            });
        }
        return;
    }

    if (element.is_group) {
        toggleExpanded(element.name);
    } else {
        router.push({ name: 'SpacePage', params: { spaceId: props.spaceId, pageId: element.name } });
    }
}

function getRowClasses(element) {
    const classes = [];

    const isSelectedPage = !element.is_group && element.name === props.selectedPageId;
    const isSelectedDraft = element._isDraft && element._contribution === props.selectedContributionId;

    if (isSelectedPage || isSelectedDraft) {
        classes.push('bg-surface-gray-3');
    }

    if (element._isDeleted) {
        classes.push('cursor-not-allowed', 'opacity-60');
    } else {
        classes.push('cursor-pointer');
    }

    return classes;
}

function getTitleClass(element) {
    if (element._isDeleted) {
        return 'text-ink-gray-4 line-through';
    }
    if (element._isDraft || element.is_published || element.is_group) {
        return 'text-ink-gray-8';
    }
    return 'text-ink-gray-5';
}

function handleChange(evt) {
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
    emit('update', payload);
}

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

    if (element.is_group) {
        options.push(...[
                {
                    label: __('Add Page'),
                    icon: 'file-plus',
                    onClick: () => emit('create', element.name, false),
                },
                {
                    label: __('Add Group'),
                    icon: 'folder-plus',
                    onClick: () => emit('create', element.name, true),
                },
            ]);
    }

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
