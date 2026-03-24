# 🚀 Stitch's Frontend Development Guide: Sistema Feria Social

This document serves as the **Source of Truth** for improving the frontend of the "Sistema Feria Social". It explains the current architecture, data flow, and provides recommendations for a premium, modern user experience.

---

## 🏗️ Technical Architecture

### **Backend (FastAPI)**
- **API Base**: All data endpoints are under `/public`, `/admin`, `/socio`, `/becario`, etc.
- **Templates**: Jinja2 (`app/templates/`).
- **Static Assets**: `app/static/` (CSS, JS, Images).

### **Frontend Current Stack**
- **HTML**: Semantic HTML5.
- **Templating**: Jinja2 (Inheritance via `base.html`).
- **CSS**: Vanilla CSS with modern variables and glassmorphism.
- **JS**: Native JavaScript (ESM modules).

---

## 🎨 Design System & Aesthetics

The current design uses a **White/Blue/Dark** palette with premium touches:
- **Colors**:
  - Primary: `#2563eb` (Blue)
  - Dark: `#0f172a` (Navy)
  - Surface: `rgba(255, 255, 255, 0.88)` with `backdrop-filter: blur(12px)`.
- **Typography**: "Segoe UI", Arial, sans-serif.
- **Effects**: Soft shadows, glassmorphism, and subtle fade-up animations.

---

## 🛠️ Key Endpoints for Frontend

### **Public / Student Flows**
- `GET /catalogo-proyectos`: Main project catalog.
- `GET /acceso-estudiante`: Student QR generation page.
- `GET /public/projects`: JSON list of all active projects.
- `POST /public/generate-qr`: Generates a JWT for the student's QR.
- `POST /public/register`: Enrolls a student in a project using a temporary code.

### **Dashboard Flows**
- `GET /admin-panel`: Admin control center.
- `GET /socio`: Partner (Socio Formador) dashboard.
- `GET /becario`: Scholarship recipient dashboard (check-in focus).

---

## 💡 Recommendations for "Stitch"

To build a **WOW** frontend, I recommend focusing on these areas:

### 1. **Responsive & Mobile-First**
Current dashboards are clean but can be optimized for mobile devices. Ensure charts and tables wrap correctly or use horizontal scrolling where necessary.

### 2. **Interactive UI with Alpine.js (Optional)**
Since you are using Jinja2, adding **Alpine.js** can provide modern interactivity (modals, dropdowns, tabs) without the complexity of a full framework like React. It fits perfectly with the current structure.

### 3. **Component modularity**
Use Jinja2 `{% include 'components/my-component.html' %}` to break down large files like `admin_dashboard.html` into smaller, manageable chunks.

### 4. **Enhanced Feedback**
Improve user notifications (Toasts) using a library like `SweetAlert2` or a custom CSS toast system for actions like "Project Registered" or "Login Failed".

### 5. **Skeleton Loaders**
When fetching projects from `/public/projects`, use skeleton loaders to make the perceived performance faster.

---

## 📂 Project Navigation for Stitch
- `app/templates/base.html`: Main layout and nav logic.
- `app/static/css/styles.css`: Global design tokens and component styles.
- `app/static/js/auth.js`: Handles session and cookies.
- `app/routers/views.py`: Route definitions for all pages.
