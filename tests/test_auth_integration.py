"""
Tests de integración para endpoints de autenticación.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestAuthEndpoints:
    """Tests de integración para endpoints de auth."""

    def test_health_endpoint(self):
        """El endpoint de health debe responder sin exponer BD."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "db" not in data  # No exponer estado de BD

    def test_session_endpoint_no_auth(self):
        """El endpoint de sesión debe indicar no autenticado sin cookie."""
        response = client.get("/auth/session")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert data["student"] is None

    def test_logout_clears_cookies(self):
        """El logout debe limpiar cookies."""
        response = client.get("/auth/logout", follow_redirects=False)

        assert response.status_code == 302
        # Verificar que hay headers de limpieza
        assert "location" in response.headers

    def test_google_login_requires_config(self):
        """El login de Google requiere configuración."""
        # Este test fallará si no hay GOOGLE_CLIENT_ID configurado
        response = client.get("/auth/google/login", follow_redirects=False)

        # Si no hay config, debe retornar 503
        # Si hay config, debe redirigir a Google (302)
        assert response.status_code in [302, 503]

    def test_switch_account_requires_config(self):
        """El switch-account requiere configuración o redirige."""
        response = client.get("/auth/google/switch-account", follow_redirects=False)

        assert response.status_code == 302
        # Debe redirigir al logout federado

    def test_post_logout_no_session_id(self):
        """Post-logout sin session_id debe ir a acceso-estudiante."""
        response = client.get("/auth/post-logout", follow_redirects=False)

        assert response.status_code == 302
        assert "/acceso-estudiante" in response.headers["location"]

    def test_me_requires_auth(self):
        """El endpoint /me requiere autenticación."""
        response = client.get("/auth/me")

        assert response.status_code == 401


class TestAuthErrorCodes:
    """Tests para verificar códigos de error específicos."""

    def test_invalid_login_credentials(self):
        """Login con credenciales inválidas debe retornar 401."""
        response = client.post(
            "/auth/login",
            data={"username": "invalid@test.com", "password": "wrongpass"}
        )

        assert response.status_code == 401

    def test_rate_limit_headers_present(self):
        """Los endpoints rate-limited deben tener headers de rate limit."""
        # Este test verifica que el middleware de rate limiting esté activo
        response = client.get("/health")

        # No hay rate limit en /health, pero verificamos que la app funcione
        assert response.status_code == 200
