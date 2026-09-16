# MASTER INSTRUCTION — OLD SCHOOL INVENTORY MANAGEMENT SYSTEM

## ROLE & MISSION

You are acting as a **Senior Django Architect, Full-Stack Engineer, Database Engineer, QA Engineer, and Technical Lead**.

Your mission is to **analyze, plan, design, implement, test, and deliver a complete working Django web application** for:

**Website Quản lý kho và Chuỗi cung ứng cửa hàng thời trang Old School.**

This is a full implementation task, NOT a documentation-only task.

You must NOT stop after writing a plan, generating Django models, or creating mock UI pages.

You are expected to implement a genuinely functioning application that satisfies the documented use cases, role permissions, database relationships, validation rules, stock transactions, business workflows, and user interface requirements.

**All user-facing text must be in Vietnamese.** Technical documents, source code identifiers, and code comments may be in English.

---

# 1. REQUIRED INPUT DOCUMENTS

Read and analyze these files before implementing anything:

1. `50K22.3-Nhom09-ChuDe6-BCTD2.docx` — original project specification, business processes, use cases, Figma requirements, and database tables.
2. `SƠ ĐỒ ERD.drawio.html` — current editable ERD exported from diagrams.net.
3. Any existing Django project, migrations, source files, configuration, assets, or frontend designs already present in the repository.
4. Existing Figma reference, if accessible through provided resources.

Do NOT rely solely on filenames, the diagram preview, or previous AI summaries.

Extract the full use-case specifications, including:

- Actor
- Objective
- Preconditions
- Main Flow
- Alternative Flows
- Exceptional Flows
- Postconditions

The DOCX includes 53 use-case specification tables covering general and detailed functionality, plus 12 documented database tables.

The current ERD includes 13 entities, including `BienThe`.

You must compare all three levels:

**Business Requirements ↔ ERD ↔ Django Models.**

When they disagree, identify the inconsistency instead of blindly copying an incorrect structure.

## Requirement precedence

1. Explicit user instructions.
2. Detailed use-case specifications.
3. Proposed business processes.
4. General functional descriptions.
5. Database specification.
6. Current ERD.
7. Figma visual references.

Where the specification is incomplete or contradictory, document the issue in `docs/DECISIONS.md`, choose a conservative implementation assumption, and mark it as pending business confirmation.

Do not silently present proposed business rules as requirements from the original document.

---

# 2. EXECUTION RULES

Follow these rules throughout implementation:

1. Inspect the existing repository before creating or modifying files.
2. Preserve existing working code and valid migrations.
3. Never delete project data or reset an existing database without explicit authorization.
4. Create a complete implementation plan before coding.
5. After planning, proceed with implementation automatically.
6. Implement one coherent vertical slice at a time: models, business logic, views, templates, tests.
7. Run tests after every significant implementation phase.
8. Fix regressions before proceeding to the next phase.
9. Do not fabricate test results or claim an unexecuted feature works.
10. Do not implement core business logic using hardcoded mock data.
11. Keep the code modular, readable, maintainable, and consistent.
12. Prefer Django-native capabilities over unnecessary packages.
13. Do not create empty placeholder pages merely to appear complete.
14. Keep a running implementation checklist and requirement coverage matrix.
15. If an external dependency or environment limitation blocks execution, record the exact blocker and continue with independent tasks.

The definition of complete is **working, validated application behavior**, not merely code generation.

---

# 3. TECHNOLOGY STACK

For a new repository, use the following baseline.

## Backend

- Python 3.12
- Django 5.2 LTS, latest supported security patch
- PostgreSQL 16
- Django ORM
- Django Authentication
- Django Forms and ModelForms
- Django class-based or function-based views as appropriate
- Django migrations
- Django management commands

## Frontend

- Django Templates
- Bootstrap 5
- HTML5
- CSS3
- Vanilla JavaScript
- Chart.js for supported visual reporting

Use reusable Django templates, partials, and static assets.

Do not introduce React, Vue, Next.js, or a separate SPA unless an existing project already depends on them.

## Supporting libraries

Use maintained, compatible versions of:

- psycopg for PostgreSQL
- Pillow for product image handling
- openpyxl for Excel import/export
- python-dotenv or django-environ for configuration
- pytest / pytest-django or Django's built-in test framework
- Playwright for browser-level testing when available

Verify package compatibility before pinning versions.

## Architectural pattern

**Modular Django Monolith**

Do not split the project into microservices.

Keep business logic in explicit service modules rather than placing complex inventory operations inside views, templates, signals, or `Model.save()` methods.

---

# 4. PROJECT STRUCTURE

Use a structure similar to:

    oldschool/
      config/
      apps/
        accounts/
        branches/
        catalog/
        inventory/
        purchasing/
        sales_outbound/
        transfers/
        stocktakes/
        reports/
        notifications/
      templates/
        base.html
        components/
        accounts/
        catalog/
        purchasing/
        sales_outbound/
        transfers/
        stocktakes/
        reports/
      static/
        css/
        js/
        images/
      media/
      docs/
      tests/
      manage.py
      requirements.txt
      .env.example
      README.md

Adjust to the existing repository where necessary.

Each Django app should own its relevant models, forms, validators, services, selectors/query logic, views, URLs, templates, and tests.

Avoid circular dependencies between apps.

Centralize stock mutations in the `inventory` domain.

---

# 5. MANDATORY PRE-IMPLEMENTATION AUDIT

Before coding, produce:

## `docs/REQUIREMENTS_MATRIX.md`

Columns:

| Use Case ID | Actor | Business Requirement | Django Model | Service | View/Screen | Tests | Status |

Include every documented use case.

Use exactly the identifiers found in the source, including:

- UC-1, UC-2
- UC-3.1 through UC-3.7
- UC-4.1 through UC-4.11
- UC-5.1 through UC-5.13
- UC-6.1 through UC-6.10
- UC-7.1 through UC-7.5

Also cover the general use cases and explicitly described workflows.

Do not assume every use case needs a separate URL or HTML page. Search, filtering, confirmation dialogs, and subflows may be implemented within an existing screen.

Every use case must still have a traceable implementation and verification method.

## `docs/ERD_AUDIT.md`

Identify:

- Existing entities and attributes
- Missing entities
- Missing fields
- Incorrect foreign keys
- Incorrect cardinality
- Duplicate attributes
- Naming inconsistencies
- Unsupported business relationships
- Proposed schema improvements
- Differences between the DOCX database tables and new ERD

## `docs/DECISIONS.md`

Record each unresolved business rule, proposed default behavior, rationale, and impact.

## `docs/IMPLEMENTATION_PLAN.md`

Include phases, dependencies, deliverables, acceptance criteria, and status.

After writing these files, execute the plan. Do not stop at this point.

---

# 6. DATABASE DESIGN REQUIREMENTS

The original ERD is a starting point, not a schema that must remain unchanged.

Retain valid relationships and attributes.

Introduce additional tables only when necessary to implement documented behavior and maintain data integrity.

Use PostgreSQL constraints, foreign keys, indexes, unique constraints, and transactional operations.

## 6.1 User / Account

Use a custom Django user model from the beginning of a new project.

Prefer extending `AbstractUser`.

Configure `AUTH_USER_MODEL` before the initial migration.

Support three business roles:

- ADMIN — Chủ / Admin
- MANAGER — Quản lý cơ sở
- STAFF — Nhân viên bán hàng

Required business data:

- User ID
- Username
- Password hash managed by Django
- Full name
- Role
- Assigned branch, nullable for system-wide Admin
- Active/inactive status
- Creation and relevant account timestamps

Use Django's built-in password hashing, sessions, authentication, and permission mechanisms.

Do not create separate authentication tables for each business role.

If the existing repository already has a working custom user model, reuse it rather than creating another.

Django's technical `is_superuser` and the application's ADMIN business role must be handled deliberately; they are not automatically interchangeable.

Support administrator management of accounts and branches through Django Admin, unless detailed custom UI requirements are supplied.

Do not permit public self-registration.

---

## 6.2 Branch / CoSo

Represent the existing `CoSo` entity.

Fields:

- Primary key
- Unique branch code
- Branch name
- Address
- Phone

Provide seed data for:

- Cơ sở 1 — Kho tổng
- Cơ sở 2

The application must not hardcode branch primary keys into business logic.

Use stable branch codes or configuration to identify the central warehouse.

Relationships:

- One branch has many assigned managers/staff.
- One branch has many stock balances.
- One branch has many inventory counts.
- One branch has many sales outbound records.
- One branch may be a sending or receiving branch in many transfers.
- One receiving branch may be associated with many import receipts.

---

## 6.3 Supplier / NhaCungCap

Preserve the documented supplier master data:

- ID
- Unique supplier code
- Supplier name
- Address
- Phone

Relationship:

`Supplier 1 — N ImportReceipt`

Use appropriate `PROTECT` relationships to preserve transactional history.

---

## 6.4 Product / SanPham

Separate the product master from its variants.

Suggested attributes:

- ID
- Unique product code
- Product name
- Product category/group
- Unit of measure
- Product image
- Description/notes
- Business status
- Created/updated timestamps where useful

Do not store size, color, and branch-wide stock directly in the product master when multiple variants exist.

Remove a stored `stt` field unless it has a real business meaning beyond list numbering.

Support:

- Active product
- Discontinued/inactive product

Products referenced in finalized transactions must not be hard-deleted.

A discontinued product may still have historical inventory and transactions.

---

## 6.5 Product Variant / BienThe

Each product may have multiple variants.

Required attributes:

- ID
- Product FK
- Unique variant code/SKU
- Color
- Size
- Selling price
- Optional variant status
- Additional fields only when justified

Enforce uniqueness of SKU.

If color and size are the complete variant dimensions, prevent duplicate `(product, color, size)` combinations.

All inventory-moving transaction details must reference a specific variant.

Relationships:

- `SanPham 1 — N BienThe`
- `BienThe 1 — N TonKho`
- `BienThe 1 — N ChiTietPhieuNhapKho`
- `BienThe 1 — N ChiTietPhieuXuatHangBan`
- `BienThe 1 — N ChiTietPhieuDieuChuyen`
- `BienThe 1 — N ChiTietKiemKe`

Avoid duplicate product identifiers on detail records unless they have a documented independent purpose.

---

## 6.6 Stock Balance / TonKho

Create an explicit stock balance model for the selected design.

Suggested fields:

- ID
- Branch FK
- Variant FK
- Current quantity
- Minimum stock threshold
- Updated timestamp

Constraint:

**UNIQUE(branch, variant)**

A variant can have different quantities at different branches.

Requirements:

- No negative stock for ordinary outbound and transfer operations.
- Stock quantities are integers.
- Low-stock threshold is non-negative.
- Stock balance cannot be modified directly by arbitrary views or users.
- Business services are responsible for every stock update.

Stock status should be calculated from current quantity and configured threshold.

Document exact threshold-boundary semantics.

Use the documented comparison to the minimum threshold unless a newer explicit business rule overrides it.

---

## 6.7 Stock Movement / Inventory Ledger

Create a stock movement record for auditability and report computation.

Suggested fields:

- ID
- Branch FK
- Variant FK
- Movement type
- Signed quantity delta
- Balance after movement, where useful
- Source document type
- Source document identifier
- Source detail identifier
- Actor FK
- Effective timestamp
- Created timestamp
- Unique business event key

Movement types should cover:

- Opening balance
- Approved supplier import
- Completed sales outbound
- Transfer out
- Transfer in
- Explicit stock adjustment, only if enabled by the approved business rule

A transfer out and a transfer in must remain distinguishable.

Movement records should be immutable once committed.

Never delete or rewrite finalized stock history to simulate an adjustment.

Use compensating movements for approved corrections.

The stock ledger and stock balance must remain consistent.

---

# 7. DOCUMENT / TRANSACTION MODELS

## 7.1 Import Receipt

Preserve:

- Receipt ID
- Unique receipt code
- Supplier
- Receiving branch
- Import date
- Receipt details
- Unit costs
- Discounts
- Line totals
- Notes
- Status

Add enough information to support:

- Creator
- Creation timestamp
- Approver
- Approval timestamp
- Return/rejection reason
- Last update timestamp

States:

- DRAFT, only if supported
- PENDING_APPROVAL
- RETURNED
- APPROVED

A receipt is editable before approval or when returned.

Approval is performed by the business ADMIN role.

**Stock is increased only after approval succeeds.**

Approval and stock changes must commit in a single transaction.

A failed stock update must not leave a receipt marked approved.

A receipt must not be approved twice.

Deleting an approved receipt must be prohibited.

Discount representation must be unambiguous: select either a fixed amount, a percentage with an explicit type, or a documented fixed-only rule.

Store transactional prices so historical receipts do not change when current product prices change.

---

## 7.2 Sales Outbound Receipt

Preserve:

- Outbound receipt ID
- Unique code
- Source branch
- Date
- Receipt details
- Product variants
- Quantities
- Unit prices
- Line totals
- Total amount

Add:

- Status
- Creator
- Created timestamp
- Finalized by
- Finalization timestamp

Suggested states:

- DRAFT/PENDING
- COMPLETED
- CANCELLED

Creating a receipt must NOT automatically deduct inventory.

Finalizing a receipt:

1. Check authorization.
2. Lock the required stock balances.
3. Validate receipt state.
4. Validate current available stock.
5. Deduct stock atomically.
6. Record stock movements.
7. Update receipt state.
8. Record actor and timestamp.
9. Commit.
10. Display success.

If stock is insufficient, reject the operation without partially deducting inventory.

Completed receipts are read-only.

Only eligible uncompleted receipts may be deleted/cancelled.

Keep sales outbound separate from interbranch stock transfer.

---

## 7.3 Sales Outbound Request

The proposed business process describes a sales employee creating an outbound request before a manager prepares the actual outbound receipt.

Implement a lightweight request workflow if confirmed in the documented business flow.

Support:

- Requesting employee
- Branch
- Requested products/SKUs
- Quantities
- Request date
- Status
- Processing manager
- Related outbound receipt

A STAFF user may create a request where permitted but must never finalize inventory deductions.

Keep requests and finalized receipts conceptually separate.

If no independent approval lifecycle is required, avoid unnecessary duplication and document the chosen representation.

---

## 7.4 Transfer / PhieuDieuChuyen

Support actual interbranch transfer behavior.

Fields should account for:

- Transfer ID/code
- Source branch
- Destination branch
- Requested products
- Requested quantities
- Dispatched quantities
- Received quantities
- Reason
- Creator
- Processing user
- Created timestamp
- Dispatched timestamp
- Received timestamp
- Status
- Notes

A source branch and destination branch must be different.

Suggested state flow:

`REQUESTED → ACCEPTED → DISPATCHED → RECEIVED`

Additional states when required:

- REJECTED
- CANCELLED
- DISCREPANCY / RECEIVED_WITH_SHORTAGE

Use request and dispatch documents separately if independent lifecycle or multiple dispatches require that modeling.

Business behavior:

- Creating a request does not change stock.
- Checking availability does not change stock.
- Completing dispatch reduces stock at the sending branch.
- Receiving confirmation increases stock at the destination branch.
- A shortage must be recorded; do not silently mark a short receipt fully received.
- Track goods in transit.
- Prevent duplicate dispatch or receipt posting.
- Preserve the actual requested/dispatched/received quantities.

For discrepancies, create an explicit documented handling procedure rather than losing quantities.

Do not count an internal transfer as a customer sale.

---

## 7.5 Inventory Count / KiemKe

Preserve the existing:

- Inventory count ID
- Unique count code
- Branch
- Count date
- Purpose
- Status
- Creator
- Approval/rejection users
- Relevant timestamps

Also support the actual person who performed counting when different from the creator.

Detail records must use Variant FK and preserve:

- System quantity snapshot
- Actual counted quantity
- Difference
- Unit of measure snapshot
- Unit price snapshot where required
- Handling note
- General note

Difference formula:

**Actual quantity − System snapshot quantity**

Reconciliation states:

- MATCH
- SHORTAGE
- EXCESS

The status is derived from the difference.

Actual counted quantity may be zero.

It must never be negative.

Count status:

- PENDING
- APPROVED
- REJECTED

The detailed UC-6.10 identifies ADMIN as the approval actor.

Use ADMIN-only approval as the initial conservative behavior and record the conflicting general description in `docs/DECISIONS.md`.

Important:

Approval of an inventory-count record must not silently overwrite physical stock.

The source use case clearly describes approving the record, but does not conclusively specify automatic stock adjustment.

Until explicitly resolved, approval changes only count status and approval metadata.

If stock adjustment is later authorized, implement it as an auditable, independently specified operation based on the approved difference, not a blind assignment of the old actual count to current stock.

Ensure the count snapshot remains stable even if new stock transactions occur after the count was taken.

---

## 7.6 Reports / BaoCao

Investigate whether the existing `BaoCao` entity represents:

1. A saved report/snapshot; or
2. Dynamically generated report data.

Do not store redundant aggregates without justification.

For dynamic reports, calculate from effective stock movements and valid documents.

For saved reports, include explicit scope and period:

- Branch or all-branches scope
- Date from
- Date to
- Relevant variant/category
- Report metadata
- Detailed values

Support:

- Opening balance
- Quantity imported
- Quantity exported
- Closing balance
- Sales movement
- Interbranch transfers
- Stock warnings
- Inventory value where costing rules are established

Do not mistake customer sales for transfer activity.

Do not invent a cost-accounting method.

Record unresolved cost valuation requirements.

---

## 7.7 Notifications and Alerts

Implement notification behavior for:

- Import approved
- Import returned
- Outbound finalized
- Transfer request
- Transfer dispatched
- Transfer received
- Inventory count pending approval
- Inventory count approved/rejected
- Low-stock warning

Persist notifications when read/unread history is required.

Notification fields should include:

- Recipient
- Type
- Title
- Content
- Related entity
- Creation timestamp
- Read status

Low-stock warnings should be scoped to branch and variant.

Prevent duplicate unresolved alerts for the same issue.

Support resolution when stock returns to an acceptable level.

---

# 8. DATABASE CONSTRAINTS AND PERFORMANCE

Apply appropriate Django ORM and PostgreSQL constraints.

Required examples:

- Unique product code
- Unique SKU
- Unique document code
- Unique branch + variant stock balance
- Positive import quantity
- Positive outbound quantity
- Positive transfer quantity
- Nonnegative counted quantity
- Nonnegative current stock
- Source branch different from destination branch
- Valid discount range/type
- Valid document status transitions

Use:

- `ForeignKey`
- `PROTECT` for historical business references
- `UniqueConstraint`
- `CheckConstraint`
- `TextChoices`
- `DecimalField` for money
- Indexes for commonly filtered fields
- `select_related` and `prefetch_related`

Avoid floating-point numbers for monetary calculations.

Use sensible precision for VND amounts.

Use timezone-aware datetimes.

Do not introduce migrations that drop existing production data without an approved migration strategy.

---

# 9. STOCK TRANSACTION SAFETY

This is a critical system requirement.

All stock mutations must use a centralized service layer.

Use `transaction.atomic()` and row-level locking with `select_for_update()` on PostgreSQL where appropriate.

For concurrent transactions:

1. Lock the document being finalized.
2. Validate its current status.
3. Lock required stock rows in stable ordering.
4. Recheck available stock.
5. Apply all changes.
6. Create uniquely identified ledger events.
7. Update the document state.
8. Commit atomically.

If any step fails, roll back all steps.

Protect against:

- Double-click submissions
- Duplicate HTTP requests
- Repeated approvals
- Replayed finalization requests
- Concurrent outbound transactions
- Concurrent transfers
- Missing stock balance rows
- Stale inventory values
- Invalid branch relationships

Use idempotency safeguards.

Do not rely solely on disabled frontend buttons.

If stock records must be created concurrently, protect creation using database unique constraints and safe retry handling.

Do not claim SQLite unit tests prove PostgreSQL row-locking behavior.

Run real concurrency/integration tests against PostgreSQL.

---

# 10. ROLE-BASED ACCESS CONTROL

Build a centralized permission matrix.

## ADMIN

- View system-wide data
- View branch-specific reports
- Approve/return import receipts
- Approve/reject inventory counts
- Manage users/branches through Django Admin according to authorized administrative permissions
- View relevant notifications

## MANAGER

- Manage permitted products
- View stock in authorized scope
- Create/manage import receipts for CS1 where specified
- Create and finalize permitted outbound receipts
- Request/process transfers
- Perform inventory counts for assigned branch
- View and export authorized reports
- Receive stock alerts

## STAFF

- Login/logout
- View and search product catalogue
- View permitted product variants/prices/stock
- Submit sales outbound requests if enabled
- No direct stock modification
- No administrative CRUD
- No document approval

Enforce permissions at:

- Navigation
- Queryset
- Object retrieval
- Django view
- Form validation
- Service layer

Hiding a button is not sufficient.

A manager must not access another branch's restricted record by changing a URL or POST parameter.

Never trust branch IDs submitted by the browser without checking authorization.

Tests must attempt direct unauthorized POST requests.

---

# 11. IMPLEMENTATION OF ALL FUNCTIONAL MODULES

## A. Authentication

Implement:

- Login
- Logout
- Logout confirmation
- Invalid credentials feedback
- Inactive account handling
- Session expiry
- Access denied
- Role-based redirect/navigation

Password reset should be implemented only if explicitly required or selected as an approved supplementary feature.

---

## B. Product Catalogue

Implement:

- Product list
- Product detail
- Create product
- Edit product
- Delete when eligible
- Discontinue/reactivate business status where applicable
- Product variant management
- Search
- Filter
- Category filter
- Size/color filter
- Stock status filter
- Pagination
- Image upload

Staff must see a read-only variation.

Historical product references must remain valid.

---

## C. Import Warehouse

Implement UC-4.1 to UC-4.11.

Required functionality:

- Import Excel
- Create receipt manually
- Add multiple product variants
- Validate quantity and unit costs
- Receipt list/detail
- Search/filter
- Edit before approval
- Delete eligible receipt
- Admin approval
- Return with reason
- Stock increase upon successful approval
- Import activity report
- Import report export where authorized

The general import flow and detailed approval flow have inconsistent descriptions of when inventory is increased.

Use **UC-4.9 approval** as the default stock-posting moment and document the conflict.

---

## D. Sales Outbound

Implement UC-5.1, UC-5.2, UC-5.4 through UC-5.12.

Required functionality:

- Lookup product/stock
- Manual product selection
- Excel product import
- Create sales outbound receipt
- Edit pending receipt
- Detail/list
- Search/filter
- Quantity validation
- Finalize/record outbound
- Deduct inventory
- Delete eligible uncompleted receipt
- Print completed receipt
- Handle insufficient stock

Staff sales-request flow from the proposed business process must also be accounted for.

Printed receipts should use a print-friendly HTML page and browser printing.

Do not fabricate unsupported PDF export requirements.

---

## E. Interbranch Transfers

Implement UC-5.3 and the transfer process documented in the proposed workflow.

Required:

- Create transfer request
- Select source/destination
- Product variants and quantity
- Validate sender stock
- Accept/reject request
- Dispatch
- Receiving notification
- Verify actual receipt
- Record discrepancies
- Confirm receipt
- Update stock at the correct stages
- Transfer history and status

---

## F. Inventory Count

Implement UC-6.1 to UC-6.10.

Required:

- Count list/detail
- Create count
- Manual quantities
- Excel import
- Validate imported product codes/SKUs
- Compare system snapshot and actual count
- Calculate differences
- Match/Shortage/Excess states
- Summary counts
- Edit eligible pending record
- Search/filter
- Delete eligible record
- Admin approval/rejection
- Display processor and timestamps

Do not lose the original system quantity snapshot.

---

## G. Reporting

Implement UC-7.1 to UC-7.5 plus the documented import reporting flows.

Support:

- Product inventory reporting
- Inbound quantity
- Outbound quantity
- Closing stock
- Reports by period
- Reports by branch
- Reports by category
- Reports by variant
- Best-selling products using actual sales movements
- Slow-moving stock using a documented measure
- Low-stock data
- Excel export

Admin may view all branches and individual branches.

Manager sees only the assigned branch.

UC-7.3 specifies Manager as Excel export actor; do not automatically broaden export permissions without an explicit decision.

---

# 12. EXCEL IMPORT IMPLEMENTATION

Use openpyxl for `.xlsx` files.

Do not claim unsupported formats work.

Build reusable Excel upload logic for:

- Import receipt details
- Outbound receipt details
- Inventory counts

Flow:

1. Upload file.
2. Validate extension, size, and parseability.
3. Parse workbook.
4. Validate required headers.
5. Resolve SKU/product references.
6. Validate quantities and fields.
7. Generate preview.
8. Display row-level errors.
9. Confirm import.
10. Save the validated data.

An invalid file must not corrupt or partially apply business transactions.

Use atomic persistence when the import becomes a confirmed document operation.

Do not immediately finalize stock changes merely because an Excel file was uploaded.

Show clear row numbers and error messages.

Support replacing invalid files and retrying.

Protect against oversized uploads and unsafe file content.

For exports, prevent spreadsheet formula injection from untrusted text.

---

# 13. FRONTEND / UX REQUIREMENTS

Use the existing Old School design reference where available.

Design direction:

- Dark brown primary navigation
- Warm beige/cream backgrounds
- White content surfaces
- Clear cards and data tables
- Vietnamese labels
- Consistent dialogs and status badges

Use a reusable `base.html`.

Global header:

- Old School branding
- Module navigation
- Branch selector according to permissions
- Notifications bell
- User menu
- Logout

Main modules:

1. Danh mục
2. Nhập kho
3. Xuất kho
4. Kiểm kê
5. Báo cáo

Transfer screens may appear inside Xuất kho or a clearly identified subnavigation.

## Required screen coverage

### Authentication
- Login
- Login error
- Session expired
- Access denied

### Catalogue
- Product list
- Product detail
- Add/edit product
- Manage variants
- Delete confirmation
- Stock status/filter states

### Import
- Receipt list
- Create
- Edit
- Detail
- Upload Excel
- Excel preview/errors
- Approval confirmation
- Return/rejection
- Import report

### Outbound / Transfer
- Stock lookup
- Sales outbound request
- Outbound list
- Create/edit/detail
- Finalization confirmation
- Print view
- Transfer request
- Transfer processing
- Receiving confirmation
- Discrepancy state

### Inventory Count
- List
- Create
- Detail
- Edit
- Excel import/preview
- Approval/rejection
- Count summary

### Reporting
- Inventory report
- Period/branch filters
- Charts
- Detail table
- Excel export

### Global
- Notification dropdown
- Empty states
- Loading states
- Validation errors
- Success/error toasts
- Confirmation modals

Do not leave buttons as decorative elements.

Every permitted action must have working navigation and backend behavior.

Use realistic Vietnamese clothing-store seed data, not Lorem Ipsum.

---

# 14. STOCK STATUS

Implement the three specified stock statuses:

- Còn hàng — green
- Sắp hết hàng — yellow
- Hết hàng — red

Statuses must have text labels, not only color.

Evaluate them per branch and SKU, not globally per parent product.

Use the minimum stock threshold for low-stock detection.

Create and resolve warnings consistently when stock changes.

Prevent warning spam.

---

# 15. FORMS AND VALIDATION

Every user input must be validated on the server.

Required checks include:

- Required fields
- Unique codes
- Positive quantities
- Nonnegative counted quantity
- Valid prices
- Valid dates
- Valid branch selection
- Product/variant existence
- Stock sufficiency
- Document-state eligibility
- Permission ownership
- Valid transitions
- Valid import rows

Provide helpful inline Vietnamese error messages.

Preserve form inputs on failed validation.

Do not rely solely on JavaScript for validation.

---

# 16. REPORTING RULES

Reports must be backed by actual persisted data.

Do not use randomly generated numbers in production reports.

The data must respect:

- Branch
- Time period
- Variant
- Document status
- Transaction effective time

Opening and closing balances must reconcile with stock movements.

Sales ranking must use customer sales, not internal transfers.

For system-wide reporting, define how goods in transit are represented.

If historical opening balances are unavailable, record and implement an explicit opening-balance initialization procedure.

Avoid silently assuming all historical inventory began at zero.

---

# 17. TESTING STRATEGY

Implement automated tests alongside each module.

## Model tests

Verify:

- Foreign keys
- Unique constraints
- Validation
- Product variants
- Stock uniqueness
- Business statuses

## Permission tests

Verify:

- Admin permissions
- Manager branch isolation
- Staff read-only restrictions
- Forbidden direct POST
- Forbidden object access by guessed ID

## Import tests

Verify:

- Creating a pending receipt does not increase stock
- Approval increases correct variant at correct branch
- Approval cannot occur twice
- Returned receipt does not change stock
- Failed posting rolls back approval

## Outbound tests

Verify:

- Draft does not reduce stock
- Finalization reduces correct stock
- Insufficient stock is rejected
- Duplicate finalization does not deduct twice
- Completed receipt cannot be deleted
- Two simultaneous outbound requests cannot oversell stock

## Transfer tests

Verify:

- Request alone has no stock effect
- Dispatch reduces sender stock once
- Receipt increases destination stock once
- Wrong branch cannot receive
- Sending and receiving branches differ
- Receiving discrepancy is preserved
- Repeated receipt cannot credit inventory twice

## Inventory count tests

Verify:

- Correct difference calculation
- Match/Shortage/Excess result
- Actual quantity 0 is valid
- Negative count rejected
- Manager branch isolation
- Admin approval permissions
- Approval does not automatically adjust stock without a resolved adjustment rule

## Reporting tests

Verify:

- Correct date filtering
- Correct branch filtering
- Correct variant breakdown
- Sales separated from transfers
- Consistent opening/closing quantities
- Excel export scope
- Unauthorized exports rejected

## Browser tests

Verify:

- Login/logout
- Navigation
- Forms
- Search/filter
- Modal behavior
- Excel preview
- Approval workflow
- Confirmation workflow
- Report export
- Error handling

Use browser automation where available.

Take screenshots of representative final screens for visual review.

Do not accept tests that merely assert HTTP 200 while ignoring business state.

---

# 18. DEVELOPMENT PHASES

Execute in the following order.

## PHASE 0 — Discovery and Planning

Tasks:

- Inspect repository
- Extract all use cases
- Parse ERD
- Audit database
- Establish requirement coverage
- Identify business conflicts
- Create implementation plan

Deliverables:

- Requirements matrix
- ERD audit
- Decision log
- Implementation plan

Gate:

All documented use cases have a mapped implementation strategy.

## PHASE 1 — Project Foundation

Tasks:

- Configure Django
- PostgreSQL connection
- Environment configuration
- Custom user model
- App structure
- Base templates
- Authentication
- Permission helpers
- Shared error handling

Gate:

Django starts, migrations succeed, login works, and basic permission tests pass.

## PHASE 2 — Master Data and Inventory

Tasks:

- Branch
- Supplier
- Product
- Variant
- Stock balance
- Stock ledger
- Product CRUD
- Stock lookup
- Low-stock calculation

Gate:

One variant can have independent quantities in two branches, and catalogue screens work.

## PHASE 3 — Warehouse Import

Tasks:

- Import models
- Manual creation
- Excel preview
- Approval
- Return
- Transactional inventory increase
- UI and tests

Gate:

Only approved imports increase stock, exactly once.

## PHASE 4 — Outbound Sales

Tasks:

- Requests where applicable
- Outbound receipts
- Stock validation
- Finalization
- Stock deductions
- Print view
- UI/tests

Gate:

Finalization updates stock once and prevents overselling.

## PHASE 5 — Transfers

Tasks:

- Transfer requests
- Source/destination processing
- Dispatch
- Receiving
- Discrepancies
- Notifications
- UI/tests

Gate:

Branch inventory movements reconcile across transfer states.

## PHASE 6 — Inventory Counting

Tasks:

- Inventory count creation
- Excel import
- Snapshots
- Difference calculation
- Approval/rejection
- UI/tests

Gate:

Count records are auditable, scoped to branches, and do not silently corrupt stock.

## PHASE 7 — Reports and Notifications

Tasks:

- Stock movement reporting
- Filters
- Charts
- Excel exports
- Low-stock alerts
- Notification dropdown
- UI/tests

Gate:

Reports reconcile with actual valid transactions.

## PHASE 8 — System Integration and QA

Tasks:

- Full requirements audit
- Cross-module integration tests
- Permission regression
- Concurrent stock tests
- Performance checks
- Browser testing
- UX polishing
- Bug fixing

Gate:

All critical business scenarios pass.

## PHASE 9 — Delivery

Tasks:

- Seed/demo dataset
- Final migration check
- Documentation
- Installation instructions
- Admin/user guidance
- Test report
- Final implementation status

Gate:

A developer can clone, configure, migrate, seed, run, test, and demonstrate the application.

---

# 19. QUALITY REQUIREMENTS

## Security

Implement:

- CSRF protection
- Safe session management
- Password hashing
- Server-side authorization
- Queryset branch isolation
- Safe file uploads
- Secrets in environment variables
- Production-safe settings
- No DEBUG in production
- No real credentials committed to Git

## Performance

Implement:

- Pagination
- Efficient ORM queries
- `select_related`
- `prefetch_related`
- Indexed search/filter columns
- No avoidable N+1 queries
- Reasonable file upload limits

## Maintainability

Implement:

- Named URLs
- Reusable templates
- Services for business logic
- Reusable validators
- Centralized permission policies
- Consistent statuses
- Django migrations
- Documented important decisions

## Reliability

Implement:

- Atomic stock mutations
- Idempotent posting
- Transaction rollback
- Explicit error handling
- Relevant audit information
- Repeatable seed data
- Integration tests

---

# 20. USER ACCEPTANCE SCENARIOS

The final system must demonstrate at least these complete scenarios:

### Scenario 1 — Product and Variant

Manager creates a product with Black/M and Black/L variants.

Each receives a unique SKU.

Inventory is tracked independently for both variants.

### Scenario 2 — Supplier Import

CS1 Manager creates an import receipt for 20 units of a SKU.

Before approval, stock remains unchanged.

Admin approves.

CS1 stock increases by 20.

Repeating approval does not add another 20.

### Scenario 3 — Outbound Sale

CS1 has 20 units.

Manager creates an outbound receipt for 5 units.

Before finalization, stock remains 20.

After finalization, stock becomes 15.

The receipt becomes non-editable.

### Scenario 4 — Branch Transfer

CS1 has 15 units.

CS2 requests 8.

CS1 dispatches 8.

CS1 now has 7.

Until CS2 confirms receipt, the 8 units remain represented as in transit.

CS2 confirms all 8.

CS2 stock increases by 8.

### Scenario 5 — Transfer Shortage

CS1 dispatches 8 units.

CS2 counts only 6.

The system records the discrepancy.

It must not silently treat 8 units as successfully received.

### Scenario 6 — Inventory Count

System snapshot is 10.

Actual count is 8.

Difference = -2.

Result = Thiếu.

Manager submits the count.

Admin approves.

Approval metadata updates.

Inventory is not silently reset to 8 unless a separate adjustment rule has been authorized.

### Scenario 7 — Reporting

Admin can view data across both branches.

Manager assigned to CS2 sees CS2 only.

Reports distinguish sales from interbranch transfer.

Excel export matches permitted filters.

### Scenario 8 — Permission Enforcement

Staff attempts to submit a direct stock adjustment request or approve a receipt.

Backend rejects the request even if the staff member crafts the HTTP request manually.

### Scenario 9 — Concurrent Outbound

A stock balance contains 5 units.

Two concurrent requests each attempt to finalize a sale of 4 units.

At most one succeeds.

Final stock must never become negative.

### Scenario 10 — Failure Rollback

Simulate a database error during inventory posting.

No partial stock movement or incorrect completed/approved document state remains.

---

# 21. REQUIRED DOCUMENTATION OUTPUTS

Create and maintain:

- `README.md`
- `.env.example`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/REQUIREMENTS_MATRIX.md`
- `docs/ERD_AUDIT.md`
- `docs/DECISIONS.md`
- `docs/DATABASE_DESIGN.md`
- `docs/PERMISSIONS.md`
- `docs/STOCK_WORKFLOWS.md`
- `docs/TEST_RESULTS.md`
- `docs/DEMO_GUIDE.md`

Also produce a final ERD matching the actual implemented Django models, or a reproducible diagram generated from the models.

The final ERD must reflect implemented foreign keys and cardinality, not an outdated conceptual proposal.

---

# 22. RUN AND VERIFY

Run appropriate commands, such as:

- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py migrate`
- `python manage.py test`

Use PostgreSQL for stock concurrency integration tests.

Run code quality and browser checks where configured.

Do not claim success unless the command actually completed successfully.

Document exact commands and results.

Ensure the project has a reliable local setup procedure.

Provide sample data through fixtures or management commands, not manually edited database state.

---

# 23. DEFINITION OF DONE

The task is complete only when:

1. All documented use cases have implementation coverage.
2. The database supports variants and branch-specific stock.
3. Django migrations work.
4. Authentication and role permissions work.
5. Product CRUD works.
6. Import approval and inventory posting work.
7. Outbound stock deductions work.
8. Transfer processing works.
9. Inventory counts work.
10. Reports use real business data.
11. Excel import/export works.
12. Notifications and stock warnings work.
13. Core user flows are accessible through the UI.
14. Automated tests pass.
15. Critical concurrency and rollback tests pass.
16. No major workflow is represented only by mock buttons.
17. Database design, ERD, and implementation match.
18. Installation and demonstration steps are documented.
19. Unresolved specification conflicts are explicitly listed.
20. The implementation can be demonstrated end-to-end.

Do not report a feature as complete solely because a model, URL, or template exists.

---

# 24. FINAL RESPONSE FORMAT

At the end, provide:

### 1. Implementation Summary
What was actually built.

### 2. Architecture
Django apps and major responsibilities.

### 3. Database
Final tables, relationships, and changes from the original ERD.

### 4. Use Case Coverage
Implemented, partially implemented, blocked, and not implemented.

### 5. Tests
Executed commands, passed/failed results, and untested areas.

### 6. Running the Application
Actual installation and startup commands.

### 7. Demo Accounts
Only development/test accounts, with credentials delivered securely and never committed as production secrets.

### 8. Known Issues
Unresolved defects, business decisions, limitations, and next steps.

---

# 25. FINAL DIRECTIVE

**START NOW.**

First inspect all documents and the existing repository.

Then create the audit, requirement matrix, architecture and implementation plan.

Immediately proceed to implementation in the planned order.

Do not stop after planning.

Do not stop after building the ERD.

Do not stop after creating Django models.

Do not stop after implementing the backend.

Continue through the interface, integration, testing, and verification phases.

Prioritize correctly implemented business logic, data integrity, permissions, and working end-to-end workflows over superficial completeness.

If the available execution environment prevents completion, finish every independent task possible, clearly identify the blocker, and never claim unfinished work is complete.

The expected deliverable is a **functional, tested Django inventory management application for Old School**, traceable to the original specification.