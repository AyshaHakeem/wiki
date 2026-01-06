<template>
	<div class="flex flex-col h-full">
		<div class="flex items-center justify-between p-4 border-b border-outline-gray-2 bg-surface-white shrink-0">
			<div class="flex items-center gap-4">
				<Button variant="ghost" icon-left="arrow-left" :route="{ name: 'Contributions' }">
					{{ __('Back') }}
				</Button>
				<div v-if="batch.doc">
					<div class="flex items-center gap-2">
						<h1 class="text-xl font-semibold text-ink-gray-9">{{ batch.doc.title }}</h1>
						<Badge :variant="'subtle'" :theme="getStatusTheme(batch.doc.status)" size="sm">
							{{ batch.doc.status }}
						</Badge>
					</div>
					<p class="text-sm text-ink-gray-5 mt-0.5">
						{{ batch.doc.wiki_space_name || batch.doc.wiki_space }}
						<span v-if="batch.doc.contributor_name">
							&middot; {{ __('by') }} {{ batch.doc.contributor_name }}
						</span>
					</p>
				</div>
			</div>

			<div v-if="canReview" class="flex items-center gap-2">
				<Button variant="outline" theme="red" @click="showRejectDialog = true">
					<template #prefix>
						<LucideX class="size-4" />
					</template>
					{{ __('Reject') }}
				</Button>
				<Button variant="solid" theme="green" :loading="approveResource.loading" @click="handleApprove">
					<template #prefix>
						<LucideCheck class="size-4" />
					</template>
					{{ __('Approve') }}
				</Button>
			</div>

			<div v-else-if="canWithdraw" class="flex items-center gap-2">
				<Button variant="outline" :loading="withdrawResource.loading" @click="handleWithdraw">
					{{ __('Withdraw') }}
				</Button>
			</div>
		</div>

		<div class="flex-1 overflow-auto p-4">
			<div
				v-if="batch.doc?.status === 'Rejected' && batch.doc?.review_comment"
				class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg"
			>
				<div class="flex items-start gap-3">
					<LucideAlertCircle class="size-5 text-red-500 shrink-0 mt-0.5" />
					<div>
						<p class="font-medium text-red-800">{{ __('Changes Requested') }}</p>
						<p class="text-sm text-red-700 mt-1">{{ batch.doc.review_comment }}</p>
						<p class="text-xs text-red-600 mt-2">
							{{ __('Reviewed by') }} {{ batch.doc.reviewed_by }} {{ __('on') }} {{ formatDate(batch.doc.reviewed_at) }}
						</p>
					</div>
				</div>
			</div>

			<div class="space-y-4">
				<h3 class="text-lg font-medium text-ink-gray-8">
					{{ __('Changes') }} ({{ contributions.data?.length || 0 }})
				</h3>

				<div v-if="contributions.loading" class="flex items-center justify-center py-8">
					<LoadingIndicator class="size-8" />
				</div>

				<div v-else-if="contributions.data?.length" class="space-y-3">
					<div
						v-for="contrib in contributions.data"
						:key="contrib.name"
						class="border border-outline-gray-2 rounded-lg overflow-hidden"
					>
						<!-- Contribution header -->
						<div
							class="flex items-center justify-between p-4 bg-surface-gray-1 cursor-pointer"
							@click="toggleContribution(contrib.name)"
						>
							<div class="flex items-center gap-3">
								<div
									class="flex items-center justify-center size-8 rounded-full shrink-0"
									:class="getOperationIconClass(contrib.operation)"
								>
									<component :is="getOperationIcon(contrib.operation)" class="size-4" />
								</div>
								<div>
									<div class="flex items-center gap-2">
										<span class="font-medium text-ink-gray-9">
											{{ getContributionTitle(contrib) }}
										</span>
										<Badge variant="subtle" :theme="getOperationTheme(contrib.operation)" size="sm">
											{{ getOperationLabel(contrib.operation) }}
										</Badge>
									</div>
									<p class="text-sm text-ink-gray-5">
										{{ getContributionDescription(contrib) }}
									</p>
								</div>
							</div>
							<LucideChevronDown
								class="size-5 text-ink-gray-4 transition-transform"
								:class="{ 'rotate-180': expandedContributions.has(contrib.name) }"
							/>
						</div>

						<!-- Contribution content (expandable) -->
						<div v-if="expandedContributions.has(contrib.name)" class="border-t border-outline-gray-2">
							<!-- For edit operations, show diff -->
							<div v-if="contrib.operation === 'edit'" class="p-4">
								<div class="grid grid-cols-2 gap-4">
									<div>
										<h4 class="text-sm font-medium text-ink-gray-6 mb-2">{{ __('Original') }}</h4>
										<div class="prose prose-sm max-w-none p-3 bg-surface-gray-1 rounded border border-outline-gray-2 max-h-96 overflow-auto">
											<div v-html="renderMarkdown(contrib.original_content || '')" />
										</div>
									</div>
									<div>
										<h4 class="text-sm font-medium text-ink-gray-6 mb-2">{{ __('Proposed') }}</h4>
										<div class="prose prose-sm max-w-none p-3 bg-surface-gray-1 rounded border border-outline-gray-2 max-h-96 overflow-auto">
											<div v-html="renderMarkdown(contrib.proposed_content || '')" />
										</div>
									</div>
								</div>
							</div>

							<!-- For create operations, show proposed content -->
							<div v-else-if="contrib.operation === 'create'" class="p-4">
								<h4 class="text-sm font-medium text-ink-gray-6 mb-2">{{ __('New Content') }}</h4>
								<div class="prose prose-sm max-w-none p-3 bg-surface-gray-1 rounded border border-outline-gray-2 max-h-96 overflow-auto">
									<div v-html="renderMarkdown(contrib.proposed_content || '')" />
								</div>
							</div>

							<!-- For delete, move, reorder - just show info -->
							<div v-else class="p-4 text-sm text-ink-gray-6">
								<div v-if="contrib.operation === 'delete'">
									{{ __('This page will be deleted.') }}
								</div>
								<div v-else-if="contrib.operation === 'move'">
									{{ __('This page will be moved to a new location.') }}
								</div>
								<div v-else-if="contrib.operation === 'reorder'">
									{{ __('This page will be reordered within its parent.') }}
								</div>
							</div>
						</div>
					</div>
				</div>

				<div v-else class="text-center py-8 text-ink-gray-5">
					{{ __('No changes in this contribution.') }}
				</div>
			</div>
		</div>

		<Dialog v-model="showRejectDialog" :options="{ size: 'md' }">
			<template #body-title>
				<h3 class="text-xl font-semibold text-ink-gray-9">{{ __('Reject Contribution') }}</h3>
			</template>
			<template #body-content>
				<div class="space-y-4">
					<p class="text-ink-gray-7">
						{{ __('Please provide feedback for the contributor explaining why the changes are being rejected.') }}
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
						{{ __('Reject') }}
					</Button>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { ref, computed, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { createDocumentResource, createResource, Button, Badge, Dialog, FormControl, LoadingIndicator, toast } from 'frappe-ui';
import { userResource } from '@/data/user';
import { isWikiManager } from '@/composables/useContributionMode';
import { marked } from 'marked';
import LucideChevronDown from '~icons/lucide/chevron-down';
import LucideCheck from '~icons/lucide/check';
import LucideX from '~icons/lucide/x';
import LucideAlertCircle from '~icons/lucide/alert-circle';
import LucidePlus from '~icons/lucide/plus';
import LucidePencil from '~icons/lucide/pencil';
import LucideTrash2 from '~icons/lucide/trash-2';
import LucideMove from '~icons/lucide/move';
import LucideArrowUpDown from '~icons/lucide/arrow-up-down';
import LucideFileText from '~icons/lucide/file-text';

const props = defineProps({
	batchId: {
		type: String,
		required: true,
	},
});

const router = useRouter();

const showRejectDialog = ref(false);
const rejectComment = ref('');
const expandedContributions = reactive(new Set());

const batch = createDocumentResource({
	doctype: 'Wiki Contribution Batch',
	name: props.batchId,
	auto: true,
});

const contributions = createResource({
	url: 'wiki.frappe_wiki.doctype.wiki_contribution.wiki_contribution.get_batch_contributions',
	params: { batch: props.batchId },
	auto: true,
});

const approveResource = createResource({
	url: 'wiki.api.contributions.approve_contribution_batch',
});

const rejectResource = createResource({
	url: 'wiki.api.contributions.reject_contribution_batch',
});

const withdrawResource = createResource({
	url: 'wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch.withdraw_batch',
});

const isManager = computed(() => isWikiManager());
const isOwner = computed(() => batch.doc?.contributor === userResource.data?.name);

const canReview = computed(() => {
	return isManager.value && ['Submitted', 'Under Review'].includes(batch.doc?.status);
});

const canWithdraw = computed(() => {
	return isOwner.value && ['Submitted', 'Under Review'].includes(batch.doc?.status);
});

function toggleContribution(name) {
	if (expandedContributions.has(name)) {
		expandedContributions.delete(name);
	} else {
		expandedContributions.add(name);
	}
}

async function handleApprove() {
	try {
		await approveResource.submit({ batch_name: props.batchId });
		toast.success(__('Contribution approved and merged'));
		batch.reload();
	} catch (error) {
		toast.error(error.messages?.[0] || __('Error approving contribution'));
	}
}

async function handleReject(close) {
	if (!rejectComment.value.trim()) {
		toast.warning(__('Please provide feedback'));
		return;
	}

	try {
		await rejectResource.submit({
			batch_name: props.batchId,
			comment: rejectComment.value.trim(),
		});
		toast.success(__('Contribution rejected'));
		rejectComment.value = '';
		close();
		batch.reload();
	} catch (error) {
		toast.error(error.messages?.[0] || __('Error rejecting contribution'));
	}
}

async function handleWithdraw() {
	try {
		await withdrawResource.submit({ batch_name: props.batchId });
		toast.success(__('Contribution withdrawn'));
		batch.reload();
	} catch (error) {
		toast.error(error.messages?.[0] || __('Error withdrawing contribution'));
	}
}

function getStatusTheme(status) {
	switch (status) {
		case 'Draft': return 'blue';
		case 'Submitted': return 'orange';
		case 'Under Review': return 'orange';
		case 'Approved': return 'green';
		case 'Rejected': return 'red';
		case 'Merged': return 'green';
		default: return 'gray';
	}
}

const OPERATION_CONFIG = {
	create: {
		icon: LucidePlus,
		iconClass: 'bg-green-100 text-green-600',
		theme: 'green',
		label: __('New'),
	},
	edit: {
		icon: LucidePencil,
		iconClass: 'bg-blue-100 text-blue-600',
		theme: 'blue',
		label: __('Edit'),
	},
	delete: {
		icon: LucideTrash2,
		iconClass: 'bg-red-100 text-red-600',
		theme: 'red',
		label: __('Delete'),
	},
	move: {
		icon: LucideMove,
		iconClass: 'bg-purple-100 text-purple-600',
		theme: 'purple',
		label: __('Move'),
	},
	reorder: {
		icon: LucideArrowUpDown,
		iconClass: 'bg-gray-100 text-gray-600',
		theme: 'gray',
		label: __('Reorder'),
	},
};

function getOperationIcon(operation) {
	return OPERATION_CONFIG[operation]?.icon || LucideFileText;
}

function getOperationIconClass(operation) {
	return OPERATION_CONFIG[operation]?.iconClass || 'bg-gray-100 text-gray-600';
}

function getOperationTheme(operation) {
	return OPERATION_CONFIG[operation]?.theme || 'gray';
}

function getOperationLabel(operation) {
	return OPERATION_CONFIG[operation]?.label || operation;
}

function getContributionTitle(contrib) {
	if (contrib.operation === 'create') {
		return contrib.proposed_title || __('Untitled');
	}
	if (contrib.operation === 'edit') {
		return contrib.proposed_title || contrib.original_title || __('Untitled');
	}
	return contrib.original_title || contrib.target_route || __('Unknown');
}

function getContributionDescription(contrib) {
	switch (contrib.operation) {
		case 'create':
			return contrib.proposed_is_group
				? __('New group to be created')
				: __('New page to be created');
		case 'edit':
			const changes = [];
			if (contrib.proposed_title && contrib.proposed_title !== contrib.original_title) {
				changes.push(__('title'));
			}
			if (contrib.proposed_content && contrib.proposed_content !== contrib.original_content) {
				changes.push(__('content'));
			}
			return changes.length > 0
				? __('Changed: {0}', [changes.join(', ')])
				: __('Content modified');
		case 'delete':
			return __('Will be deleted');
		case 'move':
			return __('Will be moved to a new location');
		case 'reorder':
			return __('Position changed');
		default:
			return '';
	}
}

function renderMarkdown(content) {
	if (!content) return '';
	try {
		return marked.parse(content);
	} catch (e) {
		return content;
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
