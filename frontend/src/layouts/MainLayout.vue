<template>
	<div class="flex h-screen w-full flex-row shadow">
        <Sidebar />
        <div class="flex-1 h-full min-w-0">
			<slot></slot>
        </div>
	</div>
</template>

<script setup>
import Sidebar from '../components/Sidebar.vue';
</script>