---
name: technical-writing
description: >-
  Write and revise prose for this API so a tired engineer understands it on
  the first read. Use when writing or editing the README, files under doc/,
  AGENTS.md, a skill, a commit message, a pull-request body, or an OpenAPI
  summary or description, and when the user invokes @technical-writing.
  Leave OpenAPI schema shape, status codes, and the response envelope to
  @api-docs.
disable-model-invocation: true
metadata:
  usage: "@technical-writing <doc-or-change>"
  example: "@technical-writing revise doc/design-and-decision/storage-buckets.md"
allowed-tools: Read Grep Glob Edit Write
---

## What I Do

Apply one writing standard to Haruna API prose. The standard has four layers: pick a single mode, write the sentence
to the reader, give each sentence one thought, and leave no sentence with two readings. Three shorter rules sit above
the layers.

The codebase is the word list. Write the real symbol, path, setting, command, or bucket name. A synonym names
something the code does not have.

## When to Use Me

Use this skill for:

* `README.md`: setup, run, test, and deploy
* `doc/conventions-and-standards/`: normative rules
* `doc/design-and-decision/`: why a design is the way it is
* `AGENTS.md` and skills under `.agents/skills/`
* Commit messages and pull-request bodies
* The summary or description string on a route

Leave these to their own skills:

* Schema shape, status codes, and the `{ok, content}` envelope belong to `@api-docs`.
* A review verdict belongs to `@code-review` or `@pr-review`.

Do not restyle a conventions page into tutorial prose, and do not rewrite headings you were not asked to change.

## Standing rules

* Cut every word that does no work. If the sentence survives without a word, the word goes. "In order to" is "to".
* Use the short, everyday word. "Use", not "utilize". "Help", not "facilitate". A long word has to buy its length
  with precision the short word lacks.
* When a rule makes the sentence worse, fix the sentence another way or leave it alone. A sentence that follows every
  rule and sounds like a machine wrote it has failed.

State the fact. Use a negative when the distinction is the rule, as in "Lunch does not consume paid time off." Skip
filler, hedging, and pre-announcements ("it is important to note", "simply", "easy", "quickly", "we will soon"). If
the step were simple, the reader would not be here.

## Rhythm

A page can obey every layer and still read machine-written: every sentence the same length, no judgment anywhere,
nothing specific.

* Mix lengths on purpose. A short sentence lands a point. A longer one carries a fact with its condition.
* One thought per sentence does not mean one length per sentence. Split the sentence that carries two thoughts. Keep
  the long sentence that carries one.
* Have a view where the mode allows it. A design note weighs a trade-off and says what the design makes of it.
  A conventions page stays dry.
* Be specific. "`POST /medias/videos` is still a stub, so uploading an original is not an API route" beats "some
  endpoints are incomplete".

## Pick the mode first

One document, one mode. Two questions pick it: does the page inform action or understanding, and does it serve
learning or work?

* Action and learning: a tutorial. This repo rarely needs one. When it does, keep it out of `doc/`.
* Action and work: a how-to. The README.
* Understanding and work: reference. Conventions, `AGENTS.md`, and skills.
* Understanding and learning: explanation. `doc/design-and-decision/`.

Name the mode before drafting. An edit keeps the mode the file already has.

**How-to.** Solve the task the reader has. Assume they can run a shell, and skip teaching Python. Every step is a
command, and the next sentence says what they should see. Link background instead of explaining it.

> Copy `.env.example` to `.env` and fill in the values. Start the API with `uvicorn app.main:app --reload`. It
> listens at `http://localhost:8000`.

**Reference.** Describe the rule. No persuasion, no history. A conventions page keeps its current shape: a bold
title, numbered sections, **Must** and **Should**, and tables. `doc/conventions-and-standards/coding.md` is the model.
A new conventions page uses that shape. An existing page keeps the headings it has.

> Must raise `AppException(status_code, code, message)` for domain failures.

**Explanation.** One bounded why, readable away from the editor. Give the constraint, the decision, and the
alternative you rejected. `doc/design-and-decision/attendance.md` is the model: purpose, then the rules, with each
term defined once. A table states a rule. It does not turn the page into a conventions file. A new design note uses
one sentence-case title and headings that carry the point ("Missed minutes", not "Calculation").

> A recorded absence is time the employee treats as actually taken. It is not a request still waiting on the company.

**Agent reference.** `AGENTS.md` and a skill tell an agent what to do. Match the sibling shape when editing a skill:
what it does, when to use it, then the procedure. Point at a file. Do not turn a skill into an essay.

> Routers in `app/http/` parse the request, delegate to a service, and return the inner value.

Do not mix modes. A how-to does not argue a design. A conventions page does not walk through setup. A design note
does not become a list of **Must** lines. Split and link.

## Sentences

Talk to the reader as "you", in the present tense, on a how-to, a design note, a pull-request body, and an OpenAPI
sentence. "Will" is for something that happens later. A conventions page stays impersonal and uses **Must** or
**Should**.

* Say who does what. "The middleware wraps the result" beats "the result is wrapped". Passive is fine when the actor
  is unknown or beside the point.
* Write a step as a command. "Run `uv run pytest`." Put the condition before the action. "To run one feature's
  tests, pass the directory: `uv run pytest tests/features/media`."
* Put the common case first. Exceptions after.
* Headings on a new design note carry the point and use sentence case. A task heading is a bare verb phrase. A
  concept heading is a noun phrase. One title per page, and no skipped levels. A conventions page keeps its own
  heading style.
* Number a sequence. Use bullets for everything else. Introduce a list with a complete sentence, and keep the items
  parallel.
* Put code, paths, commands, and symbols in code font. Use a serial comma. Say up front that a list is partial.
* A link uses the page title or a short description of the destination. Prefer a sentence of context on the page
  over a link off it.

## One thought at a time

* One instruction per sentence. One thought per sentence everywhere else.
* Treat about 20 words for an instruction, and about 25 for any other sentence, as a check. Split when a sentence
  is doing two jobs. Keep it when the length is one thought with its condition. The standing rules outrank the count.
* Put the warning or the condition before the step it guards.
* Keep "the" and "a". "Delete media row" reads two ways. "Delete the media row" reads one.
* Give each word one meaning, then keep it. If "check" means inspect, do not also use it for a lint run. Say "lint".
* Pick one verb per action and stick to it. "Raise `AppException`" on every page that means that, not "throw" on
  the next page.
* Write a procedure as commands, addressed to the reader.
* Prefer a finite verb over an "-ing" word when both say the same thing.

## One reading

* Keep "only" and "not" next to the word they change. "This API writes only `resized`" limits the bucket. "It only
  reads `medias` and `thumbnails`" limits the action. Both can be true. Pick the one you mean.
* Break a long noun string. "The media thumbnail path builder" becomes "the method that builds the thumbnail path"
  (`CreateMediaThumbnailService.__make_thumbnail_path`).
* Make every "it", "they", and "this" point at one noun. Repeat the noun when two nouns are in play. Do not let
  "this" or "which" point at a whole clause.
* Do not drop a verb. "The reader loads the bank and the writer the balance" leaves the writer without one.
* Keep the small words that show structure, such as "that" in "Ensure that `APP_ENABLE_DOCS` is true".
* Repeat the article in a series when dropping it can merge two things. "The reader and the writer" are two classes.
* When "and" or "or" can group two ways, say which parts they join. "Both … and", "either … or", and "if … then"
  do that work.
* Use periods. Give an aside its own sentence. Text in parentheses is a full grammatical unit or its own sentence.
  Do not form a plural with "(s)". Write "a, b, or both" instead of "a/b" or "and/or".
* Call each thing by one name, on every page. A note that says "the bank", "the ledger", and "the entitlement" for one
  figure teaches three figures. Use the name the code or the design note already uses (`missed minutes`,
  `uncovered absence`, `SupabasePort`). Do not invent a new one.
* Skip idioms, colloquialisms, and Latin abbreviations.

## Commit messages and pull requests

Commit messages follow `doc/conventions-and-standards/git.md`. The layers above apply inside that template. Do not
invent a second format.

```
doc: Describe how attendance minutes are counted

- Add the attendance design note under doc/design-and-decision/.
- Define missed minutes as the union of declared paid absence and uncovered absence.
```

The summary is sentence case and names the change. Each bullet is one change and names the file or module when that
helps. Types are `feat`, `fix`, `hotfix`, `ref`, `test`, `conf`, `chore`, and `doc`.

A pull-request body is a briefing a reviewer can read in a minute: what changed, why, and the setup the change
requires (a new dependency, a migration, a new environment variable). Link the design note when one exists. Leave
logs and metric tables out of the body.

## OpenAPI sentences

A route summary or description is one dry reference sentence in the present tense. It names what the operation does.

> Return the caller's paid-time-off bank for a calendar year.

`@api-docs` owns the return type, the `responses` map, and the envelope. This skill does not add a hand-written spec.

## Procedure

1. Read the page you are changing, and read a sibling page in the same directory before starting a new one.
2. Name the mode. Keep the mode the file already has.
3. Read the code, command, or design note the page names. The word list is those files: `AppException`, `handle()`,
   `SupabasePort`, `AuthenticatedGuardDep`, `app/http/`, `app/features/`, `{"ok": true, "content": ...}`.
4. Draft in that one mode. Confirm every path, symbol, command, and count against the code. If you cannot confirm a
   number, omit it.
5. Read the page once as a tired engineer. You can name the mode in one word. Every code span exists. No sentence
   does two jobs. A conventions page still uses **Must** or **Should** and its own headings.

Then report the files changed, the mode of each page, and any symbol you corrected because the draft had invented a
name.

## Worked example

Before:

> Configuration of storage bucket access is performed via the Supabase port. It is important to note that writing
> should only be done to the resized bucket, while reading of medias and thumbnails is also supported. Since video
> upload is not yet implemented, originals cannot be uploaded through the API.

After, in the voice of `doc/design-and-decision/storage-buckets.md`:

> The API reaches every bucket only through `SupabasePort`. This API writes only `resized`. It only reads `medias`
> and `thumbnails`. `POST /medias/videos` is still a stub, so uploading an original is not an API route.
