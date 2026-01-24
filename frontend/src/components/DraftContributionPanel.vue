<template>
	<div class="h-full flex flex-col">
		<div v-if="crPage" class="h-full flex flex-col">
			<div class="flex items-center justify-between p-6 pb-4 bg-surface-white shrink-0 border-b-2 border-b-gray-500/20">
				<div class="flex items-center gap-2">
					<h1 class="text-2xl font-semibold text-ink-gray-9">{{ crPage.title }}</h1>
					<Badge variant="subtle" theme="blue" size="sm">
						{{ __('Draft') }}
					</Badge>
					<Badge v-if="crPage.is_group" variant="subtle" theme="gray" size="sm">
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

			<div v-if="!crPage.is_group" class="flex-1 overflow-auto px-6 pb-6">
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
import { useChangeRequestMode, useChangeRequest, currentChangeRequest } from '@/composables/useChangeRequest';
import LucideSave from '~icons/lucide/save';
import LucideMoreVertical from '~icons/lucide/more-vertical';
import LucideFolder from '~icons/lucide/folder';
import LucideAlertCircle from '~icons/lucide/alert-circle';

const props = defineProps({
	docKey: {
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
	initChangeRequest,
	loadChanges,
} = useChangeRequestMode(spaceIdRef);

	const {
		updatePage,
		updatePageResource,
		deletePage,
	} = useChangeRequest();

const crPage = ref(null);
const isLoading = ref(true);

const fetchCrPageResource = createResource({
	url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.get_cr_page',
});

async function loadCrPage() {
	if (!currentChangeRequest.value) {
		crPage.value = null;
		return;
	}
	isLoading.value = true;
	try {
		const result = await fetchCrPageResource.submit({
			name: currentChangeRequest.value.name,
			doc_key: props.docKey,
		});
		crPage.value = result;
	} catch (error) {
		console.error('Error loading draft page:', error);
		crPage.value = null;
	} finally {
		isLoading.value = false;
	}
}

onMounted(async () => {
	if (props.spaceId) {
		await initChangeRequest();
		await loadChanges();
	}
	await loadCrPage();
});

watch(() => props.docKey, async (newId) => {
	if (newId) {
		await loadCrPage();
	}
});

watch(() => props.spaceId, async (newSpaceId) => {
	if (newSpaceId) {
		currentChangeRequest.value = null;
		await initChangeRequest();
		await loadChanges();
		await loadCrPage();
	}
});

const editorContent = computed(() => {
	return crPage.value?.content || '';
});

const isSaving = computed(() => {
	return updatePageResource.loading;
});

const editorKey = computed(() => {
	if (crPage.value) {
		return `draft-${props.docKey}-${crPage.value?.doc_key}`;
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
	if (!currentChangeRequest.value || !crPage.value?.doc_key) return;
	try {
		await updatePage(
			currentChangeRequest.value.name,
			crPage.value.doc_key,
			{ content, title: crPage.value.title },
		);
		toast.success(__('Draft updated'));
		await loadChanges();
		await loadCrPage();
		emit('refresh');
	} catch (error) {
		console.error('Error saving draft:', error);
		toast.error(error.messages?.[0] || __('Error saving draft'));
	}
}

async function deleteDraft() {
	if (!currentChangeRequest.value || !crPage.value?.doc_key) return;
	try {
		await deletePage(currentChangeRequest.value.name, crPage.value.doc_key);
		toast.success(__('Draft deleted'));
		await loadChanges();
		emit('refresh');
		router.push({ name: 'SpaceDetails', params: { spaceId: props.spaceId } });
	} catch (error) {
		console.error('Error deleting draft:', error);
		toast.error(error.messages?.[0] || __('Error deleting draft'));
	}
}

</script>
