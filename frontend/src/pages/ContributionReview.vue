<template>
	<div class="flex flex-col h-full">
		<div class="flex items-center justify-between p-4 border-b border-outline-gray-2 bg-surface-white shrink-0">
			<div class="flex items-center gap-4">
				<Button variant="ghost" icon-left="arrow-left" :route="{ name: 'ChangeRequests' }">
					{{ __('Back') }}
				</Button>
				<div v-if="changeRequest.doc">
					<div class="flex items-center gap-2">
						<h1 class="text-xl font-semibold text-ink-gray-9">{{ changeRequest.doc.title }}</h1>
						<Badge :variant="'subtle'" :theme="getStatusTheme(changeRequest.doc.status)" size="sm">
							{{ changeRequest.doc.status }}
						</Badge>
					</div>
					<p class="text-sm text-ink-gray-5 mt-0.5">
						{{ changeRequest.doc.wiki_space }}
						<span v-if="changeRequest.doc.owner">
							&middot; {{ __('by') }} {{ changeRequest.doc.owner }}
						</span>
					</p>
				</div>
			</div>

			<div v-if="canReview" class="flex items-center gap-2">
				<Button variant="outline" theme="red" @click="showRejectDialog = true">
					<template #prefix>
						<LucideX class="size-4" />
					</template>
					{{ __('Request Changes') }}
				</Button>
				<Button variant="solid" theme="green" :loading="mergeResource.loading" @click="handleApprove">
					<template #prefix>
						<LucideCheck class="size-4" />
					</template>
					{{ __('Merge') }}
				</Button>
			</div>

			<div v-else-if="canWithdraw" class="flex items-center gap-2">
				<Button variant="outline" :loading="withdrawResource.loading" @click="handleWithdraw">
					{{ __('Archive') }}
				</Button>
			</div>
		</div>

		<div class="flex-1 overflow-auto p-4">
			<div
				v-if="reviewNote"
				class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg"
			>
				<div class="flex items-start gap-3">
					<LucideAlertCircle class="size-5 text-red-500 shrink-0 mt-0.5" />
					<div>
						<p class="font-medium text-red-800">{{ __('Changes Requested') }}</p>
						<p class="text-sm text-red-700 mt-1">{{ reviewNote.comment }}</p>
						<p class="text-xs text-red-600 mt-2">
							{{ __('Reviewed by') }} {{ reviewNote.reviewer }} {{ __('on') }} {{ formatDate(reviewNote.reviewed_at) }}
						</p>
					</div>
				</div>
			</div>

			<div class="space-y-4">
				<h3 class="text-lg font-medium text-ink-gray-8">
					{{ __('Changes') }} ({{ changes.data?.length || 0 }})
				</h3>

				<div v-if="changes.loading" class="flex items-center justify-center py-8">
					<LoadingIndicator class="size-8" />
				</div>

				<div v-else-if="changes.data?.length" class="space-y-3">
					<div
						v-for="change in changes.data"
						:key="change.doc_key"
						class="border border-outline-gray-2 rounded-lg overflow-hidden"
					>
						<div
							class="flex items-center justify-between p-4 bg-surface-gray-1 cursor-pointer"
							@click="toggleChange(change.doc_key)"
						>
							<div class="flex items-center gap-3">
								<div
									class="flex items-center justify-center size-8 rounded-full shrink-0"
									:class="getChangeIconClass(change.change_type)"
								>
									<component :is="getChangeIcon(change.change_type)" class="size-4" />
								</div>
								<div>
									<div class="flex items-center gap-2">
										<span class="font-medium text-ink-gray-9">
											{{ change.title || __('Untitled') }}
										</span>
										<Badge variant="subtle" :theme="getChangeTheme(change.change_type)" size="sm">
											{{ getChangeLabel(change.change_type) }}
										</Badge>
									</div>
									<p class="text-sm text-ink-gray-5">
										{{ getChangeDescription(change.change_type, change.is_group) }}
									</p>
								</div>
							</div>
							<LucideChevronDown
								class="size-5 text-ink-gray-4 transition-transform"
								:class="{ 'rotate-180': expandedChanges.has(change.doc_key) }"
							/>
						</div>

						<div v-if="expandedChanges.has(change.doc_key)" class="border-t border-outline-gray-2">
							<div class="p-4">
								<DiffViewer
									v-if="diffsByDocKey[change.doc_key]"
									:old-content="diffsByDocKey[change.doc_key]?.base?.content || ''"
									:new-content="diffsByDocKey[change.doc_key]?.head?.content || ''"
									:file-name="change.title || change.doc_key"
									language="markdown"
								/>
								<div v-else class="flex items-center justify-center py-8">
									<LoadingIndicator class="size-6" />
								</div>
							</div>
						</div>
					</div>
				</div>

				<div v-else class="text-center py-8 text-ink-gray-5">
					{{ __('No changes in this change request.') }}
				</div>
			</div>
		</div>

		<Dialog v-model="showRejectDialog" :options="{ size: 'md' }">
			<template #body-title>
				<h3 class="text-xl font-semibold text-ink-gray-9">{{ __('Request Changes') }}</h3>
			</template>
			<template #body-content>
				<div class="space-y-4">
					<p class="text-ink-gray-7">
						{{ __('Please provide feedback explaining what needs to change.') }}
					</p>
					<FormControl
						v-model="rejectComment"
						type="textarea"
						:label="__('Feedback')"
						:placeholder="__('Enter your feedback...')"
						:rows="4"
					/>
				</div>
			</template>
			<template #actions="{ close }">
				<div class="flex justify-end gap-2">
					<Button variant="outline" @click="close">{{ __('Cancel') }}</Button>
					<Button
						variant="solid"
						theme="red"
						:loading="rejectResource.loading"
						@click="handleReject(close)"
					>
						{{ __('Request Changes') }}
					</Button>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { ref, computed, reactive } from 'vue';
import { createDocumentResource, createResource, Button, Badge, Dialog, FormControl, LoadingIndicator, toast } from 'frappe-ui';
import { userResource } from '@/data/user';
import { isWikiManager, currentChangeRequest } from '@/composables/useChangeRequest';
import DiffViewer from '@/components/DiffViewer.vue';
import LucideChevronDown from '~icons/lucide/chevron-down';
import LucideCheck from '~icons/lucide/check';
import LucideX from '~icons/lucide/x';
import LucideAlertCircle from '~icons/lucide/alert-circle';
import LucideArrowUpDown from '~icons/lucide/arrow-up-down';
import LucidePlus from '~icons/lucide/plus';
import LucidePencil from '~icons/lucide/pencil';
import LucideTrash2 from '~icons/lucide/trash-2';
import LucideFileText from '~icons/lucide/file-text';

const props = defineProps({
	changeRequestId: {
		type: String,
		required: true,
	},
});

const showRejectDialog = ref(false);
const rejectComment = ref('');
const expandedChanges = reactive(new Set());
const diffsByDocKey = reactive({});

const changeRequest = createDocumentResource({
	doctype: 'Wiki Change Request',
	name: props.changeRequestId,
	auto: true,
});

const changes = createResource({
	url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.diff_change_request',
	params: { name: props.changeRequestId, scope: 'summary' },
	auto: true,
});

const diffResource = createResource({
	url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.diff_change_request',
});

const mergeResource = createResource({
	url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.merge_change_request',
});

const rejectResource = createResource({
	url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.review_action',
});

const withdrawResource = createResource({
	url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.archive_change_request',
});

const isManager = computed(() => isWikiManager());
const isOwner = computed(() => changeRequest.doc?.owner === userResource.data?.name);

const canReview = computed(() => {
	return isManager.value && ['In Review', 'Approved'].includes(changeRequest.doc?.status);
});

const canWithdraw = computed(() => {
	return isOwner.value && ['In Review', 'Changes Requested'].includes(changeRequest.doc?.status);
});

const reviewNote = computed(() => {
	if (changeRequest.doc?.status !== 'Changes Requested') return null;
	const reviewer = (changeRequest.doc?.reviewers || []).find(
		(row) => row.status === 'Changes Requested' && row.comment,
	);
	if (!reviewer) return null;
	return {
		comment: reviewer.comment,
		reviewer: reviewer.reviewer,
		reviewed_at: reviewer.reviewed_at,
	};
});

async function toggleChange(docKey) {
	if (expandedChanges.has(docKey)) {
		expandedChanges.delete(docKey);
		return;
	}
	expandedChanges.add(docKey);
	if (!diffsByDocKey[docKey]) {
		try {
			const result = await diffResource.submit({
				name: props.changeRequestId,
				scope: 'page',
				doc_key: docKey,
			});
			diffsByDocKey[docKey] = result;
		} catch (error) {
			toast.error(error.messages?.[0] || __('Error loading diff'));
		}
	}
}

async function handleApprove() {
	try {
		await mergeResource.submit({ name: props.changeRequestId });
		toast.success(__('Change request merged'));
		if (currentChangeRequest.value?.name === props.changeRequestId) {
			currentChangeRequest.value = null;
		}
		changeRequest.reload();
		await changes.submit({ name: props.changeRequestId, scope: 'summary' });
	} catch (error) {
		toast.error(error.messages?.[0] || __('Error merging change request'));
	}
}

async function handleReject(close) {
	if (!rejectComment.value.trim()) {
		toast.warning(__('Please provide feedback'));
		return;
	}

	try {
		await rejectResource.submit({
			name: props.changeRequestId,
			reviewer: userResource.data?.name,
			status: 'Changes Requested',
			comment: rejectComment.value.trim(),
		});
		toast.success(__('Requested changes'));
		rejectComment.value = '';
		close();
		changeRequest.reload();
	} catch (error) {
		toast.error(error.messages?.[0] || __('Error requesting changes'));
	}
}

async function handleWithdraw() {
	try {
		await withdrawResource.submit({ name: props.changeRequestId });
		toast.success(__('Change request archived'));
		changeRequest.reload();
	} catch (error) {
		toast.error(error.messages?.[0] || __('Error archiving change request'));
	}
}

function getStatusTheme(status) {
	switch (status) {
		case 'Draft': return 'blue';
		case 'In Review': return 'orange';
		case 'Changes Requested': return 'red';
		case 'Approved': return 'green';
		case 'Merged': return 'green';
		case 'Archived': return 'gray';
		default: return 'gray';
	}
}

function getChangeIcon(changeType) {
	switch (changeType) {
		case 'added': return LucidePlus;
		case 'deleted': return LucideTrash2;
		case 'modified': return LucidePencil;
		case 'reordered': return LucideArrowUpDown;
		default: return LucideFileText;
	}
}

function getChangeIconClass(changeType) {
	switch (changeType) {
		case 'added': return 'bg-green-100 text-green-600';
		case 'deleted': return 'bg-red-100 text-red-600';
		case 'modified': return 'bg-blue-100 text-blue-600';
		case 'reordered': return 'bg-amber-100 text-amber-600';
		default: return 'bg-gray-100 text-gray-600';
	}
}

function getChangeTheme(changeType) {
	switch (changeType) {
		case 'added': return 'green';
		case 'deleted': return 'red';
		case 'modified': return 'blue';
		case 'reordered': return 'orange';
		default: return 'gray';
	}
}

function getChangeLabel(changeType) {
	switch (changeType) {
		case 'added': return __('New');
		case 'deleted': return __('Deleted');
		case 'modified': return __('Modified');
		case 'reordered': return __('Reordered');
		default: return changeType;
	}
}

function getChangeDescription(changeType, isGroup) {
	switch (changeType) {
		case 'added':
			return isGroup ? __('New group to be created') : __('New page to be created');
		case 'deleted':
			return __('Will be deleted');
		case 'modified':
			return __('Content or metadata updated');
		case 'reordered':
			return __('Order updated');
		default:
			return '';
	}
}

function formatDate(dateStr) {
	if (!dateStr) return '';
	const date = new Date(dateStr);
	return date.toLocaleDateString(undefined, {
		year: 'numeric',
		month: 'short',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit',
	});
}
</script>
