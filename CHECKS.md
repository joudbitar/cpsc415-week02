# Checks

Run on 2026-09-23 between 21:28 and 21:31 UTC. Question every time: "In one sentence, what is a context window?" The coding agent ran the commands at my request; the key came from the macOS Keychain for each command and was never printed or saved.

"The record" below is OpenRouter's own entry for the request, fetched from its `/api/v1/generation?id=...` endpoint with the request id that `--show-request` prints. It is the same data the Activity page shows, and it does not come from my program's output.

| Check | Expected | Observed | Pass/fail |
|---|---|---|---|
| Question through OpenRouter | An answer and a usage line | `minimax/minimax-m3`, angry pirate: a one-sentence pirate answer, then `── minimax/minimax-m3 · 207 in / 182 out · $0.000245` | Pass |
| Usage record matches | Same model; same or close token counts | Rerun as angry pirate, id `gen-1790199016-kspxHG8CAggZaC0wq9OZ`. Receipt: 207 in / 102 out, $0.000149. Record: 207 / 102 native tokens, $0.00014898, provider AtlasCloud. Token counts and cost match exactly. The model name differs slightly: the record says `minimax/minimax-m3-20260531`, the dated version behind the name I asked for | Pass |
| System prompt changed | Answer style changes accordingly | Same model, `--role shakespearean-actor --tone sleepy`: the answer opened with "*yawns and stretches* Methinks..." and ended "*rubs eyes*". The pirate version said "Arrr, ye scallywag". The content (tokens the model can hold at once) stayed the same; only the voice changed | Pass |
| `max_tokens` = 20 | Truncated or empty answer; tokens still billed | MiniMax M3: empty answer, 20 tokens out, $0.000051 billed. Record for id `gen-1790199030-95QRDAoWvtIWr1ieMCS9`: reasoning tokens 20, finish reason `length`. All 20 tokens went to hidden reasoning before any visible text | Pass |
| Model swapped (step 4) | Different model name in usage; answer may differ | Changed only `CHAT_MODEL` to `deepseek/deepseek-v4-flash`: receipt said `deepseek/deepseek-v4-flash · 120 in / 53 out · $0.000021`, with a shorter pirate answer | Pass |
| Local model (optional) | Answer from localhost; no OpenRouter entry | Not tried. No Ollama or LM Studio is installed on this laptop, and the 16 GB of memory is the minimum the setup guide lists | Not run |

## Something I didn't expect

DeepSeek V4 Flash with `--max-tokens 20` once came back with 52 output tokens and a whole sentence, which is more than the cap. The input count on that run was 41, not the 120 from a minute earlier with the same prompt. I ran it again and fetched the records: OpenRouter sent the same model to a different provider each time (DeepInfra, then AtlasCloud). On the rerun the cap held (20 tokens, finish reason `length`) and the receipt matched the record. I didn't keep the id of the 52-token run, so I can't prove which provider ignored the cap. What I can say is that one model name on OpenRouter can mean different providers with different token counts, which is why the provider's record matters more than the program's output.

## Automated checks

`python3 -m unittest` runs 20 offline tests in `test_chat.py`: no network, no key. They cover the request shape (system and user roles, `max_tokens`), all 36 role and tone combinations, the 1-cent guard (a cheap model is sent, an expensive one is refused before any chat request, a failed price lookup sends nothing, the limit sits exactly at $0.01), the receipt format, the empty-answer note, and the error messages. Result on 2026-09-23: 20 passed on Python 3.13 and on the macOS built-in Python 3.9.

Two more checks outside the table:

- Against OpenRouter's real price list, `anthropic/claude-opus-4.1` was refused before sending: worst case $0.0232 with 300 max tokens.
- The arrow-key menus were driven in a pseudo-terminal: four presses of Down picked "lebanese teta", and Up from "angry" wrapped to "suspicious". Both showed up in the system message.
