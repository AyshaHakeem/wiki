# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import hashlib
from typing import Any

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from frappe.website.utils import cleanup_page_name


class WikiRevision(Document):
	pass


def create_revision_from_live_tree(
	wiki_space: str,
	message: str | None = None,
	change_request: str | None = None,
	parent_revision: str | None = None,
	is_working: int = 0,
	is_merge: int = 0,
) -> Document:
	space = frappe.get_doc("Wiki Space", wiki_space)
	root = frappe.get_doc("Wiki Document", space.root_group)

	docs = frappe.get_all(
		"Wiki Document",
		fields=[
			"name",
			"doc_key",
			"title",
			"slug",
			"is_group",
			"is_published",
			"is_external_link",
			"external_url",
			"parent_wiki_document",
			"sort_order",
			"content",
			"lft",
			"rgt",
		],
		filters={"lft": (">=", root.lft), "rgt": ("<=", root.rgt)},
		order_by="lft asc",
	)

	for doc in docs:
		if not doc.get("doc_key"):
			doc["doc_key"] = frappe.generate_hash(length=12)
			frappe.db.set_value(
				"Wiki Document",
				doc["name"],
				"doc_key",
				doc["doc_key"],
				update_modified=False,
			)

	name_to_key = {doc["name"]: doc["doc_key"] for doc in docs}

	revision = frappe.new_doc("Wiki Revision")
	revision.wiki_space = wiki_space
	revision.change_request = change_request
	revision.parent_revision = parent_revision
	revision.message = message or ""
	revision.is_merge = 1 if is_merge else 0
	revision.is_working = 1 if is_working else 0
	revision.created_by = frappe.session.user
	revision.created_at = now_datetime()
	revision.insert()

	for doc in docs:
		content = doc.get("content") or ""
		content_blob = get_or_create_content_blob(content)
		item = frappe.new_doc("Wiki Revision Item")
		item.revision = revision.name
		item.doc_key = doc.get("doc_key")
		item.title = doc.get("title")
		item.slug = doc.get("slug") or cleanup_page_name(doc.get("title") or "")
		item.is_group = doc.get("is_group")
		item.is_published = doc.get("is_published")
		item.is_external_link = doc.get("is_external_link")
		item.external_url = doc.get("external_url")
		item.parent_key = name_to_key.get(doc.get("parent_wiki_document"))
		item.order_index = doc.get("sort_order") or 0
		item.content_blob = content_blob
		item.is_deleted = 0
		item.insert()

	recompute_revision_hashes(revision.name)
	return revision


def clone_revision(
	base_revision: str,
	change_request: str | None = None,
	parent_revision: str | None = None,
	is_working: int = 0,
) -> Document:
	base = frappe.get_doc("Wiki Revision", base_revision)
	new_revision = frappe.new_doc("Wiki Revision")
	new_revision.wiki_space = base.wiki_space
	new_revision.change_request = change_request
	new_revision.parent_revision = parent_revision or base_revision
	new_revision.message = base.message
	new_revision.is_merge = 0
	new_revision.is_working = 1 if is_working else 0
	new_revision.created_by = frappe.session.user
	new_revision.created_at = now_datetime()
	new_revision.insert()

	items = frappe.get_all(
		"Wiki Revision Item",
		fields=[
			"doc_key",
			"title",
			"slug",
			"is_group",
			"is_published",
			"is_external_link",
			"external_url",
			"parent_key",
			"order_index",
			"content_blob",
			"is_deleted",
		],
		filters={"revision": base_revision},
	)

	for item in items:
		new_item = frappe.new_doc("Wiki Revision Item")
		new_item.revision = new_revision.name
		new_item.doc_key = item["doc_key"]
		new_item.title = item.get("title")
		new_item.slug = item.get("slug")
		new_item.is_group = item.get("is_group")
		new_item.is_published = item.get("is_published")
		new_item.is_external_link = item.get("is_external_link")
		new_item.external_url = item.get("external_url")
		new_item.parent_key = item.get("parent_key")
		new_item.order_index = item.get("order_index")
		new_item.content_blob = item.get("content_blob")
		new_item.is_deleted = item.get("is_deleted")
		new_item.insert()

	recompute_revision_hashes(new_revision.name)
	return new_revision


def get_or_create_content_blob(content: str, content_type: str = "markdown") -> str:
	content = content or ""
	hash_value = hashlib.sha256(content.encode("utf-8")).hexdigest()
	existing = frappe.db.get_value("Wiki Content Blob", {"hash": hash_value}, "name")
	if existing:
		return existing

	blob = frappe.new_doc("Wiki Content Blob")
	blob.hash = hash_value
	blob.content = content
	blob.content_type = content_type
	blob.size = len(content.encode("utf-8"))
	blob.created_by = frappe.session.user
	blob.created_at = now_datetime()
	blob.insert(ignore_permissions=True)
	return blob.name


def recompute_revision_hashes(revision: str) -> None:
	items = frappe.get_all(
		"Wiki Revision Item",
		fields=["doc_key", "parent_key", "order_index", "slug", "content_blob", "is_deleted"],
		filters={"revision": revision},
	)

	blob_names = {item["content_blob"] for item in items if item.get("content_blob")}
	blob_hashes = {
		blob["name"]: blob["hash"]
		for blob in frappe.get_all(
			"Wiki Content Blob",
			fields=["name", "hash"],
			filters={"name": ("in", list(blob_names))},
		)
	}

	tree_parts = []
	content_parts = []
	for item in sorted(items, key=lambda x: x["doc_key"]):
		if item.get("is_deleted"):
			continue
		tree_parts.append(
			"|".join(
				[
					item.get("doc_key") or "",
					item.get("parent_key") or "",
					str(item.get("order_index") or 0),
					item.get("slug") or "",
				]
			)
		)
		content_hash = blob_hashes.get(item.get("content_blob")) or ""
		content_parts.append(f"{item.get('doc_key') or ''}:{content_hash}")

	tree_hash = hashlib.sha256("\n".join(tree_parts).encode("utf-8")).hexdigest()
	content_hash = hashlib.sha256("\n".join(content_parts).encode("utf-8")).hexdigest()

	frappe.db.set_value(
		"Wiki Revision",
		revision,
		{
			"tree_hash": tree_hash,
			"content_hash": content_hash,
			"doc_count": len([item for item in items if not item.get("is_deleted")]),
		},
	)


def get_revision_item_map(revision: str) -> dict[str, dict[str, Any]]:
	items = frappe.get_all(
		"Wiki Revision Item",
		fields=[
			"name",
			"doc_key",
			"title",
			"slug",
			"is_group",
			"is_published",
			"is_external_link",
			"external_url",
			"parent_key",
			"order_index",
			"content_blob",
			"is_deleted",
			"modified",
		],
		filters={"revision": revision},
	)

	blob_names = {item["content_blob"] for item in items if item.get("content_blob")}
	blob_hashes = {}
	if blob_names:
		blob_hashes = {
			blob["name"]: blob["hash"]
			for blob in frappe.get_all(
				"Wiki Content Blob",
				fields=["name", "hash"],
				filters={"name": ("in", list(blob_names))},
			)
		}

	item_map: dict[str, dict[str, Any]] = {}
	for item in items:
		item["content_hash"] = blob_hashes.get(item.get("content_blob"))
		item_map[item["doc_key"]] = item
	return item_map


def build_tree_order(items: dict[str, dict[str, Any]]) -> list[str]:
	children: dict[str | None, list[str]] = {}
	for key, item in items.items():
		parent = item.get("parent_key")
		children.setdefault(parent, []).append(key)

	for key in list(children.keys()):
		children[key].sort(key=lambda k: items[k].get("order_index") or 0)

	ordered: list[str] = []

	def walk(parent: str | None):
		for child in children.get(parent, []):
			ordered.append(child)
			walk(child)

	walk(None)
	return ordered
