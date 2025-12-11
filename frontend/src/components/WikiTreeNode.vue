<template>
    <div>
        <!-- Node Row -->
        <div 
            class="flex items-center justify-between px-4 py-2 hover:bg-surface-gray-2 group border-b border-outline-gray-1 cursor-pointer"
            :style="{ paddingLeft: `${level * 24 + 16}px` }"
            @click="handleRowClick"
        >
            <div class="flex items-center gap-2 flex-1 min-w-0">
                <!-- Expand/Collapse Toggle for Groups -->
                <button 
                    v-if="node.is_group" 
                    class="p-0.5 hover:bg-surface-gray-3 rounded"
                    @click.stop="toggleExpanded"
                >
                    <LucideChevronRight 
                        class="size-4 text-ink-gray-5 transition-transform duration-200" 
                        :class="{ 'rotate-90': isExpanded }"
                    />
                </button>
                <div v-else class="w-5" />

                <!-- Icon -->
                <LucideFolder v-if="node.is_group" class="size-4 text-ink-gray-5 flex-shrink-0" />
                <LucideFileText v-else class="size-4 text-ink-gray-5 flex-shrink-0" />

                <!-- Title -->
                <span 
                    class="text-sm truncate" 
                    :class="(node.is_published || node.is_group) ? 'text-ink-gray-8' : 'text-ink-gray-5'"
                >
                    {{ node.title }}
                </span>

                <!-- Unpublished Badge (only for pages, not groups) -->
                <Badge v-if="!node.is_group && !node.is_published" variant="subtle" theme="orange" size="sm">
                    {{ __('Unpublished') }}
                </Badge>
            </div>

            <!-- Actions -->
            <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity" @click.stop>
                <Dropdown :options="dropdownOptions">
                    <Button variant="ghost" size="sm">
                        <LucideMoreHorizontal class="size-4" />
                    </Button>
                </Dropdown>
            </div>
        </div>

        <!-- Children (collapsed by default for groups) -->
        <div v-if="node.is_group && isExpanded && node.children?.length > 0">
            <WikiTreeNode
                v-for="child in node.children"
                :key="child.name"
                :node="child"
                :level="level + 1"
                @create="(parent, isGroup) => emit('create', parent, isGroup)"
                @delete="(n) => emit('delete', n)"
                @refresh="emit('refresh')"
            />
        </div>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { Dropdown, Badge, createResource, toast } from 'frappe-ui';
import LucideChevronRight from '~icons/lucide/chevron-right';
import LucideFolder from '~icons/lucide/folder';
import LucideFileText from '~icons/lucide/file-text';
import LucideMoreHorizontal from '~icons/lucide/more-horizontal';

const props = defineProps({
    node: {
        type: Object,
        required: true,
    },
    level: {
        type: Number,
        default: 0,
    },
});

const emit = defineEmits(['create', 'delete', 'refresh']);
const router = useRouter();

const isExpanded = ref(true);

function toggleExpanded() {
    isExpanded.value = !isExpanded.value;
}

function handleRowClick() {
    if (props.node.is_group) {
        // Toggle expand/collapse for groups
        toggleExpanded();
    } else {
        // Navigate to edit page for pages
        router.push({ name: 'WikiDocument', params: { pageId: props.node.name } });
    }
}

// Publish/Unpublish Resource
const publishResource = createResource({
    url: 'frappe.client.set_value',
    makeParams() {
        return {
            doctype: 'Wiki Document',
            name: props.node.name,
            fieldname: {
                is_published: props.node.is_published ? 0 : 1,
            },
        };
    },
    onSuccess() {
        const action = props.node.is_published ? __('unpublished') : __('published');
        toast.success(__('Page {0}', [action]));
        emit('refresh');
    },
    onError(error) {
        toast.error(error.messages?.[0] || __('Error updating publish status'));
    },
});

async function togglePublish() {
    await publishResource.submit();
}

const dropdownOptions = computed(() => {
    const options = [];

    // Add child options for groups
    if (props.node.is_group) {
        options.push({
            group: __('Add'),
            items: [
                {
                    label: __('Page'),
                    icon: 'file-plus',
                    onClick: () => emit('create', props.node.name, false),
                },
                {
                    label: __('Group'),
                    icon: 'folder-plus',
                    onClick: () => emit('create', props.node.name, true),
                },
            ],
        });
    }

    // Publish/Unpublish option for non-groups (pages)
    if (!props.node.is_group) {
        options.push({
            label: publishResource.loading 
                ? __('Publishing...') 
                : (props.node.is_published ? __('Unpublish') : __('Publish')),
            icon: props.node.is_published ? 'eye-off' : 'eye',
            onClick: togglePublish,
        });
    }

    // Danger zone - only show delete if it's not a group with children
    const hasChildren = props.node.is_group && props.node.children?.length > 0;
    if (!hasChildren) {
        options.push({
            group: __('Danger'),
            items: [
                {
                    label: __('Delete'),
                    icon: 'trash-2',
                    theme: 'red',
                    onClick: () => emit('delete', props.node),
                },
            ],
        });
    }

    return options;
});
</script>
