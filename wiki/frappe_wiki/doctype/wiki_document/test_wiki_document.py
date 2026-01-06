# Copyright (c) 2025, Frappe and Contributors
# See license.txt

import unittest
from types import SimpleNamespace

import frappe
from frappe.tests import IntegrationTestCase

from wiki.frappe_wiki.doctype.wiki_document.wiki_document import process_navbar_items
from wiki.wiki.markdown import render_markdown

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class IntegrationTestWikiDocument(IntegrationTestCase):
	"""
	Integration tests for WikiDocument.
	Use this class for testing interactions between multiple components.
	"""

	pass


class TestGetWebContext(IntegrationTestCase):
	"""
	Unit tests for the get_web_context method of WikiDocument.
	Tests navigation (prev/next doc) edge cases and wiki spaces switcher.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.test_docs = []
		cls.test_spaces = []

	def tearDown(self):
		# Clean up test documents
		for doc_name in reversed(self.test_docs):
			if frappe.db.exists("Wiki Document", doc_name):
				frappe.delete_doc("Wiki Document", doc_name, force=True)
		self.test_docs = []

		# Clean up test spaces
		for space_name in self.test_spaces:
			if frappe.db.exists("Wiki Space", space_name):
				frappe.delete_doc("Wiki Space", space_name, force=True)
		self.test_spaces = []

	def _create_wiki_document(self, title, parent=None, is_group=False, is_published=True, sort_order=0):
		"""Helper to create a wiki document for testing."""
		doc = frappe.get_doc(
			{
				"doctype": "Wiki Document",
				"title": title,
				"parent_wiki_document": parent,
				"is_group": is_group,
				"is_published": is_published,
				"sort_order": sort_order,
				"content": f"Content for {title}",
			}
		)
		doc.insert(ignore_permissions=True)
		self.test_docs.append(doc.name)
		return doc

	def _create_wiki_space(self, space_name, route, root_group, show_in_switcher=True, is_published=True):
		"""Helper to create a wiki space for testing."""
		doc = frappe.get_doc(
			{
				"doctype": "Wiki Space",
				"space_name": space_name,
				"route": route,
				"root_group": root_group,
				"show_in_switcher": show_in_switcher,
				"is_published": is_published,
			}
		)
		doc.insert(ignore_permissions=True)
		self.test_spaces.append(doc.name)
		return doc

	def test_first_document_has_no_prev_doc(self):
		"""Test that the first document in the tree has no previous document."""
		# Create a simple tree: Root Group -> Doc1 -> Doc2 -> Doc3
		root_group = self._create_wiki_document("Test Root Group", is_group=True)
		doc1 = self._create_wiki_document("First Document", parent=root_group.name)
		self._create_wiki_document("Second Document", parent=root_group.name)
		self._create_wiki_document("Third Document", parent=root_group.name)

		# Create wiki space
		self._create_wiki_space("Test Space", "test-space", root_group.name)

		# Get context for the first document
		doc1.reload()
		context = doc1.get_web_context()

		# First document should have no prev_doc but should have next_doc
		self.assertIsNone(context["prev_doc"])
		self.assertIsNotNone(context["next_doc"])
		self.assertEqual(context["next_doc"]["title"], "Second Document")

	def test_last_document_has_no_next_doc(self):
		"""Test that the last document in the tree has no next document."""
		# Create a simple tree: Root Group -> Doc1 -> Doc2 -> Doc3
		root_group = self._create_wiki_document("Test Root Group Last", is_group=True)
		self._create_wiki_document("First Doc", parent=root_group.name)
		self._create_wiki_document("Second Doc", parent=root_group.name)
		doc3 = self._create_wiki_document("Third Doc", parent=root_group.name)

		# Create wiki space
		self._create_wiki_space("Test Space Last", "test-space-last", root_group.name)

		# Get context for the last document
		doc3.reload()
		context = doc3.get_web_context()

		# Last document should have prev_doc but no next_doc
		self.assertIsNotNone(context["prev_doc"])
		self.assertEqual(context["prev_doc"]["title"], "Second Doc")
		self.assertIsNone(context["next_doc"])

	def test_middle_document_has_both_prev_and_next(self):
		"""Test that a middle document has both prev and next documents."""
		# Create a simple tree: Root Group -> Doc1 -> Doc2 -> Doc3
		root_group = self._create_wiki_document("Test Root Group Middle", is_group=True)
		self._create_wiki_document("First Page", parent=root_group.name)
		doc2 = self._create_wiki_document("Middle Page", parent=root_group.name)
		self._create_wiki_document("Last Page", parent=root_group.name)

		# Create wiki space
		self._create_wiki_space("Test Space Middle", "test-space-middle", root_group.name)

		# Get context for the middle document
		doc2.reload()
		context = doc2.get_web_context()

		# Middle document should have both prev_doc and next_doc
		self.assertIsNotNone(context["prev_doc"])
		self.assertEqual(context["prev_doc"]["title"], "First Page")
		self.assertIsNotNone(context["next_doc"])
		self.assertEqual(context["next_doc"]["title"], "Last Page")

	def test_single_document_has_no_prev_or_next(self):
		"""Test that a single document in the tree has neither prev nor next."""
		# Create a tree with only one document
		root_group = self._create_wiki_document("Test Root Group Single", is_group=True)
		only_doc = self._create_wiki_document("Only Document", parent=root_group.name)

		# Create wiki space
		self._create_wiki_space("Test Space Single", "test-space-single", root_group.name)

		# Get context for the only document
		only_doc.reload()
		context = only_doc.get_web_context()

		# Single document should have neither prev_doc nor next_doc
		self.assertIsNone(context["prev_doc"])
		self.assertIsNone(context["next_doc"])

	def test_wiki_spaces_for_switcher_includes_current_space_even_if_not_published(self):
		"""
		Test that wiki_spaces_for_switcher includes the current space
		even when show_in_switcher is disabled, because of or_filters.
		"""
		# Create three wiki spaces with their root groups
		root1 = self._create_wiki_document("Root Group Space 1", is_group=True)
		doc1 = self._create_wiki_document("Doc in Space 1", parent=root1.name)

		root2 = self._create_wiki_document("Root Group Space 2", is_group=True)
		self._create_wiki_document("Doc in Space 2", parent=root2.name)

		root3 = self._create_wiki_document("Root Group Space 3", is_group=True)
		self._create_wiki_document("Doc in Space 3", parent=root3.name)

		# Create spaces - Space 1 has show_in_switcher=False but current doc belongs to it
		self._create_wiki_space("Space One", "space-one", root1.name, show_in_switcher=False)
		self._create_wiki_space("Space Two", "space-two", root2.name, show_in_switcher=True)
		self._create_wiki_space("Space Three", "space-three", root3.name, show_in_switcher=True)

		# Get context for doc in Space 1 (which has show_in_switcher=False)
		doc1.reload()
		context = doc1.get_web_context()

		# wiki_spaces_for_switcher should include all 3 test spaces:
		# - Space 1 because it's the current space (or_filter: name=space1.name)
		# - Space 2 and 3 because show_in_switcher=True
		# Note: There may be other pre-existing spaces in the database
		switcher_spaces = context["wiki_spaces_for_switcher"]
		space_names = [s["space_name"] for s in switcher_spaces]

		self.assertIn("Space One", space_names)
		self.assertIn("Space Two", space_names)
		self.assertIn("Space Three", space_names)
		# Ensure at least our 3 test spaces are included
		self.assertGreaterEqual(len(switcher_spaces), 3)

	def test_wiki_spaces_for_switcher_excludes_hidden_spaces(self):
		"""
		Test that wiki_spaces_for_switcher excludes spaces with show_in_switcher=False
		when viewing a document from a different space.
		"""
		# Create three wiki spaces with their root groups
		root1 = self._create_wiki_document("Root Hidden Space", is_group=True)
		self._create_wiki_document("Doc in Hidden Space", parent=root1.name)

		root2 = self._create_wiki_document("Root Visible Space", is_group=True)
		doc2 = self._create_wiki_document("Doc in Visible Space", parent=root2.name)

		root3 = self._create_wiki_document("Root Another Visible", is_group=True)
		self._create_wiki_document("Doc in Another Visible", parent=root3.name)

		# Create spaces - Space 1 (Hidden) has show_in_switcher=False
		self._create_wiki_space("Hidden Space", "hidden-space", root1.name, show_in_switcher=False)
		self._create_wiki_space("Visible Space", "visible-space", root2.name, show_in_switcher=True)
		self._create_wiki_space("Another Visible", "another-visible", root3.name, show_in_switcher=True)

		# Get context for doc in Visible Space
		doc2.reload()
		context = doc2.get_web_context()

		# wiki_spaces_for_switcher should include only visible spaces + current space
		# Since current space (Visible Space) has show_in_switcher=True,
		# Hidden Space should be excluded
		switcher_spaces = context["wiki_spaces_for_switcher"]
		space_names = [s["space_name"] for s in switcher_spaces]

		self.assertNotIn("Hidden Space", space_names)
		self.assertIn("Visible Space", space_names)
		self.assertIn("Another Visible", space_names)
		# At least our 2 visible test spaces should be included
		self.assertGreaterEqual(len(switcher_spaces), 2)


class TestMarkdownCallouts(unittest.TestCase):
	"""
	Unit tests for the markdown callout/aside rendering.
	Tests the Astro Starlight-style :::type[title] syntax.
	"""

	def test_basic_note_callout(self):
		"""Test basic :::note callout with default title"""
		md = """:::note
This is a note
:::"""
		html = render_markdown(md)
		self.assertIn('class="callout callout-note"', html)
		self.assertIn('<span class="callout-title">Note</span>', html)
		self.assertIn("This is a note", html)

	def test_tip_callout(self):
		"""Test :::tip callout"""
		md = """:::tip
This is a tip
:::"""
		html = render_markdown(md)
		self.assertIn('class="callout callout-tip"', html)
		self.assertIn('<span class="callout-title">Tip</span>', html)

	def test_caution_callout(self):
		"""Test :::caution callout"""
		md = """:::caution
This is a caution
:::"""
		html = render_markdown(md)
		self.assertIn('class="callout callout-caution"', html)
		self.assertIn('<span class="callout-title">Caution</span>', html)

	def test_danger_callout(self):
		"""Test :::danger callout"""
		md = """:::danger
This is dangerous
:::"""
		html = render_markdown(md)
		self.assertIn('class="callout callout-danger"', html)
		self.assertIn('<span class="callout-title">Danger</span>', html)

	def test_warning_alias_for_caution(self):
		"""Test :::warning is aliased to caution"""
		md = """:::warning
This is a warning
:::"""
		html = render_markdown(md)
		# warning should be rendered as caution
		self.assertIn('class="callout callout-caution"', html)

	def test_custom_title(self):
		"""Test callout with custom title in brackets"""
		md = """:::tip[Did you know?]
This is a tip with a custom title
:::"""
		html = render_markdown(md)
		self.assertIn('class="callout callout-tip"', html)
		self.assertIn('<span class="callout-title">Did you know?</span>', html)

	def test_custom_title_all_types(self):
		"""Test custom titles work for all callout types"""
		types_and_titles = [
			("note", "Important Information"),
			("tip", "Pro Tip"),
			("caution", "Be Careful"),
			("danger", "Critical Warning"),
		]
		for callout_type, title in types_and_titles:
			md = f""":::{callout_type}[{title}]
Content here
:::"""
			html = render_markdown(md)
			self.assertIn(f'class="callout callout-{callout_type}"', html)
			self.assertIn(f'<span class="callout-title">{title}</span>', html)

	def test_custom_title_with_special_characters(self):
		"""Test custom title with special characters"""
		md = """:::note[What's this? A "special" title!]
Content here
:::"""
		html = render_markdown(md)
		self.assertIn('<span class="callout-title">What\'s this? A "special" title!</span>', html)

	def test_custom_title_empty_brackets(self):
		"""Test callout with empty brackets uses default title"""
		md = """:::note[]
Content here
:::"""
		html = render_markdown(md)
		self.assertIn('<span class="callout-title">Note</span>', html)

	def test_custom_title_warning_alias(self):
		"""Test custom title with warning type (aliased to caution)"""
		md = """:::warning[Watch Out!]
Be careful here
:::"""
		html = render_markdown(md)
		self.assertIn('class="callout callout-caution"', html)
		self.assertIn('<span class="callout-title">Watch Out!</span>', html)

	def test_callout_with_markdown_content(self):
		"""Test callout with markdown formatting inside"""
		md = """:::note
This has **bold** and *italic* text
:::"""
		html = render_markdown(md)
		self.assertIn("<strong>bold</strong>", html)
		self.assertIn("<em>italic</em>", html)

	def test_callout_with_link(self):
		"""Test callout with markdown link"""
		md = """:::note
Check out [this link](https://example.com)
:::"""
		html = render_markdown(md)
		self.assertIn('<a href="https://example.com">this link</a>', html)

	def test_callout_with_code_block(self):
		"""Test callout with fenced code block inside"""
		md = """:::note
Here's some code:

```python
print("Hello")
```
:::"""
		html = render_markdown(md)
		self.assertIn('class="callout callout-note"', html)
		# Quotes may be HTML-encoded as &quot;
		self.assertTrue('print("Hello")' in html or "print(&quot;Hello&quot;)" in html)
		self.assertIn("<code", html)
		self.assertIn("language-python", html)

	def test_callout_with_list(self):
		"""Test callout with bullet list"""
		md = """:::tip
Here are some items:

- Item 1
- Item 2
- Item 3
:::"""
		html = render_markdown(md)
		self.assertIn("<li>Item 1</li>", html)
		self.assertIn("<li>Item 2</li>", html)

	def test_multiple_callouts(self):
		"""Test multiple callouts in same document"""
		md = """:::note
First callout
:::

Some text in between

:::danger
Second callout
:::"""
		html = render_markdown(md)
		self.assertIn("callout-note", html)
		self.assertIn("callout-danger", html)
		self.assertIn("First callout", html)
		self.assertIn("Second callout", html)

	def test_callout_has_icon(self):
		"""Test that callouts include SVG icons"""
		md = """:::note
Content
:::"""
		html = render_markdown(md)
		self.assertIn("<svg", html)
		self.assertIn("</svg>", html)

	def test_empty_content(self):
		"""Test render_markdown with empty string"""
		self.assertEqual(render_markdown(""), "")
		self.assertEqual(render_markdown(None), "")

	def test_regular_markdown_still_works(self):
		"""Test that regular markdown without callouts still renders"""
		md = """# Heading

This is a paragraph with **bold** text.

- List item 1
- List item 2
"""
		html = render_markdown(md)
		self.assertIn("<h1>Heading</h1>", html)
		self.assertIn("<strong>bold</strong>", html)
		self.assertIn("<li>List item 1</li>", html)

	def test_callout_mixed_with_regular_content(self):
		"""Test callout mixed with regular markdown"""
		md = """# Introduction

This is some intro text.

:::note
Important note here
:::

And this is the conclusion.
"""
		html = render_markdown(md)
		self.assertIn("<h1>Introduction</h1>", html)
		self.assertIn("callout-note", html)
		self.assertIn("Important note here", html)
		self.assertIn("conclusion", html)


class TestProcessNavbarItems(unittest.TestCase):
	"""
	Unit tests for the process_navbar_items function.
	Tests icon detection for known services and navbar item processing.
	"""

	def _make_navbar_item(self, label, url, open_in_new_tab=False, right=False):
		"""Helper to create a mock navbar item (mimics Top Bar Item)."""
		return SimpleNamespace(
			label=label,
			url=url,
			open_in_new_tab=open_in_new_tab,
			right=right,
		)

	def test_github_url_detected(self):
		"""Test that GitHub URLs are detected and assigned the github icon."""
		items = [self._make_navbar_item("GitHub", "https://github.com/frappe/wiki")]
		result = process_navbar_items(items)

		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]["icon"], "github")
		self.assertEqual(result[0]["label"], "GitHub")
		self.assertEqual(result[0]["url"], "https://github.com/frappe/wiki")

	def test_github_with_www_prefix(self):
		"""Test that www.github.com URLs are also detected."""
		items = [self._make_navbar_item("GitHub", "https://www.github.com/frappe")]
		result = process_navbar_items(items)

		self.assertEqual(result[0]["icon"], "github")

	def test_youtube_url_detected(self):
		"""Test that YouTube URLs are detected."""
		items = [self._make_navbar_item("YouTube", "https://youtube.com/channel/xyz")]
		result = process_navbar_items(items)

		self.assertEqual(result[0]["icon"], "youtube")

	def test_twitter_url_detected(self):
		"""Test that Twitter URLs are detected."""
		items = [self._make_navbar_item("Twitter", "https://twitter.com/fraaboride")]
		result = process_navbar_items(items)

		self.assertEqual(result[0]["icon"], "twitter")

	def test_x_com_maps_to_twitter(self):
		"""Test that x.com URLs are mapped to twitter icon."""
		items = [self._make_navbar_item("X", "https://x.com/frappeframework")]
		result = process_navbar_items(items)

		self.assertEqual(result[0]["icon"], "twitter")

	def test_discord_url_detected(self):
		"""Test that Discord URLs are detected."""
		items = [self._make_navbar_item("Discord", "https://discord.com/invite/abc")]
		result = process_navbar_items(items)

		self.assertEqual(result[0]["icon"], "discord")

	def test_discord_gg_url_detected(self):
		"""Test that discord.gg invite URLs are detected."""
		items = [self._make_navbar_item("Join Discord", "https://discord.gg/abc123")]
		result = process_navbar_items(items)

		self.assertEqual(result[0]["icon"], "discord")

	def test_linkedin_url_detected(self):
		"""Test that LinkedIn URLs are detected."""
		items = [self._make_navbar_item("LinkedIn", "https://linkedin.com/company/frappe")]
		result = process_navbar_items(items)

		self.assertEqual(result[0]["icon"], "linkedin")

	def test_slack_url_detected(self):
		"""Test that Slack URLs are detected."""
		items = [self._make_navbar_item("Slack", "https://slack.com/workspace")]
		result = process_navbar_items(items)

		self.assertEqual(result[0]["icon"], "slack")

	def test_facebook_url_detected(self):
		"""Test that Facebook URLs are detected."""
		items = [self._make_navbar_item("Facebook", "https://facebook.com/frappe")]
		result = process_navbar_items(items)

		self.assertEqual(result[0]["icon"], "facebook")

	def test_instagram_url_detected(self):
		"""Test that Instagram URLs are detected."""
		items = [self._make_navbar_item("Instagram", "https://instagram.com/frappe")]
		result = process_navbar_items(items)

		self.assertEqual(result[0]["icon"], "instagram")

	def test_reddit_url_detected(self):
		"""Test that Reddit URLs are detected."""
		items = [self._make_navbar_item("Reddit", "https://reddit.com/r/erpnext")]
		result = process_navbar_items(items)

		self.assertEqual(result[0]["icon"], "reddit")

	def test_unknown_url_has_no_icon(self):
		"""Test that unknown/custom URLs have no icon assigned."""
		items = [self._make_navbar_item("Custom Link", "https://example.com")]
		result = process_navbar_items(items)

		self.assertIsNone(result[0]["icon"])
		self.assertEqual(result[0]["label"], "Custom Link")

	def test_empty_url_has_no_icon(self):
		"""Test that items with empty URL have no icon."""
		items = [self._make_navbar_item("Empty", "")]
		result = process_navbar_items(items)

		self.assertIsNone(result[0]["icon"])

	def test_none_url_has_no_icon(self):
		"""Test that items with None URL have no icon."""
		items = [self._make_navbar_item("None URL", None)]
		result = process_navbar_items(items)

		self.assertIsNone(result[0]["icon"])

	def test_preserves_open_in_new_tab(self):
		"""Test that open_in_new_tab flag is preserved."""
		items = [self._make_navbar_item("Link", "https://example.com", open_in_new_tab=True)]
		result = process_navbar_items(items)

		self.assertTrue(result[0]["open_in_new_tab"])

	def test_preserves_right_alignment(self):
		"""Test that right alignment flag is preserved."""
		items = [self._make_navbar_item("Link", "https://example.com", right=True)]
		result = process_navbar_items(items)

		self.assertTrue(result[0]["right"])

	def test_multiple_items_processed(self):
		"""Test that multiple items are all processed correctly."""
		items = [
			self._make_navbar_item("GitHub", "https://github.com/frappe"),
			self._make_navbar_item("Docs", "https://docs.frappe.io"),
			self._make_navbar_item("Discord", "https://discord.gg/frappe"),
		]
		result = process_navbar_items(items)

		self.assertEqual(len(result), 3)
		self.assertEqual(result[0]["icon"], "github")
		self.assertIsNone(result[1]["icon"])  # docs.frappe.io is not a known service
		self.assertEqual(result[2]["icon"], "discord")

	def test_empty_list(self):
		"""Test that empty list returns empty list."""
		result = process_navbar_items([])

		self.assertEqual(result, [])

	def test_subdomain_not_matched(self):
		"""Test that subdomains like api.github.com are still matched."""
		items = [self._make_navbar_item("API", "https://api.github.com/repos")]
		result = process_navbar_items(items)

		# api.github.com contains github.com so it should match
		self.assertEqual(result[0]["icon"], "github")

	def test_url_with_path_matched(self):
		"""Test that URLs with paths are correctly matched."""
		items = [
			self._make_navbar_item("Repo", "https://github.com/frappe/wiki/issues"),
			self._make_navbar_item("Video", "https://youtube.com/watch?v=abc123"),
		]
		result = process_navbar_items(items)

		self.assertEqual(result[0]["icon"], "github")
		self.assertEqual(result[1]["icon"], "youtube")
