"""Groq-powered UI translation: POST /api/translate/

Body: {"target_lang": "hi", "texts": ["From", "To", ...]}
Returns: {"translations": ["...", "..."]}  (same order/length as texts)

Translations are cached in-process per (lang, text) so repeated page loads and
multiple users do not re-spend Groq calls on the same strings. English ('en') is
returned unchanged without calling Groq.
"""

import json

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from . import groq_client

LANG_NAMES = {
    "en": "English", "hi": "Hindi", "bn": "Bengali", "ta": "Tamil",
    "te": "Telugu", "mr": "Marathi", "gu": "Gujarati", "kn": "Kannada",
    "pa": "Punjabi", "ml": "Malayalam", "or": "Odia", "ur": "Urdu",
}

_CACHE = {}  # (lang, text) -> translated text


def _parse_array(content, n):
    s = (content or "").strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s[:4].lower() == "json":
            s = s[4:]
    try:
        arr = json.loads(s)
        if isinstance(arr, list) and len(arr) == n:
            return [str(x) for x in arr]
    except Exception:  # noqa: BLE001
        pass
    return None


class TranslateView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        target = (request.data.get("target_lang") or "").strip().lower()
        texts = request.data.get("texts") or []
        if not isinstance(texts, list):
            return Response({"detail": "texts must be a list."}, status=400)
        texts = [str(t) for t in texts]

        if target in ("", "en"):
            return Response({"translations": texts})
        if not groq_client.is_configured():
            return Response(
                {"detail": "Translation is not configured. Set GROQ_API_KEY in the backend .env."},
                status=503,
            )

        language = LANG_NAMES.get(target, target)

        # serve cached, collect the misses
        out = [None] * len(texts)
        missing, missing_idx = [], []
        for i, txt in enumerate(texts):
            hit = _CACHE.get((target, txt))
            if hit is not None:
                out[i] = hit
            else:
                missing.append(txt)
                missing_idx.append(i)

        if missing:
            system = (
                f"You are a professional UI translator for an Indian Railways web app. "
                f"Translate each English UI string into {language}. Keep translations short and "
                f"natural for buttons, labels and headings. Preserve any HTML tags (such as <br>) "
                f"and placeholders exactly as given. Do not add quotes, notes or extra punctuation. "
                f"Return ONLY a JSON array of the translated strings, in the same order and the same "
                f"length as the input."
            )
            try:
                msg = groq_client.chat(
                    [
                        {"role": "system", "content": system},
                        {"role": "user", "content": json.dumps(missing, ensure_ascii=False)},
                    ],
                    temperature=0.1,
                    max_tokens=1200,
                )
                arr = _parse_array(msg.get("content", ""), len(missing))
            except groq_client.GroqError:
                arr = None

            if arr is None:
                # translation failed: fall back to the original English for the misses
                arr = missing
            for j, idx in enumerate(missing_idx):
                _CACHE[(target, missing[j])] = arr[j]
                out[idx] = arr[j]

        return Response({"translations": out})