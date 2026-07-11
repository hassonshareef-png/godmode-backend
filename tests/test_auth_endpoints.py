import importlib
import os
import unittest

from fastapi import HTTPException


class AuthEndpointsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["DATABASE_URL"] = "sqlite:////tmp/godmode_backend_test.db"
        os.environ["SECRET_KEY"] = "test-secret-key"
        os.environ["DIRECTOR_PIN"] = "8118"
        os.environ["ADMIN_KEY"] = "admin-secret-key"

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

    def _signup(self, email="user@example.com", pw_text="cred12345", tier="basic"):
        payload = self.main_module.SignupRequest.model_validate(
            {"email": email, "password": pw_text, "tier": tier}
        )
        return self.main_module.signup(payload, db=self.db)

    def _login(self, email="user@example.com", pw_text="cred12345"):
        payload = self.main_module.LoginRequest.model_validate(
            {"email": email, "password": pw_text}
        )
        return self.main_module.login(payload, db=self.db)

    # ========================================================================
    # BASIC HEALTH TESTS
    # ========================================================================

    def test_ping_endpoint(self):
        body = self.main_module.ping()
        self.assertTrue(body["pong"])
        self.assertIn("timestamp", body)

    def test_health_endpoint(self):
        body = self.main_module.health()
        self.assertEqual(body["status"], "ok")

    # ========================================================================
    # BASIC MODE TESTS (PUBLIC, NO AUTH)
    # ========================================================================

    def test_basic_features_public(self):
        """Basic Mode features should be accessible without authentication."""
        body = self.main_module.basic_features()
        self.assertEqual(body["mode"], "basic")
        self.assertFalse(body["requires_login"])
        self.assertIn("features", body)

    def test_basic_predict_public(self):
        """Basic Mode predictions should be accessible without authentication."""
        body = self.main_module.basic_predict(state="NY", game="P3")
        self.assertEqual(body["mode"], "basic")
        self.assertEqual(body["state"], "NY")
        self.assertEqual(body["game"], "P3")
        self.assertIn("numbers", body)

    # ========================================================================
    # SIGNUP & LOGIN TESTS
    # ========================================================================

    def test_signup_basic_tier(self):
        """User can sign up with basic tier (free)."""
        result = self._signup(email="basic@example.com", tier="basic")
        self.assertEqual(result["email"], "basic@example.com")
        self.assertEqual(result["tier"], "basic")
        self.assertFalse(result["has_god_mode"])
        self.assertFalse(result["has_universe_mode"])

    def test_signup_god_tier(self):
        """User can sign up with god tier (marked as purchased)."""
        result = self._signup(email="god@example.com", tier="god")
        self.assertEqual(result["email"], "god@example.com")
        self.assertEqual(result["tier"], "god")
        self.assertTrue(result["has_god_mode"])

    def test_signup_universe_tier(self):
        """User can sign up with universe tier (marked as purchased)."""
        result = self._signup(email="universe@example.com", tier="universe")
        self.assertEqual(result["email"], "universe@example.com")
        self.assertEqual(result["tier"], "universe")
        self.assertTrue(result["has_universe_mode"])

    def test_signup_duplicate_email(self):
        """Cannot sign up with duplicate email."""
        self._signup(email="dup@example.com")
        with self.assertRaises(HTTPException) as ctx:
            self._signup(email="dup@example.com")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_login_valid_credentials(self):
        """User can log in with valid credentials."""
        self._signup(email="login@example.com", pw_text="password123")
        result = self._login(email="login@example.com", pw_text="password123")
        self.assertIn("access_token", result)
        self.assertEqual(result["token_type"], "bearer")

    def test_login_invalid_password(self):
        """Login fails with invalid password."""
        self._signup(email="login@example.com", pw_text="password123")
        with self.assertRaises(HTTPException) as ctx:
            self._login(email="login@example.com", pw_text="wrongpassword")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_login_nonexistent_user(self):
        """Login fails for nonexistent user."""
        with self.assertRaises(HTTPException) as ctx:
            self._login(email="nonexistent@example.com", pw_text="password123")
        self.assertEqual(ctx.exception.status_code, 401)

    # ========================================================================
    # AUTHENTICATED USER TESTS
    # ========================================================================

    def test_get_current_user_valid_token(self):
        """Can retrieve current user with valid token."""
        user = self._signup(email="me@example.com", pw_text="cred56789", tier="god")
        login = self._login(email="me@example.com", pw_text="cred56789")
        token = login["access_token"]

        current_user = self.main_module.get_current_user(token=token, db=self.db)
        me = self.main_module.me(user=current_user)
        self.assertEqual(me["id"], user["id"])
        self.assertEqual(me["email"], "me@example.com")
        self.assertEqual(me["tier"], "god")
        self.assertTrue(me["has_god_mode"])

    def test_get_current_user_invalid_token(self):
        """Invalid token raises 401."""
        with self.assertRaises(HTTPException) as ctx:
            self.main_module.get_current_user(token="invalid-token", db=self.db)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_get_current_user_no_token(self):
        """Missing token raises 401."""
        with self.assertRaises(HTTPException) as ctx:
            self.main_module.get_current_user(token="", db=self.db)
        self.assertEqual(ctx.exception.status_code, 401)

    # ========================================================================
    # PASSWORD RESET TESTS
    # ========================================================================

    def test_forgot_and_reset_password_flow(self):
        """Complete password reset flow works."""
        self._signup(email="reset@example.com", pw_text="cred56789")

        forgot_payload = self.main_module.ForgotPasswordRequest(email="reset@example.com")
        forgot = self.main_module.forgot_password(forgot_payload, db=self.db)
        token = forgot["reset_token"]

        reset_payload = self.main_module.ResetPasswordRequest(
            token=token, new_password="newcred123"
        )
        reset = self.main_module.reset_password(reset_payload, db=self.db)
        self.assertIn("successful", reset["message"].lower())

        # Old password should not work
        with self.assertRaises(HTTPException) as old_login_err:
            self._login(email="reset@example.com", pw_text="cred56789")
        self.assertEqual(old_login_err.exception.status_code, 401)

        # New password should work
        new_login = self._login(email="reset@example.com", pw_text="newcred123")
        self.assertIn("access_token", new_login)

    def test_forgot_password_unknown_email(self):
        """Forgot password fails for unknown email."""
        payload = self.main_module.ForgotPasswordRequest(email="missing@example.com")
        with self.assertRaises(HTTPException) as ctx:
            self.main_module.forgot_password(payload, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_reset_password_expired_token(self):
        """Reset password fails with expired token."""
        # Create an expired token
        from app.auth import create_access_token
        expired_token = create_access_token(
            {"sub": "1", "type": "password_reset"}, expires_minutes=-1
        )
        
        payload = self.main_module.ResetPasswordRequest(
            token=expired_token, new_password="newcred123"
        )
        with self.assertRaises(HTTPException) as ctx:
            self.main_module.reset_password(payload, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("expired", ctx.exception.detail.lower())

    def test_reset_rejects_non_reset_token(self):
        """Reset password rejects non-reset tokens."""
        self._signup(email="wrongtype@example.com", pw_text="cred56789")
        login = self._login(email="wrongtype@example.com", pw_text="cred56789")
        access_token = login["access_token"]

        payload = self.main_module.ResetPasswordRequest(
            token=access_token, new_password="newcred123"
        )
        with self.assertRaises(HTTPException) as ctx:
            self.main_module.reset_password(payload, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("type", ctx.exception.detail.lower())

    # ========================================================================
    # GOD MODE TESTS (LOGIN + PURCHASE REQUIRED)
    # ========================================================================

    def test_god_mode_requires_purchase(self):
        """God Mode features require purchase."""
        self._signup(email="basic@example.com", tier="basic")
        login = self._login(email="basic@example.com", pw_text="cred12345")
        token = login["access_token"]

        current_user = self.main_module.get_current_user(token=token, db=self.db)
        with self.assertRaises(HTTPException) as ctx:
            self.main_module.god_features(user=current_user)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_god_mode_with_purchase(self):
        """God Mode features accessible with purchase."""
        self._signup(email="god@example.com", tier="god")
        login = self._login(email="god@example.com", pw_text="cred12345")
        token = login["access_token"]

        current_user = self.main_module.get_current_user(token=token, db=self.db)
        features = self.main_module.god_features(user=current_user)
        self.assertEqual(features["mode"], "god")
        self.assertIn("features", features)

    def test_god_predict_requires_purchase(self):
        """God Mode predictions require purchase."""
        self._signup(email="basic@example.com", tier="basic")
        login = self._login(email="basic@example.com", pw_text="cred12345")
        token = login["access_token"]

        current_user = self.main_module.get_current_user(token=token, db=self.db)
        with self.assertRaises(HTTPException) as ctx:
            self.main_module.god_predict(state="NY", game="P3", user=current_user)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_god_predict_with_purchase(self):
        """God Mode predictions work with purchase."""
        self._signup(email="god@example.com", tier="god")
        login = self._login(email="god@example.com", pw_text="cred12345")
        token = login["access_token"]

        current_user = self.main_module.get_current_user(token=token, db=self.db)
        result = self.main_module.god_predict(state="NY", game="P3", user=current_user)
        self.assertEqual(result["mode"], "god")
        self.assertIn("numbers", result)

    # ========================================================================
    # UNIVERSE MODE TESTS (LOGIN + PURCHASE REQUIRED)
    # ========================================================================

    def test_universe_mode_requires_purchase(self):
        """Universe Mode features require purchase."""
        self._signup(email="basic@example.com", tier="basic")
        login = self._login(email="basic@example.com", pw_text="cred12345")
        token = login["access_token"]

        current_user = self.main_module.get_current_user(token=token, db=self.db)
        with self.assertRaises(HTTPException) as ctx:
            self.main_module.universe_features(user=current_user)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_universe_mode_with_purchase(self):
        """Universe Mode features accessible with purchase."""
        self._signup(email="universe@example.com", tier="universe")
        login = self._login(email="universe@example.com", pw_text="cred12345")
        token = login["access_token"]

        current_user = self.main_module.get_current_user(token=token, db=self.db)
        features = self.main_module.universe_features(user=current_user)
        self.assertEqual(features["mode"], "universe")
        self.assertIn("features", features)

    def test_universe_predict_with_purchase(self):
        """Universe Mode predictions work with purchase."""
        self._signup(email="universe@example.com", tier="universe")
        login = self._login(email="universe@example.com", pw_text="cred12345")
        token = login["access_token"]

        current_user = self.main_module.get_current_user(token=token, db=self.db)
        result = self.main_module.universe_predict(state="NY", game="P3", user=current_user)
        self.assertEqual(result["mode"], "universe")
        self.assertIn("numbers", result)

    # ========================================================================
    # DIRECTOR MODE TESTS (PIN-ONLY, NO LOGIN)
    # ========================================================================

    def test_director_access_with_correct_pin(self):
        """Director Mode access with correct PIN (8118)."""
        payload = self.main_module.DirectorPinRequest(pin="8118")
        result = self.main_module.director_access(payload, db=self.db)
        self.assertIn("access_token", result)
        self.assertEqual(result["mode"], "director")
        self.assertIn("director", result["unlocked_modes"])

    def test_director_access_with_wrong_pin(self):
        """Director Mode access fails with wrong PIN."""
        payload = self.main_module.DirectorPinRequest(pin="0000")
        with self.assertRaises(HTTPException) as ctx:
            self.main_module.director_access(payload, db=self.db)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_director_3175_with_pin_token(self):
        """Director 3175 engine works with PIN token."""
        # Get director token
        pin_payload = self.main_module.DirectorPinRequest(pin="8118")
        director_result = self.main_module.director_access(pin_payload, db=self.db)
        director_token = director_result["access_token"]

        # Call director 3175 with token
        result = self.main_module.director_3175(
            history=["123", "456", "789"],
            token=director_token,
            db=self.db
        )
        self.assertEqual(result["mode"], "DIRECTOR")
        self.assertEqual(result["strategy"], "3175")
        self.assertIn("prediction", result)
        self.assertIn("alert", result)

    def test_director_3175_without_token(self):
        """Director 3175 engine fails without valid token."""
        with self.assertRaises(HTTPException) as ctx:
            self.main_module.director_3175(
                history=["123", "456", "789"],
                token="",
                db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 401)

    # ========================================================================
    # ADMIN ENDPOINTS TESTS
    # ========================================================================

    def test_grant_god_purchase(self):
        """Admin can grant God Mode purchase."""
        self._signup(email="user@example.com", tier="basic")
        result = self.main_module.grant_purchase(
            email="user@example.com",
            tier="god",
            admin_key="admin-secret-key",
            db=self.db
        )
        self.assertTrue(result["has_god_mode"])

    def test_grant_universe_purchase(self):
        """Admin can grant Universe Mode purchase."""
        self._signup(email="user@example.com", tier="basic")
        result = self.main_module.grant_purchase(
            email="user@example.com",
            tier="universe",
            admin_key="admin-secret-key",
            db=self.db
        )
        self.assertTrue(result["has_universe_mode"])

    def test_grant_purchase_invalid_admin_key(self):
        """Grant purchase fails with invalid admin key."""
        self._signup(email="user@example.com", tier="basic")
        with self.assertRaises(HTTPException) as ctx:
            self.main_module.grant_purchase(
                email="user@example.com",
                tier="god",
                admin_key="wrong-key",
                db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 401)

    def test_set_director(self):
        """Admin can set user as director."""
        self._signup(email="user@example.com", tier="basic")
        result = self.main_module.set_director(
            email="user@example.com",
            admin_key="admin-secret-key",
            db=self.db
        )
        self.assertTrue(result["is_director"])
        self.assertEqual(result["tier"], "director")

    def test_set_director_invalid_admin_key(self):
        """Set director fails with invalid admin key."""
        self._signup(email="user@example.com", tier="basic")
        with self.assertRaises(HTTPException) as ctx:
            self.main_module.set_director(
                email="user@example.com",
                admin_key="wrong-key",
                db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
