<template>
<Sidebar
	:collapsed="isSidebarCollapsed"
 :header="{
			title: __('Frappe Wiki'),
			logo: '/assets/wiki/images/wiki-logo.png',
			menuItems: [ { label: __('Toggle Theme'), icon: themeIcon, onClick: toggleTheme },]
		}"

		:sections="[
			{
				label: '',
				items: [
					{label: __('Spaces'), icon: LucideRocket, to: { name: 'SpaceList' }},
				]
			}
		]"/>
</template>

<script setup>
import { Sidebar } from "frappe-ui";

import { onMounted, computed, ref } from "vue";
import { useStorage } from "@vueuse/core";
import LucideMoon from "~icons/lucide/moon";
import LucideSun from "~icons/lucide/sun";
import LucideRocket from "~icons/lucide/rocket";

const userTheme = useStorage("user-theme", "dark");

const themeIcon = computed(() => {
	return userTheme.value === "dark" ? LucideSun : LucideMoon;
});

const isSidebarCollapsed  = useStorage("is-sidebar-collapsed", true);

onMounted(() => {
	document.documentElement.setAttribute("data-theme", userTheme.value);
});

function toggleTheme() {
	const currentTheme = userTheme.value;
	const newTheme = currentTheme === "dark" ? "light" : "dark";
	document.documentElement.setAttribute("data-theme", newTheme);
	userTheme.value = newTheme;
}
</script>