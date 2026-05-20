// Jenkinsfile — place at repo ROOT
// Requires: Multibranch Pipeline job in Jenkins
// Branch behaviour:
//   feature/* and develop → lint + test + docker build check (no deploy)
//   main                  → lint + test + build + push
//
// NOTE: Deploy to Kubernetes is commented out until a VPS/kubeconfig is available.

pipeline {
    agent any

    environment {
        GHCR_USER    = credentials('ghcr-username')
        GHCR_TOKEN   = credentials('ghcr-token')
        IMAGE_PREFIX = "ghcr.io/${GHCR_USER}/paper-killer"
        IMAGE_TAG    = "${env.GIT_COMMIT[0..7]}"
    }

    stages {

        // ─── STAGE 1: LINT ───────────────────────────────────────────────────
        stage('Lint & Security Scan') {
            agent {
                docker {
                    image 'python:3.12-slim'
                    reuseNode true
                    args '-u root'
                }
            }
            steps {
                sh '''
                    pip install ruff bandit pip-audit --quiet --no-cache-dir --root-user-action=ignore

                    echo "--- Ruff linter ---"
                    ruff check services/

                    echo "--- Ruff format check ---"
                    ruff format --check services/

                    echo "--- Bandit security scan ---"
                    bandit -r services/ -ll -x services/auth/tests,services/form/tests,services/workflow/tests -q

                    echo "--- pip-audit CVE check ---"
                    for svc in auth form workflow; do
                        echo "Auditing $svc..."
                        pip-audit -r services/$svc/requirements.txt --progress-spinner off --ignore-vuln CVE-2026-30922 --ignore-vuln CVE-2025-54121 --ignore-vuln CVE-2025-62727
                    done
                '''
            }
        }

        // ─── STAGE 2: TESTS ──────────────────────────────────────────────────
        stage('Tests') {
            steps {
                sh '''
                    # Create isolated network for this build
                    docker network create pk-ci-network || true

                    # Start PostgreSQL
                    docker run -d \
                        --name pk-postgres-test \
                        --network pk-ci-network \
                        -e POSTGRES_USER=pk_user \
                        -e POSTGRES_PASSWORD=pk_password \
                        -e POSTGRES_DB=paper_killer_test \
                        postgres:16-alpine

                    # Start Redis
                    docker run -d \
                        --name pk-redis-test \
                        --network pk-ci-network \
                        redis:7-alpine

                    # Wait for postgres to be ready
                    echo "Waiting for postgres..."
                    for i in $(seq 1 15); do
                        docker exec pk-postgres-test pg_isready -U pk_user && break
                        sleep 2
                    done

                    FAILED=0
                    for svc in auth form workflow; do
                        echo "====== Testing $svc ======"
                        docker run --rm \
                            --network pk-ci-network \
                            -v $(pwd)/services/$svc:/app \
                            -w /app \
                            -e DATABASE_URL=postgresql://pk_user:pk_password@pk-postgres-test:5432/paper_killer_test \
                            -e DATABASE_SCHEMA=${svc}_schema \
                            -e REDIS_URL=redis://pk-redis-test:6379/0 \
                            -e JWT_SECRET=test_secret_key_not_for_production \
                            -e JWT_ALGORITHM=HS256 \
                            -e JWT_EXPIRE_MINUTES=60 \
                            -e AUTH_SERVICE_URL=http://localhost:8001 \
                            -e WORKFLOW_SERVICE_URL=http://localhost:8003 \
                            python:3.12-slim \
                            sh -c "
                                pip install -r requirements.txt --quiet --no-cache-dir &&
                                pip install pytest pytest-asyncio pytest-cov pytest-mock httpx --quiet --no-cache-dir &&
                                alembic upgrade head &&
                                PYTHONPATH=. pytest tests/ -v \
                                    --cov=app \
                                    --cov-report=term-missing \
                                    --cov-report=xml:/app/coverage.xml \
                                    --cov-fail-under=85
                            " || FAILED=1

                        echo "====== $svc done ======"
                    done

                    # Cleanup
                    docker rm -f pk-postgres-test pk-redis-test || true
                    docker network rm pk-ci-network || true

                    if [ $FAILED -ne 0 ]; then
                        echo "One or more services failed tests or coverage gate"
                        exit 1
                    fi
                '''
            }
            post {
                always {
                    // junit requires node context — this stage runs on agent any, so it is fine
                    junit allowEmptyResults: true, testResults: 'services/*/coverage.xml'
                    // Cleanup in case of mid-loop failure
                    sh '''
                        docker rm -f pk-postgres-test pk-redis-test 2>/dev/null || true
                        docker network rm pk-ci-network 2>/dev/null || true
                    '''
                }
            }
        }

        // ─── STAGE 3: DOCKER BUILD VALIDATION ───────────────────────────────
        stage('Docker Build') {
            steps {
                sh '''
                    echo "Building all service images..."
                    docker build -t pk-auth:${IMAGE_TAG}     ./services/auth
                    docker build -t pk-form:${IMAGE_TAG}     ./services/form
                    docker build -t pk-workflow:${IMAGE_TAG} ./services/workflow

                    echo "All images built successfully"
                    docker images | grep pk-
                '''
            }
        }

        // ─── STAGE 4: PUSH TO REGISTRY (main only) ──────────────────────────
        stage('Push Images') {
            when { branch 'main' }
            steps {
                sh '''
                    echo $GHCR_TOKEN | docker login ghcr.io -u $GHCR_USER --password-stdin

                    for svc in auth form workflow; do
                        docker tag pk-${svc}:${IMAGE_TAG} ${IMAGE_PREFIX}-${svc}:${IMAGE_TAG}
                        docker tag pk-${svc}:${IMAGE_TAG} ${IMAGE_PREFIX}-${svc}:latest
                        docker push ${IMAGE_PREFIX}-${svc}:${IMAGE_TAG}
                        docker push ${IMAGE_PREFIX}-${svc}:latest
                        echo "Pushed ${svc} → ${IMAGE_TAG}"
                    done
                '''
            }
        }

        // ─── STAGE 5: DEPLOY TO KUBERNETES (commented out — no VPS yet) ─────
        // Uncomment when kubeconfig credential is added to Jenkins and VPS is ready.
        //
        // stage('Deploy to Kubernetes') {
        //     when { branch 'main' }
        //     agent {
        //         docker {
        //             image 'bitnami/kubectl:latest'
        //             reuseNode true
        //             args '-u root'
        //         }
        //     }
        //     environment {
        //         KUBECONFIG = credentials('kubeconfig')
        //     }
        //     steps {
        //         sh '''
        //             for svc in auth form workflow; do
        //                 kubectl set image deployment/pk-${svc} \
        //                     pk-${svc}=${IMAGE_PREFIX}-${svc}:${IMAGE_TAG}
        //             done
        //             for svc in auth form workflow; do
        //                 kubectl rollout status deployment/pk-${svc} --timeout=300s
        //             done
        //         '''
        //     }
        // }

        // ─── STAGE 6: SMOKE TESTS (commented out — no VPS yet) ──────────────
        //
        // stage('Smoke Tests') {
        //     when { branch 'main' }
        //     steps {
        //         sh '''
        //             sleep 15
        //             for port in 8001 8002 8003; do
        //                 STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${port}/health)
        //                 if [ "$STATUS" != "200" ]; then
        //                     echo "SMOKE TEST FAILED: port ${port} returned ${STATUS}"
        //                     exit 1
        //                 fi
        //                 echo "Health check passed: port ${port}"
        //             done
        //         '''
        //     }
        // }
    }

    post {
        failure {
            // kubectl rollback commented out — no VPS yet
            // Uncomment and add KUBECONFIG env when deploy stage is re-enabled.
            //
            // script {
            //     if (env.BRANCH_NAME == 'main') {
            //         sh '''
            //             for svc in auth form workflow; do
            //                 kubectl rollout undo deployment/pk-${svc} || true
            //             done
            //         '''
            //     }
            // }
            echo "Pipeline failed on branch: ${env.BRANCH_NAME}"
        }
        always {
            // node context is guaranteed here because agent any is set at pipeline level
            sh '''
                docker rmi $(docker images "pk-*" -q) --force 2>/dev/null || true
            '''
        }
        success {
            echo "Pipeline completed for branch: ${env.BRANCH_NAME}"
        }
    }
}
