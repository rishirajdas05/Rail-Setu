"""
Classic Google OAuth 2.0 redirect (authorization code) flow.

Unlike the Google Identity Services button (which uses hidden frames and
third-party cookies, blocked by Brave and being phased out elsewhere), this is a
plain top-level redirect: the user goes to Google's sign-in page and Google
redirects back here with a code. We exchange the code for an ID token, verify it,
find or create the user, mint our JWT, and hand it to the frontend.

Routes (wired in config/urls.py):
  GET /auth/google/login/     -> redirect the browser to Google
  GET /auth/google/callback/  -> Google returns here with ?code=...

Requires GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in settings/.env, and the
callback URL registered as an Authorized redirect URI in Google Cloud Console.
"""

import json
import secrets
import urllib.parse

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.core import signing
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.html import escape
from rest_framework_simplejwt.tokens import RefreshToken

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
STATE_SALT = "railsetu.google.oauth.state"
STATE_MAX_AGE = 600  # seconds the sign-in round trip may take


def _redirect_uri(request):
    configured = getattr(settings, "GOOGLE_REDIRECT_URI", "")
    return configured or request.build_absolute_uri("/auth/google/callback/")


def google_login(request):
    client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
    if not client_id:
        return _fail("Google sign-in is not configured (GOOGLE_CLIENT_ID is missing).")
    next_url = request.GET.get("next", "/") or "/"
    # Signed, self-contained state: survives the round trip without needing the
    # session cookie (which is easily lost across a localhost/127.0.0.1 host change).
    state = signing.dumps({"n": secrets.token_urlsafe(16), "next": next_url}, salt=STATE_SALT)
    params = {
        "client_id": client_id,
        "redirect_uri": _redirect_uri(request),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
        "access_type": "online",
    }
    return redirect(GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params))


def google_callback(request):
    if request.GET.get("error"):
        return _fail("Google sign-in was cancelled.")

    state = request.GET.get("state") or ""
    try:
        state_data = signing.loads(state, salt=STATE_SALT, max_age=STATE_MAX_AGE)
    except signing.SignatureExpired:
        return _fail("Sign-in took too long. Please start again.")
    except signing.BadSignature:
        return _fail("Sign-in could not be verified. Please try again.")
    nxt = state_data.get("next", "/") or "/"

    code = request.GET.get("code")
    if not code:
        return _fail("Google did not return an authorization code.")

    client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
    client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", "")
    if not client_secret:
        return _fail("The server is missing GOOGLE_CLIENT_SECRET. Add it to .env and restart.")

    try:
        token_resp = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": _redirect_uri(request),
                "grant_type": "authorization_code",
            },
            timeout=10,
        ).json()
    except requests.RequestException:
        return _fail("Could not reach Google to complete sign-in.")

    id_token_str = token_resp.get("id_token")
    if not id_token_str:
        detail = token_resp.get("error_description") or token_resp.get("error") or "no ID token returned"
        return _fail("Google sign-in failed during token exchange: " + str(detail))

    try:
        from google.auth.transport import requests as g_requests
        from google.oauth2 import id_token as g_id_token
        info = g_id_token.verify_oauth2_token(id_token_str, g_requests.Request(), client_id)
    except ImportError:
        return _fail("The server is missing google-auth. Run: pip install google-auth")
    except ValueError:
        return _fail("Could not verify the Google token. Please try again.")

    email = (info.get("email") or "").lower()
    if not email or not info.get("email_verified", False):
        return _fail("Your Google account has no verified email.")

    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        base = (email.split("@")[0] or "user")[:150]
        username, i = base, 1
        while User.objects.filter(username=username).exists():
            i += 1
            username = f"{base}{i}"[:150]
        user = User.objects.create_user(username=username, email=email)
        user.set_unusable_password()
        user.first_name = (info.get("given_name") or "")[:30]
        user.last_name = (info.get("family_name") or "")[:150]
        user.save()

    refresh = RefreshToken.for_user(user)
    return _success(str(refresh.access_token), str(refresh), user.username, nxt)


def _success(access, refresh, username, nxt):
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Signing you in...</title></head>
<body style="font-family:system-ui,sans-serif;padding:2rem;color:#16224a">Signing you in...
<script src="/static/js/auth.js"></script>
<script>
  try {{
    RailAuth.setSession({json.dumps(access)}, {json.dumps(refresh)}, {json.dumps(username)});
    localStorage.setItem('railsetu_last_user', {json.dumps(username)});
  }} catch (e) {{}}
  location.replace({json.dumps(nxt)});
</script></body></html>"""
    return HttpResponse(html)


def _fail(message):
    safe = escape(message)
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Sign-in failed</title></head>
<body style="font-family:system-ui,sans-serif;padding:2rem;color:#16224a">
<p>{safe}</p>
<p><a href="/login/">Back to sign in</a></p>
<script>setTimeout(function(){{location.replace('/login/');}}, 3000);</script>
</body></html>"""
    return HttpResponse(html, status=400)