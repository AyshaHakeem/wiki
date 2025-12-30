import frappe


def execute():
	active_users = frappe.db.get_all("User", filters={"enabled": 1}, pluck="name")
	for user in active_users:
		frappe.get_doc("User", user).add_roles("Wiki User")
		frappe.db.commit()
