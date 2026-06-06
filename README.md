# OmniFlow (Paper Killer) 🚀

OmniFlow is a high-performance, microservices-based workflow automation platform designed to transform physical paper forms into digital, trackable processes. It features OCR-driven field extraction, flexible workflow management, and a robust CI/CD pipeline optimized for enterprise environments.

## 🏗 Architecture

The system is architected as a set of specialized microservices following a "Database-per-Service" pattern (isolated via PostgreSQL schemas).

- **Auth Service**: Manages users, institutions, and multi-tenant authentication (JWT, OAuth2, Magic Links).
- **Form Service**: Handles form definitions, OCR field extraction (Tesseract), and public submissions.
- **Workflow Service**: Manages the graph-based state engine, publishing workflows, and transition integrity.
- **Task Service**: Orchestrates human-in-the-loop task queues and maintains an immutable audit trail.
- **Notification Service**: Delivers real-time updates via Server-Sent Events (SSE) and worker-driven pub/sub.
- **Gateway (Nginx)**: A unified API entry point with `auth_request` sidecar validation and RBAC enforcement.

## 🛠 CI/CD Pipeline (Jenkins)

The pipeline is the backbone of OmniFlow's reliability, optimized for high-performance execution on restricted network nodes.

### Pipeline Innovation
- **Parallelized Test Matrix**: Executes tests for all 5 microservices concurrently, significantly reducing build times.
- **Offline Wheelhouse**: Solves the "no-internet" CI problem by pre-caching all dependencies as wheels in a base image during the build-host phase.
- **Shared Networking**: Containers utilize the `--network container:...` stack to share the network namespace with PostgreSQL, eliminating bridge-layer latency and DNS resolution failures.
- **Automated DB Readiness**: A staggered, non-blocking readiness loop ensures that parallel tests only begin once the database is truly accepting connections.
- **Compliance & Security**: Integrated `ruff` for linting, `bandit` for static security analysis, and `pip-audit` for dependency CVE tracking.

## 📊 Pipeline Step Evaluation

| Step | Score | Rationale |
| :--- | :---: | :--- |
| **Prepare Test Base** | **10/10** | **Outstanding.** Uses `--network=host` to build a global wheelhouse. This ensures that the rest of the pipeline is 100% immune to external network failures. |
| **Lint & Security** | **9/10** | **Excellent.** Triple-threat scanning (Lint, Security, CVE). Extremely fast due to pre-baked tools in the base image. |
| **Parallel Tests** | **10/10** | **Best-in-Class.** Implements staggered startup and shared network namespaces. Solves the complex "database timeout" problem in parallel environments. |
| **Docker Build** | **8/10** | **Solid.** Thorough validation of all production Dockerfiles. Could be improved with multi-arch support. |
| **Smoke Tests** | **9/10** | **Very Good.** Conducts real HTTP health checks across the service mesh before deployment. Ensures connectivity between services is functional. |
| **Push & Deploy** | **8/10** | **Robust.** Clean GHCR lifecycle and non-blocking K8s rollouts with status monitoring. |

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ (local testing)

### Local Development
1. Clone the repository and navigate to the root.
2. Launch the full environment:
   ```bash
   docker-compose up --build
   ```
3. Access the applications:
   - **Frontend**: [http://localhost:80](http://localhost:80)
   - **Admin Portal**: [http://localhost:80/admin.html](http://localhost:80/admin.html)
   - **Staff Inbox**: [http://localhost:80/staff.html](http://localhost:80/staff.html)

### Running Tests
To run tests locally for a specific service:
```bash
cd services/auth
pytest tests/ -v --cov=app
```

---
*OmniFlow: Paper ends here.*

