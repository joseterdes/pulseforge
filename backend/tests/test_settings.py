from pulseforge.core.settings import Settings


def test_settings_derive_supabase_urls():
    s = Settings(database_url="postgresql+psycopg://x", supabase_url="https://abc.supabase.co/")
    assert s.jwks_url == "https://abc.supabase.co/auth/v1/.well-known/jwks.json"
    assert s.jwt_issuer == "https://abc.supabase.co/auth/v1"
    assert s.jwt_audience == "authenticated"
    assert s.tos_version == "v1"
