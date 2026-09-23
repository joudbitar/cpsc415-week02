"""Ask a model one question in a character's voice, then print a receipt.

    python3 chat.py --role pirate --tone angry "What is a context window?"

Needs CHAT_BASE_URL, CHAT_MODEL and a key in CHAT_API_KEY or OPENROUTER_API_KEY.
Leave out --role or --tone in a terminal to pick from a menu.
"""

import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.request

MAX_TOKENS = 300
BUDGET_USD = 0.01

ROLES = {
    "pirate": "a pirate captain",
    "noir-detective": "a hard-boiled 1940s noir detective narrating a case",
    "sports-commentator": "a live sports commentator calling the action",
    "shakespearean-actor": "a Shakespearean actor speaking Elizabethan English",
    "lebanese-teta": "a Lebanese grandmother who drops in Lebanese Arabic and worries you are not eating",
    "medieval-knight": "a medieval knight sworn to honour",
}

TONES = {
    "angry": "furious about everything",
    "sleepy": "barely awake and yawning between thoughts",
    "overdramatic": "treating every detail as a tragedy",
    "deadpan": "completely flat and unimpressed",
    "overexcited": "wildly, uncontrollably excited",
    "suspicious": "sure that someone is hiding something",
}


def system_prompt(role, tone):
    return (
        f"You are {ROLES[role]}, and you are {TONES[tone]}. Stay in character. "
        "Answer the question correctly in under 120 words."
    )


def build_request(model, role, tone, question):
    return {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "messages": [
            {"role": "system", "content": system_prompt(role, tone)},
            {"role": "user", "content": question},
        ],
        # OpenRouter adds the dollar cost to `usage`; other servers ignore this.
        "usage": {"include": True},
    }


def estimate_tokens(request):
    # About 4 characters per token, rounded up, plus a few per message for the
    # role markers. Only used for the worst-case cost, so erring high is fine.
    return sum(math.ceil(len(m["content"]) / 4) + 4 for m in request["messages"])


def listed_price(models, model):
    """Per-token (input, output) price in dollars, or None if not listed."""
    for entry in models.get("data", []):
        if entry.get("id") == model:
            pricing = entry.get("pricing") or {}
            try:
                prices = float(pricing["prompt"]), float(pricing["completion"])
            except (KeyError, TypeError, ValueError):
                return None
            return prices if min(prices) >= 0 else None  # -1 means "varies"
    return None


def worst_case_usd(request, price):
    input_price, output_price = price
    return estimate_tokens(request) * input_price + request["max_tokens"] * output_price


def http_json(url, key, body=None):
    request = urllib.request.Request(
        url,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def format_cost(usage):
    cost = usage.get("cost")
    if not isinstance(cost, (int, float)):
        return "cost not reported"
    return f"${cost:.6f}".rstrip("0").rstrip(".") if cost else "$0"


def receipt(reply):
    usage = reply.get("usage") or {}
    return (
        f"── {reply.get('model', '?')} · {usage.get('prompt_tokens', '?')} in / "
        f"{usage.get('completion_tokens', '?')} out · {format_cost(usage)}"
    )


def answer_text(reply):
    content = (reply["choices"][0]["message"].get("content") or "").strip()
    if content:
        return content
    return (
        "(empty answer: the model used its whole output budget, probably on "
        "hidden reasoning, before writing anything visible)"
    )


def pick(label, options):
    """Arrow-key menu on the terminal. Returns the chosen key."""
    keys = list(options)
    try:
        import termios
        import tty
    except ImportError:  # Windows: fall back to typing a number
        for number, key in enumerate(keys, 1):
            print(f"  {number}. {key}", file=sys.stderr)
        return keys[int(input(f"{label} number: ")) - 1]

    # Raw mode delivers each key press at once, so "\r\n" is needed for new lines.
    print(f"{label} (↑/↓, Enter):", file=sys.stderr)
    chosen, fd = 0, sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    tty.setraw(fd)
    try:
        while True:
            for i, key in enumerate(keys):
                marker = "›" if i == chosen else " "
                sys.stderr.write(f"\r\x1b[2K {marker} {key.replace('-', ' ')}\r\n")
            sys.stderr.flush()
            key = os.read(fd, 1)
            if key in (b"\r", b"\n"):
                return keys[chosen]
            if key == b"\x03":
                raise KeyboardInterrupt
            if key == b"\x1b" and os.read(fd, 1) == b"[":
                chosen = (chosen + {b"A": -1, b"B": 1}.get(os.read(fd, 1), 0)) % len(keys)
            sys.stderr.write(f"\x1b[{len(keys)}A")  # back to the top of the menu
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)


def main(argv=None, env=os.environ):
    parser = argparse.ArgumentParser(description="Ask a model one question in character.")
    parser.add_argument("question")
    parser.add_argument("--role", choices=ROLES)
    parser.add_argument("--tone", choices=TONES)
    parser.add_argument("--show-request", action="store_true", help="print the JSON sent")
    args = parser.parse_args(argv)

    base_url = env.get("CHAT_BASE_URL", "").rstrip("/")
    model = env.get("CHAT_MODEL")
    key = env.get("CHAT_API_KEY") or env.get("OPENROUTER_API_KEY")
    missing = [name for name, value in [("CHAT_BASE_URL", base_url), ("CHAT_MODEL", model),
                                        ("OPENROUTER_API_KEY", key)] if not value]
    if missing:
        sys.exit(f"missing environment variable: {', '.join(missing)}")

    for name, options in (("role", ROLES), ("tone", TONES)):
        if getattr(args, name) is None:
            if not sys.stdin.isatty():
                sys.exit(f"--{name} is required here; choose from: {', '.join(options)}")
            setattr(args, name, pick(f"Choose a {name}", options))

    request = build_request(model, args.role, args.tone, args.question)
    if args.show_request:
        print(json.dumps(request, indent=2), file=sys.stderr)

    # If the price list can't be read, send nothing: the 1¢ limit has to hold.
    try:
        price = listed_price(http_json(f"{base_url}/models", key), model)
    except (urllib.error.URLError, ValueError) as error:
        sys.exit(f"refused: could not read prices from {base_url}/models ({error})")
    if price is None:
        print("note: no listed price for this model, 1¢ check skipped", file=sys.stderr)
    elif worst_case_usd(request, price) > BUDGET_USD:
        sys.exit(
            f"refused: worst case ${worst_case_usd(request, price):.4f} is over the 1¢ limit "
            f"({model}, {MAX_TOKENS} max tokens)"
        )

    try:
        reply = http_json(f"{base_url}/chat/completions", key, request)
    except urllib.error.HTTPError as error:
        sys.exit(f"request failed: HTTP {error.code}: {error.read().decode()[:300]}")
    except urllib.error.URLError as error:
        sys.exit(f"could not reach {base_url}: {error.reason}")

    print(answer_text(reply))
    line = receipt(reply)
    print(f"\x1b[2m{line}\x1b[0m" if sys.stdout.isatty() else line)


if __name__ == "__main__":
    main()
