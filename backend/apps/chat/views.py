"""
RailSetu chatbot endpoint: POST /api/chat/

Hybrid RAG + tool calling:
1. Retrieve relevant knowledge base chunks for the user's message (TF-IDF).
2. Ask Groq with a grounding system prompt, the retrieved context, and the live
   tool schemas.
3. If Groq asks to call tools (train search, availability, PNR, prediction), run
   them and send the results back for a final grounded answer.

Degrades gracefully: if GROQ_API_KEY is missing, returns a clear 503 so the widget
can show a friendly "not configured" message.
"""

import json

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from . import groq_client, tools
from .retriever import context_block, retrieve

SYSTEM_PROMPT = (
    "You are RailSetu Assistant, a friendly multilingual guide for an Indian Railways demo app.\n"
    "For anything about live trains, routes, schedules, availability, PNR, fares, or confirmation "
    "chances, use ONLY the knowledge base context and the results of the tools you call, and never "
    "invent train numbers, times, fares, PNR results, or availability. If such railway information is "
    "not in the context or tool results, say you do not have it, and call the appropriate tool when "
    "one fits instead of answering from memory.\n"
    "For general questions, greetings, casual chat, and language or translation help, respond helpfully "
    "and naturally even when the knowledge base has nothing relevant. You can translate text and reply "
    "in whatever language the user asks for.\n"
    "Be concise and friendly. Mention that fares, availability, platforms, and coach data are "
    "indicative/simulated when relevant. Do not use em dashes."
)

MAX_TOOL_ROUNDS = 3
MAX_HISTORY = 6


def _is_toolcall_failure(exc):
    """Groq sometimes 400s because the llama model emitted a bad function call.
    Detect it so we can retry without tools and still answer from knowledge."""
    s = str(exc).lower()
    return (
        "failed to call a function" in s
        or "tool_use_failed" in s
        or ("400" in s and "function" in s)
    )


class ChatView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        message = (request.data.get("message") or "").strip()
        if not message:
            return Response({"detail": "Please enter a message."}, status=400)
        if not groq_client.is_configured():
            return Response(
                {"detail": "The assistant is not configured yet. Set GROQ_API_KEY in the backend .env."},
                status=503,
            )

        # 1) retrieve knowledge
        chunks = retrieve(message, k=4)
        history = request.data.get("history") or []
        history = [
            {"role": m.get("role"), "content": str(m.get("content", ""))}
            for m in history
            if m.get("role") in ("user", "assistant") and m.get("content")
        ][-MAX_HISTORY:]

        # reply in the user's selected UI language when it isn't English
        from .translate import LANG_NAMES
        lang = (request.data.get("lang") or "en").strip().lower()
        lang_note = ""
        if lang and lang != "en":
            lang_name = LANG_NAMES.get(lang, lang)
            lang_note = f"\nAlways write your reply in {lang_name}, regardless of the language of the question."

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + lang_note + "\n\nKnowledge base context:\n" + context_block(chunks)},
            *history,
            {"role": "user", "content": message},
        ]

        used_tools = []
        try:
            # First turn: offer tools, but if Groq rejects the model's tool call,
            # fall back to a plain knowledge-grounded answer.
            try:
                msg = groq_client.chat(messages, tools=tools.TOOL_SCHEMAS)
            except groq_client.GroqError as exc:
                if _is_toolcall_failure(exc):
                    msg = groq_client.chat(messages)
                else:
                    raise

            rounds = 0
            while msg.get("tool_calls"):
                messages.append(msg)
                for call in msg["tool_calls"]:
                    name = call["function"]["name"]
                    try:
                        args = json.loads(call["function"].get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    result = tools.execute(name, args)
                    used_tools.append(name)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "name": name,
                        "content": json.dumps(result)[:4000],
                    })
                rounds += 1
                if rounds >= MAX_TOOL_ROUNDS:
                    msg = groq_client.chat(messages)  # no tools -> force prose
                    break
                try:
                    msg = groq_client.chat(messages, tools=tools.TOOL_SCHEMAS)
                except groq_client.GroqError as exc:
                    if _is_toolcall_failure(exc):
                        msg = groq_client.chat(messages)  # force prose from tool results
                        break
                    raise

            answer = (msg.get("content") or "").strip()
            if not answer:
                messages.append({
                    "role": "user",
                    "content": "Please answer my question in plain language using the information above.",
                })
                msg = groq_client.chat(messages)
                answer = (msg.get("content") or "").strip() or "Sorry, I could not produce an answer."
        except groq_client.GroqError as exc:
            return Response({"detail": str(exc)}, status=502)

        return Response({
            "answer": answer,
            "sources": [{"source": c["source"], "title": c["title"]} for c in chunks],
            "tools_used": used_tools,
        })