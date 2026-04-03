# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Development server with auto-reload
python -m app.main
# OR
uvicorn app.main:app --reload

# Production server (as configured in Procfile)
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Database Operations
```bash
# Create a new migration after model changes
alembic revision --autogenerate -m "description"

# Apply pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View current migration version
alembic current
```

### Environment Setup
```bash
# Create virtual environment
python -m venv env

# Activate (Windows)
source env/Scripts/activate

# Activate (Unix)
source env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Seeding Data
The `scripts/` directory contains seed scripts for development:
- `seed_admin.py` - Create admin user
- `seed_user.py` - Create SOCIO users
- `seed_project.py` - Create sample projects
- `seed_student.py` - Create sample students

## Architecture Overview

### Technology Stack
- **Backend**: FastAPI + SQLAlchemy 2.0 + PostgreSQL (via Supabase)
- **Frontend**: Vanilla JS (ES modules) + Jinja2 templates + CSS
- **Auth**: JWT tokens (stored in cookies for browser views, Bearer tokens for API)
- **Migrations**: Alembic

### Request Flow
1. **Public Routes** (`routers/public.py`): No authentication required
2. **View Routes** (`routers/views.py`): JWT from cookie + role check via `require_roles()`
3. **API Routes**: JWT from Authorization header via `OAuth2PasswordBearer`

All HTML views extend `templates/base.html` and use JS modules in `static/js/`.

### Role-Based Access Control (RBAC)
Roles are defined in `User.role`: ADMIN, SOCIO, BECARIO.

Authorization patterns:
- **API endpoints**: Use `require_role("ROLE")` dependency from `security.py`
- **HTML views**: Use `require_roles(request, ["ROLE"])` from `views.py`

### Authentication Flow
1. User logs in via `/auth/login` (returns JWT)
2. Browser stores JWT in `access_token` cookie via `auth.js`
3. Subsequent requests: cookie is sent, validated by `get_current_user_from_cookie()` or `get_current_user()`
4. Token expiration: handled by 401 response → redirect to `/login`

### Database Architecture
- **Session Management**: `get_db()` dependency yields SQLAlchemy sessions, auto-closes
- **Connection Handling**: Supports both Supabase (SSL) and local PostgreSQL via `USE_LOCAL_DB` env var
- **Base Model**: All models inherit from `app/db/base.py:Base`
- **UUID Primary Keys**: All tables use `UUID(as_uuid=True)` with `uuid.uuid4()` default

### Frontend Architecture
- **Entry Point**: Templates extend `base.html`, which loads `auth.js`
- **Module System**: ES modules in `static/js/` - each page has its own JS file (e.g., `socio.js`, `admin.js`)
- **Shared Utilities**:
  - `api.js`: `requestJSON()` wrapper for fetch with error handling
  - `ui.js`: Toast notifications, loading overlay, modal helpers
  - `auth.js`: Token management, logout, role-based UI updates

### API Patterns
- **Schemas**: Minimal - only `schemas/auth.py` exists; most endpoints use model dicts directly
- **Error Handling**: `HTTPException` with status codes; global SQLAlchemy error handler in `main.py`
- **Response Format**: JSON with `detail` key for errors

### Template Patterns
- All pages extend `base.html`
- Use `url_for('static', path='...')` for assets
- Query version strings (`?v=N`) for cache busting on static assets
- Conditional header rendering for public pages (no auth header)

### Key Directories
```
app/
  core/           # Config, security utilities
  db/             # Session, Base model
  models/         # SQLAlchemy models
  routers/        # FastAPI route handlers by role
  schemas/        # Pydantic schemas (minimal)
  services/       # Business logic (mostly empty)
  static/         # CSS, JS, images
  templates/      # Jinja2 HTML
scripts/          # Seed/utility scripts
alembic/          # Database migrations
```

## Project Overview

**Feria Servicio Social Tec** is a web-based management system for the Social Service Fair at Tecnológico de Monterrey. It connects students with social service projects offered by external partners (Socios Formadores).

The platform handles:
- **Project Catalog**: Public listing of available social service projects with filtering.
- **Student Registration**: Process for students to sign up for specific projects using temporary codes.
- **Socio Dashboard**: Tools for partners to manage their projects, monitor capacity, and export student lists.
- **Admin Dashboard**: System-wide oversight of users, projects, and event logistics.
- **Check-in System**: Real-time attendance tracking during the fair using QR codes.

## Current State (DO NOT BREAK)

The following core functionalities are fully operational and should not be refactored unless specifically requested:
- **Authentication & RBAC**: JWT-based login and role-based access (ADMIN, SOCIO, BECARIO).
- **Database Schema**: SQLAlchemy models for Users, Students, Projects, Registrations, and TempCodes.
- **Socio Project Management**: Ability to list, view details, and generate registration codes.
- **Static File Serving**: The `/static` mounting and Jinja2 template rendering.
- **CSV Export**: The student list export functionality in the Socio dashboard.

## Rules for the AI Agent
- **Stability First**: Do not break existing registration or authentication flows.
- **Incremental Improvements**: Prefer adding new features or enhancing UI over rewriting existing logic.
- **Modular Code**: Keep routers and services focused on their specific roles.
- **Style Consistency**: Maintain the current Python (PEP 8) and Javascript patterns. Use Vanilla CSS/JS unless asked otherwise.
- **No Refactoring**: Do not refactor core DB models or authentication logic unless explicitly instructed.

## Development Guidelines
- **FastAPI Best Practices**: Use Pydantic schemas for all API inputs/outputs. Use dependency injection for DB sessions and auth.
- **Template Safety**: Use Jinja2 blocks correctly; extend `base.html` for all new pages.
- **Frontend**: Keep Javascript modular (e.g., `socio.js`, `admin.js`). Use `ui.js` for shared UI utilities.
- **Error Handling**: Use FastAPI `HTTPException` for consistent API error responses.

## Current Focus / Roadmap

The project is moving from "Functional" to "Premium". The current focus is on visual excellence and data storytelling.

**Priorities**:
- **Modernizing Dashboards**: Transitioning from text-heavy lists to interactive, visual dashboards.
- **UI/UX Refinement**: implementing smoother transitions, better spacing, and a more polished "Tec" brand feel.
- **Interactive Visualizations**: Using modern JS libraries to show project progress and registration stats.

## Visualization Goals
- **Interactive Charts**: Replace static numbers with charts showing capacity vs. registrations.
- **Data Storytelling**: Clearer visual indicators for project status (Active, Full, Pending).
- **Student Analytics**: (For Admins) Visual overview of registration trends across different careers.

## What to Improve (but carefully)
- **CSS Layouts**: Improve responsiveness and visual hierarchy.
- **Dashboard UI**: Make the Socio/Admin views more intuitive and "glanceable".
- **Project Cards**: Enhance the visual appeal of the project catalog.

## What NOT to do
- **Do not rewrite** the authentication system or the role-based dependency checks.
- **Do not change** the database engine or core SQLAlchemy configuration.
- **Do not delete** any existing templates even if they look simple; improve them instead.
