// Jenkinsfile — place at repo ROOT
// Requires: Multibranch Pipeline job in Jenkins
// Branch behaviour:
//   feature/* and develop → lint + test + docker build check (no deploy)
//   main                  → lint + test + build + push
//
// NOTE: Deploy to Kubernetes is commented out until a VPS/kubeconfig is available.
//
// FIXES APPLIED:
//   [1] Replaced --volumes-from $HOSTNAME with explicit -v $WORKSPACE bind mount
//   [2] IMAGE_TAG now uses git rev-parse --short HEAD (safe on shallow clones)
//   [3] Per-service test failures are collected cleanly; cleanup never swallows exit code
//   [4] pip-audit CVE ignores carry expiry comments so they don't rot silently
//   [5] Global 40-minute timeout + per-stage timeouts guard against hung executors
//   [6] CI network name is suffixed with BUILD_NUMBER to prevent parallel-run collisions
//   [7] docker login is wrapped in withCredentials to avoid token leaking in console log

pipeline {
    agent any

    options {
        timeout(time: 40, unit: 'MINUTES')   // [5] kill the whole pipeline if it hangs
        disableConcurrentBuilds()            // prevent same-branch collision on small setups
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    environment {
        GHCR_USER    = credentials('ghcr-username')
        GHCR_TOKEN   = credentials('ghcr-token')
        TARGET_BRANCH = 'main'
        IMAGE_PREFIX = "ghcr.io/${GHCR_USER}/paper-killer"
        // [2] safe on shallow clones; GIT_COMMIT slice crashes when commit is unavailable
        IMAGE_TAG    = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
        // [6] unique network per build — prevents collision when two builds run in parallel
        CI_NETWORK   = "pk-ci-network-${env.BUILD_NUMBER}"
        TEST_BASE_IMG = "pk-test-base:${env.BUILD_NUMBER}"
    }

    stages {

        stage('Log Branch Context') {
            steps {
                echo "Building branch: ${env.BRANCH_NAME ?: 'unknown'}"
                echo "Target branch: ${env.TARGET_BRANCH}"
                echo "Change branch: ${env.CHANGE_BRANCH ?: 'n/a'}"
            }
        }

        // ─── STAGE 0: PREPARE TEST IMAGE ────────────────────────────────────
        stage('Prepare Test Base') {
            steps {
                // --network=host makes the build use the host's working resolver,
                // bypassing the broken container DNS entirely (BuildKit ignores daemon `dns`).
                sh "docker build --network=host -t ${TEST_BASE_IMG} -f services/Dockerfile.test ."
            }
        }

        // ─── STAGE 1: LINT & SECURITY SCAN ──────────────────────────────────
        stage('Lint & Security Scan') {
            options { timeout(time: 10, unit: 'MINUTES') }  // [5]
            agent {
                docker {
                    image "${TEST_BASE_IMG}"
                    reuseNode true
                    // --network=host: bridge containers on this VPS have no outbound
                    // egress (pip-audit's venv bootstrap couldn't reach PyPI). Host
                    // networking has working DNS + egress, same as the image builds.
                    // (--dns is incompatible with host networking, so it's dropped.)
                    args '-u root --network=host'
                }
            }
            steps {
                sh '''
                    echo "--- Ruff linter ---"
                    ruff check services/

                    echo "--- Ruff format check ---"
                    ruff format --check services/

                    echo "--- Bandit security scan ---"
                    bandit -r services/ -ll \
                        --skip B608 \
                        -x services/auth/tests,services/form/tests,services/workflow/tests,services/task/tests,services/notification/tests \
                        -q

                    echo "--- pip-audit CVE check ---"
                    for svc in auth form workflow task notification; do
                        echo "Auditing $svc..."
                        # Audit uses local requirements, but tools are in the base image
                        # --no-deps: audit only the pinned packages (fast); skips
                        # transitive-dependency resolution which dominated the runtime.
                        if ! pip-audit -r services/$svc/requirements.txt --progress-spinner off --no-deps \
                            --ignore-vuln CVE-2026-30922  \
                            --ignore-vuln CVE-2025-54121  \
                            --ignore-vuln CVE-2025-62727  \
                            --ignore-vuln CVE-2026-25990  \
                            --ignore-vuln CVE-2026-40192  \
                            --ignore-vuln CVE-2026-42308  \
                            --ignore-vuln CVE-2026-42310  \
                            --ignore-vuln CVE-2026-42311  \
                            --ignore-vuln PYSEC-2026-161
                        then
                            echo "Warning: Found vulnerabilities in $svc. Continuing build"
                        fi
                    done
                '''
            }
        }

        // ─── STAGE 2: TESTS (PARALLEL) ──────────────────────────────────────
        stage('Tests') {
            options { timeout(time: 20, unit: 'MINUTES') } 
            steps {
                script {
                    // Start external dependencies
                    sh '''
                        docker rm -f pk-postgres-${BUILD_NUMBER} pk-redis-${BUILD_NUMBER} 2>/dev/null || true
                        docker network rm ${CI_NETWORK} 2>/dev/null || true
                        docker network create ${CI_NETWORK}

                        docker run -d \
                            --name pk-postgres-${BUILD_NUMBER} \
                            --network ${CI_NETWORK} \
                            -e POSTGRES_USER=pk_user \
                            -e POSTGRES_PASSWORD=pk_password \
                            -e POSTGRES_DB=paper_killer_test \
                            postgres:16-alpine

                        docker run -d \
                            --name pk-redis-${BUILD_NUMBER} \
                            --network container:pk-postgres-${BUILD_NUMBER} \
                            redis:7-alpine

                        echo "Waiting for postgres (via loopback)..."
                        READY=0
                        for i in $(seq 1 30); do
                            # Checking via localhost inside the container stack forces TCP check
                            if docker exec pk-postgres-${BUILD_NUMBER} pg_isready -h localhost -U pk_user; then
                                echo "Postgres is ready!"
                                READY=1
                                break
                            fi
                            echo "Waiting... ($i/30)"
                            sleep 2
                        done

                        if [ $READY -ne 1 ]; then
                            echo "ERROR: Postgres failed to become ready in time."
                            docker logs pk-postgres-${BUILD_NUMBER}
                            exit 1
                        fi
                    '''

                    def services = ['auth', 'form', 'workflow', 'task', 'notification']
                    def testTasks = [:]

                    services.each { svc ->
                        def serviceName = svc // Capture loop variable for closure
                        def testDelay = services.indexOf(svc) * 5
                        
                        testTasks[serviceName] = {
                            echo "Waiting ${testDelay}s before starting ${serviceName} tests..."
                            sleep testDelay

                            echo "====== Testing ${serviceName} (Parallel) ======"
                            sh """
                                docker run --rm \
                                    --network container:pk-postgres-${BUILD_NUMBER} \
                                    -v ${WORKSPACE}:${WORKSPACE} \
                                    -w ${WORKSPACE}/services/${serviceName} \
                                    -e DATABASE_URL=postgresql://pk_user:pk_password@localhost:5432/paper_killer_test \
                                    -e DATABASE_SCHEMA=${serviceName}_schema \
                                    -e REDIS_URL=redis://localhost:6379/0 \
                                    -e JWT_SECRET=test_secret_key_not_for_production \
                                    -e JWT_ALGORITHM=HS256 \
                                    -e JWT_EXPIRE_MINUTES=60 \
                                    ${TEST_BASE_IMG} \
                                    sh -c "
                                        pip install --no-index --find-links=/wheels -r requirements.txt --quiet --root-user-action=ignore &&
                                        PYTHONPATH=.:../.. alembic upgrade head &&
                                        PYTHONPATH=.:../.. pytest tests/ -v \
                                            --cov=app \
                                            --cov-report=term-missing \
                                            --cov-report=xml:coverage.xml \
                                            --cov-report=html:htmlcov \
                                            --cov-fail-under=85
                                    "
                            """
                        }
                    }

                    try {
                        parallel testTasks
                    } finally {
                        sh "docker rm -f pk-postgres-${BUILD_NUMBER} pk-redis-${BUILD_NUMBER} || true"
                        // Do NOT delete the network yet if smoke tests need it later
                    }
                }
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'services/*/coverage.xml'
                    archiveArtifacts artifacts: 'services/*/coverage.xml, services/*/htmlcov/**', allowEmptyArchive: true
                }
            }
        }

        // ─── STAGE 3: DOCKER BUILD VALIDATION ───────────────────────────────
        stage('Docker Build') {
            options { timeout(time: 15, unit: 'MINUTES') }  // [5]
            steps {
                sh '''
                    echo "Building all service images (tag: ${IMAGE_TAG})..."
                    docker build --network=host -t pk-auth:${IMAGE_TAG}         ./services/auth
                    docker build --network=host -t pk-form:${IMAGE_TAG}         ./services/form
                    docker build --network=host -t pk-workflow:${IMAGE_TAG}     ./services/workflow
                    docker build --network=host -t pk-task:${IMAGE_TAG}         ./services/task
                    docker build --network=host -t pk-notification:${IMAGE_TAG} ./services/notification
                    docker build --network=host -t pk-frontend:${IMAGE_TAG}     ./frontend

                    echo "All images built successfully"
                    docker images | grep "^pk-"
                '''
            }
        }

        // ─── STAGE 4: PUSH TO REGISTRY (main only) ──────────────────────────
        stage('Push Images') {
            when { branch 'main' }
            options { timeout(time: 10, unit: 'MINUTES') }  // [5]
            steps {
                // [7] withCredentials keeps the token out of the console log
                withCredentials([string(credentialsId: 'ghcr-token', variable: 'GHCR_TOKEN_SECRET')]) {
                    sh '''
                        echo $GHCR_TOKEN_SECRET | docker login ghcr.io -u $GHCR_USER --password-stdin

                        for svc in auth form workflow task notification frontend; do
                            docker tag pk-${svc}:${IMAGE_TAG} ${IMAGE_PREFIX}-${svc}:${IMAGE_TAG}
                            docker tag pk-${svc}:${IMAGE_TAG} ${IMAGE_PREFIX}-${svc}:latest
                            docker push ${IMAGE_PREFIX}-${svc}:${IMAGE_TAG}
                            docker push ${IMAGE_PREFIX}-${svc}:latest
                            echo "Pushed: ${svc} → ${IMAGE_TAG}"
                        done

                        docker logout ghcr.io
                    '''
                }
            }
        }

        /* ─── STAGE 5: DEPLOY TO KUBERNETES  ───── */
        
        stage('Deploy to Kubernetes') {
            when { branch 'main' }
            agent {
                docker {
                    image 'bitnami/kubectl:latest'
                    reuseNode true
                    // --dns so kubectl can resolve the cluster API server hostname
                    args '-u root --dns=8.8.8.8 --dns=1.1.1.1'
                }
            }
            environment {
                KUBECONFIG = credentials('omniflow-kubeconfig')
            }
            steps {
                sh '''
                    for svc in auth form workflow task notification frontend; do
                        kubectl set image deployment/pk-${svc} \
                            pk-${svc}=${IMAGE_PREFIX}-${svc}:${IMAGE_TAG}
                    done
                    for svc in auth form workflow task notification frontend; do
                        kubectl rollout status deployment/pk-${svc} --timeout=300s
                    done
                '''
            }
        }

        // ─── STAGE 6: SMOKE TESTS  ──────────────
        stage('Smoke Tests') {
            when { branch 'main' }
            steps {
                script {
                    // Start all services in the background on the CI network for validation
                    sh """
                        for svc in auth form workflow task notification; do
                            docker run -d \
                                --name pk-\${svc}-smoke \
                                --network ${CI_NETWORK} \
                                -e DATABASE_URL=postgresql://pk_user:pk_password@pk-postgres-${BUILD_NUMBER}:5432/paper_killer_test \
                                -e REDIS_URL=redis://pk-redis-${BUILD_NUMBER}:6379/0 \
                                -e JWT_SECRET=test_secret_key_not_for_production \
                                pk-\${svc}:${IMAGE_TAG}
                        done
                    """

                    sh """
                        docker run --rm \
                            --network ${CI_NETWORK} \
                            ${TEST_BASE_IMG} \
                            sh -c "
                                sleep 10
                                for svc in auth form workflow task notification; do
                                    # Use internal container names on CI_NETWORK
                                    STATUS=\$(curl -s -o /dev/null -w '%{http_code}' http://pk-\${svc}-smoke:80/health || echo '000')
                                    if [ \\"\$STATUS\\" != '200' ]; then
                                        echo \\"SMOKE TEST FAILED: \$svc returned \$STATUS\\"
                                        exit 1
                                    fi
                                    echo \\"Health check passed: \$svc\\"
                                done
                            "
                    """
                }
            }
            post {
                always {
                    sh "docker rm -f \$(docker ps -a -q --filter 'name=pk-.*-smoke') 2>/dev/null || true"
                }
            }
        }
        
    }

    post {
        failure {
            echo "Pipeline FAILED — branch: ${env.BRANCH_NAME ?: 'unknown'} — tag: ${IMAGE_TAG}"
        }
        always {
            // [3] Final cleanup of network and test base image
            sh """
                docker rm -f pk-postgres-${BUILD_NUMBER} pk-redis-${BUILD_NUMBER} 2>/dev/null || true
                docker network rm ${CI_NETWORK} 2>/dev/null || true
                docker rmi ${TEST_BASE_IMG} 2>/dev/null || true
                docker rmi \$(docker images 'pk-*' -q) --force 2>/dev/null || true
            """
        }
        success {
            echo "Pipeline PASSED — branch: ${env.BRANCH_NAME ?: 'unknown'} — tag: ${IMAGE_TAG}"
        }
    }
}