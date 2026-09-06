# Cadence — Prototype Working

**A complete technical account of what was built, how it runs, and how it would
connect to real enterprise systems.**

Agentic AI Hackathon, Track 2 · Built on Neuro SAN (neuro-san) · Cognizant AI Lab

---

## Table of contents

1. [What we built](#1-what-we-built)
2. [The problem](#2-the-problem)
3. [How it works, end to end](#3-how-it-works-end-to-end)
4. [The agents](#4-the-agents)
5. [The coded tools](#5-the-coded-tools)
6. [The pipelines](#6-the-pipelines)
7. [Memory management](#7-memory-management)
8. [LLM configuration and failover](#8-llm-configuration-and-failover)
9. [File-by-file reference](#9-file-by-file-reference)
10. [Data model](#10-data-model)
11. [Running the prototype](#11-running-the-prototype)
12. [Connecting to real applications](#12-connecting-to-real-applications)
13. [What is proven, and what is not](#13-what-is-proven-and-what-is-not)

---

## 1. What we built

**Cadence is a second brain for one employee.** It holds their calendar, tasks,
messages, learning obligations, past decisions and knowledge-transfer material in
one place, and reasons across all of it to answer the questions that actually
matter during a working day:

- What did I miss?
- What deserves my attention right now?
- What should I actually do today, and when?
- Can I finish this today? (Often: no, and here is why.)
- What do I need to know before this meeting?
- Why did we decide that, six months ago?
- What should I learn next?

And critically, it works in the other direction too: **the employee can tell it
things.** "I have a meeting at 5pm." "A new course was assigned, due 30
September." Those become records immediately, and the next plan reflects them.

**Built as:** 8 agents and 7 deterministic Python tools orchestrated by neuro-san,
declared in a single 553-line HOCON file, over a synthetic dataset of one
employee's working life.

**The distinguishing design choice:** every number the system states — free
windows, durations, priority scores, constraint violations — is computed in
Python, never by a language model. The agents decide what to ask, interpret
results, weigh trade-offs and explain themselves. They are forbidden from
inventing a fact a tool did not return.

---

## 2. The problem

An employee's context is scattered across systems that do not talk to each other:
mail, chat, calendar, tickets, documents, a learning portal, recorded handovers.
Each is individually fine. Together they produce a specific daily failure:

> You have ninety minutes free. You have a three-hour task that matters most.
> Every tool you own will happily let you start it.

Calendars show availability but know nothing about the shape of your work. Task
lists rank by due date but know nothing about your day. Learning portals list
courses but know nothing about either.

Cadence reasons about **fit**: whether a specific piece of work can actually be
done in a specific window, given its size, whether it can be interrupted, what it
depends on, and what else is competing for the day.

---

## 3. How it works, end to end

```
   Employee
      |  natural language, in and out
      v
 +----------------------------------------------------------+
 |  Cadence  (front man agent, AAOSA routing)               |
 |  Decides which specialists a question actually needs      |
 +----------------------------------------------------------+
      |            |            |           |          |
      v            v            v           v          v
 TimeKeeper   WorkTracker  LearningCoach  Memory    Capture     DayPlanner
                                          Keeper                    |
      |            |            |           |          |       PlanBuilder
      |            |            |           |          |            |
      |            |            |           |          |        PlanCritic
      +------------+------------+-----------+----------+------------+
                                |
                    +-----------------------+
                    |  Coded tools (Python) |   deterministic, no LLM
                    +-----------------------+
                    CalendarGaps   ContextQuery
                    PriorityScore  PlanBuilder
                    PlanValidate   Capture
                    MemoryWrite
                                |
                    +-----------------------+
                    |  JSON stores on disk  |   read and written
                    +-----------------------+
```

**The flow of a single request:**

1. The employee asks something in plain language.
2. The **front man** classifies it and routes to the specialists that can help —
   not all of them. This is neuro-san's AAOSA pattern: agents are polled about
   whether they can contribute, and only relevant ones are engaged.
3. Specialists call **coded tools** to get facts. No agent computes a time, a
   duration or a score itself.
4. For planning, the schedule is **constructed in Python**, then **independently
   validated** by a second, separate Python implementation.
5. The front man composes one answer, citing record ids.
6. If the request created or changed something, it is **written back to disk**, so
   the next question sees it.

---

## 4. The agents

**Eight agents.** Six are LLM-backed reasoning agents; the split of
responsibility is by *domain of knowledge*, not by task type.

| # | Agent | Purpose | Model | Tools it can call |
|---|---|---|---|---|
| 1 | **Cadence** | Front man. The only agent the employee talks to. Classifies the request, routes to specialists, composes the final answer. | gpt-oss-120b | all six specialists |
| 2 | **TimeKeeper** | Owns *time*. Free windows, meeting load, whether a given piece of work fits in the time available. | gpt-oss-20b | CalendarGaps, ContextQuery |
| 3 | **WorkTracker** | Owns *work*. The backlog, tickets, unread mail, who is blocked on what, and the ranking of what deserves attention. | gpt-oss-20b | ContextQuery, PriorityScore |
| 4 | **LearningCoach** | Owns *obligations to learn*. Distinguishes the five origins of learning and the consequences of letting each slip. | gpt-oss-20b | ContextQuery, PriorityScore |
| 5 | **MemoryKeeper** | Owns *history*. Past decisions and their rationale, meeting context, transcripts. Also extracts skill gaps from handover material. | gpt-oss-20b | ContextQuery, MemoryWrite |
| 6 | **Capture** | Owns *input*. Turns something the employee says into a stored meeting, task or learning item. | gpt-oss-20b | Capture |
| 7 | **DayPlanner** | Produces the day's schedule. A fixed three-step workflow, not a router. | gpt-oss-120b | PlanBuilder, PlanCritic |
| 8 | **PlanCritic** | Independently reviews a proposed schedule and reports violations. Explicitly instructed not to soften or approve around a blocker. | gpt-oss-120b | PlanValidate |

### Why this split

Agents are divided by **what they know**, so each has a small, coherent set of
facts and a short instruction. A single "assistant" agent with every tool would
need one enormous prompt and would make worse routing decisions.

### Where adaptive routing is used, and where it is not

AAOSA polling is used **only at the front man**. A question about learning does
not wake the planner; a question about the calendar does not wake memory.

It is deliberately **switched off** for `DayPlanner` and `PlanCritic`. Planning is
a *workflow*, not a routing decision — asking a coded tool whether it is
"relevant" costs a model call and returns no information. An early build left
AAOSA on everywhere and a single planning request woke all five specialists and
blew the execution ceiling.

---

## 5. The coded tools

**Seven tools. All pure Python. No tool calls a language model.**

This is the core architectural rule: **tools produce facts, agents reason over
facts.** Models are unreliable at clock arithmetic — "how many minutes between
10:15 and 11:30, and does a 45-minute task fit" is exactly the kind of question
they get subtly wrong — and a hallucinated calendar is worse than no calendar.

| Tool | Class | What it does |
|---|---|---|
| **CalendarGapsTool** | `calendar_gaps.CalendarGaps` | Computes exact free windows between meetings for a date, plus the longest uninterrupted block. |
| **ContextQueryTool** | `context_query.ContextQuery` | The single retrieval surface. Filters across tasks, calendar, learning, messages, decisions, persona and transcripts by keyword, id or date range. |
| **PriorityScoreTool** | `priority_score.PriorityScore` | Ranks open work 0–100, decomposed into four named components so the ranking can be explained rather than asserted. |
| **PlanBuilderTool** | `plan_builder.PlanBuilder` | Constructs a constraint-satisfying schedule greedily, and reports what did not fit and why. |
| **PlanValidateTool** | `plan_validate.PlanValidate` | Independently checks a schedule against ten families of hard constraint. |
| **CaptureTool** | `capture.Capture` | Records a new meeting, task or learning item from the employee, including time parsing and conflict detection. |
| **MemoryWriteTool** | `memory_write.MemoryWriteBatch` | Writes newly identified skill gaps onto the learning plan. |

### The priority scoring model

Deterministic, and decomposed so every score can be defended:

| Component | Max | Meaning |
|---|---|---|
| `deadline_pressure` | 40 | Slack = time available minus time needed. Negative slack scores maximum. |
| `blocking_others` | 25 | Someone else cannot proceed until this is done. |
| `unblocks_own_work` | 15 | How many of your own tasks depend on this one. |
| `meeting_dependency` | 20 | Needed for a meeting happening today. |

Worked example from the dataset — AUTH-249 scores **90/100**:

```
deadline_pressure    30/40   5h of slack - due today
blocking_others      25/25   architecture review CAL-133 cannot proceed without it
unblocks_own_work    15/15   2 tasks depend on it: AUTH-247, AUTH-254
meeting_dependency   20/20   needed for the 15:00 review today
```

No model produced that ordering. It is arithmetic, and it is reproducible.

### The ten validation constraints

`PlanValidate` enforces:

1. Blocks fall inside working hours
2. No collision with a meeting
3. No collision with another planned block
4. Deep work gets its full duration and is never split across gaps
5. Deep work is not fragmented below a viable block size
6. Nothing finishes after its deadline
7. **Meeting preparation finishes before the meeting it prepares for**
8. Prerequisites are scheduled before dependent work
9. Mandatory learning near its deadline is not silently dropped
10. Daily deep-work load stays within a sustainable ceiling

Constraint 7 is the one both humans and language models get wrong: scheduling the
prep for a 3 pm review into the 4 pm slot.

---

## 6. The pipelines

Six distinct request pipelines. Each is a different path through the network.

### Pipeline A — Planning the day

The most involved, and the one that was rebuilt.

```
User: "what are my plans today?"
   |
   v
Cadence  -- routing exception: planning goes straight to DayPlanner,
   |        no polling of other specialists
   v
DayPlanner
   |
   +--> PlanBuilderTool  (Python)
   |      1. compute free windows
   |      2. rank candidates: forced -> mandatory learning -> priority score
   |      3. greedy first-fit, honouring deadlines, meeting order,
   |         dependencies, deep-work indivisibility, daily deep-work cap
   |      4. return plan + unscheduled items + reasons
   |
   +--> PlanCritic
   |      +--> PlanValidateTool  (Python, independent implementation)
   |             re-checks all ten constraints
   |             returns PASS or a list of blockers
   v
DayPlanner reports: the schedule, what could not fit and why,
                    and that it passed independent validation
```

**Why it is built this way.** The first version had a language model *propose*
schedules and the critic reject them until one passed. It did not converge: a
single request produced **39 critic round-trips** and timed out without ever
answering. Constructing the schedule in Python is instant and correct by design,
and the critic then validates **once**.

| | Before | After |
|---|---|---|
| Response | never returned | **57 s** |
| Validator round-trips | 39 | 1 |

The critic is not decoration. `PlanBuilder` and `PlanValidate` are **separate
implementations** of the same constraints, so a bug in the builder is caught
rather than rubber-stamped.

### Pipeline B — Capturing user input

```
User: "I have a meeting at 5pm today with the vendor"
   |
   v
Cadence  -- recognises a statement, not a question
   v
Capture  -- classifies: meeting / task / learning
   |         infers missing fields, states assumptions
   v
CaptureTool  -- parses "5pm" -> 17:00, defaults 60 min duration,
   |            allocates CAL-161, checks conflicts, writes calendar.json
   v
"Added 'Meeting with vendor' 17:00-18:00 as CAL-161. No conflicts.
 You may want to re-plan."
```

Then re-planning picks it up immediately: the last free window shrinks from 90 to
60 minutes, a 75-minute task drops out of the plan, and a 20-minute one takes the
slot.

### Pipeline C — Return-from-absence triage

```
User: "What did I miss while I was on leave?"
   -> Cadence -> WorkTracker
        -> ContextQueryTool (messages, since/until = leave dates from persona)
        -> PriorityScoreTool
   -> grouped into: Critical today / Important this week /
                    For information / Newly assigned
   -> plus one line naming who is waiting on you
```

### Pipeline D — Meeting preparation

```
User: "Prepare me for the 3 PM architecture review"
   -> Cadence -> MemoryKeeper (+ WorkTracker)
        -> ContextQueryTool across calendar, decisions, messages, transcripts
   -> brief: purpose, prior decisions and rationale, what changed recently,
             open questions nobody has answered, what you personally owe
   -> flags anything decided while the employee was on leave
```

### Pipeline E — Knowledge into learning

```
User: "Process the KT transcript and update my learning plan"
   -> Cadence -> MemoryKeeper
        -> ContextQueryTool (sources=transcript)
        -> extract concepts, decisions, dependencies, risks,
           action items, unanswered questions
        -> ContextQueryTool (sources=learning)  - what is already on the plan?
        -> MemoryWriteTool  - record 1 to 3 genuine skill gaps
   -> learning.json changes on disk
```

The point of this pipeline is that asking *"what should I learn next?"* before
and after gives **different answers**, because the system learned something.

### Pipeline F — Time-fit questions

```
User: "What are my free windows today?" / "Can I fit AUTH-247 today?"
   -> Cadence -> TimeKeeper -> CalendarGapsTool
   -> exact windows, longest uninterrupted block,
      and a plain statement when something cannot fit
```

---

## 7. Memory management

Cadence has **four distinct kinds of memory**. Conflating them is a common design
mistake, so they are kept separate.

### 7.1 Durable state — JSON on disk

The system of record. Six JSON stores plus a transcript directory, in
`cadence_tools/cadence/data/`. This is what survives restarts and what everything
reasons over.

| Store | Holds | Written by |
|---|---|---|
| `persona.json` | The employee, preferences, leave dates, pinned demo date | never (read-only) |
| `calendar.json` | Meetings | `capture.py` |
| `tasks.json` | The backlog | `capture.py` |
| `learning.json` | Learning obligations | `capture.py`, `memory_write.py` |
| `messages.json` | Mail and chat | never (read-only in this build) |
| `decisions.json` | Decision records and rationale | never (read-only in this build) |
| `transcripts/*.txt` | Knowledge-transfer material | never (read-only) |

### 7.2 Process cache — `cadence_store._CACHE`

Files are loaded once per process and held in a module-level dictionary. Reads are
cheap; writes go through `_persist()`, which appends to the in-memory structure
**and** rewrites the file, so cache and disk never diverge.

One bug worth recording, because it is easy to reintroduce: an early version of
the token-trimming logic mutated records *in place*. Since those records come
straight from the cache, it permanently truncated stored data for the life of the
process. Every transformation now copies first.

### 7.3 Retrieval memory — `ContextQuery`

The single read surface. Every agent sees the world only through this tool,
filtered by source, keyword, id or date range.

**This is keyword and structured filtering, not semantic search.** There are no
embeddings and no vector store. For a single employee's working context — a few
dozen records — exact filters are faster, fully explainable, and cannot retrieve
something spuriously similar. At the scale of years of history this would need to
change; see §12.

Two deliberate behaviours:

- **`sources=all` excludes transcripts.** A transcript is thousands of tokens and
  must be asked for by name, or it silently dominates every prompt.
- **The tool always advertises what transcripts exist**, whatever was searched.
  Without this, an agent that queried the wrong sources concludes the transcript
  does not exist — which is exactly what happened before the fix.

### 7.4 Write-back memory — the part that makes it a second brain

Memory that only reads is a search box. Two tools write:

- **`capture.py`** — what the employee tells the system directly
- **`memory_write.py`** — skill gaps extracted from handover material, with
  duplicate detection so re-processing a transcript does not double-write

Both allocate ids by scanning existing records (`next_id`), so ids never collide.

### 7.5 Conversation memory

Per-session chat history is held by neuro-san itself and returned in
`chat_context`. Cadence adds nothing here — it is short-term and belongs to the
framework.

### 7.6 Reset

Because the system genuinely writes to disk, demos need a known starting point.
`learning.seed.json`, `calendar.seed.json` and `tasks.seed.json` are pristine
copies; `scripts/reset_demo.py` restores all three.

---

## 8. LLM configuration and failover

### How neuro-san fallbacks actually work

Verified by reading the framework source, not assumed:

1. `llm_config.fallbacks` is a list of complete LLM configurations. Each is built
   into its own client, with its own API key and base URL.
2. Entry 1 becomes the primary model. Entries 2..N are attached through
   LangChain's `model.with_fallbacks(...)`.
3. LangChain's `RunnableWithFallbacks` catches `exceptions_to_handle`, which
   defaults to `(Exception,)`. **Any** failure from the primary — 429 rate limit,
   503 overload, timeout, auth error — moves that call to the next entry.
4. Entries whose API key cannot be resolved are skipped at construction time.

**A flat list is ordered failover, not load balancing.** Every call tries entry 1
first; only an exception moves it down the chain.

**But a nested list is a peer group, and peer groups are shuffled.** Reading
`default_llm_factory.py`: when an entry inside `fallbacks` is itself a list,
neuro-san recurses into it with `randomize_peers=True`, which shuffles the group
and picks a random member as primary. That converts failover into genuine load
spreading — different agents start on different keys instead of every call
draining key 1 until it dies.

This build uses peer groups deliberately.

### The chains in this build

**Planner, critic and front man** (`llm_config`) — eight targets in two stages:

```
1. [ gpt-oss-120b key1 | key2 | key3 | key4 ]   peer group, SHUFFLED
2. [ gpt-oss-20b  key1 | key2 | key3 | key4 ]   peer group, SHUFFLED
```

**Specialists** (`specialist_llm_config`) — four targets:

```
1. [ gpt-oss-20b key1 | key2 | key3 | key4 ]    peer group, SHUFFLED
```

**Gemini was removed from both chains**, and the reason is worth recording. Its
free tier is 20 requests/day, which is spent almost immediately. Worse, the
`google-genai` client retries internally with exponential backoff before
LangChain's fallback logic gives up — 1.5s, 2s, 4.4s, 8.6s, 16.8s. A single
request that reached Gemini stalled for 30-60 seconds before failing. A
last-resort provider that is always exhausted is not a safety net; it is a
latency trap. Four Groq accounts is the real redundancy.

Specialists run the lighter model because they are polled most often; the strong
model is reserved for planning and criticism. Escalation is: try a random key on
the strong model, then any surviving key in that group, then the light model
across all four keys, then a different provider.

Measured after a run of planning, capture and triage requests, remaining
per-key request budgets were 995 / 997 / 997 / 993 out of 1000 — load genuinely
spread across all four accounts rather than concentrated on one.

### Keys must come from separate accounts — measured, not assumed

An earlier build used four keys from **one** Groq account. That gives one quota,
not four: all four keys reported the same remaining-token count and it decremented
across all of them. They shared organisation `org_...z7xjf7`.

The current build uses four keys from **four separate accounts**, verified by
experiment: burning roughly 900 tokens on key 2 dropped key 2 from 7,923 to 7,003
remaining while keys 1, 3 and 4 did not move at all.

That is the difference between one daily quota and four.

Useful header facts, since they are easy to misread:

| Header | Meaning |
|---|---|
| `x-ratelimit-limit-tokens: 8000` | tokens per **minute**, resets in under a second |
| `x-ratelimit-limit-requests: 1000` | requests, on a rolling window |
| 200,000 TPD | the daily token cap, surfaced only in the 429 message |

### Token discipline

Because quotas are measured in tokens, tool output size is an architectural
concern, not a detail:

Four measures, in order of how much they saved:

1. **Transcripts excluded from `sources=all`.** A transcript is thousands of
   tokens; it must now be asked for by name.
2. **Field projection.** `ContextQuery` returns only the fields an agent needs to
   reason and cite, dropping bookkeeping like `assigned_on`, `tags`, `source_refs`
   and `participants`. `full=true` restores whole records.
3. **Score detail capped.** `PriorityScore` returns the four-component breakdown
   only for the top 6 contenders; the tail is id, title, score and effort.
4. **Result caps and text trimming.** At most 20 records per source; long bodies
   and rationales truncated.

Measured effect:

| Tool output | Before | After | Saving |
|---|---|---|---|
| `ContextQuery(all)` | 26,165 chars (~6,540 tokens) | 15,835 (~3,960) | **39%** |
| `PriorityScore` | 9,298 chars (~2,320 tokens) | 6,709 (~1,680) | **28%** |

A fifth measure sits in the prompt rather than the tools: the front man now
**decides from its routing table instead of polling every specialist**. Each poll
costs a full model call carrying its entire system prompt (the AAOSA instructions
alone are ~480 tokens), so answering a calendar question by waking six agents was
the single largest avoidable cost. AAOSA polling remains as the fallback for
requests the routing table does not cover.

---

## 9. File-by-file reference

```
My-Project/
├── README.md                    Product-facing overview: problem, capabilities,
│                                architecture, demo script, judging criteria
├── PROTOTYPE_WORKING.md         This document
├── run_cadence.ps1              Launcher (52 lines)
├── .env                         Secrets and paths. Gitignored, never committed
├── .gitignore                   Excludes .env, __pycache__, logs/
│
├── registries/
│   ├── manifest.hocon           6 lines. Registers cadence.hocon with the server.
│   │                            Pointed at by AGENT_MANIFEST_FILE
│   └── cadence.hocon            553 lines. THE agent network. Contains:
│                                  - AAOSA substitutions (reproduced, Apache-2.0)
│                                  - max_execution_seconds
│                                  - llm_config: 5-entry failover chain
│                                  - specialist_llm_config: 4-entry chain
│                                  - metadata and sample queries
│                                  - instructions_prefix: the anti-hallucination
│                                    rules every agent inherits
│                                  - 8 agent definitions
│                                  - 7 coded-tool declarations with JSON schemas
│
├── cadence_tools/               Named cadence_tools, NOT coded_tools, so it cannot
│   │                            collide with the framework's own package
│   ├── __init__.py
│   └── cadence/                 Must match the .hocon filename
│       ├── __init__.py
│       │
│       ├── cadence_store.py     114 lines. Shared data access, the single point
│       │                        every other tool reads through. Loads and caches
│       │                        the JSON stores; provides events(), tasks(),
│       │                        learning(), messages(), decisions(), persona(),
│       │                        transcript(); write helpers write_event(),
│       │                        write_task(), write_learning_item(); id allocation
│       │                        via next_id(); time helpers to_minutes()/to_clock()
│       │                        and deadline_parts().
│       │                        >>> This file is the connector seam. See §12.
│       │
│       ├── calendar_gaps.py     73 lines. CalendarGaps. Sorts the day's meetings,
│       │                        walks the gaps between them within working hours,
│       │                        returns each free window with its exact length,
│       │                        the total, and the longest uninterrupted block.
│       │
│       ├── context_query.py     143 lines. ContextQuery. The single retrieval
│       │                        surface. Source selection, keyword matching, id
│       │                        lookup, date-range filtering, unread filtering,
│       │                        result caps, long-field trimming, and a permanent
│       │                        index of available transcripts.
│       │
│       ├── priority_score.py    151 lines. PriorityScore. Computes the four
│       │                        scoring components for every open task, builds the
│       │                        reverse dependency map to know what each task
│       │                        unblocks, and ranks learning items separately by
│       │                        origin and deadline pressure. Returns the
│       │                        component breakdown, not just a number.
│       │
│       ├── plan_builder.py      251 lines. PlanBuilder. The deterministic
│       │                        scheduler. Computes free windows, orders
│       │                        candidates (user-forced, then mandatory learning,
│       │                        then priority), and greedily first-fits each one
│       │                        subject to: latest permissible finish (deadline or
│       │                        the meeting it prepares for), earliest permissible
│       │                        start (prerequisites), deep-work indivisibility,
│       │                        and the daily deep-work ceiling. Consumes windows
│       │                        as it books them. Returns the plan, everything
│       │                        unscheduled with a specific reason, and anything
│       │                        the user demanded that is impossible.
│       │
│       ├── plan_validate.py     241 lines. PlanValidate. The independent checker
│       │                        behind PlanCritic. Ten constraint families,
│       │                        each producing a blocker or a warning with a
│       │                        human-readable message naming the record.
│       │
│       ├── capture.py           199 lines. Capture. Turns employee statements into
│       │                        records. Includes _clock() which normalises "5pm",
│       │                        "17:00" and "5:30 pm"; meeting conflict detection
│       │                        against the existing calendar; task effort defaults
│       │                        with automatic deep-work inference at >= 60 min;
│       │                        and learning items with a computed daily study pace.
│       │
│       ├── memory_write.py      117 lines. MemoryWrite and MemoryWriteBatch.
│       │                        Appends learning items with duplicate detection by
│       │                        title, origin validation, and id allocation.
│       │                        The batch class records a whole transcript's worth
│       │                        in one call and reports written vs skipped.
│       │
│       └── data/
│           ├── persona.json         The employee, working preferences, colleagues,
│           │                        leave dates, and demo_today (pins the date so
│           │                        runs are reproducible)
│           ├── calendar.json        13 events across three weeks
│           ├── tasks.json           12 tasks with the full scheduling schema
│           ├── learning.json        5 items across all five origin types
│           ├── messages.json        15 mail and chat messages, weighted to the
│           │                        leave window
│           ├── decisions.json       5 decision records with rationale and
│           │                        rejected alternatives
│           ├── *.seed.json          Pristine copies for reset
│           └── transcripts/
│               └── auth_kt.txt      53-line knowledge-transfer transcript
│
├── scripts/
│   ├── ask.py                   79 lines. Command-line client. Posts to the
│   │                            streaming endpoint, parses the response, prints
│   │                            the answer and elapsed time. --trace shows which
│   │                            agents participated. Encodes output defensively so
│   │                            a Windows console cannot crash it on an en-dash.
│   └── reset_demo.py            37 lines. Restores learning, calendar and tasks
│                                from their seeds.
│
└── logs/                        server.log, nsflow.log, thinking traces.
                                 Written here, not into the framework checkout.
```

### Isolation from the framework

`neuro-san-studio` is treated as strictly read-only and is never written to.
Three mechanisms:

- `AGENT_MANIFEST_FILE` and `AGENT_TOOL_PATH` point at this project
- `cadence.hocon` is **self-contained** — the AAOSA substitutions are reproduced
  locally under Apache-2.0 attribution rather than `include`-d
- The server runs with `My-Project` as its working directory, so logs, thinking
  traces and `.env` loading all stay here

Two integration details that cost real debugging time:

- The project root **must** be on `PYTHONPATH` — neuro-san derives a module prefix
  from the tool path
- The tool package **must not** be called `coded_tools`, or it collides with the
  framework's own package on the import path

---

## 10. Data model

The intelligence lives in the task schema. A task list with only titles and due
dates cannot support fit reasoning.

```json
{
  "id": "AUTH-247",
  "title": "Implement refresh-token rotation ahead of Auroria policy change",
  "effort_minutes": 180,
  "deep_work": true,
  "interruptibility": "low",
  "deadline": "2026-09-16T17:30",
  "status": "not_started",
  "blocks": ["Helix release train 2026-09-11"],
  "depends_on": ["AUTH-249"],
  "meeting_dependency": null,
  "source": "Jira, assigned by Anita Deshpande while Kiran was on leave",
  "project": "Helix"
}
```

| Field | Why it exists |
|---|---|
| `effort_minutes` | Without it, "does this fit" is unanswerable |
| `deep_work` | Marks work that cannot be split across gaps |
| `interruptibility` | Distinguishes work suited to a fragmented window |
| `blocks` | Someone else is waiting — drives 25 points of priority |
| `depends_on` | Enforces ordering within a plan |
| `meeting_dependency` | Forces preparation to precede its meeting |

Learning items carry `origin` (one of five), `remaining_minutes`,
`min_session_minutes` and `consequence_if_missed`. Decisions carry `rationale`
and `alternatives_rejected`, which is what makes "why did we choose Redis"
answerable rather than merely retrievable.

**All data is synthetic.** No personal data, no real organisations, consistent
with the hackathon's data rules.

---

## 11. Running the prototype

**Requirements:** Python 3.13, neuro-san-studio installed in a virtual
environment, and at least one Groq API key. No additional packages — Groq is
reached through its OpenAI-compatible endpoint using neuro-san's built-in
`openai` provider class.

**Configure** `My-Project/.env`:

```
AGENT_MANIFEST_FILE=<abs path>\My-Project\registries\manifest.hocon
AGENT_TOOL_PATH=<abs path>\My-Project\cadence_tools
PYTHONPATH=<abs path>\My-Project

OPENAI_API_KEY=<Groq key 1>
GROQ_API_KEY_1=<Groq key 1>
GROQ_API_KEY_2=<Groq key 2>
GROQ_API_KEY_3=<Groq key 3>
GROQ_API_KEY_4=<Groq key 4>
GEMINI_API_KEY=<optional last-resort fallback>
```

**Start** — from inside `My-Project`, which matters:

```powershell
.\run_cadence.ps1
```

or

```bash
ns run --server-http-port 8081 --nsflow-port 4174
```

The nsflow UI is at `http://localhost:4174`; the server is on 8081. Non-default
ports are used so a default neuro-san instance can keep running alongside.

**Ask it something:**

```bash
python scripts/ask.py "I have today - what should I work on, and when?"
python scripts/ask.py --trace "What did I miss?"
```

**Reset between rehearsals** — Cadence writes to disk by design:

```bash
python scripts/reset_demo.py
```

---

## 12. Connecting to real applications

Everything today runs on mock data. This section is the migration path.

### 12.1 The seam already exists

`cadence_store.py` is the **only** module that touches storage. Every other tool
calls `events()`, `tasks()`, `learning()`, `messages()`, `decisions()`,
`transcript()` and the three write helpers. No agent and no other tool knows the
data is JSON.

Replacing mock data therefore means reimplementing those functions against real
APIs. **Nothing in the agent network, the HOCON, the scoring model, the scheduler
or the validator changes.**

```
        agents + tools  (unchanged)
                |
        cadence_store.py          <-- swap the body of these functions
                |
   +------------+-------------+
   |                          |
 JSON files (today)   real connectors (next)
```

The clean shape is a provider interface with a mock implementation and a real one
selected by configuration:

```python
class CalendarProvider:
    def events(self, since, until): ...
    def create_event(self, record): ...

# config decides which is loaded
PROVIDER = MockCalendar() if settings.mock else GraphCalendar(token)
```

That way the mock provider stays as the offline demo and test fixture rather than
being thrown away.

### 12.2 System-by-system mapping

| Cadence store | Real source | API | Auth |
|---|---|---|---|
| `events()` | Outlook / Teams calendar | Microsoft Graph `/me/calendarView` | OAuth 2.0, `Calendars.Read` |
| `write_event()` | Outlook calendar | Graph `POST /me/events` | `Calendars.ReadWrite` |
| `messages()` | Outlook mail | Graph `/me/messages` with `$filter` on receivedDateTime | `Mail.Read` |
| `messages()` | Teams chat | Graph `/me/chats/{id}/messages` | `Chat.Read` |
| `tasks()` | Jira | Jira REST `/rest/api/3/search` by assignee | OAuth 2.0 3LO or PAT |
| `write_task()` | Jira | `POST /rest/api/3/issue` | same |
| `learning()` | LMS / learning portal | Vendor REST, or SCORM/xAPI records | service account |
| `decisions()` | Confluence / SharePoint | Confluence REST, Graph `/sites/{id}/drive` | `Sites.Read.All` |
| `transcript()` | Recorded meetings | Graph `/me/onlineMeetings` + transcript endpoint, or Whisper on the recording | `OnlineMeetings.Read` |

Microsoft Graph covers calendar, mail, Teams and files in one credential and one
consent flow, which is why it is the highest-value first connector.

### 12.3 The hard part is not the API

Three genuine problems that plumbing does not solve:

**1. Real backlogs have no `effort_minutes` and no `deep_work` flag.**
Jira has story points at best, and nothing about interruptibility. Fit reasoning
depends on these fields entirely. Options, in increasing order of quality:

- Ask the employee once per ticket and remember (`capture.py` already does this
  shape of thing)
- Infer from issue type, labels and description length as a starting estimate
- **Learn from history** — record planned versus actual duration and correct the
  estimate over time. This is the version that gets genuinely good, and it is a
  real piece of work, not a detail.

**2. Volume breaks keyword retrieval.**
Twelve tasks and fifteen messages filter fine with exact matching. Two years of
mail does not. At that scale `ContextQuery` needs a hybrid: structured filters for
dates, ids and assignees — which are exact and must stay exact — plus semantic
search over free text for "why did we choose Redis". The store interface does not
change; the implementation behind it gains an index.

**3. Sync strategy.**
Do not call live APIs inside a reasoning loop; latency and rate limits make it
unusable. Pull on a schedule into a local cache, use delta queries where the API
supports them (Graph does), and treat the cache as the system of record for
reasoning. `cadence_store`'s existing `_CACHE` is the natural place for this to
land.

### 12.4 What changes for security and compliance

The moment real data arrives, several things that are free with synthetic data
become mandatory:

- **Per-user tokens, never a shared service account** for personal mail and
  calendar. Cadence reasons about one person's private context.
- **Encryption at rest** for the local cache, which now holds real mail.
- **Retention and deletion.** A cache of someone's mail is subject to the same
  policies as the mail itself.
- **Scope minimisation.** `Calendars.Read` and `Mail.Read` are sufficient for most
  capabilities; write scopes only where a capability genuinely writes back.
- **Audit trail** on anything written into a real system — a calendar event
  created by an agent should be identifiable as such.

None of this is exotic, but it is why the prototype deliberately uses synthetic
data rather than a real tenant.

### 12.5 A staged plan

| Stage | Scope | Why this order |
|---|---|---|
| 1 | Calendar read via Graph | Highest value, single scope, read-only, immediately makes fit reasoning real |
| 2 | Mail read via Graph | Powers "what did I miss" against a real inbox |
| 3 | Jira read | Real backlog, with effort estimates captured from the user at first sight |
| 4 | Write-back: create calendar blocks | The plan stops being advice and becomes the actual day |
| 5 | Transcripts via Graph or Whisper | Real handover material into the learning plan |
| 6 | Learned effort estimation | Planned versus actual, closing the loop |

Stages 1 and 2 alone would make this usable by a real employee, and neither
requires touching the agent network.

---

## 13. What is proven, and what is not

**Verified working, end to end, against a live model:**

| Capability | Evidence |
|---|---|
| Free-window computation | 75/90/90/90 minutes, exact tool numbers, 17 s |
| Day planning | Full schedule, 57 s, validator clean |
| Honest refusal | AUTH-247 declined with arithmetic: 180 min needed, 90 available |
| Capture — meeting | "5pm today" → CAL-161, 17:00–18:00, conflict-checked, 27 s |
| Capture — course | "due 30th Sep" → LRN-007, with daily pace, 35 s |
| Capture changes the plan | 5 pm meeting added → AUTH-254 dropped, AUTH-255 took the slot |
| Return-from-absence triage | 21 lines, four buckets, cites message ids |
| Meeting preparation | Flags ADR-016 as decided during leave; surfaces three open questions |
| Independent validation | `PlanValidate` invoked once per plan, confirmed in server logs |
| Efficiency | 1 builder call + 1 validator call per plan; 0 rate-limit errors in a clean run |

**Honest limitations:**

- **No live integrations.** §12 is a design, not a shipped connector.
- **Latency is 25–75 seconds** per query. Fine recorded, tolerable live.
- **Token quota is the binding constraint.** Four keys on one Groq account share
  one quota — measured, not assumed.
- **Narration can drift even though tools are exact.** One run described a
  September date as October. Numbers from coded tools are reliable; prose around
  them occasionally is not. Scripted demo questions are safer than improvised.
- **Open-weight models need explicit guarding against phantom tool calls.** The
  stock AAOSA instruction says "return a json block". The gpt-oss models read
  that as an instruction to call a tool literally named `json`, producing
  `{"name": "json", ...}` and a 400 `tool_use_failed` from Groq. Because
  LangChain treats any exception as a reason to fall back, one malformed tool
  call cascaded down the entire chain. The instruction now states explicitly
  that the format describes message text, not a tool call.
- **Write tools must be idempotent.** Retries re-invoke them. Before this was
  fixed, one "meeting at 5pm" produced nine identical calendar entries, each
  reporting conflicts with the previous ones.
- **Capture parses times, not full sentences.** "5pm" and "17:00" work; "the day
  after tomorrow" does not.
- **Captured effort estimates are guesses.** "About an hour" records 60 minutes,
  and nothing yet checks that against reality.
- **Single user.** No multi-tenancy, no auth, no database.
- **Retrieval is keyword-based**, which is correct at this scale and wrong at
  enterprise scale.

---

## Credits

Built on **Neuro SAN / neuro-san-studio**, Cognizant AI Lab, Apache-2.0. The AAOSA
instruction and call substitutions in `registries/cadence.hocon` are reproduced
from that project under Apache-2.0 with attribution.

All scenario data — people, company, projects, messages, decisions and the
knowledge-transfer transcript — is fabricated for demonstration. Any resemblance
to real individuals or organisations is coincidental.
