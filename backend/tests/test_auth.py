import base64
import json
import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from pulseforge.core.auth import (
    AuthError,
    AuthUnavailable,
    Claims,
    TokenVerifier,
    _jwks_getter,
)

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


def _jwk(public_key, kind) -> jwt.PyJWK:
    if kind == "ec":
        data = jwt.algorithms.ECAlgorithm.to_jwk(public_key, as_dict=True)
    else:
        data = jwt.algorithms.RSAAlgorithm.to_jwk(public_key, as_dict=True)
    return jwt.PyJWK.from_dict(data)


def test_rs256_header_against_ec_key_rejected(private_key):
    from cryptography.hazmat.primitives.asymmetric import rsa

    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(_valid_claims(), rsa_key, algorithm="RS256", headers={"kid": "test-key"})
    v = TokenVerifier(
        issuer=ISSUER,
        audience="authenticated",
        get_signing_key=lambda _t: _jwk(private_key.public_key(), "ec"),
    )
    with pytest.raises(AuthError):
        v.verify(token)


def test_es256_header_against_p384_key_rejected():
    p384 = ec.generate_private_key(ec.SECP384R1())
    signed = jwt.encode(_valid_claims(), p384, algorithm="ES384")
    forged = base64.urlsafe_b64encode(b'{"alg":"ES256","typ":"JWT"}').rstrip(b"=").decode()
    token = ".".join([forged, *signed.split(".")[1:]])
    v = TokenVerifier(
        issuer=ISSUER,
        audience="authenticated",
        get_signing_key=lambda _t: _jwk(p384.public_key(), "ec"),
    )
    with pytest.raises(AuthError):
        v.verify(token)


def test_es256_header_against_rsa_key_rejected(private_key):
    from cryptography.hazmat.primitives.asymmetric import rsa

    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(_valid_claims(), private_key, algorithm="ES256")
    v = TokenVerifier(
        issuer=ISSUER,
        audience="authenticated",
        get_signing_key=lambda _t: _jwk(rsa_key.public_key(), "rsa"),
    )
    with pytest.raises(AuthError):
        v.verify(token)


class _FakeClient:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def get_signing_key_from_jwt(self, _token: str):
        raise self._exc


@pytest.mark.parametrize(
    "exc", [json.JSONDecodeError("Expecting value", "<html>", 0), ConnectionResetError("reset")]
)
def test_jwks_garbage_or_dropped_is_unavailable(make_token, exc):
    v = TokenVerifier(
        issuer=ISSUER, audience="authenticated", get_signing_key=_jwks_getter(_FakeClient(exc))
    )
    with pytest.raises(AuthUnavailable):
        v.verify(make_token())


def test_jwks_getter_keeps_decode_error_as_auth_error():
    getter = _jwks_getter(_FakeClient(jwt.DecodeError("bad token")))
    v = TokenVerifier(issuer=ISSUER, audience="authenticated", get_signing_key=getter)
    with pytest.raises(AuthError):
        v.verify("abc.def")


def test_for_supabase_does_not_trust_revoked_keys_after_jwks_cache_expires(monkeypatch):
    import jwt.jwk_set_cache as jwk_set_cache_module
    from jwt.algorithms import ECAlgorithm
    from pulseforge.core.settings import Settings

    k1, k2 = ec.generate_private_key(ec.SECP256R1()), ec.generate_private_key(ec.SECP256R1())

    def jwk(kid, key):
        return {**ECAlgorithm.to_jwk(key.public_key(), as_dict=True), "kid": kid, "use": "sig", "alg": "ES256"}

    published = {"keys": [jwk("k1", k1), jwk("k2", k2)]}
    fetches: list[int] = []

    def fake_fetch(self):
        fetches.append(1)
        self.jwk_set_cache.put(published)
        return published

    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", fake_fetch)
    offset = [0.0]
    real_monotonic = time.monotonic
    monkeypatch.setattr(
        jwk_set_cache_module, "time", type("T", (), {"monotonic": staticmethod(lambda: real_monotonic() + offset[0])})
    )

    verifier = TokenVerifier.for_supabase(Settings(database_url="postgresql+psycopg://x@h/d", supabase_url="https://test.supabase.co"))
    token = jwt.encode({**_valid_claims()}, k1, algorithm="ES256", headers={"kid": "k1"})

    assert verifier.verify(token).sub
    assert verifier.verify(token).sub
    assert len(fetches) == 1  # served from the JWK-set cache

    published["keys"] = [jwk("k2", k2)]  # k1 revoked
    assert verifier.verify(token).sub  # still within the cache lifespan
    fetches_before_expiry = len(fetches)
    offset[0] = 601  # cache lifespan is 600 s
    with pytest.raises(AuthError):
        verifier.verify(token)
    assert len(fetches) > fetches_before_expiry  # expiry forced a fresh fetch
