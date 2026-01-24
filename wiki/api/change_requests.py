import frappe
from frappe import _

from wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request import diff_change_request


def _is_wiki_manager() -> bool:
	roles = frappe.get_roles()
	return "Wiki Manager" in roles or "System Manager" in roles


@frappe.whitelist()
def get_my_change_requests() -> list[dict]:
	change_requests = frappe.get_all(
		"Wiki Change Request",
		filters={"owner": frappe.session.user},
		fields=[
			"name",
			"title",
			"wiki_space",
			"status",
			"modified",
			"archived_at",
			"merged_at",
		],
		order_by="modified desc",
	)

	if not change_requests:
		return change_requests

	space_ids = list({cr["wiki_space"] for cr in change_requests if cr.get("wiki_space")})
	space_name_map = {}
	if space_ids:
		spaces = frappe.get_all(
			"Wiki Space",
			filters={"name": ("in", space_ids)},
			fields=["name", "space_name"],
		)
		space_name_map = {s["name"]: s["space_name"] for s in spaces}

	for cr in change_requests:
		cr["wiki_space_name"] = space_name_map.get(cr.get("wiki_space"))
		changes = diff_change_request(cr["name"], scope="summary")
		cr["change_count"] = len(changes)

	return change_requests


@frappe.whitelist()
def get_pending_reviews() -> list[dict]:
	if not _is_wiki_manager():
		frappe.throw(_("Only Wiki Managers can view pending reviews"))

	change_requests = frappe.get_all(
		"Wiki Change Request",
		filters={"status": ("in", ["In Review", "Approved"])},
		fields=[
			"name",
			"title",
			"wiki_space",
			"status",
			"owner",
			"modified",
		],
		order_by="modified asc",
	)

	if not change_requests:
		return change_requests

	space_ids = list({cr["wiki_space"] for cr in change_requests if cr.get("wiki_space")})
	owner_ids = list({cr["owner"] for cr in change_requests if cr.get("owner")})

	space_name_map = {}
	if space_ids:
		spaces = frappe.get_all(
			"Wiki Space",
			filters={"name": ("in", space_ids)},
			fields=["name", "space_name"],
		)
		space_name_map = {s["name"]: s["space_name"] for s in spaces}

	owner_map = {}
	if owner_ids:
		owners = frappe.get_all(
			"User",
			filters={"name": ("in", owner_ids)},
			fields=["name", "full_name", "user_image"],
		)
		owner_map = {o["name"]: o for o in owners}

	for cr in change_requests:
		cr["wiki_space_name"] = space_name_map.get(cr.get("wiki_space"))
		owner = owner_map.get(cr.get("owner")) or {}
		cr["author_name"] = owner.get("full_name") or cr.get("owner")
		cr["author_image"] = owner.get("user_image")
		cr["submitted_at"] = cr.get("modified")
		changes = diff_change_request(cr["name"], scope="summary")
		cr["change_count"] = len(changes)

	return change_requests
