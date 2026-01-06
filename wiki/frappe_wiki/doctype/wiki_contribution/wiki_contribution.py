# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class WikiContribution(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		batch: DF.Link
		new_parent_ref: DF.Data | None
		new_sort_order: DF.Int
		operation: DF.Literal["create", "edit", "delete", "move", "reorder"]
		original_content: DF.MarkdownEditor | None
		original_parent: DF.Link | None
		original_title: DF.Data | None
		parent_ref: DF.Data | None
		proposed_content: DF.MarkdownEditor | None
		proposed_is_group: DF.Check
		proposed_is_published: DF.Check
		proposed_slug: DF.Data | None
		proposed_sort_order: DF.Int
		proposed_title: DF.Data | None
		sequence: DF.Int
		target_document: DF.Link | None
		target_route: DF.Data | None
		temp_id: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.validate_operation_fields()
		self.validate_batch_status()
		self.set_sequence()
		self.snapshot_original()

	def validate_operation_fields(self):
		"""Validate that required fields are set for each operation type."""
		if self.operation == "create":
			if not self.proposed_title:
				frappe.throw(_("Proposed Title is required for create operation"))
			if not self.parent_ref:
				frappe.throw(_("Parent Reference is required for create operation"))
			if not self.temp_id:
				# Auto-generate temp_id if not provided
				self.temp_id = f"temp_{frappe.generate_hash(length=8)}"

		elif self.operation == "edit":
			if not self.target_document:
				frappe.throw(_("Target Document is required for edit operation"))

		elif self.operation == "delete":
			if not self.target_document:
				frappe.throw(_("Target Document is required for delete operation"))

		elif self.operation == "move":
			if not self.target_document:
				frappe.throw(_("Target Document is required for move operation"))
			if not self.new_parent_ref:
				frappe.throw(_("New Parent Reference is required for move operation"))

		elif self.operation == "reorder":
			if not self.target_document:
				frappe.throw(_("Target Document is required for reorder operation"))

	def validate_batch_status(self):
		"""Ensure contributions can only be modified when batch is in Draft status."""
		batch_status = frappe.db.get_value("Wiki Contribution Batch", self.batch, "status")
		if batch_status and batch_status != "Draft":
			frappe.throw(_("Cannot modify contributions in a batch that is {0}").format(batch_status))

	def set_sequence(self):
		"""Auto-set sequence if not provided."""
		if not self.sequence:
			result = frappe.db.sql(
				"""SELECT MAX(sequence) FROM `tabWiki Contribution` WHERE batch = %s""",
				(self.batch,),
			)
			max_sequence = result[0][0] if result and result[0][0] else 0
			self.sequence = max_sequence + 1

	def snapshot_original(self):
		"""Take a snapshot of the original document state for edits."""
		if self.operation in ["edit", "delete", "move", "reorder"] and self.target_document:
			if not self.original_title:  # Only snapshot if not already done
				doc = frappe.get_doc("Wiki Document", self.target_document)
				self.original_title = doc.title
				self.original_content = doc.content
				self.original_parent = doc.parent_wiki_document
				self.target_route = doc.route
				self.original_modified = doc.modified

	def resolve_parent_ref(self, temp_to_real: dict) -> str | None:
		"""
		Resolve parent_ref to an actual Wiki Document name.
		temp_to_real maps temp_ids to real document names.
		"""
		if not self.parent_ref:
			return None

		# Check if it's a temp_id reference
		if self.parent_ref.startswith("temp_"):
			if self.parent_ref in temp_to_real:
				return temp_to_real[self.parent_ref]
			frappe.throw(
				_("Cannot resolve temp_id {0}. Referenced document not yet created.").format(self.parent_ref)
			)

		# It's a real Wiki Document name
		return self.parent_ref

	def resolve_new_parent_ref(self, temp_to_real: dict) -> str | None:
		"""Resolve new_parent_ref for move operations."""
		if not self.new_parent_ref:
			return None

		if self.new_parent_ref.startswith("temp_"):
			if self.new_parent_ref in temp_to_real:
				return temp_to_real[self.new_parent_ref]
			frappe.throw(
				_("Cannot resolve temp_id {0}. Referenced document not yet created.").format(
					self.new_parent_ref
				)
			)

		return self.new_parent_ref

	def apply(self, temp_to_real: dict):
		"""
		Apply this contribution to the live Wiki Document tree.
		Updates temp_to_real with any new documents created.
		"""
		if self.operation == "create":
			self._apply_create(temp_to_real)
		elif self.operation == "edit":
			self._apply_edit()
		elif self.operation == "delete":
			self._apply_delete()
		elif self.operation == "move":
			self._apply_move(temp_to_real)
		elif self.operation == "reorder":
			self._apply_reorder()

	def _apply_create(self, temp_to_real: dict):
		"""Create a new Wiki Document."""
		parent = self.resolve_parent_ref(temp_to_real)

		doc = frappe.new_doc("Wiki Document")
		doc.title = self.proposed_title
		doc.content = self.proposed_content or ""
		doc.parent_wiki_document = parent
		doc.is_group = self.proposed_is_group
		doc.is_published = self.proposed_is_published
		doc.sort_order = self.proposed_sort_order or 0

		# Set route if slug is provided, otherwise let it auto-generate
		if self.proposed_slug:
			doc.route = self.proposed_slug  # Will be corrected in validate

		doc.insert()

		# Map temp_id to real document name
		if self.temp_id:
			temp_to_real[self.temp_id] = doc.name

	def _apply_edit(self):
		"""Update an existing Wiki Document."""
		doc = frappe.get_doc("Wiki Document", self.target_document)

		# Check for conflicts - document was modified after the contribution was created
		if self.original_modified and doc.modified > self.original_modified:
			frappe.throw(
				_(
					"Conflict detected: The document '{0}' has been modified since this contribution was created. "
					"Please reject this contribution and ask the contributor to resubmit with the latest changes."
				).format(doc.title),
				title=_("Merge Conflict"),
			)

		if self.proposed_title:
			doc.title = self.proposed_title
		if self.proposed_content is not None:
			doc.content = self.proposed_content
		if self.proposed_is_published is not None:
			doc.is_published = self.proposed_is_published

		doc.save()

	def _apply_delete(self):
		"""Delete a Wiki Document and its children."""
		doc = frappe.get_doc("Wiki Document", self.target_document)
		doc.delete_with_children()

	def _apply_move(self, temp_to_real: dict):
		"""Move a Wiki Document to a new parent."""
		new_parent = self.resolve_new_parent_ref(temp_to_real)

		doc = frappe.get_doc("Wiki Document", self.target_document)
		doc.parent_wiki_document = new_parent
		if self.new_sort_order is not None:
			doc.sort_order = self.new_sort_order

		# Clear route so it regenerates based on new parent
		doc.route = None
		doc.save()

	def _apply_reorder(self):
		"""Change the sort order of a Wiki Document."""
		doc = frappe.get_doc("Wiki Document", self.target_document)
		if self.proposed_sort_order is not None:
			doc.sort_order = self.proposed_sort_order
		elif self.new_sort_order is not None:
			doc.sort_order = self.new_sort_order
		doc.save()

	def get_diff(self) -> dict:
		"""
		Get a diff between original and proposed content.
		Returns a dict with highlighted changes.
		"""
		if self.operation != "edit":
			return {}

		from wiki.utils import apply_markdown_diff, highlight_changes

		original = self.original_content or ""
		proposed = self.proposed_content or ""

		diff_html = None
		if original != proposed:
			# Get the changes between original and proposed
			_, changes = apply_markdown_diff(original, proposed)
			# Generate highlighted HTML showing the changes
			diff_html = highlight_changes(original, changes)

		return {
			"original": original,
			"proposed": proposed,
			"diff_html": diff_html,
			"title_changed": self.original_title != self.proposed_title,
			"original_title": self.original_title,
			"proposed_title": self.proposed_title,
		}


# API Functions


def check_contribution_permission(name: str, ptype: str = "read"):
	"""
	Check if current user has permission to access the contribution.
	Enforces if_owner policy for users without Wiki Manager/System Manager roles.
	"""
	user = frappe.session.user
	if user == "Administrator":
		return

	user_roles = frappe.get_roles(user)
	# System Manager and Wiki Manager have full access
	if "System Manager" in user_roles or "Wiki Manager" in user_roles:
		return

	# For other users, enforce if_owner policy
	owner = frappe.db.get_value("Wiki Contribution", name, "owner")
	if not owner:
		frappe.throw(_("Wiki Contribution {0} not found").format(name), frappe.DoesNotExistError)

	if owner != user:
		frappe.throw(
			_("You don't have permission to {0} this Wiki Contribution").format(ptype),
			frappe.PermissionError,
		)


def check_batch_permission(batch: str, ptype: str = "read"):
	"""
	Check if current user has permission to access the batch.
	Enforces if_owner policy for users without Wiki Manager/System Manager roles.
	"""
	user = frappe.session.user
	if user == "Administrator":
		return

	user_roles = frappe.get_roles(user)
	# System Manager and Wiki Manager have full access
	if "System Manager" in user_roles or "Wiki Manager" in user_roles:
		return

	# For other users, enforce if_owner policy
	owner = frappe.db.get_value("Wiki Contribution Batch", batch, "owner")
	if not owner:
		frappe.throw(_("Wiki Contribution Batch {0} not found").format(batch), frappe.DoesNotExistError)

	if owner != user:
		frappe.throw(
			_("You don't have permission to {0} contributions in this batch").format(ptype),
			frappe.PermissionError,
		)


@frappe.whitelist()
def create_contribution(
	batch: str,
	operation: str,
	target_document: str | None = None,
	parent_ref: str | None = None,
	temp_id: str | None = None,
	proposed_title: str | None = None,
	proposed_content: str | None = None,
	proposed_slug: str | None = None,
	proposed_is_group: bool = False,
	proposed_is_published: bool = True,
	proposed_sort_order: int = 0,
	new_parent_ref: str | None = None,
	new_sort_order: int | None = None,
) -> dict:
	"""Create a new contribution in a batch."""
	check_batch_permission(batch, "write")
	contrib = frappe.new_doc("Wiki Contribution")
	contrib.batch = batch
	contrib.operation = operation
	contrib.target_document = target_document
	contrib.parent_ref = parent_ref
	contrib.temp_id = temp_id
	contrib.proposed_title = proposed_title
	contrib.proposed_content = proposed_content
	contrib.proposed_slug = proposed_slug
	contrib.proposed_is_group = proposed_is_group
	contrib.proposed_is_published = proposed_is_published
	contrib.proposed_sort_order = proposed_sort_order
	contrib.new_parent_ref = new_parent_ref
	contrib.new_sort_order = new_sort_order
	contrib.insert()

	return contrib.as_dict()


@frappe.whitelist()
def update_contribution(
	name: str,
	proposed_title: str | None = None,
	proposed_content: str | None = None,
	proposed_slug: str | None = None,
	proposed_is_group: bool | None = None,
	proposed_is_published: bool | None = None,
	proposed_sort_order: int | None = None,
	new_parent_ref: str | None = None,
	new_sort_order: int | None = None,
) -> dict:
	"""Update an existing contribution."""
	check_contribution_permission(name, "write")
	contrib = frappe.get_doc("Wiki Contribution", name)

	# Verify batch permission and status
	check_batch_permission(contrib.batch, "write")
	batch_status = frappe.db.get_value("Wiki Contribution Batch", contrib.batch, "status")
	if batch_status and batch_status != "Draft":
		frappe.throw(_("Cannot modify contributions in a batch that is {0}").format(batch_status))

	if proposed_title is not None:
		contrib.proposed_title = proposed_title
	if proposed_content is not None:
		contrib.proposed_content = proposed_content
	if proposed_slug is not None:
		contrib.proposed_slug = proposed_slug
	if proposed_is_group is not None:
		contrib.proposed_is_group = proposed_is_group
	if proposed_is_published is not None:
		contrib.proposed_is_published = proposed_is_published
	if proposed_sort_order is not None:
		contrib.proposed_sort_order = proposed_sort_order
	if new_parent_ref is not None:
		contrib.new_parent_ref = new_parent_ref
	if new_sort_order is not None:
		contrib.new_sort_order = new_sort_order

	contrib.save()
	return contrib.as_dict()


@frappe.whitelist()
def delete_contribution(name: str):
	"""Delete a contribution from a batch."""
	check_contribution_permission(name, "delete")

	# Verify batch permission and status before deletion
	batch = frappe.db.get_value("Wiki Contribution", name, "batch")
	if batch:
		check_batch_permission(batch, "write")
		batch_status = frappe.db.get_value("Wiki Contribution Batch", batch, "status")
		if batch_status and batch_status != "Draft":
			frappe.throw(_("Cannot delete contributions from a batch that is {0}").format(batch_status))

	frappe.delete_doc("Wiki Contribution", name)
	return {"success": True}


@frappe.whitelist()
def get_batch_contributions(batch: str) -> list:
	"""Get all contributions in a batch with details."""
	check_batch_permission(batch, "read")
	contributions = frappe.get_all(
		"Wiki Contribution",
		filters={"batch": batch},
		fields=["*"],
		order_by="sequence asc",
	)

	# Enrich with additional data
	for contrib in contributions:
		if contrib.operation == "edit":
			contrib_doc = frappe.get_doc("Wiki Contribution", contrib.name)
			contrib["diff"] = contrib_doc.get_diff()

	return contributions


@frappe.whitelist()
def get_contribution_diff(name: str) -> dict:
	"""Get the diff for an edit contribution."""
	check_contribution_permission(name, "read")
	contrib = frappe.get_doc("Wiki Contribution", name)
	return contrib.get_diff()


@frappe.whitelist()
def get_merged_tree(wiki_space: str, batch: str | None = None) -> list:
	"""
	Get the Wiki Document tree with pending contributions merged in.
	This provides a preview of what the tree will look like after merge.
	"""
	from frappe.utils.nestedset import get_descendants_of

	# Get the space and its root group
	root_group = frappe.db.get_value("Wiki Space", wiki_space, "root_group")
	if not root_group:
		return []

	# Get live documents
	descendants = get_descendants_of("Wiki Document", root_group, ignore_permissions=True)
	live_docs = frappe.get_all(
		"Wiki Document",
		filters={"name": ("in", descendants)},
		fields=[
			"name",
			"title",
			"is_group",
			"parent_wiki_document",
			"route",
			"content",
			"is_published",
			"sort_order",
		],
	)

	# Build a dict for easy lookup
	doc_map = {doc["name"]: {**doc, "status": "live", "children": []} for doc in live_docs}

	if not batch:
		# No batch, just return live tree
		return _build_tree_from_map(doc_map, root_group)

	# Get contributions from batch
	contributions = frappe.get_all(
		"Wiki Contribution",
		filters={"batch": batch},
		fields=["*"],
		order_by="sequence asc",
	)

	# Apply contributions to create merged view
	temp_docs = {}  # temp_id -> doc dict

	for contrib in contributions:
		if contrib.operation == "create":
			# Add new document to the view
			new_doc = {
				"name": contrib.temp_id,
				"title": contrib.proposed_title,
				"is_group": contrib.proposed_is_group,
				"parent_wiki_document": contrib.parent_ref,
				"route": None,  # Will be generated
				"content": contrib.proposed_content,
				"is_published": contrib.proposed_is_published,
				"sort_order": contrib.proposed_sort_order,
				"status": "new",
				"children": [],
				"contribution": contrib.name,
			}
			temp_docs[contrib.temp_id] = new_doc

		elif contrib.operation == "edit":
			if contrib.target_document in doc_map:
				doc = doc_map[contrib.target_document]
				doc["title"] = contrib.proposed_title or doc["title"]
				doc["content"] = (
					contrib.proposed_content if contrib.proposed_content is not None else doc["content"]
				)
				doc["is_published"] = (
					contrib.proposed_is_published
					if contrib.proposed_is_published is not None
					else doc["is_published"]
				)
				doc["status"] = "modified"
				doc["contribution"] = contrib.name

		elif contrib.operation == "delete":
			if contrib.target_document in doc_map:
				doc_map[contrib.target_document]["status"] = "deleted"
				doc_map[contrib.target_document]["contribution"] = contrib.name

		elif contrib.operation == "move":
			if contrib.target_document in doc_map:
				doc = doc_map[contrib.target_document]
				doc["parent_wiki_document"] = contrib.new_parent_ref
				doc["sort_order"] = (
					contrib.new_sort_order if contrib.new_sort_order is not None else doc["sort_order"]
				)
				doc["status"] = "moved"
				doc["contribution"] = contrib.name

		elif contrib.operation == "reorder":
			if contrib.target_document in doc_map:
				doc = doc_map[contrib.target_document]
				new_order = (
					contrib.proposed_sort_order
					if contrib.proposed_sort_order is not None
					else contrib.new_sort_order
				)
				doc["sort_order"] = new_order if new_order is not None else doc["sort_order"]
				doc["status"] = "reordered"
				doc["contribution"] = contrib.name

	# Merge temp_docs into doc_map
	doc_map.update(temp_docs)

	return _build_tree_from_map(doc_map, root_group)


def _build_tree_from_map(doc_map: dict, root_group: str) -> list:
	"""Build a nested tree structure from a flat doc map."""
	# Find root nodes (direct children of root_group)
	root_nodes = []

	for _name, doc in doc_map.items():
		parent = doc.get("parent_wiki_document")

		if parent == root_group:
			root_nodes.append(doc)
		elif parent in doc_map:
			doc_map[parent]["children"].append(doc)

	# Sort by sort_order
	def sort_nodes(nodes):
		for node in nodes:
			if node.get("children"):
				node["children"] = sort_nodes(node["children"])
		return sorted(nodes, key=lambda x: (x.get("sort_order", 0), x.get("title", "")))

	return sort_nodes(root_nodes)
