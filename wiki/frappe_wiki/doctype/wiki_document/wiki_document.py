# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.nestedset import NestedSet, get_descendants_of
from frappe.website.page_renderers.base_renderer import BaseRenderer


class WikiDocument(NestedSet):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		content: DF.MarkdownEditor | None
		is_group: DF.Check
		is_published: DF.Check
		lft: DF.Int
		old_parent: DF.Link | None
		parent_wiki_document: DF.Link | None
		rgt: DF.Int
		route: DF.Data | None
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		self.set_route()
		self.set_boilerplate_content()

	def set_boilerplate_content(self):
		if not self.content and not self.is_group:
			self.content = "Welcome to your new wiki page! Start editing this content to add information, images, and more."

	def set_route(self):
		if not self.route:
			# Build route from ancestor path
			route_parts = []

			# For new documents, get_ancestors() won't work as lft/rgt aren't set yet
			# Use parent_wiki_document to build the ancestor chain
			ancestors = []
			if not self.is_new():
				ancestors = self.get_ancestors()
			else:
				# Build ancestor list by traversing parent_wiki_document
				current_parent = self.parent_wiki_document
				while current_parent:
					ancestors.append(current_parent)
					current_parent = frappe.get_cached_value(
						"Wiki Document", current_parent, "parent_wiki_document"
					)

			# Get Wiki Space route as the base
			root_group = None
			if ancestors:
				root_group = ancestors[-1]
			elif self.parent_wiki_document:
				root_group = self.parent_wiki_document

			if root_group:
				space_route = frappe.get_cached_value("Wiki Space", {"root_group": root_group}, "route")
				if space_route:
					route_parts.append(space_route)

			if ancestors:
				# ancestors are ordered from immediate parent to root
				# Exclude the root group (last item) as it's the Wiki Space root
				for ancestor_name in reversed(ancestors[:-1]):
					ancestor_route = frappe.get_cached_value("Wiki Document", ancestor_name, "route")
					if ancestor_route:
						route_parts.append(ancestor_route)

			# Add this document's slug
			slug = frappe.website.utils.cleanup_page_name(self.title).replace("_", "-")
			route_parts.append(slug)

			self.route = "/".join(route_parts)

	def get_edit_link(self) -> str:
		root_group = self.get_ancestors()[-1]
		space_name = frappe.get_cached_value("Wiki Space", {"root_group": root_group}, "name")
		return f"/frontend/spaces/{space_name}/page/{self.name}"

	@frappe.whitelist()
	def get_breadcrumbs(self) -> dict:
		"""Get the breadcrumb trail for this Wiki Document including space info."""
		ancestors = self.get_ancestors()

		# Build breadcrumb items from ancestors (excluding root)
		breadcrumb_items = []
		for ancestor_name in reversed(ancestors):
			doc = frappe.get_cached_doc("Wiki Document", ancestor_name)
			breadcrumb_items.append(
				{
					"name": doc.name,
					"title": doc.title,
					"is_group": doc.is_group,
				}
			)

		# Get the space that owns this document tree
		space = None
		root_group = None

		if ancestors:
			# ancestors are ordered from immediate parent to root, so last item is root
			root_group = ancestors[-1]
		elif self.parent_wiki_document:
			# Document is direct child of root group, parent is the root
			root_group = self.parent_wiki_document

		if root_group:
			space_name = frappe.get_cached_value("Wiki Space", {"root_group": root_group}, "name")
			if space_name:
				space_doc = frappe.get_cached_doc("Wiki Space", space_name)
				space = {
					"name": space_doc.name,
					"space_name": space_doc.space_name,
					"route": space_doc.route,
				}

		return {
			"ancestors": breadcrumb_items,
			"space": space,
			"current": {
				"name": self.name,
				"title": self.title,
			},
		}

	@frappe.whitelist()
	def get_children_count(self) -> int:
		"""Get the count of children for this Wiki Document."""
		descendants = get_descendants_of("Wiki Document", self.name)
		return len(descendants) if descendants else 0

	@frappe.whitelist()
	def delete_with_children(self) -> dict:
		"""Delete this Wiki Document and all its children."""
		descendants = get_descendants_of("Wiki Document", self.name)
		child_count = len(descendants) if descendants else 0

		# Delete all descendants first (NestedSet requires this)
		if descendants:
			for child_name in reversed(descendants):
				frappe.delete_doc("Wiki Document", child_name, force=True)

		# Delete the document itself
		frappe.delete_doc("Wiki Document", self.name, force=True)

		return {"deleted": self.name, "children_deleted": child_count}


class WikiDocumentRenderer(BaseRenderer):
	def can_render(self) -> bool:
		document_name = frappe.db.get_value("Wiki Document", {"route": self.path, "is_published": 1}, "name")
		if document_name:
			self.wiki_doc_name = document_name
			return True

		return False

	def render(self):
		doc = frappe.get_cached_doc("Wiki Document", self.wiki_doc_name)

		wiki_space_root = doc.get_ancestors()[-1]
		wiki_space = frappe.get_cached_value("Wiki Space", {"root_group": wiki_space_root}, "name")
		wiki_space = frappe.get_cached_doc("Wiki Space", wiki_space)

		descendants = get_descendants_of("Wiki Document", wiki_space_root)
		nested_tree = build_nested_wiki_tree(descendants)

		# Get adjacent documents for prev/next navigation
		adjacent_docs = get_adjacent_documents(nested_tree, doc.route)

		content_html = frappe.utils.md_to_html(doc.content)
		html = frappe.render_template(
			"templates/wiki/document.html",
			{
				"doc": doc,
				"wiki_space": wiki_space,
				"rendered_content": content_html,
				"raw_markdown": doc.content or "",
				"nested_tree": nested_tree,
				"prev_doc": adjacent_docs["prev"],
				"next_doc": adjacent_docs["next"],
			},
		)
		return self.build_response(html)


def build_nested_wiki_tree(documents: list[str]):
	# Create a mapping of document name to document data
	wiki_documents = frappe.db.get_all(
		"Wiki Document",
		fields=["name", "title", "is_group", "parent_wiki_document", "route"],
		filters={"name": ("in", documents)},
		or_filters={"is_published": 1, "is_group": 1},
		order_by="lft asc",
	)

	doc_map = {doc["name"]: {**doc, "children": []} for doc in wiki_documents}

	# Find root nodes and build the tree
	root_nodes = []

	for doc in wiki_documents:
		parent_name = doc["parent_wiki_document"]

		# If parent exists in our dataset, add as child
		if parent_name and parent_name in doc_map:
			doc_map[parent_name]["children"].append(doc_map[doc["name"]])
		else:
			# This is a root node (parent not in our dataset)
			root_nodes.append(doc_map[doc["name"]])

	# Remove empty groups recursively
	def remove_empty_groups(nodes):
		filtered_nodes = []
		for node in nodes:
			if node["is_group"]:
				# Recursively filter children first
				node["children"] = remove_empty_groups(node["children"])
				# Only include group if it has children with content
				if has_published_content(node):
					filtered_nodes.append(node)
			else:
				# Include non-group nodes (they are already published due to DB filtering)
				filtered_nodes.append(node)
		return filtered_nodes

	def has_published_content(node):
		# If it's not a group, it has content (already filtered to be published at DB level)
		if not node["is_group"]:
			return True

		# If it's a group, check if any of its children have content
		if node["is_group"]:
			for child in node["children"]:
				if has_published_content(child):
					return True

		return False

	return remove_empty_groups(root_nodes)


@frappe.whitelist()
def get_breadcrumbs(name: str) -> dict:
	"""Get the breadcrumb trail for a Wiki Document including space info."""
	doc = frappe.get_cached_doc("Wiki Document", name)
	return doc.get_breadcrumbs()


def get_adjacent_documents(nested_tree: list, current_route: str) -> dict:
	"""
	Get the previous and next documents based on the flattened tree order.
	Only returns non-group documents (actual pages).

	Args:
		nested_tree: The nested tree structure from build_nested_wiki_tree
		current_route: The route of the current document

	Returns:
		dict with 'prev' and 'next' keys, each containing {title, route} or None
	"""

	def flatten_tree(nodes: list) -> list:
		"""Flatten the nested tree into a list of non-group documents in order."""
		result = []
		for node in nodes:
			if not node.get("is_group"):
				result.append({"title": node["title"], "route": node["route"]})
			if node.get("children"):
				result.extend(flatten_tree(node["children"]))
		return result

	flat_list = flatten_tree(nested_tree)

	# Find current document index
	current_index = None
	for i, doc in enumerate(flat_list):
		if doc["route"] == current_route:
			current_index = i
			break

	result = {"prev": None, "next": None}

	if current_index is not None:
		if current_index > 0:
			result["prev"] = flat_list[current_index - 1]
		if current_index < len(flat_list) - 1:
			result["next"] = flat_list[current_index + 1]

	return result
