# Paper Killer (OmniFlow)

Paper Killer is a document-workflow automation platform designed for institutions like hospitals, schools, and government offices that still rely on manual paper-based approval chains.

## Project Vision
Administrators upload existing PDF forms → OCR extracts fields → Administrators define multi-step approval workflows → End users submit data via QR codes → Tasks route through role-based queues to completion.

---

## Architecture Overview

Paper Killer is built as a **microservices system** with the following components:

-   **Auth Service (Port 8001)**: Manages users, institutions, and JWT authentication (OAuth, Magic Links).
-   **Form Service (Port 8002)**: Handles PDF uploads, OCR (Tesseract), field extraction, and submission storage.
-   **Workflow Service (Port 8003)**: Manages workflow definitions (graph-based) and state transitions.
-   **Task Service (Port 8004)**: Manages task assignments, staff inboxes, and audit history.
-   **Notification Service (Port 8005)**: Dispatches in-app notifications and manages Server-Sent Events (SSE).
-   **API Gateway (Nginx)**: Central entry point (Port 80) handling routing and RBAC verification.
-   **Frontend**: Vanilla JS applications served by Nginx.

### Data Flow
-   **Database**: Single PostgreSQL instance with schema-per-service isolation.
-   **Events**: Redis-based asynchronous event bus for side effects (e.g., notifications).
-   **Communication**: Synchronous REST APIs for core business logic.

---

## Tech Stack

-   **Backend**: FastAPI, SQLAlchemy 2.0 (Async), Pydantic, Alembic.
-   **Frontend**: HTML5, Tailwind CSS (via CDN), Vanilla JavaScript (ES Modules).
-   **Security**: JWT-based RBAC, Bandit security scanning, Ruff linting.
-   **Infrastructure**: Docker, Docker Compose, Jenkins CI/CD, Nginx.
-   **OCR**: Tesseract.

---

## Getting Started

### Prerequisites
-   Docker and Docker Compose
-   Git

### Local Development
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd omniflow
   ```
2. Start the full stack:
   ```bash
   docker-compose up --build
   ```
3. Access the dashboard:
   -   Gateway: `http://localhost:80`
   -   Admin Dashboard: `http://localhost:80/admin.html`
   -   Staff Dashboard: `http://localhost:80/staff.html`

### Running Tests
Tests must be run from each service's root directory:
```bash
cd services/auth
pytest tests/
```

---

## CI/CD Pipeline

The project uses a Jenkins-based pipeline defined in the `Jenkinsfile`.

### Stages:
1.  **Lint & Security Scan**: Ruff (linter/formatter), Bandit (security), Pip-audit (CVEs).
2.  **Tests & Coverage**: Per-service test execution with an 85% coverage threshold.
3.  **Docker Build**: Validates that all service Dockerfiles build correctly.
4.  **Push Images** (Main branch only): Pushes versioned images to GHCR.
5.  **Deployment** (Planned): Continuous deployment to Kubernetes.

---

## Directory Structure
```
.
├── frontend/               # Static HTML/JS files
├── gateway/                # Nginx API Gateway configuration
├── services/
│   ├── auth/               # Authentication & User Management
│   ├── form/               # OCR & Form Management
│   ├── workflow/           # Workflow Engine
│   ├── task/               # Task & Submission Routing
│   └── notification/       # Events & SSE Notifications
├── scripts/                # Database initialization scripts
└── Jenkinsfile             # CI/CD Pipeline definition
```

---

## License
[Insert License Information]
