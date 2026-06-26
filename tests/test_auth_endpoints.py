import importlib
import os
import unittest

from fastapi import HTTPException
from starlette.requests import Request


class AuthEndpointsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["DATABASE_URL"] = "sqlite:////tmp/godmode_backend_test.db"
        os.environ["SECRET_KEY"] = "test-secret-key"

        import app.main

        cls.main_module = importlib.reload(app.main)
        cls._clear_users()

    @classmethod
    def tearDownClass(cls):
        cls._clear_users()
        db_path = "/tmp/godmode_backend_test.db"
        if os.path.exists(db_path):
            os.remove(db_path)

    @classmethod
    def _clear_users(cls):
        db = cls.main_module.SessionLocal()
        try:
            db.query(cls.main_module.User).delete()
            db.commit()
        finally:
            db.close()

    def setUp(self):
        self._clear_users()
        self.db = self.main_module.SessionLocal()

    def tearDown(self):
        self.db.close()

    def _signup(self, email="user@example.com", pw_text="cred12345", tier="god"):
        payload = self.main_module.SignupRequest.model_validate(
            {"email": email, "password": pw_text, "tier": tier}
        )
        return self.main_module.signup(payload, self._request(), db=self.db)

    def _login(self, email="user@example.com", pw_text="cred12345"):
        payload = self.main_module.LoginRequest.model_validate(
            {"email": email, "password": pw_text}
        )
        return self.main_module.login(payload, self._request(), db=self.db)

    def _request(self):
        return Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/",
                "headers": [],
                "client": ("127.0.0.1", 12345),
            }
        )

    def test_ping_endpoint(self):
        body = self.main_module.ping()
        self.assertTrue(body["pong"])
        self.assertIn("timestamp", body)

    def test_get_current_user_invalid_token(self):
        with self.assertRaises(HTTPException) as ctx:
            self.main_module.get_current_user(token="invalid-token", db=self.db)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_get_current_user_valid_token(self):
        user = self._signup(email="me@example.com", pw_text="cred56789", tier="universe")
        login = self._login(email="me@example.com", pw_text="cred56789")
        token = login["access_token"]

        current_user = self.main_module.get_current_user(token=token, db=self.db)
        me = self.main_module.me(user=current_user)
        self.assertEqual(me["id"], user["id"])
        self.assertEqual(me["email"], "me@example.com")
        self.assertEqual(me["tier"], "universe")

    def test_forgot_and_reset_password_flow(self):
        self._signup(email="reset@example.com", pw_text="cred56789")

        forgot_payload = self.main_module.ForgotPasswordRequest(email="reset@example.com")
        forgot = self.main_module.forgot_password(forgot_payload, self._request(), db=self.db)
        self.assertEqual(
            forgot,
            {
                "message": "If this email is registered, a password reset link has been sent."
            },
        )
        user_obj = self.db.query(self.main_module.User).filter_by(email="reset@example.com").first()
        token = user_obj.reset_token
        self.assertIsNotNone(token)

        reset_payload = self.main_module.ResetPasswordRequest(
            token=token, new_password="newcred123"
        )
        reset = self.main_module.reset_password(reset_payload, db=self.db)
        self.assertEqual(reset["message"], "Password reset successful")
        self.assertIsNone(user_obj.reset_token)

        with self.assertRaises(HTTPException) as old_login_err:
            self._login(email="reset@example.com", pw_text="cred56789")
        self.assertEqual(old_login_err.exception.status_code, 401)

        new_login = self._login(email="reset@example.com", pw_text="newcred123")
        self.assertIn("access_token", new_login)

    def test_forgot_password_unknown_email(self):
        payload = self.main_module.ForgotPasswordRequest(email="missing@example.com")
        body = self.main_module.forgot_password(payload, self._request(), db=self.db)
        self.assertEqual(
            body,
            {"message": "If this email is registered, a password reset link has been sent."},
        )

    def test_reset_rejects_non_reset_token(self):
        self._signup(email="wrongtype@example.com", pw_text="cred56789")
        login = self._login(email="wrongtype@example.com", pw_text="cred56789")
        access_token = login["access_token"]

        payload = self.main_module.ResetPasswordRequest(
            token=access_token, new_password="newcred123"
        )
        with self.assertRaises(HTTPException) as ctx:
            self.main_module.reset_password(payload, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("type", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
