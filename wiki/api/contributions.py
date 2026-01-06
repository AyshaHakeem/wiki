import frappe
from frappe import _


@frappe.whitelist()
def get_my_contribution_batches() -> list[dict]:
	"""Get all contribution batches owned by the current user."""
	batches = frappe.db.get_all(
		"Wiki Contribution Batch",
		filters={"contributor": frappe.session.user},
		fields=[
			"name",
			"title",
			"wiki_space",
			"status",
			"modified",
			"submitted_at",
		],
		order_by="modified desc",
	)

	if not batches:
		return batches

	# Get all wiki space names in one query
	space_ids = list({b["wiki_space"] for b in batches})
	space_names = dict(
		frappe.db.get_all(
			"Wiki Space",
			filters={"name": ("in", space_ids)},
			fields=["name", "space_name"],
			as_list=True,
		)
	)

	# Get contribution counts in one query
	batch_names = [b["name"] for b in batches]
	contribution_counts = frappe.db.sql(
		"""
		SELECT batch, COUNT(*) as count
		FROM `tabWiki Contribution`
		WHERE batch IN %s
		GROUP BY batch
		""",
		[batch_names],
		as_dict=True,
	)
	counts_map = {c["batch"]: c["count"] for c in contribution_counts}

	# Enrich batches
	for batch in batches:
		batch["wiki_space_name"] = space_names.get(batch["wiki_space"])
		batch["contribution_count"] = counts_map.get(batch["name"], 0)

	return batches


@frappe.whitelist()
def get_pending_reviews() -> list[dict]:
	"""Get all contribution batches pending review (for Wiki Managers)."""
	# Check if user is a Wiki Manager
	if not _is_wiki_manager():
		frappe.throw(_("Only Wiki Managers can view pending reviews"))

	batches = frappe.db.get_all(
		"Wiki Contribution Batch",
		filters={"status": ("in", ["Submitted", "Under Review"])},
		fields=[
			"name",
			"title",
			"wiki_space",
			"status",
			"contributor",
			"submitted_at",
		],
		order_by="submitted_at asc",
	)

	if not batches:
		return batches

	# Collect IDs for bulk queries
	space_ids = list({b["wiki_space"] for b in batches if b.get("wiki_space")})
	batch_names = [b["name"] for b in batches]
	contributor_ids = list({b["contributor"] for b in batches if b.get("contributor")})

	# Bulk fetch wiki space names
	space_name_map = {}
	if space_ids:
		spaces = frappe.get_all(
			"Wiki Space",
			filters={"name": ("in", space_ids)},
			fields=["name", "space_name"],
		)
		space_name_map = {s["name"]: s["space_name"] for s in spaces}

	# Bulk fetch contribution counts
	contribution_count_map = {}
	if batch_names:
		counts = frappe.db.sql(
			"""
			SELECT batch, COUNT(*) as contribution_count
			FROM `tabWiki Contribution`
			WHERE batch IN %s
			GROUP BY batch
			""",
			(batch_names,),
			as_dict=True,
		)
		contribution_count_map = {c["batch"]: c["contribution_count"] for c in counts}

	# Bulk fetch contributor info
	contributor_map = {}
	if contributor_ids:
		contributors = frappe.get_all(
			"User",
			filters={"name": ("in", contributor_ids)},
			fields=["name", "full_name", "user_image"],
		)
		contributor_map = {c["name"]: c for c in contributors}

	# Enrich batches from lookup maps
	for batch in batches:
		batch["wiki_space_name"] = space_name_map.get(batch.get("wiki_space"))
		batch["contribution_count"] = contribution_count_map.get(batch["name"], 0)
		contributor = contributor_map.get(batch.get("contributor"))
		if contributor:
			batch["contributor_name"] = contributor["full_name"]
			batch["contributor_image"] = contributor["user_image"]

	return batches


@frappe.whitelist()
def approve_contribution_batch(batch_name: str):
	"""Approve a contribution batch and merge the changes."""
	if not _is_wiki_manager():
		frappe.throw(_("Only Wiki Managers can approve contributions"))

	batch = frappe.get_doc("Wiki Contribution Batch", batch_name)

	if batch.status not in ["Submitted", "Under Review"]:
		frappe.throw(_("This contribution cannot be approved in its current state"))

	# First approve the batch
	batch.approve()

	# Then merge the changes
	batch.merge()


@frappe.whitelist()
def reject_contribution_batch(batch_name: str, comment: str):
	"""Reject a contribution batch with feedback."""
	if not _is_wiki_manager():
		frappe.throw(_("Only Wiki Managers can reject contributions"))

	batch = frappe.get_doc("Wiki Contribution Batch", batch_name)

	if batch.status not in ["Submitted", "Under Review"]:
		frappe.throw(_("This contribution cannot be rejected in its current state"))

	batch.status = "Rejected"
	batch.reviewed_by = frappe.session.user
	batch.reviewed_at = frappe.utils.now()
	batch.review_comment = comment
	batch.save()


def _is_wiki_manager() -> bool:
	"""Check if the current user is a Wiki Manager."""
	user_roles = frappe.get_roles(frappe.session.user)
	return "Wiki Manager" in user_roles or "System Manager" in user_roles
