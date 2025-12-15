# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe


def after_install():
	# create the wiki space
	space = frappe.new_doc("Wiki Space")
	space.space_name = "Wiki"
	space.route = "wiki"
	space.insert()

	page = frappe.new_doc("Wiki Document Page")
	page.parent_wiki_document = space.root_group
	page.title = "Welcome to Frappe Wiki"
	page.content = "# Welcome to Frappe Wiki!"
	page.insert()
