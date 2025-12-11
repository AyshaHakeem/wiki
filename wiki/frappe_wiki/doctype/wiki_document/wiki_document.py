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
			self.content = f"# {self.title}\n\nWelcome to your new wiki page! Start editing this content to add information, images, and more."

	def set_route(self):
		if not self.route:
			self.route = frappe.website.utils.cleanup_page_name(self.title).replace("_", "-")

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

		content_html = frappe.utils.md_to_html(doc.content)
		html = frappe.render_template(
			"templates/wiki/document.html",
			{
				"doc": doc,
				"wiki_space": wiki_space,
				"rendered_content": content_html,
				"nested_tree": nested_tree,
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
