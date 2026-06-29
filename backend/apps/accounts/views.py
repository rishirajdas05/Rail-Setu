from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/  -> create a user account."""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(APIView):
    """GET /api/auth/me/  -> the currently authenticated user (token required)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    """POST /api/auth/change-password/  -> update the caller's password."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        current = request.data.get("current_password") or ""
        new = request.data.get("new_password") or ""

        if not request.user.check_password(current):
            return Response({"detail": "Your current password is incorrect."}, status=400)
        if not new:
            return Response({"detail": "Please enter a new password."}, status=400)
        if current == new:
            return Response(
                {"detail": "New password must be different from your current one."},
                status=400,
            )
        try:
            validate_password(new, user=request.user)
        except DjangoValidationError as exc:
            return Response({"detail": " ".join(exc.messages)}, status=400)

        request.user.set_password(new)
        request.user.save(update_fields=["password"])
        return Response({"detail": "Password updated successfully."})


class GoogleAuthView(APIView):
    """POST /api/auth/google/  -> verify a Google ID token and return our JWT.

    Expects {"credential": "<google id token>"} from Google Identity Services.
    Finds or creates a user by their verified Google email, then issues the
    same access/refresh pair the normal login returns, so the frontend can
    treat it identically.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        credential = (request.data.get("credential") or "").strip()
        if not credential:
            return Response({"detail": "Missing Google credential."}, status=400)

        client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
        if not client_id:
            return Response(
                {"detail": "Google sign-in is not configured on the server. Set GOOGLE_CLIENT_ID."},
                status=503,
            )

        try:
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token as google_id_token
        except ImportError:
            return Response(
                {"detail": "Server is missing google-auth. Run: pip install google-auth"},
                status=503,
            )

        try:
            info = google_id_token.verify_oauth2_token(
                credential, google_requests.Request(), client_id
            )
        except ValueError:
            return Response({"detail": "Could not verify Google sign-in. Please try again."}, status=401)

        email = (info.get("email") or "").lower()
        if not email or not info.get("email_verified", False):
            return Response({"detail": "Your Google account has no verified email."}, status=400)

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
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "username": user.username,
        })