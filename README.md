# Chat client with a role and a tone

Asks a model one question and prints the answer in a character's voice: pick a role (pirate, noir detective, Lebanese teta...) and a tone (angry, sleepy, deadpan...), any of 36 combinations. The last line is a receipt with the model, the token counts and the cost. Before anything is sent, the program checks the model's price and refuses if the question could cost more than 1 cent.

Built for CPSC 415 Week 2 from the approved intent in [`intent/chat-client.md`](intent/chat-client.md).

## Run it

Python 3.9 or newer, standard library only.

```bash
export CHAT_BASE_URL=https://openrouter.ai/api/v1
export CHAT_MODEL=minimax/minimax-m3
export OPENROUTER_API_KEY=...   # never in a file in this repo
python3 chat.py --role pirate --tone angry "In one sentence, what is a context window?"
```

```text
Arrr, ye scallywag, a context window be the blasted chunk o' text ...
── minimax/minimax-m3 · 207 in / 182 out · $0.000245
```

Leave out `--role` or `--tone` and a menu opens (arrow keys, Enter). `--show-request` prints the exact JSON sent and the request id. `--max-tokens` changes the reply budget from the default 300. For a local model, point `CHAT_BASE_URL` at it and set `CHAT_API_KEY` to any string.

Tests run offline, with no key:

```bash
python3 -m unittest
```

## What I corrected in the intent

The agent interviewed me and wrote the draft, then I made two corrections before approving it. The commits show each step.

1. I deleted a sentence claiming I only use models through apps that hide the request. That was made up. I've already called OpenRouter from code in another project.
2. I set `max_tokens` to 300. The draft left it as an open question, and it has to be settled because it controls both how long an answer can be and the worst-case cost the 1 cent check uses.

I also chose the six roles and six tones, and decided the receipt shows the cost OpenRouter reports rather than one the program computes, so it's the same number the Activity page records.

## One line I can explain

```python
return estimate_tokens(request) * input_price + request["max_tokens"] * output_price
```

That's `worst_case_usd` in `chat.py`, the heart of the 1 cent guard. The price per token comes from OpenRouter's public model list. The input side is an estimate (about 4 characters per token, rounded up). The output side assumes the model uses its entire `max_tokens` budget, because nothing stops it from doing that. If the total is over $0.01, the program exits before the chat request is sent. With Claude Opus 4.1 that comes to $0.0232, so it's refused. With MiniMax M3 it's under $0.0004.

## A bug the checks caught

The first version put the price lookup in a `try` block and treated any failure as "no listed price", which skips the guard. My Python 3.13 couldn't make HTTPS calls at first (the python.org installer ships without root certificates), so every lookup failed, and a model of any price would have been sent anyway. Now a failed lookup refuses to send, and `test_a_failed_price_lookup_sends_nothing` covers it.

## Two models, one question

Same question, same angry pirate, only `CHAT_MODEL` changed:

| Model | Answer | Tokens (in / out) | Cost (OpenRouter's record) |
|---|---|---|---|
| `minimax/minimax-m3` | Long, heavy on pirate slang, and it explained that input and output tokens both count | 207 / 182 | $0.000245 |
| `deepseek/deepseek-v4-flash` | One short sentence: the amount of text a model can see before it forgets the rest | 120 / 53 | $0.000021 |

That's one question each, so it's an observation, not a benchmark. Part of MiniMax's output count is hidden reasoning: on another run its record showed 48 of 102 output tokens spent reasoning. With `max_tokens` at 20, all 20 went to reasoning and the visible answer was empty, but it was still billed $0.000051.

The biggest surprise was DeepSeek. OpenRouter sent it to a different provider on different requests (DeepInfra, then AtlasCloud), and the input count for the same prompt went from 120 to 41. One run even returned 52 tokens past a 20-token cap. Details are in [`CHECKS.md`](CHECKS.md).

## Local model

Not tried. There's no Ollama or LM Studio on this laptop, and 16 GB of memory is the minimum the setup guide lists. The code already supports it: `CHAT_API_KEY` takes priority over `OPENROUTER_API_KEY`, and a model with no listed price skips the 1 cent check with a note.

## How it was built

Harness: Claude Code. Model: Claude Opus 5.5, on my Claude subscription. The agent ran the discovery interview, drafted the intent, proposed a plan I approved, and wrote `chat.py` and the tests. The live checks were run by the agent at my request, with my OpenRouter key read from the macOS Keychain for each command and never written to a file. The models the program itself called are MiniMax M3 and DeepSeek V4 Flash, through my OpenRouter account.

All the live calls in this lab together cost under $0.001 on OpenRouter.
