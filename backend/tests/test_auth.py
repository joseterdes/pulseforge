import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from pulseforge.core.auth import AuthError, AuthUnavailable, Claims, TokenVerifier

ISSUER = "https://test.supabase.co/auth/v1"


def _valid_claims() -> dict:
    return {
        "sub": str(uuid.uuid4()),
        "aud": "authenticated",
        "iss": ISSUER,
        "exp": int(time.time()) + 3600,
    }


def test_valid_token_returns_claims(verifier, make_token):
    uid = uuid.uuid4()
    assert verifier.verify(make_token(sub=str(uid))) == Claims(sub=uid, email="dj@example.com")


@pytest.mark.parametrize(
    "overrides",
    [
        {"exp": int(time.time()) - 120},
        {"aud": "anon"},
        {"iss": "https://evil.example/auth/v1"},
        {"sub": None},
        {"sub": "not-a-uuid"},
        {"exp": None},
    ],
)
def test_bad_claims_rejected(verifier, make_token, overrides):
    with pytest.raises(AuthError):
        verifier.verify(make_token(**overrides))


def test_token_from_other_key_rejected(verifier):
    other = ec.generate_private_key(ec.SECP256R1())
    token = jwt.encode(_valid_claims(), other, algorithm="ES256", headers={"kid": "test-key"})
    with pytest.raises(AuthError):
        verifier.verify(token)


def test_hs256_token_rejected(verifier):
    token = jwt.encode(_valid_claims(), "secret" * 6, algorithm="HS256")
    with pytest.raises(AuthError):
        verifier.verify(token)


def test_unsigned_token_rejected(verifier):
    token = jwt.encode(_valid_claims(), None, algorithm="none")
    with pytest.raises(AuthError):
        verifier.verify(token)


def test_garbage_token_rejected(verifier):
    with pytest.raises(AuthError):
        verifier.verify("abc.def")


def _verifier_raising(exc: Exception) -> TokenVerifier:
    def getter(_token: str):
        raise exc

    return TokenVerifier(issuer=ISSUER, audience="authenticated", get_signing_key=getter)


def test_unknown_key_id_rejected(make_token):
    with pytest.raises(AuthError):
        _verifier_raising(jwt.PyJWKClientError("no key")).verify(make_token())


def test_jwks_unreachable_raises_unavailable(make_token):
    with pytest.raises(AuthUnavailable):
        _verifier_raising(jwt.PyJWKClientConnectionError("down")).verify(make_token())
