# Phase 01: Project Foundation & Authentication

## Overview
- **Priority**: P1
- **Status**: In Progress
- **Description**: Configure Django 5.2 LTS, PostgreSQL 16 connection, custom `User` model (`ADMIN`, `MANAGER`, `STAFF`), `CoSo` (Branch) model, global `base.html` matching Figma Old School branding, authentication (`UC-1`, `UC-2`), and centralized RBAC helpers.

## Related Code Files
- `manage.py`
- `config/__init__.py`, `config/settings.py`, `config/urls.py`, `config/wsgi.py`, `config/asgi.py`
- `apps/branches/models.py`, `apps/branches/admin.py`
- `apps/accounts/models.py`, `apps/accounts/permissions.py`, `apps/accounts/forms.py`, `apps/accounts/views.py`, `apps/accounts/urls.py`, `apps/accounts/context_processors.py`
- `templates/base.html`, `templates/accounts/login.html`, `templates/403.html`, `static/css/oldschool.css`, `static/js/oldschool.js`

## Todo List
- [ ] Install Python 3.12, PostgreSQL 16, and `.venv` dependencies
- [ ] Create Django `config/` and `manage.py`
- [ ] Implement `branches.CoSo` and `accounts.User`
- [ ] Implement `UC-1` (Login + lockout on repeated failed attempts) and `UC-2` (Logout confirmation)
- [ ] Implement centralized RBAC decorators/mixins & branch scoping
- [ ] Build `base.html` and Old School CSS/JS theme
