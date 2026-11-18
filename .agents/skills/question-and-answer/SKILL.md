---
name: question-and-answer
description: >-
  Interview in rounds until a plan or design for this API is settled. Use when
  the user wants to stress-test a plan, a feature, an API shape, or a design
  decision before coding, or invokes @question-and-answer. Do not use for a
  code review, a pull-request review, or rewriting documentation.
disable-model-invocation: true
metadata:
  usage: "@question-and-answer <plan-or-design>"
  example: "@question-and-answer where should missed minutes be calculated?"
allowed-tools: Read Grep Glob
---

## What I Do

Interview until you and the user share one plan. Map the plan as a tree: each decision unlocks the decisions that
depend on it. Ask in rounds. Do not implement, edit files, or open a pull request during the interview.

## When to Use Me

Use this skill when the user wants a plan, a feature, an API shape, or a design decision stress-tested before any
code is written.

Leave these to their own skills:

* A review of the working tree belongs to `@code-review`.
* A review of a branch diff belongs to `@pr-review`.
* Prose, a design note's wording, and a commit message belong to `@technical-writing`.
* OpenAPI schema shape belongs to `@api-docs`.

## The tree

A decision is settled when the user has accepted an answer, or when the repo already decides it and the user is not
proposing to depart from it. Answers already in the message that invoked this skill are settled. Do not ask them
again.

The frontier is every unsettled decision whose prerequisites are settled. Those are the questions you can ask now
without guessing at an answer you have not heard.

Work one frontier per round. After the user answers, update the tree. Settled decisions push the frontier outward.
A rejected recommendation changes that branch: drop the questions that depended on the old answer and recompute.

## A round

Ask the whole frontier in one message, then wait. A question whose answer depends on another question in this round
belongs to a later round.

Number each question. Give it a short title, the context the user needs, and one recommended answer. Word it so
"yes" accepts that recommendation. The recommendation is the answer you would ship, not a menu. When two options are
real, recommend one and say what the other costs.

```
**Q1. Where the calculation runs**

`doc/design-and-decision/attendance.md` calculates the account from the employee's own record. `AGENTS.md` puts
work on this API when it must stay off the client. This calculation uses no service credential.

Recommended: leave the calculation on the client. Reply yes to accept it.
```

One decision per question. Cite the file when the recommendation comes from the repo. Prefer, in order, security,
simplicity, maintainability, and consistency with the existing code, as `AGENTS.md` states.

"Yes", "yes to all", or "go with your recommendations" settles those questions. A "no" needs the alternative the
user wants. If they give the alternative, that answer is settled. If they do not, ask only for that alternative in
the next round.

## Facts and decisions

Facts are yours. Decisions are the user's.

Before asking, look up anything this repo can answer. Read `app/`, `doc/`, `AGENTS.md`, and the relevant skill.
Search with Read, Grep, and Glob. A wide search can go to a subagent when one is available. A search still in
flight is an unsettled prerequisite: questions that depend on it wait, and the rest of the frontier is asked now.

Do not ask the user for a path, a symbol, a status code, a convention, or a behavior you could read. State that
fact inside the question, with the file, and ask only for the decision that remains.

Do not ask the user to confirm a convention they are not trying to change. State it as settled and move to the
frontier it unlocks.

## What to ask about

Ask about decisions that change behavior, data, or where the work runs. The usual ones in this API:

* Whether the client does the work through Supabase, or this API does it because the work must stay off the client.
  `AGENTS.md` draws that line.
* Which layer owns it: a thin router in `app/http/`, a service, a reader, a writer, a guard, or a port.
* Whether the route requires `AuthenticatedGuardDep`.
* Whether a failure is `AppException` or `HTTPException`, and which `code` the client will see.
* Secrets, service credentials, uploads, and anything logged or returned to the client.
* A change that is risky or hard to reverse.

Skip formatting, naming nits, and wording. Skip a question the code or a design note already answers, unless the
plan departs from that answer. Then the question is whether to depart, and the recommendation is to stay.

Make the smallest change that fully solves the problem. Recommend against a broader architecture change unless the
user asked for one.

## When to stop

The interview is done when the frontier is empty: every branch that could change the work has an answer, and nothing
material is still assumed.

Then send a short confirmation, in dependency order. One line per settled decision. No new questions.

```
Settled:

1. The client calculates missed minutes.
2. This API does not grow a route for that calculation.

Reply yes if that is the shared plan.
```

After the user confirms, stop. Implementation, a design note, and a commit are separate requests. If they confirm
and in the same message ask you to build it, the interview is over and that later request is ordinary work.
