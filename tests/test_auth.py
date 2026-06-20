import importlib
import os
import sys
import tempfile
import unittest

from fastapi.testclient import TestClient


def load_test_app(database_url: str):
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["DATABASE_URL"] = database_url
    os.environ["ALLOWED_ORIGINS"] = "http://testserver,http://localhost:3000"
    os.environ["AUTH_EXPOSE_RESET_TOKEN"] = "true"

    for module_name in ["app.main", "app.models", "app.database", "app.auth"]:
        sys.modules.pop(module_name, None)

    app_module = importlib.import_module("app.main")
    return app_module, TestClient(app_module.app)


class AuthenticationFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_url = f"sqlite:///{self.temp_dir.name}/test.db"
        self.app_module, self.client = load_test_app(database_url)

    def tearDown(self):
        self.client.close()
        importlib.import_module("app.database").engine.dispose()
        self.temp_dir.cleanup()

    def test_complete_authentication_flow(self):
        signup_response = self.client.post(
            "/auth/signup",
            json={
                "username": "new_user",
                "email": "new_user@example.com",
                "password": "SecurePass1!",
                "tier": "god",
            },
        )
        self.assertEqual(signup_response.status_code, 201)
        self.assertEqual(signup_response.json()["username"], "new_user")

        email_login_response = self.client.post(
            "/auth/login",
            json={"identifier": "new_user@example.com", "password": "SecurePass1!"},
        )
        self.assertEqual(email_login_response.status_code, 200)
        auth_payload = email_login_response.json()
        self.assertIn("access_token", auth_payload)
        self.assertIn("refresh_token", auth_payload)

        username_login_response = self.client.post(
            "/auth/login",
            json={"username": "new_user", "password": "SecurePass1!"},
        )
        self.assertEqual(username_login_response.status_code, 200)

        me_response = self.client.get(
            "/auth/me",
            headers={"Authorization": "Bearer " + auth_payload["access_token"]},
        )
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["email"], "new_user@example.com")

        refresh_response = self.client.post(
            "/auth/refresh",
            json={"refresh_token": auth_payload["refresh_token"]},
        )
        self.assertEqual(refresh_response.status_code, 200)
        self.assertIn("access_token", refresh_response.json())

        forgot_password_response = self.client.post(
            "/auth/forgot-password",
            json={"email": "new_user@example.com"},
        )
        self.assertEqual(forgot_password_response.status_code, 200)
        reset_token = forgot_password_response.json()["reset_token"]

        reset_response = self.client.post(
            "/auth/reset-password",
            json={"token": reset_token, "new_password": "EvenBetter2@"},
        )
        self.assertEqual(reset_response.status_code, 200)

        old_password_response = self.client.post(
            "/auth/login",
            json={"identifier": "new_user", "password": "SecurePass1!"},
        )
        self.assertEqual(old_password_response.status_code, 401)

        new_password_response = self.client.post(
            "/auth/login",
            json={"identifier": "new_user", "password": "EvenBetter2@"},
        )
        self.assertEqual(new_password_response.status_code, 200)

        stale_refresh_response = self.client.post(
            "/auth/refresh",
            json={"refresh_token": auth_payload["refresh_token"]},
        )
        self.assertEqual(stale_refresh_response.status_code, 401)

    def test_validation_duplicate_checks_and_rate_limiting(self):
        invalid_email_response = self.client.post(
            "/auth/signup",
            json={
                "username": "valid_user",
                "email": "bad-email",
                "password": "SecurePass1!",
            },
        )
        self.assertEqual(invalid_email_response.status_code, 422)

        weak_password_response = self.client.post(
            "/auth/signup",
            json={
                "username": "valid_user",
                "email": "valid_user@example.com",
                "password": "weakpass",
            },
        )
        self.assertEqual(weak_password_response.status_code, 422)

        first_signup_response = self.client.post(
            "/auth/signup",
            json={
                "username": "valid_user",
                "email": "valid_user@example.com",
                "password": "SecurePass1!",
            },
        )
        self.assertEqual(first_signup_response.status_code, 201)

        duplicate_username_response = self.client.post(
            "/auth/signup",
            json={
                "username": "valid_user",
                "email": "other@example.com",
                "password": "SecurePass1!",
            },
        )
        self.assertEqual(duplicate_username_response.status_code, 400)

        for _ in range(10):
            response = self.client.post(
                "/auth/login",
                json={"identifier": "valid_user", "password": "WrongPass1!"},
            )
            self.assertEqual(response.status_code, 401)

        rate_limited_response = self.client.post(
            "/auth/login",
            json={"identifier": "valid_user", "password": "WrongPass1!"},
        )
        self.assertEqual(rate_limited_response.status_code, 429)


if __name__ == "__main__":
    unittest.main()
