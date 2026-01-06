<template>
    <div class="h-full flex flex-col">
        <div v-if="wikiDoc.doc" class="h-full flex flex-col">
            <ContributionBanner
                :isContributionMode="isContributionMode"
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
                    <h1 class="text-2xl font-semibold text-ink-gray-9">{{ wikiDoc.doc.title }}</h1>
                    <LucideLock v-if="wikiDoc.doc.is_private" class="size-4 text-ink-gray-5" :title="__('Private')" />
                    <Badge v-if="wikiDoc.doc.is_published" variant="subtle" theme="green" size="sm">
                        {{ __('Published') }}
                    </Badge>
                    <Badge v-else variant="subtle" theme="orange" size="sm">
                        {{ __('Not Published') }}
                    </Badge>
                    <Badge v-if="hasContributionForCurrentPage" variant="subtle" theme="blue" size="sm">
                        {{ __('Has Draft Changes') }}
                    </Badge>
                </div>

                <div class="flex items-center gap-2">
                    <Button
                        v-if="wikiDoc.doc?.is_published"
                        variant="outline"
                        @click="openPage"
                    >
                        <template #prefix>
                            <LucideExternalLink class="size-4" />
                        </template>
                        {{ __('View Page') }}
                    </Button>
                    <Button
                        :variant="isContributionMode ? 'subtle' : 'solid'"
                        :loading="isSaving"
                        @click="saveFromHeader"
                    >
                        <span class="flex items-center gap-2">
                            {{ isContributionMode ? __('Save Draft') : __('Save') }}
                            <kbd v-if="!isContributionMode" class="inline-flex items-center gap-1 rounded bg-white/25 px-1.5 py-0.5 text-[11px] font-medium opacity-80">
                                <span class="text-sm">{{ isMac ? '⌘' : 'Ctrl+' }}</span><span>S</span>
                            </kbd>
                        </span>
                    </Button>
                    <Dropdown :options="menuOptions">
                        <Button variant="outline">
                            <LucideMoreVertical class="size-4" />
                        </Button>
                    </Dropdown>
                </div>
            </div>

            <div class="flex-1 overflow-auto px-6 pb-6">
                <WikiEditor v-if="editorKey" :key="editorKey" ref="editorRef" :content="editorContent" :saving="isSaving" @save="saveContent" />
            </div>
        </div>

        <WikiDocumentSettings
            v-model="showSettingsDialog"
            :pageId="props.pageId"
            :doc="wikiDoc.doc"
            @saved="onSettingsSaved"
        />
    </div>
</template>

<script setup>
import { ref, computed, watch, toRef, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { createDocumentResource, Badge, Button, Dropdown, toast } from "frappe-ui";
import WikiEditor from './WikiEditor.vue';
import WikiDocumentSettings from './WikiDocumentSettings.vue';
import ContributionBanner from './ContributionBanner.vue';
import { useContributionMode, useContribution, currentBatch } from '@/composables/useContributionMode';
import LucideMoreVertical from '~icons/lucide/more-vertical';
import LucideLock from '~icons/lucide/lock';
import LucideExternalLink from '~icons/lucide/external-link';

// Detect if user is on Mac for keyboard shortcut display
const isMac = computed(() => /Mac|iPhone|iPad|iPod/i.test(navigator.userAgent));

const props = defineProps({
    pageId: {
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
const showSettingsDialog = ref(false);

const spaceIdRef = toRef(props, 'spaceId');
const {
    isContributionMode,
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
    createEditContribution,
    updateContribution,
    findContributionForDocument,
    createContributionResource,
    updateContributionResource,
} = useContribution();

const currentPageContribution = ref(null);

const wikiDoc = createDocumentResource({
    doctype: "Wiki Document",
    name: props.pageId,
    auto: true,
});

onMounted(async () => {
    if (isContributionMode.value && props.spaceId) {
        await initBatch();
        await loadContributions();
        findCurrentPageContribution();
    }
});

watch(() => props.pageId, async (newPageId) => {
    if (newPageId) {
        wikiDoc.name = newPageId;
        wikiDoc.reload();
        if (isContributionMode.value) {
            findCurrentPageContribution();
        }
    }
});

watch(() => props.spaceId, async (newSpaceId) => {
    if (newSpaceId && isContributionMode.value) {
        // Clear shared state immediately to prevent stale data from prior space
        currentBatch.value = null;
        await initBatch();
        await loadContributions();
        findCurrentPageContribution();
    }
});

function findCurrentPageContribution() {
    const contributions = contributionsResource.data || [];
    currentPageContribution.value = findContributionForDocument(contributions, props.pageId);
}

const hasContributionForCurrentPage = computed(() => {
    return !!currentPageContribution.value;
});

const editorContent = computed(() => {
    if (isContributionMode.value && currentPageContribution.value && currentPageContribution.value.proposed_content != null) {
        return currentPageContribution.value.proposed_content;
    }
    return wikiDoc.doc?.content || '';
});

const isSaving = computed(() => {
    if (isContributionMode.value) {
        return createContributionResource.loading || updateContributionResource.loading;
    }
    return wikiDoc.setValue.loading;
});

const editorKey = computed(() => {
    if (wikiDoc.doc?.name === props.pageId) {
        const contribMod = currentPageContribution.value?.modified || '';
        return `${props.pageId}-${wikiDoc.doc.modified || 'new'}-${contribMod}`;
    }
    return null;
});

const menuOptions = computed(() => {
    const options = [];

    if (!isContributionMode.value) {
        options.push({
            label: wikiDoc.doc?.is_published ? __('Unpublish') : __('Publish'),
            icon: 'upload-cloud',
            onClick: togglePublish,
        });
    }

    options.push({
        label: __('Settings'),
        icon: 'settings',
        onClick: openSettingsDialog,
    });

    return options;
});

async function togglePublish() {
    const newStatus = wikiDoc.doc?.is_published ? 0 : 1;
    const action = newStatus ? __('published') : __('unpublished');

    try {
        await wikiDoc.setValue.submit({
            is_published: newStatus,
        });
        toast.success(__('Page {0}', [action]));
        emit('refresh');
    } catch (error) {
        toast.error(error.messages?.[0] || __('Error updating publish status'));
    }
}

function openSettingsDialog() {
    showSettingsDialog.value = true;
}

function onSettingsSaved() {
    wikiDoc.reload();
    emit('refresh');
}

function openPage() {
    window.open(`/${wikiDoc.doc.route}`, '_blank');
}

function saveFromHeader() {
    editorRef.value?.saveToDB();
}

async function saveContent(content) {
    if (isContributionMode.value) {
        await saveAsContribution(content);
    } else {
        await saveDirectly(content);
    }
}

async function saveDirectly(content) {
    try {
        await wikiDoc.setValue.submit({ content });
    } catch (error) {
        toast.error(error.messages?.[0] || __('Error saving page'));
    }
}

async function saveAsContribution(content) {
    try {
        if (!currentBatch.value) {
            await initBatch();
        }

        if (!currentBatch.value) {
            toast.error(__('Could not create contribution batch'));
            return;
        }

        if (currentPageContribution.value) {
            await updateContribution(
                currentPageContribution.value.name,
                wikiDoc.doc.title,
                content
            );
            toast.success(__('Draft updated'));
        } else {
            const result = await createEditContribution(
                currentBatch.value.name,
                props.pageId,
                wikiDoc.doc.title,
                content
            );
            currentPageContribution.value = result;
            toast.success(__('Draft saved'));
        }

        await loadContributions();
        findCurrentPageContribution();
    } catch (error) {
        console.error('Error saving contribution:', error);
        toast.error(error.messages?.[0] || __('Error saving draft'));
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
