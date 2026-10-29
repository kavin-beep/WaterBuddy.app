"""Server-side Groq chat request; never persist or display the API key."""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GroqError(RuntimeError):
    """A user-safe error without request headers or provider response bodies."""


def groq_reply(api_key, messages, context):
    system = (
        "You are FLOW, Water Buddy's friendly hydration coach. Be concise. "
        "Use the supplied hydration totals accurately. You cannot change app settings, "
        "log water, or send notifications. Offer general habit support, not diagnosis "
        "or medical targets. For medical conditions or fluid restrictions, suggest a "
        "qualified clinician; for urgent symptoms, suggest urgent medical care. "
        "Never encourage rapid excessive drinking. Today's context: "
        + json.dumps(context)
    )
    history = [
        {"role": m["role"], "content": str(m["content"])[:4000]}
        for m in messages[1:][-20:]
        if isinstance(m, dict) and m.get("role") in {"user", "assistant"}
        and m.get("content")
    ]
    request = Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps({
            "model": "openai/gpt-oss-120b",
            "messages": [{"role": "system", "content": system}, *history],
            "temperature": 0.5, "max_completion_tokens": 2048,
        }).encode("utf-8"),
        headers={"Authorization": "Bearer " + api_key,
                 "Content-Type": "application/json", "User-Agent": "WaterBuddy/1.0"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=25) as response:
            result = json.load(response)
        content = result["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Empty response")
    except HTTPError as exc:
        if exc.code in (401, 403):
            message = "Groq rejected the API key. Check GROQ_API_KEY in the app's secrets."
        elif exc.code == 429:
            message = "Groq's usage limit was reached. Try again shortly or check your Groq quota."
        else:
            message = "Groq is unavailable right now. Please try again shortly."
        raise GroqError(message) from None
    except (URLError, TimeoutError, OSError):
        raise GroqError("Could not reach Groq. Check your connection and try again.") from None
    except (ValueError, KeyError, IndexError, TypeError):
        raise GroqError("Groq returned an incomplete response. Please try again.") from None
    return content.strip()
