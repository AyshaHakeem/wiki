# Wiki Change Requests + 3-Way Merge (GitBook-style)

## Summary
Implement GitBook-like Change Requests (CRs) for the Wiki. All edits (including Wiki Managers) must go through CRs. CRs are snapshot-based branches with 3-way merges back into the main tree. Live edits are disabled. The current `Wiki Document` tree remains the source of truth for published content.

## Goals
- GitBook-style CR workflow: edit in CR, review, merge.
- Snapshot-based revisions with 3-way merge (base/ours/theirs).
- Support page creation, edits, delete, move, reorder, and new pages in CRs.
- Show diffs and detect conflicts during merge.
- Keep UI performant with lightweight diffing and content dedupe.

## Non-Goals
- No migration of existing `Wiki Contribution` / `Wiki Contribution Batch` data (archive only).
- No Git sync.
- No optimization beyond basic indexes and content dedupe.

## Key Decisions
- **All edits via CRs** (no direct edits even for managers, though they can merge directly).
- **doc_key** (immutable UUID, check ../apps/frappe for UUID gen logic) added to `Wiki Document` for stable identity.
- **slug** stored separately; **route derived at merge** from tree path + slug.
- **Autosave** behavior like GitBook: CR edits auto-save to working head revision; no explicit save requirement.

## Doctypes

### 1) Wiki Change Request
- title (Data, reqd)
- wiki_space (Link: Wiki Space, reqd)
- status (Select: Draft, Open, In Review, Changes Requested, Approved, Merged, Archived; default Draft)
- description (Small Text)
- base_revision (Link: Wiki Revision, reqd)
- head_revision (Link: Wiki Revision, reqd; working snapshot)
- merge_revision (Link: Wiki Revision, read_only)
- outdated (Check, read_only)
- merged_by (Link: User, read_only)
- merged_at (Datetime, read_only)
- archived_at (Datetime, read_only)
- reviewers (Table: Wiki CR Reviewer)
- participants (Table: Wiki CR Participant)

### 2) Wiki CR Reviewer (child)
- reviewer (Link: User, reqd)
- status (Select: Requested, Approved, Changes Requested)
- reviewed_at (Datetime)
- comment (Text)

### 3) Wiki CR Participant (child)
- user (Link: User, reqd)
- role (Select: Author, Reviewer, Contributor, Viewer)

### 4) Wiki Revision
- wiki_space (Link: Wiki Space, reqd)
- change_request (Link: Wiki Change Request, optional)
- parent_revision (Link: Wiki Revision, optional; linear history in CR)
- message (Data)
- is_merge (Check, default 0)
- is_working (Check, default 0)
- created_by (Link: User, read_only, default __user)
- created_at (Datetime, read_only)
- tree_hash (Data, read_only)
- content_hash (Data, read_only)
- doc_count (Int, read_only)

### 5) Wiki Revision Item
- revision (Link: Wiki Revision, reqd)
- doc_key (Data, reqd; unique with revision)
- title (Data)
- slug (Data)
- is_group (Check)
- is_published (Check)
- parent_key (Data)
- order_index (Int)
- content_blob (Link: Wiki Content Blob)
- is_deleted (Check, default 0)

### 6) Wiki Content Blob
- hash (Data, reqd, unique)
- content (Long Text, reqd)
- content_type (Data, default "markdown")
- size (Int, read_only)
- created_by (Link: User, read_only)
- created_at (Datetime, read_only)

### 7) Wiki Merge Conflict
- change_request (Link: Wiki Change Request, reqd)
- doc_key (Data, reqd)
- conflict_type (Select: content, meta, tree; reqd)
- base_payload (JSON)
- ours_payload (JSON)
- theirs_payload (JSON)
- resolution (Select: ours, theirs, manual)
- resolved_payload (JSON)
- resolved_by (Link: User)
- resolved_at (Datetime)
- status (Select: Open, Resolved; default Open)

### Changes to Wiki Document
- doc_key (Data, reqd, unique, immutable UUID)
- slug (Data, reqd)
- route becomes derived from tree path + slug at merge

### Changes to Wiki Space
- main_revision (Link: Wiki Revision, reqd)

## Workflow

### Create CR
1) Create `Wiki Change Request` with status Draft.
2) base_revision = Wiki Space main_revision.
3) head_revision = working snapshot created from base_revision (is_working = 1).

### Edit in CR
- All edits (create/update/delete/move/reorder) apply to head_revision items.
- Autosave with debounce; CR head is updated as changes occur.

### Review & Merge
- Reviewers can approve or request changes.
- Merge triggers 3-way merge (base/ours/theirs). Conflicts produce `Wiki Merge Conflict` records.
- Resolve conflicts then merge to main: apply merge revision to `Wiki Document`, rebuild tree, update `Wiki Space.main_revision`.

## 3-Way Merge Logic
- Base: CR base_revision
- Ours: current main revision
- Theirs: CR head_revision
- Per doc_key:
  - Create/Delete/Edit/Move/Reorder detected.
  - Content: 3-way diff3 merge; conflicts produce conflict records.
  - Meta: field-level 3-way merge; conflicts produce conflict records.
  - Tree/reorder: list merge by parent; conflicting reorders produce tree conflicts.

## Diffing
- Summary: list of changed pages between base and head.
- Page: base vs head for Markdown diff.
- Use tree_hash/content_hash to quickly detect changes.
- Diff viewer UI must use Diffs (`@pierre/diffs`) and follow official docs.

### Diffs.com References (add to implementation notes)
- https://diffs.com/docs#overview
- https://diffs.com/docs#rendering-diffs
- https://diffs.com/docs#installation
- https://diffs.com/docs#installation-package-exports
- https://diffs.com/docs#core-types-filecontents
- https://diffs.com/docs#core-types-filediffmetadata
- https://diffs.com/docs#core-types-creating-diffs
- https://diffs.com/docs#utilities-parsedifffromfile
- https://diffs.com/docs#utilities-parsepatchfiles
- https://diffs.com/docs#react-api
- https://diffs.com/docs#react-api-components
- https://diffs.com/docs#vanilla-js-api
- https://diffs.com/docs#vanilla-js-api-components
- https://diffs.com/docs#vanilla-js-api-renderers
- https://diffs.com/docs#styling
- https://diffs.com/docs#themes
- https://diffs.com/docs#worker-pool

## API Endpoints (server-side)

### CR lifecycle
- create_change_request(wiki_space, title, description=None)
- get_change_request(name)
- list_change_requests(wiki_space, status=None)
- update_change_request(name, title=None, description=None)
- request_review(name, reviewers[])
- review_action(name, reviewer, status, comment=None)
- archive_change_request(name)

### Tree/content edits (autosave)
- get_cr_tree(name)
- create_cr_page(name, parent_key, title, slug, is_group, is_published, content)
- update_cr_page(name, doc_key, fields)
- move_cr_page(name, doc_key, new_parent_key, new_order_index)
- reorder_cr_children(name, parent_key, ordered_doc_keys[])
- delete_cr_page(name, doc_key)

### Diff/merge
- diff_change_request(name, scope="summary|page", doc_key=None)
- merge_change_request(name) -> enqueues merge job
- check_outdated(name)

## Background Jobs
- enqueue_merge_change_request(name)
- apply_merge_revision(merge_revision)
- recompute_revision_hashes(revision)
- mark_outdated_change_requests() (scheduled)
- cleanup_working_snapshots() (optional)

## Permissions
- All edits require CRs; no live edits.
- Wiki Managers and Approvers can merge CRs.
- Authors can edit their CRs; reviewers can comment/approve.

## Archival of Existing Contribution Flow
- Existing `Wiki Contribution` / `Wiki Contribution Batch` remain read-only and are marked archived in UI.
- No data migration.

## Testing Strategy (write unit tests first)
Implement tests before code changes. Minimum unit test coverage:
1) CR creation sets base/head revisions correctly.
2) Autosave updates head revision items and hashes.
3) New page creation with parent linkage and ordering.
4) Update content and metadata updates correct revision items.
5) Move/reorder operations update parent_key/order_index.
6) Delete sets is_deleted and handles descendants.
7) Diff summary reflects changed pages only.
8) Merge without conflicts applies changes to `Wiki Document` and updates main_revision.
9) Merge conflict cases create `Wiki Merge Conflict` records for content and tree conflicts.
10) Outdated flag set when main_revision advances.
11) Permission checks: edits always require CR; merge restricted to manager/approver.

## Acceptance Criteria
- Editing a page always creates/uses a CR, never writes to `Wiki Document` directly.
- CRs show diff summary and per-page diff.
- Merge applies all changes or blocks with explicit conflicts.
- Tree reorder works and is preserved after merge.
- Performance acceptable for medium-sized spaces (hash-based diffing + content dedupe).

## Implementation Tasks
- Integrate Diffs (`@pierre/diffs`) as the diff renderer; follow diffs.com docs for API usage, styling, and worker pool setup.
