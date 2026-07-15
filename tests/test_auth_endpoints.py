import importlib
import os
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient
from jose import jwt


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

    def signup(self, email="user@example.com", password="cred12345", tier="basic"):
        return self.client.post(
            "/auth/signup", json={"email": email, "password": password, "tier": tier}
        )

    def login(self, email="user@example.com", password="cred12345"):
        return self.client.post("/auth/login", json={"email": email, "password": password})

    @staticmethod
    def bearer(token):
        return {"Authorization": f"Bearer {token}"}

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

    def test_signup_never_grants_paid_access_from_client_tier(self):
        for selected_tier in ("god", "universe"):
            response = self.signup(email=f"{selected_tier}@example.com", tier=selected_tier)
            self.assertEqual(response.status_code, 201)
            body = response.json()
            self.assertEqual(body["tier"], "basic")
            self.assertFalse(body["has_god_mode"])
            self.assertFalse(body["has_universe_mode"])
            self.assertIn("access_token", body)
            self.assertIn("refresh_token", body)

    def test_signup_normalizes_email_and_rejects_duplicates(self):
        first = self.signup(email="User@Example.com")
        self.assertEqual(first.status_code, 201)
        duplicate = self.signup(email="user@example.com")
        self.assertEqual(duplicate.status_code, 400)

    def test_login_me_and_refresh_flow(self):
        self.assertEqual(self.signup().status_code, 201)
        login = self.login()
        self.assertEqual(login.status_code, 200)
        tokens = login.json()
        me = self.client.get("/auth/me", headers=self.bearer(tokens["access_token"]))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["email"], "user@example.com")

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
        self.signup()
        self.assertEqual(self.login(password="wrongpass").status_code, 401)
        self.assertEqual(self.client.get("/auth/me").status_code, 401)
        self.assertEqual(
            self.client.get("/auth/me", headers=self.bearer("invalid")).status_code, 401
        )

    def test_forgot_password_is_non_enumerating_and_reset_works(self):
        self.signup(email="reset@example.com", password="cred56789")
        missing = self.client.post("/auth/forgot-password", json={"email": "missing@example.com"})
        known = self.client.post("/auth/forgot-password", json={"email": "reset@example.com"})
        self.assertEqual(missing.status_code, 200)
        self.assertEqual(known.status_code, 200)
        self.assertEqual(missing.json()["message"], known.json()["message"])
        reset_token = known.json()["reset_token"]
        reset = self.client.post(
            "/auth/reset-password",
            json={"token": reset_token, "new_password": "newcred123"},
        )
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(
            self.login(email="reset@example.com", password="newcred123").status_code, 200
        )

    def test_reset_rejects_access_token(self):
        tokens = self.signup().json()
        response = self.client.post(
            "/auth/reset-password",
            json={"token": tokens["access_token"], "new_password": "newcred123"},
        )
        self.assertEqual(response.status_code, 400)

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

    def test_paid_routes_require_entitlement(self):
        tokens = self.signup().json()
        headers = self.bearer(tokens["access_token"])
        self.assertEqual(self.client.get("/god/features", headers=headers).status_code, 403)
        self.assertEqual(
            self.client.get("/universe/features", headers=headers).status_code, 403
        )

    def test_admin_grant_unlocks_paid_route(self):
        tokens = self.signup().json()
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
        self.signup()
        response = self.client.post(
            "/admin/grant-purchase",
            params={"email": "user@example.com", "tier": "god", "admin_key": "wrong"},
        )
        self.assertEqual(response.status_code, 401)

    def test_checkout_uses_signed_non_sensitive_reference(self):
        tokens = self.signup().json()
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
        signup_body = self.signup().json()
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
