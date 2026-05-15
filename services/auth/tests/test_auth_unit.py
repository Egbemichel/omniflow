# services/auth/tests/test_auth_unit.py
# Follow TDD: make ONE test pass at a time


class TestUserRegistration:
    """Tests for POST /auth/register"""

    def test_register_valid_data_returns_201(self, client):
        response = client.post("/auth/register", json={
            "email": "alice@hospital.com",
            "password": "SecurePass123!",
            "full_name": "Alice Smith"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "alice@hospital.com"
        assert data["full_name"] == "Alice Smith"
        assert "id" in data

    def test_register_assigns_end_user_role_by_default(self, client):
        response = client.post("/auth/register", json={
            "email": "bob@hospital.com",
            "password": "SecurePass123!",
            "full_name": "Bob Jones"
        })
        assert response.status_code == 201
        assert response.json()["role"] == "end_user"

    def test_register_duplicate_email_returns_409(self, client, register_user):
        register_user()   # creates test@example.com
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "AnotherPass!",
            "full_name": "Duplicate"
        })
        assert response.status_code == 409

    def test_register_missing_email_returns_422(self, client):
        response = client.post("/auth/register", json={
            "password": "SecurePass123!",
            "full_name": "No Email"
        })
        assert response.status_code == 422

    def test_register_missing_password_returns_422(self, client):
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "full_name": "No Password"
        })
        assert response.status_code == 422

    def test_register_password_not_in_response(self, client):
        """Security: raw password must NEVER appear in any response."""
        response = client.post("/auth/register", json={
            "email": "secure@test.com",
            "password": "MySecretPassword999!",
            "full_name": "Secure User"
        })
        assert "MySecretPassword999!" not in str(response.json())

    def test_register_invalid_email_format_returns_422(self, client):
        response = client.post("/auth/register", json={
            "email": "not-an-email",
            "password": "SecurePass123!",
            "full_name": "Bad Email"
        })
        assert response.status_code == 422


class TestLogin:
    """Tests for POST /auth/login"""

    def test_login_correct_credentials_returns_token(self, client, register_user):
        register_user()
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "SecurePass123!"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password_returns_401(self, client, register_user):
        register_user()
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "WrongPassword!"
        })
        assert response.status_code == 401

    def test_login_nonexistent_email_returns_401(self, client):
        response = client.post("/auth/login", json={
            "email": "nobody@nowhere.com",
            "password": "pass"
        })
        assert response.status_code == 401

    def test_login_empty_body_returns_422(self, client):
        response = client.post("/auth/login", json={})
        assert response.status_code == 422


class TestTokenVerify:
    """Tests for GET /auth/verify — used by API Gateway"""

    def test_verify_valid_token_returns_200_with_user_info(self, client, logged_in_user):
        response = client.get(
            "/auth/verify",
            headers={"Authorization": f"Bearer {logged_in_user['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "role" in data
        assert "email" in data

    def test_verify_fake_token_returns_401(self, client):
        response = client.get(
            "/auth/verify",
            headers={"Authorization": "Bearer this.is.completely.fake"}
        )
        assert response.status_code == 401

    def test_verify_missing_token_returns_401(self, client):
        response = client.get("/auth/verify")
        assert response.status_code == 401

    def test_verify_expired_token_returns_401(self, client):
        # This token was valid once — expired timestamp in payload
        expired = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxfQ.abc"
        response = client.get(
            "/auth/verify",
            headers={"Authorization": f"Bearer {expired}"}
        )
        assert response.status_code == 401


class TestRBAC:
    """Tests for role-based access control"""

    def test_admin_can_access_user_list(self, client, admin_token):
        response = client.get(
            "/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200

    def test_end_user_cannot_access_admin_routes(self, client, logged_in_user):
        response = client.get(
            "/admin/users",
            headers={"Authorization": f"Bearer {logged_in_user['token']}"}
        )
        assert response.status_code == 403

    def test_unauthenticated_request_to_protected_route_returns_401(self, client):
        response = client.get("/admin/users")
        assert response.status_code == 401

    def test_admin_can_assign_role_to_user(self, client, admin_token, register_user):
        reg = register_user(email="newuser@pk.com")
        user_id = reg.json()["id"]
        response = client.put(
            f"/admin/users/{user_id}/role",
            json={"role": "staff"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json()["role"] == "staff"

    def test_non_admin_cannot_assign_roles(self, client, logged_in_user, register_user):
        reg = register_user(email="target@pk.com")
        user_id = reg.json()["id"]
        response = client.put(
            f"/admin/users/{user_id}/role",
            json={"role": "admin"},
            headers={"Authorization": f"Bearer {logged_in_user['token']}"}
        )
        assert response.status_code == 403


class TestHealthCheck:
    """Every service must have /health — used by Kubernetes"""

    def test_health_endpoint_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"