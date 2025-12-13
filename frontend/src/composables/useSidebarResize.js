import { ref } from 'vue';

export function useSidebarResize(sidebarRef) {
	const storedWidth = localStorage.getItem('wiki-sidebar-width');
	const sidebarWidth = ref(storedWidth ? parseInt(storedWidth) : 280);
	const sidebarResizing = ref(false);

	function startResize(e) {
		e.preventDefault();
		document.addEventListener('mousemove', resize);
		document.addEventListener(
			'mouseup',
			() => {
				document.body.classList.remove('select-none');
				document.body.classList.remove('cursor-col-resize');
				localStorage.setItem(
					'wiki-sidebar-width',
					sidebarWidth.value.toString(),
				);
				sidebarResizing.value = false;
				document.removeEventListener('mousemove', resize);
			},
			{ once: true },
		);
	}

	function resize(e) {
		sidebarResizing.value = true;
		document.body.classList.add('select-none');
		document.body.classList.add('cursor-col-resize');

		// Calculate width relative to sidebar's left position
		const sidebarLeft = sidebarRef.value?.getBoundingClientRect().left || 0;
		let newWidth = e.clientX - sidebarLeft;

		// snap to default width (280)
		const range = [280 - 10, 280 + 10];
		if (newWidth > range[0] && newWidth < range[1]) {
			newWidth = 280;
		}

		// min width: 200px
		if (newWidth < 200) {
			newWidth = 200;
		}
		// max width: 600px
		if (newWidth > 600) {
			newWidth = 600;
		}

		sidebarWidth.value = newWidth;
	}

	return {
		sidebarWidth,
		sidebarResizing,
		startResize,
		resize,
	};
}
