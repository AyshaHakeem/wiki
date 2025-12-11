<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <h2 class="text-xl font-semibold text-ink-gray-9">Wiki Spaces</h2>
      <Button variant="solid" @click="showCreateDialog = true">
        <template #prefix>
          <LucidePlus class="h-4 w-4" />
        </template>
        New Space
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
        emptyState: {
          title: 'No Wiki Spaces',
          description: 'Create your first wiki space to get started',
          button: {
            label: 'New Space',
            variant: 'solid',
            onClick: () => (showCreateDialog = true),
          },
        },
      }"
      row-key="name"
    />

    <Dialog
      v-model="showCreateDialog"
      :options="{
        title: 'Create Wiki Space',
        size: 'lg',
        actions: [
          {
            label: 'Create',
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
            label="Space Name"
            v-model="newSpace.space_name"
            placeholder="My Wiki Space"
          />
          <FormControl
            type="text"
            label="Route"
            required
            :modelValue="newSpace.route"
            @update:modelValue="handleRouteInput"
            placeholder="my-wiki-space"
            :description="'The URL path for this wiki space (e.g., /my-wiki-space)'"
          />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from "vue";
import {
  ListView,
  createListResource,
  Button,
  Dialog,
  FormControl,
} from "frappe-ui";
import LucidePlus from "~icons/lucide/plus";

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
    label: "Space Name",
    key: "space_name",
    width: 2,
  },
  {
    label: "Route",
    key: "route",
    width: 2,
  },
];

const spaces = createListResource({
  doctype: "Wiki Space",
  fields: ["name", "space_name", "route"],
  orderBy: "creation desc",
  pageLength: 20,
  auto: true,
  insert: {
    onSuccess: () => {
      showCreateDialog.value = false;
      newSpace.space_name = "";
      newSpace.route = "";
      routeManuallyEdited.value = false;
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