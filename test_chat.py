"""Offline tests for chat.py: no network, no key. Run with: python3 -m unittest"""

import contextlib
import io
import unittest
from unittest import mock

import chat

ENV = {"CHAT_BASE_URL": "https://openrouter.ai/api/v1/", "CHAT_MODEL": "cheap/model",
       "OPENROUTER_API_KEY": "test-key"}

MODELS = {"data": [
    {"id": "cheap/model", "pricing": {"prompt": "0.0000001", "completion": "0.0000004"}},
    {"id": "pricey/model", "pricing": {"prompt": "0.000015", "completion": "0.000075"}},
    {"id": "router/auto", "pricing": {"prompt": "-1", "completion": "-1"}},
]}

REPLY = {
    "model": "cheap/model",
    "choices": [{"message": {"role": "assistant", "content": "Arr, 'tis the text a model can see!"}}],
    "usage": {"prompt_tokens": 42, "completion_tokens": 17, "cost": 0.0000109},
}


def run(argv, env=ENV, replies=(MODELS, REPLY)):
    """Runs main() with fake HTTP replies. Returns (stdout, stderr, exit message, calls)."""
    out, err = io.StringIO(), io.StringIO()
    with mock.patch("chat.http_json", side_effect=list(replies)) as http, \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            chat.main(argv, env)
            exit_message = None
        except SystemExit as stop:
            exit_message = str(stop.code)
    return out.getvalue(), err.getvalue(), exit_message, http.call_args_list


class RequestShape(unittest.TestCase):
    def test_role_and_tone_become_the_system_message(self):
        request = chat.build_request("m", "pirate", "angry", "What is a token?")
        self.assertEqual([m["role"] for m in request["messages"]], ["system", "user"])
        self.assertIn("a pirate captain", request["messages"][0]["content"])
        self.assertIn("furious", request["messages"][0]["content"])
        self.assertEqual(request["messages"][1]["content"], "What is a token?")
        self.assertEqual(request["max_tokens"], 300)

    def test_every_role_goes_with_every_tone(self):
        prompts = {chat.system_prompt(r, t) for r in chat.ROLES for t in chat.TONES}
        self.assertEqual(len(prompts), 36)

    def test_the_request_goes_to_chat_completions_with_the_key(self):
        _, _, _, calls = run(["--role", "pirate", "--tone", "angry", "hi"])
        url, key, body = calls[1].args
        self.assertEqual(url, "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(key, "test-key")
        self.assertEqual(body["model"], "cheap/model")

    def test_chat_api_key_wins_for_a_local_model(self):
        env = {**ENV, "CHAT_API_KEY": "ollama"}
        _, _, _, calls = run(["--role", "pirate", "--tone", "angry", "hi"], env)
        self.assertEqual(calls[1].args[1], "ollama")


class CostGuard(unittest.TestCase):
    def test_listed_price_reads_the_models_list(self):
        self.assertEqual(chat.listed_price(MODELS, "cheap/model"), (0.0000001, 0.0000004))
        self.assertIsNone(chat.listed_price(MODELS, "missing/model"))
        self.assertIsNone(chat.listed_price(MODELS, "router/auto"))
        self.assertIsNone(chat.listed_price({"data": [{"id": "x"}]}, "x"))

    def test_worst_case_counts_the_full_reply_budget(self):
        request = chat.build_request("m", "pirate", "angry", "x" * 400)
        tokens = chat.estimate_tokens(request)
        self.assertGreaterEqual(tokens, 100)  # 400 characters is at least 100 tokens
        self.assertAlmostEqual(chat.worst_case_usd(request, (0.001, 0.002)),
                               tokens * 0.001 + 300 * 0.002)

    def test_a_cheap_model_is_sent(self):
        out, _, exit_message, calls = run(["--role", "pirate", "--tone", "angry", "hi"])
        self.assertIsNone(exit_message)
        self.assertEqual(len(calls), 2)
        self.assertIn("Arr", out)

    def test_an_expensive_model_is_refused_before_sending(self):
        env = {**ENV, "CHAT_MODEL": "pricey/model"}
        _, _, exit_message, calls = run(["--role", "pirate", "--tone", "angry", "hi"], env)
        self.assertIn("refused", exit_message)
        self.assertIn("1¢", exit_message)
        self.assertEqual(len(calls), 1)  # only the price lookup, no chat request

    def test_a_failed_price_lookup_sends_nothing(self):
        failure = chat.urllib.error.URLError("certificate verify failed")
        _, _, exit_message, calls = run(["--role", "pirate", "--tone", "angry", "hi"],
                                        replies=(failure,))
        self.assertIn("refused: could not read prices", exit_message)
        self.assertEqual(len(calls), 1)  # the price lookup only

    def test_max_tokens_flag_changes_the_request(self):
        _, _, _, calls = run(["--role", "pirate", "--tone", "angry", "--max-tokens", "20", "hi"])
        self.assertEqual(calls[1].args[2]["max_tokens"], 20)

    def test_the_limit_is_exactly_one_cent(self):
        request = chat.build_request("m", "pirate", "angry", "hi")
        per_output_token = 0.01 / 300
        just_under = (0.0, per_output_token * 0.99)
        just_over = (0.0, per_output_token * 1.01)
        self.assertLessEqual(chat.worst_case_usd(request, just_under), chat.BUDGET_USD)
        self.assertGreater(chat.worst_case_usd(request, just_over), chat.BUDGET_USD)

    def test_an_unpriced_model_skips_the_check_and_says_so(self):
        env = {**ENV, "CHAT_MODEL": "llama3.2"}
        reply = {**REPLY, "model": "llama3.2", "usage": {"prompt_tokens": 30, "completion_tokens": 9}}
        out, err, exit_message, _ = run(["--role", "pirate", "--tone", "angry", "hi"], env,
                                        ({"data": [{"id": "llama3.2"}]}, reply))
        self.assertIsNone(exit_message)
        self.assertIn("1¢ check skipped", err)
        self.assertIn("cost not reported", out)


class Output(unittest.TestCase):
    def test_receipt_shows_model_tokens_and_cost(self):
        self.assertEqual(chat.receipt(REPLY), "── cheap/model · 42 in / 17 out · $0.000011")

    def test_cost_formatting(self):
        self.assertEqual(chat.format_cost({"cost": 0.00004}), "$0.00004")
        self.assertEqual(chat.format_cost({"cost": 0.01}), "$0.01")
        self.assertEqual(chat.format_cost({"cost": 0}), "$0")
        self.assertEqual(chat.format_cost({}), "cost not reported")

    def test_answer_then_receipt_on_stdout(self):
        out, _, _, _ = run(["--role", "pirate", "--tone", "angry", "hi"])
        self.assertEqual(out.splitlines(), ["Arr, 'tis the text a model can see!",
                                            "── cheap/model · 42 in / 17 out · $0.000011"])

    def test_empty_answer_explains_hidden_reasoning(self):
        reply = {**REPLY, "choices": [{"message": {"content": None}}]}
        self.assertIn("hidden reasoning", chat.answer_text(reply))

    def test_show_request_prints_the_json_but_never_the_key(self):
        _, err, _, _ = run(["--role", "pirate", "--tone", "angry", "--show-request", "hi"])
        self.assertIn('"max_tokens": 300', err)
        self.assertIn('"role": "system"', err)
        self.assertNotIn("test-key", err)


class Errors(unittest.TestCase):
    def test_missing_environment_is_named(self):
        _, _, exit_message, calls = run(["--role", "pirate", "--tone", "angry", "hi"], {})
        for name in ("CHAT_BASE_URL", "CHAT_MODEL", "OPENROUTER_API_KEY"):
            self.assertIn(name, exit_message)
        self.assertEqual(calls, [])

    def test_a_missing_role_outside_a_terminal_lists_the_choices(self):
        with mock.patch("sys.stdin.isatty", return_value=False):
            _, _, exit_message, _ = run(["--tone", "angry", "hi"])
        self.assertIn("--role is required", exit_message)
        self.assertIn("lebanese-teta", exit_message)

    def test_an_unknown_tone_is_rejected_by_the_parser(self):
        _, err, exit_message, calls = run(["--role", "pirate", "--tone", "cheerful", "hi"])
        self.assertEqual(exit_message, "2")
        self.assertIn("invalid choice", err)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
