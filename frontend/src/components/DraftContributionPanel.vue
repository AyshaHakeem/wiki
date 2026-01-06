<template>
    <div class="h-full flex flex-col">
        <div v-if="contribution" class="h-full flex flex-col">
            <ContributionBanner
                :isContributionMode="true"
                :batchStatus="currentBatch?.status || 'Draft'"
                :contributionCount="contributionCount"
                :contributions="contributionsResource.data || []"
                :submitBatchResource="submitBatchResource"
                :withdrawBatchResource="withdrawBatchResource"
                @submit="handleSubmitBatch"
                @withdraw="handleWithdrawBatch"
                @revise="handleReviseBatch"
            />

            <div class="flex items-center justify-between p-6 pb-4 bg-surface-white shrink-0 border-b-2 border-b-gray-500/20">
                <div class="flex items-center gap-2">
                    <h1 class="text-2xl font-semibold text-ink-gray-9">{{ contribution.proposed_title }}</h1>
                    <Badge variant="subtle" theme="blue" size="sm">
                        {{ __('Draft') }}
                    </Badge>
                    <Badge v-if="contribution.proposed_is_group" variant="subtle" theme="gray" size="sm">
                        {{ __('Group') }}
                    </Badge>
                </div>

                <div class="flex items-center gap-2">
                    <Button
                        variant="solid"
                        :loading="isSaving"
                        @click="saveFromHeader"
                    >
                        <template #prefix>
                            <LucideSave class="size-4" />
                        </template>
                        {{ __('Save Draft') }}
                    </Button>
                    <Dropdown :options="menuOptions">
                        <Button variant="outline">
                            <LucideMoreVertical class="size-4" />
                        </Button>
                    </Dropdown>
                </div>
            </div>

            <div v-if="!contribution.proposed_is_group" class="flex-1 overflow-auto px-6 pb-6">
                <WikiEditor v-if="editorKey" :key="editorKey" ref="editorRef" :content="editorContent" :saving="isSaving" @save="saveContent" />
            </div>

            <div v-else class="flex-1 flex items-center justify-center text-ink-gray-5">
                <div class="text-center">
                    <LucideFolder class="size-12 mx-auto mb-4 text-ink-gray-4" />
                    <p>{{ __('This is a draft group.') }}</p>
                    <p class="text-sm">{{ __('Groups organize pages but have no content.') }}</p>
                </div>
            </div>
        </div>

        <div v-else-if="isLoading" class="h-full flex items-center justify-center">
            <LoadingIndicator class="size-8" />
        </div>

        <div v-else class="h-full flex items-center justify-center text-ink-gray-5">
            <div class="text-center">
                <LucideAlertCircle class="size-12 mx-auto mb-4 text-ink-gray-4" />
                <p>{{ __('Draft not found') }}</p>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, watch, toRef, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { createResource, Badge, Button, Dropdown, toast, LoadingIndicator } from "frappe-ui";
import WikiEditor from './WikiEditor.vue';
import ContributionBanner from './ContributionBanner.vue';
import { useContributionMode, useContribution, currentBatch } from '@/composables/useContributionMode';
import LucideSave from '~icons/lucide/save';
import LucideMoreVertical from '~icons/lucide/more-vertical';
import LucideFolder from '~icons/lucide/folder';
import LucideAlertCircle from '~icons/lucide/alert-circle';

const props = defineProps({
    contributionId: {
        type: String,
        required: true
    },
    spaceId: {
        type: String,
        required: false
    }
});

const emit = defineEmits(['refresh']);
const router = useRouter();
const editorRef = ref(null);

const spaceIdRef = toRef(props, 'spaceId');
const {
    contributionCount,
    submitBatchResource,
    withdrawBatchResource,
    initBatch,
    loadContributions,
    submitForReview,
    withdrawBatch,
    contributionsResource,
} = useContributionMode(spaceIdRef);

const {
    updateContribution,
    updateContributionResource,
    deleteContributionResource,
} = useContribution();

const contribution = ref(null);
const isLoading = ref(true);

const fetchContributionResource = createResource({
    url: 'frappe.client.get',
});

async function loadContribution() {
    isLoading.value = true;
    try {
        // First try to find in the already loaded contributions
        const contributions = contributionsResource.data || [];
        let found = contributions.find(c => c.name === props.contributionId || c.temp_id === props.contributionId);

        if (found) {
            contribution.value = found;
        } else {
            // Fetch from server
            const result = await fetchContributionResource.submit({
                doctype: 'Wiki Contribution',
                name: props.contributionId,
            });
            contribution.value = result;
        }
    } catch (error) {
        console.error('Error loading contribution:', error);
        contribution.value = null;
    } finally {
        isLoading.value = false;
    }
}

onMounted(async () => {
    if (props.spaceId) {
        await initBatch();
        await loadContributions();
    }
    await loadContribution();
});

watch(() => props.contributionId, async (newId) => {
    if (newId) {
        await loadContribution();
    }
});

watch(() => props.spaceId, async (newSpaceId) => {
    if (newSpaceId) {
        // Clear shared state immediately to prevent stale data from prior space
        currentBatch.value = null;
        await initBatch();
        await loadContributions();
        await loadContribution();
    }
});

const editorContent = computed(() => {
    return contribution.value?.proposed_content || '';
});

const isSaving = computed(() => {
    return updateContributionResource.loading;
});

const editorKey = computed(() => {
    if (contribution.value) {
        return `draft-${props.contributionId}-${contribution.value.modified || 'new'}`;
    }
    return null;
});

const menuOptions = computed(() => {
    return [
        {
            label: __('Delete Draft'),
            icon: 'trash-2',
            onClick: deleteDraft,
        },
    ];
});

function saveFromHeader() {
    editorRef.value?.saveToDB();
}

async function saveContent(content) {
    try {
        await updateContribution(
            contribution.value.name,
            contribution.value.proposed_title,
            content
        );
        toast.success(__('Draft updated'));

        await loadContributions();
        await loadContribution();
    } catch (error) {
        console.error('Error saving contribution:', error);
        toast.error(error.messages?.[0] || __('Error saving draft'));
    }
}

async function deleteDraft() {
    try {
        await deleteContributionResource.submit({
            name: contribution.value.name,
        });
        toast.success(__('Draft deleted'));

        await loadContributions();
        emit('refresh');

        router.push({ name: 'SpaceDetails', params: { spaceId: props.spaceId } });
    } catch (error) {
        console.error('Error deleting contribution:', error);
        toast.error(error.messages?.[0] || __('Error deleting draft'));
    }
}

async function handleSubmitBatch() {
    try {
        const result = await submitForReview();
        toast.success(__('Contribution submitted for review'));
        if (result?.name) {
            router.push({ name: 'ContributionReview', params: { batchId: result.name } });
        }
    } catch (error) {
        toast.error(error.messages?.[0] || __('Error submitting for review'));
    }
}

async function handleWithdrawBatch() {
    try {
        await withdrawBatch();
        toast.success(__('Contribution withdrawn'));
    } catch (error) {
        toast.error(error.messages?.[0] || __('Error withdrawing contribution'));
    }
}

async function handleReviseBatch() {
    try {
        await withdrawBatch();
        toast.success(__('You can now revise your contribution'));
    } catch (error) {
        toast.error(error.messages?.[0] || __('Error'));
    }
}
</script>
