pipeline {
    agent any
    options {
        timestamps()
    }
    environment {
        DATABASE_URL = "postgresql://pk_user:pk_password@localhost:5432/paper_killer_test"
        REDIS_URL = "redis://localhost:6379/0"
        JWT_SECRET = "test_secret_key_not_for_production"
        JWT_ALGORITHM = "HS256"
        JWT_EXPIRE_MINUTES = "60"
        AUTH_SERVICE_URL = "http://localhost:8001"
        WORKFLOW_SERVICE_URL = "http://localhost:8003"
        PIP_DISABLE_PIP_VERSION_CHECK = "1"
        PYTHONUNBUFFERED = "1"
    }
    stages {
        stage("Lint") {
            steps {
                sh "python3 -m pip install --upgrade pip"
                sh "python3 -m pip install ruff bandit pip-audit"
                sh "ruff check services/"
                sh "ruff format --check services/"
                sh "bandit -r services/ -ll --exclude services/auth/tests,services/form/tests,services/workflow/tests,services/task/tests,services/notification/tests"
                sh """
                    for svc in auth form workflow task notification; do
                        echo "Auditing ${svc}..."
                        (cd services/${svc} && pip-audit \
                            --ignore-vuln CVE-2026-30922 \
                            --ignore-vuln CVE-2025-62727 \
                            --ignore-vuln CVE-2024-47874 \
                            --ignore-vuln CVE-2025-54121)
                    done
                """
            }
        }
        stage("Tests") {
            steps {
                sh """
                    docker rm -f pk-postgres-test pk-redis-test pk-ci-network >/dev/null 2>&1 || true
                    docker network create pk-ci-network
                    docker run -d --name pk-postgres-test --network pk-ci-network \
                        -e POSTGRES_USER=pk_user \
                        -e POSTGRES_PASSWORD=pk_password \
                        -e POSTGRES_DB=paper_killer_test \
                        -p 5432:5432 \
                        postgres:16-alpine
                    docker run -d --name pk-redis-test --network pk-ci-network \
                        -p 6379:6379 \
                        redis:7-alpine

                    echo "Waiting for Postgres..."
                    until docker exec pk-postgres-test pg_isready -U pk_user >/dev/null 2>&1; do
                        sleep 2
                    done

                    echo "Waiting for Redis..."
                    until docker exec pk-redis-test redis-cli ping | grep -q PONG; do
                        sleep 2
                    done
                """
                script {
                    def services = ["auth", "workflow", "task"]
                    def branches = [:]
                    for (svc in services) {
                        def serviceName = svc
                        branches[serviceName] = {
                            sh """
                                cd services/${serviceName}
                                python3 -m pip install -r requirements.txt
                                python3 -m pip install pytest pytest-asyncio pytest-cov pytest-mock httpx
                                DATABASE_SCHEMA=${serviceName}_schema alembic upgrade head
                                DATABASE_SCHEMA=${serviceName}_schema \
                                    PYTHONPATH=. \
                                    pytest tests/ -v \
                                      --cov=app \
                                      --cov-report=term-missing \
                                      --cov-report=xml:coverage.xml \
                                      --cov-fail-under=85
                            """
                        }
                    }
                    parallel branches
                }
            }
        }
        stage("Docker Build") {
            steps {
                sh """
                    docker build -t pk-auth:test ./services/auth
                    docker build -t pk-form:test ./services/form
                    docker build -t pk-workflow:test ./services/workflow
                    docker build -t pk-task:test ./services/task
                    docker build -t pk-notification:test ./services/notification
                    docker images | grep pk-
                """
            }
        }
    }
    post {
        always {
            sh """
                docker rm -f pk-postgres-test pk-redis-test >/dev/null 2>&1 || true
                docker network rm pk-ci-network >/dev/null 2>&1 || true
            """
        }
    }
}
