import frappe
from frappe.translate import get_all_translations
from frappe.utils.nestedset import get_descendants_of


@frappe.whitelist()
def get_user_info() -> dict:
	"""Get basic information about the logged-in user."""
	if frappe.session.user == "Guest":
		return {"is_logged_in": False}

	user = frappe.get_cached_doc("User", frappe.session.user)

	return {
		"name": user.name,
		"is_logged_in": True,
		"first_name": user.first_name,
		"last_name": user.last_name,
		"full_name": user.full_name,
		"email": user.email,
		"user_image": user.user_image,
		"roles": user.roles,
		"brand_image": frappe.get_single_value("Website Settings", "banner_image"),
		"language": user.language,
	}


@frappe.whitelist(allow_guest=True)
def get_translations():
	if frappe.session.user != "Guest":
		language = frappe.db.get_value("User", frappe.session.user, "language")
	else:
		language = frappe.db.get_single_value("System Settings", "language")

	return get_all_translations(language)


@frappe.whitelist()
def get_wiki_tree(space_id: str) -> dict:
	"""Get the tree structure of Wiki Documents for a given Wiki Space."""
	space = frappe.get_cached_doc("Wiki Space", space_id)
	space.check_permission("read")

	if not space.root_group:
		return {"children": [], "root_group": None}

	root_group = space.root_group
	descendants = get_descendants_of("Wiki Document", root_group)

	if not descendants:
		return {"children": [], "root_group": root_group}

	tree = build_wiki_tree_for_api(descendants)
	return {"children": tree, "root_group": root_group}


def build_wiki_tree_for_api(documents: list[str]) -> list[dict]:
	"""Build a nested tree structure from a list of Wiki Document names."""
	wiki_documents = frappe.db.get_all(
		"Wiki Document",
		fields=["name", "title", "is_group", "parent_wiki_document", "route", "is_published"],
		filters={"name": ("in", documents)},
		order_by="lft asc",
	)

	doc_map = {doc["name"]: {**doc, "label": doc["title"], "children": []} for doc in wiki_documents}

	root_nodes = []
	for doc in wiki_documents:
		parent_name = doc["parent_wiki_document"]
		if parent_name and parent_name in doc_map:
			doc_map[parent_name]["children"].append(doc_map[doc["name"]])
		else:
			root_nodes.append(doc_map[doc["name"]])

	return root_nodes
