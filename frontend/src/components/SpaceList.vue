<template>
  <div class="flex flex-col gap-4 p-4">
    <div class="flex items-center justify-between">
      <h2 class="text-xl font-semibold text-ink-gray-9">{{ __('Wiki Spaces') }}</h2>
      <Button v-if="isManager" variant="solid" @click="showCreateDialog = true">
        <template #prefix>
          <LucidePlus class="h-4 w-4" />
        </template>
        {{ __('New Space') }}
      </Button>
    </div>

    <ListView
      class="h-[calc(100vh-200px)]"
      :columns="columns"
      :rows="spaces.data || []"
      :options="{
        selectable: false,
        showTooltip: true,
        resizeColumn: false,
        getRowRoute: (row) => ({ name: 'SpaceDetails', params: { spaceId: row.name } }),
        emptyState: {
          title: __('No Wiki Spaces'),
          description: isManager ? __('Create your first wiki space to get started') : __('No wiki spaces available'),
          button: isManager ? {
            label: __('New Space'),
            variant: 'solid',
            onClick: () => (showCreateDialog = true),
          } : undefined,
        },
      }"
      row-key="name"
    />

    <Dialog
      v-model="showCreateDialog"
      :options="{
        title: __('Create Wiki Space'),
        size: 'lg',
        actions: [
          {
            label: __('Create'),
            variant: 'solid',
            onClick: handleCreateSpace,
          },
        ],
      }"
    >
      <template #body-content>
        <div class="flex flex-col gap-4">
          <FormControl
            type="text"
            :label="__('Space Name')"
            v-model="newSpace.space_name"
            :placeholder="__('My Wiki Space')"
          />
          <FormControl
            type="text"
            :label="__('Route')"
            required
            :modelValue="newSpace.route"
            @update:modelValue="handleRouteInput"
            :placeholder="__('my-wiki-space')"
            :description="__('The URL path for this wiki space (e.g., /my-wiki-space)')"
          />

          <ErrorMessage :message="spaces.insert.error" />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed } from "vue";
import { useRouter } from "vue-router";
import {
  ListView,
  createListResource,
  Button,
  Dialog,
  FormControl,
  ErrorMessage,
  toast
} from "frappe-ui";
import LucidePlus from "~icons/lucide/plus";
import { isWikiManager } from "@/composables/useContributionMode";

const router = useRouter();
const isManager = computed(() => isWikiManager());

const showCreateDialog = ref(false);
const routeManuallyEdited = ref(false);

const newSpace = reactive({
  space_name: "",
  route: "",
});

function slugify(text) {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, "")
    .replace(/[\s_-]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

watch(
  () => newSpace.space_name,
  (newName) => {
    if (!routeManuallyEdited.value) {
      newSpace.route = slugify(newName);
    }
  }
);

function handleRouteInput(value) {
  if (value !== slugify(newSpace.space_name)) {
    routeManuallyEdited.value = true;
  }
  newSpace.route = value;
}

const columns = [
  {
    label: __("Space Name"),
    key: "space_name",
    width: 2,
  },
  {
    label: __("Route"),
    key: "route",
    width: 2,
  },
];

const spaces = createListResource({
  doctype: "Wiki Space",
  fields: ["name", "space_name", "route", "root_group"],
  orderBy: "creation desc",
  limit: 100,
  auto: true,
  insert: {
    onSuccess: (doc) => {
      showCreateDialog.value = false;
      newSpace.space_name = "";
      newSpace.route = "";
      routeManuallyEdited.value = false;
      toast.success(__('Wiki Space "{0}" created successfully.', [doc.space_name]));
      router.push({ name: "SpaceDetails", params: { spaceId: doc.name } });
    },
  },
});

const handleCreateSpace = () => {
  if (!newSpace.route) {
    return Promise.reject(new Error("Route is required"));
  }

  return spaces.insert.submit({
    space_name: newSpace.space_name,
    route: newSpace.route,
  });
};
</script>