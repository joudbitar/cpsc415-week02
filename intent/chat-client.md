# Intent: chat client with a role and a tone

## Goal
A command-line program that sends one question to a language model and prints the answer in a character's voice, built from a role (pirate, detective, sports commentator...) and a tone (angry, sleepy, overdramatic...) chosen from two menus. After the answer it prints one receipt line with the model name, the input and output token counts, and the cost.

## Who it is for
Me, as a student learning what a chat API call contains. The role and tone make the system prompt visible: changing them changes the answer in a way anyone can see.

## Constraints
- Python 3.9 or later, standard library only. One file, `chat.py`.
- The base URL comes from `CHAT_BASE_URL`, the model from `CHAT_MODEL`, the key from `OPENROUTER_API_KEY`. Nothing secret in the code or the repository.
- At most 1 cent per question. Before sending, the program looks up the model's price and refuses if the worst case (the prompt plus the full `max_tokens` reply) could go over 1 cent. Models with no listed price, such as a local one, skip the check.
- Role and tone come from `--role` and `--tone` flags. If either is missing and the program runs in a terminal, it shows an arrow-key menu for it.
- `max_tokens` is 300.
- Due Monday, September 28, 2026, 1:30 PM.

## Not in scope
- Streaming the answer as it is generated.
- Chat history or follow-up questions. One question per run.
- A web page or graphical interface.
- Retries after a failed request.
- More than one provider at a time.
- Custom roles or tones typed in by the user. The lists are fixed in the code.

## Success looks like
- `python3 chat.py --role pirate --tone angry "What is a context window?"` prints an answer an angry pirate would give, then the receipt line.
- Changing only `CHAT_MODEL` sends the same question to a different model, and the model name on the receipt changes.
- The model name and token counts on the receipt match the request's entry on the OpenRouter Activity page.
- A model too expensive for 1 cent at the chosen `max_tokens` is refused before any request is sent.

## Open questions
- Which roles and tones go in the menus, and how many of each?
- Does the receipt's cost come from OpenRouter's response, or is it computed from the price list?

**Approved by:** <your name>, <date>
