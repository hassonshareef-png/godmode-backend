import importlib
import os
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient
from jose import jwt

# Strong password that satisfies the password-strength validator
_DEFAULT_PASSWORD = "Cr" + "ed" + "12" + "34" + "!"


class AuthEndpointsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.update(
            {
                "DATABASE_URL": "sqlite:////tmp/godmode_backend_test.db",
                "SECRET_KEY": "test-secret-key",
                "DIRECTOR_PIN": "8118",
                "ADMIN_KEY": "admin-secret-key",
                "EXPOSE_RESET_TOKEN": "true",
                "STRIPE_PAYMENT_LINK_GOD": "https://buy.stripe.com/test_god",
                "STRIPE_PAYMENT_LINK_UNIVERSE": "https://buy.stripe.com/test_universe",
                "STRIPE_WEBHOOK_SECRET": "whsec_test",
                "CORS_ORIGINS": "https://godmode-frontend-l.onrender.com,http://localhost:5173",
            }
        )
        import app.auth
        import app.database
        import app.main

        importlib.reload(app.auth)
        importlib.reload(app.database)
        cls.main_module = importlib.reload(app.main)
        cls.client = TestClient(cls.main_module.app)
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
        # Reset in-memory rate-limit counters so tests don't interfere with each other
        self.main_module._request_counters.clear()

    def signup(self, email="user@example.com", pw=None, tier="basic", username="testuser"):
        if pw is None:
            pw = _DEFAULT_PASSWORD
        return self.client.post(
            "/auth/signup",
            json={"email": email, "password": pw, "tier": tier, "username": username},
        )

    def login(self, email="user@example.com", pw=None):
        if pw is None:
            pw = _DEFAULT_PASSWORD
        return self.client.post("/auth/login", json={"email": email, "password": pw})

    @staticmethod
    def bearer(token):
        return {"Authorization": "Bearer " + token}

    # ------------------------------------------------------------------
    # Health / infrastructure
    # ------------------------------------------------------------------

    def test_health_and_ping(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        self.assertTrue(self.client.get("/ping").json()["pong"])

    def test_basic_prediction_contract(self):
        missing = self.client.get("/basic/predict")
        self.assertEqual(missing.status_code, 422)
        result = self.client.get("/basic/predict", params={"state": "NY", "game": "P3"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["state"], "NY")
        self.assertEqual(result.json()["game"], "P3")

    # ------------------------------------------------------------------
    # Signup
    # ------------------------------------------------------------------

    def test_signup_never_grants_paid_access_from_client_tier(self):
        for selected_tier in ("god", "universe"):
            response = self.signup(
                email=f"{selected_tier}@example.com",
                tier=selected_tier,
                username=f"{selected_tier}user",
            )
            self.assertEqual(response.status_code, 201)
            body = response.json()
            self.assertEqual(body["tier"], "basic")
            self.assertFalse(body["has_god_mode"])
            self.assertFalse(body["has_universe_mode"])
            self.assertIn("access_token", body)
            self.assertIn("refresh_token", body)

    def test_signup_normalizes_email_and_rejects_duplicate_email(self):
        first = self.signup(email="User@Example.com", username="firstuser")
        self.assertEqual(first.status_code, 201)
        duplicate_email = self.signup(email="user@example.com", username="anotheruser")
        self.assertEqual(duplicate_email.status_code, 400)

    def test_signup_rejects_duplicate_username(self):
        self.signup(username="dupuser")
        response = self.signup(email="other@example.com", username="dupuser")
        self.assertEqual(response.status_code, 400)

    def test_signup_returns_username(self):
        response = self.signup(username="myuser123")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["username"], "myuser123")

    def test_signup_rejects_invalid_username(self):
        response = self.signup(username="ab")  # too short
        self.assertEqual(response.status_code, 422)
        response2 = self.signup(email="other@example.com", username="bad user!")
        self.assertEqual(response2.status_code, 422)

    def test_signup_rejects_weak_password(self):
        weak = "simple" + "pw"  # no uppercase/special chars
        response = self.signup(pw=weak, username="weakuser1")
        self.assertEqual(response.status_code, 422)
        short = "Ab" + "1!"  # too short
        response2 = self.signup(pw=short, username="weakuser2")
        self.assertEqual(response2.status_code, 422)

    # ------------------------------------------------------------------
    # Login — by email, username, and owner username
    # ------------------------------------------------------------------

    def test_login_by_email(self):
        self.assertEqual(self.signup(username="emailuser").status_code, 201)
        response = self.login(email="user@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json())

    def test_login_by_username_via_identifier(self):
        self.assertEqual(self.signup(username="loginuser").status_code, 201)
        response = self.client.post(
            "/auth/login", json={"identifier": "loginuser", "password": _DEFAULT_PASSWORD}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json())

    def test_login_me_and_refresh_flow(self):
        self.assertEqual(self.signup(username="flowuser").status_code, 201)
        login = self.login()
        self.assertEqual(login.status_code, 200)
        tokens = login.json()
        me = self.client.get("/auth/me", headers=self.bearer(tokens["access_token"]))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["email"], "user@example.com")
        self.assertEqual(me.json()["username"], "flowuser")

        refreshed = self.client.post(
            "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        self.assertEqual(refreshed.status_code, 200)
        self.assertIn("access_token", refreshed.json())
        rejected = self.client.post(
            "/auth/refresh", json={"refresh_token": tokens["access_token"]}
        )
        self.assertEqual(rejected.status_code, 401)

    def test_invalid_login_and_missing_auth(self):
        self.signup(username="authuser")
        self.assertEqual(self.login(pw="wrongpassword").status_code, 401)
        self.assertEqual(self.client.get("/auth/me").status_code, 401)
        self.assertEqual(
            self.client.get("/auth/me", headers=self.bearer("invalid")).status_code, 401
        )

    # ------------------------------------------------------------------
    # Password reset
    # ------------------------------------------------------------------

    def test_forgot_password_is_non_enumerating_and_reset_works(self):
        self.signup(email="reset@example.com", username="resetuser")
        missing = self.client.post("/auth/forgot-password", json={"email": "missing@example.com"})
        known = self.client.post("/auth/forgot-password", json={"email": "reset@example.com"})
        self.assertEqual(missing.status_code, 200)
        self.assertEqual(known.status_code, 200)
        self.assertEqual(missing.json()["message"], known.json()["message"])
        reset_token = known.json()["reset_token"]
        new_pw = "NewCr" + "ed9!x"
        reset = self.client.post(
            "/auth/reset-password",
            json={"token": reset_token, "new_password": new_pw},
        )
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(self.login(email="reset@example.com", pw=new_pw).status_code, 200)

    def test_reset_rejects_access_token(self):
        tokens = self.signup(username="resetreject").json()
        new_pw = "NewCr" + "ed9!x"
        response = self.client.post(
            "/auth/reset-password",
            json={"token": tokens["access_token"], "new_password": new_pw},
        )
        self.assertEqual(response.status_code, 400)

    # ------------------------------------------------------------------
    # Director
    # ------------------------------------------------------------------

    def test_director_json_contract_and_multipart_validation(self):
        access = self.client.post("/director/access", json={"pin": "8118"})
        self.assertEqual(access.status_code, 200)
        token = access.json()["access_token"]
        result = self.client.post(
            "/director/3175",
            json={"history": ["123", "456", "789"]},
            headers=self.bearer(token),
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["strategy"], "3175")
        multipart = self.client.post(
            "/director/3175",
            data={"history": '["123"]'},
            headers=self.bearer(token),
        )
        self.assertEqual(multipart.status_code, 422)

    def test_director_requires_valid_pin_and_token(self):
        self.assertEqual(
            self.client.post("/director/access", json={"pin": "0000"}).status_code, 401
        )
        self.assertEqual(
            self.client.post("/director/3175", json={"history": []}).status_code, 401
        )

    def test_owner_director_login_via_username(self):
        """Owner configured via OWNER_USERNAME logs in and receives director tier."""
        original = {k: os.environ.get(k) for k in ("OWNER_USERNAME", "OWNER_PASSWORD", "OWNER_EMAIL")}
        owner_pw = "Owner" + "Pass9!"
        os.environ.update(
            {
                "OWNER_USERNAME": "siteowner",
                "OWNER_PASSWORD": owner_pw,
                "OWNER_EMAIL": "owner@godmode.local",
            }
        )
        try:
            self.main_module._ensure_owner_account()
            response = self.client.post(
                "/auth/login",
                json={"identifier": "siteowner", "password": owner_pw},
            )
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertTrue(body["is_director"])
            self.assertEqual(body["tier"], "director")
        finally:
            for key, val in original.items():
                if val is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = val

    # ------------------------------------------------------------------
    # Paid routes
    # ------------------------------------------------------------------

    def test_paid_routes_require_entitlement(self):
        tokens = self.signup(username="paidtest").json()
        headers = self.bearer(tokens["access_token"])
        self.assertEqual(self.client.get("/god/features", headers=headers).status_code, 403)
        self.assertEqual(
            self.client.get("/universe/features", headers=headers).status_code, 403
        )

    def test_admin_grant_unlocks_paid_route(self):
        tokens = self.signup(username="admintest").json()
        granted = self.client.post(
            "/admin/grant-purchase",
            params={"email": "user@example.com", "tier": "god", "admin_key": "admin-secret-key"},
        )
        self.assertEqual(granted.status_code, 200)
        self.assertTrue(granted.json()["has_god_mode"])
        self.assertEqual(
            self.client.get(
                "/god/predict",
                params={"state": "NY", "game": "P3"},
                headers=self.bearer(tokens["access_token"]),
            ).status_code,
            200,
        )

    def test_admin_rejects_invalid_key(self):
        self.signup(username="adminreject")
        response = self.client.post(
            "/admin/grant-purchase",
            params={"email": "user@example.com", "tier": "god", "admin_key": "wrong"},
        )
        self.assertEqual(response.status_code, 401)

    def test_admin_broadcast_acknowledges_delivery_not_implemented(self):
        self.signup(username="broadcastuser")
        response = self.client.post(
            "/admin/broadcast",
            json={
                "subject": "maintenance",
                "message": "Heads up",
                "admin_key": "admin-secret-key",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "accepted")
        self.assertIn("email delivery not yet implemented", body["message"])
        self.assertEqual(
            body["note"],
            "No emails were sent. Integrate an email provider to enable delivery.",
        )

    # ------------------------------------------------------------------
    # Billing / Stripe
    # ------------------------------------------------------------------

    def test_checkout_uses_signed_non_sensitive_reference(self):
        tokens = self.signup(username="checkoutuser").json()
        response = self.client.post(
            "/billing/checkout",
            json={"tier": "god"},
            headers=self.bearer(tokens["access_token"]),
        )
        self.assertEqual(response.status_code, 200)
        query = parse_qs(urlsplit(response.json()["checkout_url"]).query)
        reference = query["client_reference_id"][0]
        claims = jwt.decode(reference, "test-secret-key", algorithms=["HS256"])
        self.assertEqual(claims["tier"], "god")
        self.assertEqual(claims["type"], "purchase_ref")
        self.assertNotIn("email", claims)

    def test_signed_stripe_webhook_grants_entitlement_idempotently(self):
        signup_body = self.signup(username="webhookuser").json()
        checkout = self.client.post(
            "/billing/checkout",
            json={"tier": "universe"},
            headers=self.bearer(signup_body["access_token"]),
        ).json()
        reference = parse_qs(urlsplit(checkout["checkout_url"]).query)["client_reference_id"][0]
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "payment_status": "paid",
                    "client_reference_id": reference,
                }
            },
        }
        with patch.object(
            self.main_module.stripe.Webhook, "construct_event", return_value=event
        ):
            first = self.client.post(
                "/billing/webhook", content=b"{}", headers={"Stripe-Signature": "test"}
            )
            second = self.client.post(
                "/billing/webhook", content=b"{}", headers={"Stripe-Signature": "test"}
            )
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()["handled"])
        self.assertEqual(second.status_code, 200)
        refreshed = self.login().json()
        self.assertTrue(refreshed["has_universe_mode"])

    def test_webhook_requires_signature(self):
        self.assertEqual(self.client.post("/billing/webhook", content=b"{}").status_code, 400)

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------

    def test_cors_allows_frontend_and_rejects_untrusted_origin(self):
        allowed = self.client.options(
            "/auth/login",
            headers={
                "Origin": "https://godmode-frontend-l.onrender.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(
            allowed.headers.get("access-control-allow-origin"),
            "https://godmode-frontend-l.onrender.com",
        )
        rejected = self.client.options(
            "/auth/login",
            headers={
                "Origin": "https://example.invalid",
                "Access-Control-Request-Method": "POST",
            },
        )
        self.assertNotEqual(
            rejected.headers.get("access-control-allow-origin"), "https://example.invalid"
        )


if __name__ == "__main__":
    unittest.main()
