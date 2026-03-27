# Project Overview
**Feria Servicio Social Tec** is a web-based management system for the Social Service Fair at Tecnológico de Monterrey. It connects students with social service projects offered by external partners (Socios Formadores).

The platform handles:
- **Project Catalog**: Public listing of available social service projects with filtering.
- **Student Registration**: Process for students to sign up for specific projects using temporary codes.
- **Socio Dashboard**: Tools for partners to manage their projects, monitor capacity, and export student lists.
- **Admin Dashboard**: System-wide oversight of users, projects, and event logistics.
- **Check-in System**: Real-time attendance tracking during the fair using QR codes.

# Current State (DO NOT BREAK)
The following core functionalities are fully operational and should not be refactored unless specifically requested:
- **Authentication & RBAC**: JWT-based login and role-based access (ADMIN, SOCIO, BECARIO).
- **Database Schema**: SQLAlchemy models for Users, Students, Projects, Registrations, and TempCodes.
- **Socio Project Management**: Ability to list, view details, and generate registration codes.
- **Static File Serving**: The `/static` mounting and Jinja2 template rendering.
- **CSV Export**: The student list export functionality in the Socio dashboard.

# Project Structure
- `app/main.py`: Application entry point and router registration.
- `app/models/`: Database schema definitions (SQLAlchemy).
- `app/routers/`: Business logic divided by role (e.g., `socio.py`, `admin.py`, `public.py`).
- `app/schemas/`: Pydantic models for request/response validation.
- `app/services/`: Reusable business logic and helper functions.
- `app/templates/`: Jinja2 HTML templates for the frontend.
- `app/static/`: Frontend assets (CSS, JS, images).
- `alembic/`: Database migration scripts.
- `requirements.txt`: Python dependencies (FastAPI, SQLAlchemy, Pydantic).

# Rules for the AI Agent
- **Stability First**: Do not break existing registration or authentication flows.
- **Incremental Improvements**: Prefer adding new features or enhancing UI over rewriting existing logic.
- **Modular Code**: Keep routers and services focused on their specific roles.
- **Style Consistency**: Maintain the current Python (PEP 8) and Javascript patterns. Use Vanilla CSS/JS unless asked otherwise.
- **No Refactoring**: Do not refactor core DB models or authentication logic unless explicitly instructed.

# Development Guidelines
- **FastAPI Best Practices**: Use Pydantic schemas for all API inputs/outputs. Use dependency injection for DB sessions and auth.
- **Template Safety**: Use Jinja2 blocks correctly; extend `base.html` for all new pages.
- **Frontend**: Keep Javascript modular (e.g., `socio.js`, `admin.js`). Use `ui.js` for shared UI utilities.
- **Error Handling**: Use FastAPI `HTTPException` for consistent API error responses.

# Current Focus / Roadmap
The project is moving from "Functional" to "Premium". The current focus is on visual excellence and data storytelling.

**Priorities**:
- **Modernizing Dashboards**: Transitioning from text-heavy lists to interactive, visual dashboards.
- **UI/UX Refinement**: implementing smoother transitions, better spacing, and a more polished "Tec" brand feel.
- **Interactive Visualizations**: Using modern JS libraries to show project progress and registration stats.

# Visualization Goals
- **Interactive Charts**: Replace static numbers with charts showing capacity vs. registrations.
- **Data Storytelling**: Clearer visual indicators for project status (Active, Full, Pending).
- **Student Analytics**: (For Admins) Visual overview of registration trends across different careers.

# What to Improve (but carefully)
- **CSS Layouts**: Improve responsiveness and visual hierarchy.
- **Dashboard UI**: Make the Socio/Admin views more intuitive and "glanceable".
- **Project Cards**: Enhance the visual appeal of the project catalog.

# What NOT to do
- **Do not rewrite** the authentication system or the role-based dependency checks.
- **Do not change** the database engine or core SQLAlchemy configuration.
- **Do not delete** any existing templates even if they look simple; improve them instead.

# Suggested Next Steps for the Agent
1.  **Dashboard Modernization**: Update `socio_dashboard.html` and `socio.js` to include a visual progress bar or small chart for each project's capacity.
2.  **UI Utility Expansion**: Add more reusable components to `app/static/js/ui.js` (e.g., modern modal system, improved toast notifications).
3.  **Catalog Enhancement**: Refine `catalogo_proyectos.html` with better filters and a "hero" section for a more premium look.
4.  **Admin Overview**: Implement a summary card section in `admin_dashboard.html` with real-time stats (Total Projects, Total Registrations).
