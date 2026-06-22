"""Google OAuth2 client configuration for MezzaRPG."""
import os
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

# Load from environment
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
_DEFAULT_REDIRECT = (
    "http://localhost:8001/auth/google/callback"
    if os.getenv("MEZZARPG_ENV", "dev").lower() not in ("prod", "production")
    else "https://mezza.rednerds.com.br/auth/google/callback"
)
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", _DEFAULT_REDIRECT)

# Optional: allow running without Google OAuth for local dev
OAUTH_ENABLED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

if OAUTH_ENABLED:
    # OAuth configuration
    config = Config(environ={
        "GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID,
        "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET,
    })

    oauth = OAuth(config)

    oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile',
            'prompt': 'select_account',  # Forces account picker every time
        }
    )
else:
    # Dummy oauth object for when Google OAuth is not configured
    oauth = None