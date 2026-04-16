"""
Tests para el sistema de autenticación.
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.core.auth_errors import AuthErrorCode, AuthException
from app.services.auth_service import (
    OAuthStateService,
    StudentAuthService,
)


class TestOAuthStateService:
    """Tests para el servicio de state OAuth."""

    def test_generate_state_returns_tuple(self):
        """El servicio debe retornar state y auth_request_id."""
        state, auth_request_id = OAuthStateService.generate_state()

        assert isinstance(state, str)
        assert isinstance(auth_request_id, str)
        assert len(auth_request_id) > 0
        assert "." in state

    def test_validate_valid_state(self):
        """Debe validar un state correcto."""
        state, expected_auth_id = OAuthStateService.generate_state()

        auth_id = OAuthStateService.validate_state(state, state)

        assert auth_id == expected_auth_id

    def test_validate_missing_state(self):
        """Debe rechazar state faltante."""
        with pytest.raises(AuthException) as exc_info:
            OAuthStateService.validate_state("", "some_cookie")

        assert exc_info.value.code == AuthErrorCode.STATE_MISSING

    def test_validate_mismatched_state(self):
        """Debe rechazar state que no coincida."""
        state1, _ = OAuthStateService.generate_state()
        state2, _ = OAuthStateService.generate_state()

        with pytest.raises(AuthException) as exc_info:
            OAuthStateService.validate_state(state1, state2)

        assert exc_info.value.code == AuthErrorCode.STATE_MISMATCH

    def test_validate_tampered_state(self):
        """Debe rechazar state alterado."""
        state, _ = OAuthStateService.generate_state()
        tampered_state = state[:-10] + "TAMPERED!!"

        with pytest.raises(AuthException) as exc_info:
            OAuthStateService.validate_state(tampered_state, tampered_state)

        assert exc_info.value.code == AuthErrorCode.STATE_INVALID_HMAC

    def test_state_single_use(self):
        """Un state no debe poder usarse dos veces."""
        state, auth_id = OAuthStateService.generate_state()

        # Primera validación (éxito)
        OAuthStateService.validate_state(state, state)
        OAuthStateService.consume_state(state, auth_id)

        # Segunda validación (debe fallar)
        with pytest.raises(AuthException) as exc_info:
            OAuthStateService.validate_state(state, state)

        assert exc_info.value.code == AuthErrorCode.STATE_ALREADY_USED


class TestStudentAuthService:
    """Tests para el servicio de autenticación de estudiantes."""

    def test_validate_valid_tec_email(self):
        """Debe aceptar emails @tec.mx válidos."""
        valid_emails = [
            "A01234567@tec.mx",
            "a01234567@tec.mx",
            "A01659113@tec.mx",
            "estudiante@tec.mx",
        ]

        for email in valid_emails:
            assert StudentAuthService.validate_email_domain(email) is True

    def test_reject_invalid_domain(self):
        """Debe rechazar emails de otros dominios."""
        invalid_emails = [
            "user@gmail.com",
            "student@itesm.mx",
            "test@hotmail.com",
            "user@tec.com",
        ]

        for email in invalid_emails:
            with pytest.raises(AuthException) as exc_info:
                StudentAuthService.validate_email_domain(email)

            assert exc_info.value.code == AuthErrorCode.FORBIDDEN_DOMAIN

    def test_reject_empty_email(self):
        """Debe rechazar email vacío."""
        with pytest.raises(AuthException) as exc_info:
            StudentAuthService.validate_email_domain("")

        assert exc_info.value.code == AuthErrorCode.INVALID_EMAIL_FORMAT

    def test_extract_matricula_from_email(self):
        """Debe extraer correctamente la matrícula."""
        test_cases = [
            ("A01234567@tec.mx", "A01234567"),
            ("a01234567@tec.mx", "A01234567"),
            ("L01234567@tec.mx", "L01234567"),
        ]

        for email, expected in test_cases:
            assert StudentAuthService.extract_matricula(email) == expected


class TestAuthExceptions:
    """Tests para las excepciones de autenticación."""

    def test_auth_exception_to_client_response(self):
        """La respuesta al cliente no debe exponer detalles internos."""
        exc = AuthException(
            code=AuthErrorCode.STATE_INVALID_HMAC,
            message="Detalle técnico interno",
            auth_request_id="req-123",
            details={"internal": "data"},
        )

        response = exc.to_client_response()

        assert response["error"] is True
        assert response["code"] == "AUTH_STATE_INVALID_HMAC"
        assert "auth_request_id" in response
        assert "internal" not in response.get("message", "")

    def test_auth_exception_log_dict(self):
        """El log debe contener todos los detalles para debugging."""
        exc = AuthException(
            code=AuthErrorCode.GOOGLE_CODE_EXCHANGE_FAILED,
            message="Error interno",
            auth_request_id="req-456",
            details={"status_code": 400},
        )

        log_dict = exc.to_log_dict()

        assert log_dict["event"] == "AUTH_FAILURE"
        assert log_dict["error_code"] == "AUTH_GOOGLE_CODE_EXCHANGE_FAILED"
        assert log_dict["auth_request_id"] == "req-456"
        assert log_dict["details"]["status_code"] == 400
