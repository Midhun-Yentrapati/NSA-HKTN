<<<<<<< HEAD
# Cadence

**A work-fit reasoning system built on Cognizant's Neuro AI Multi-Agent Accelerator (neuro-san).**

Submitted to the Agentic AI Hackathon, Track 2 (Vibing + Grounding), September 2026.

---

## 1. The one-sentence version

Your calendar knows *when* you are free. Your task list knows *what* is pending.
**Nothing knows whether the free window actually fits the work.** Cadence does — and
it refuses to hand you a plan that does not survive checking.

---

## 2. The problem

An employee's working life is spread across systems that do not talk to each other:
mail, chat, calendar, tickets, documents, a learning portal, knowledge-transfer
recordings. Each one is individually fine. Together they produce a specific,
daily failure:

> You have ninety minutes free. You have a three-hour task that matters most.
> Every tool you own will happily let you start it.

Calendars show availability but know nothing about the shape of your work. Task
lists rank by due date but know nothing about your day. Learning portals list
courses but know nothing about either. The employee is left doing the integration
in their head, every morning, badly.

Cadence closes that gap. It reasons about **fit** — whether a specific piece of
work can actually be done in a specific window, given its size, its
interruptibility, its dependencies and what else is competing for the day.

---

## 3. Who it is for

**Primary user: an individual knowledge worker.** The demonstration persona is a
senior software engineer, but nothing in the reasoning is engineering-specific.
The task schema (effort, deep-work flag, interruptibility, dependencies,
deadlines) describes consultants, analysts, designers and managers equally well.

**Situations where it earns its keep:**

- Returning from leave to an inbox and a changed project
- Inheriting a system or a set of responsibilities from someone who is leaving
- Any day where mandatory training, project deadlines and meetings collide
- Preparing for a meeting whose context is scattered across six months of history

**Who it is *not* for:** it is a personal reasoning layer for one person's work.
It is not a team project-management tool, and it does not schedule other people.

---

## 4. What it can do

Eight capabilities, each reached by plain language - no commands, no syntax:

### 4.1 "What are my free windows today?" — time fit
Computes exact free windows between meetings and states the longest uninterrupted
block. Critically, it will tell you when a task **cannot** fit rather than
pretending it can.

### 4.2 "I have today — what should I work on, and when?" — planning
Produces a concrete, block-by-block schedule drawn from the backlog, the learning
plan and the actual free windows, with a one-line justification for every block.

### 4.3 "I need to finish X today" — the honest refusal
When asked for something impossible, Cadence says so with the arithmetic, plans
everything else that *does* fit, and recommends what to do instead. This is the
capability most systems lack: they generate a plausible plan and let you discover
the problem at 4 pm.

### 4.4 "What did I miss?" — return-from-absence triage
Reads only what arrived during the absence window and groups it into what needs
action today, what needs action this week, what is informational, and what was
newly assigned — plus who is now waiting on you.

### 4.5 "Prepare me for the 3 pm review" — cross-source briefing
Assembles the meeting's purpose, the prior decisions and their rationale, what
changed recently, the open questions nobody has answered, and what you personally
are on the hook for. Flags anything decided while you were away.

### 4.6 "Process this KT transcript" — knowledge into learning
Extracts concepts, decisions, dependencies, risks, action items and unanswered
questions from a knowledge-transfer session, then **writes the resulting skill
gaps back into your learning plan**. The system's answer to "what should I learn
next?" changes as a result. Memory that only reads is a search box; memory that
writes is a second brain.

### 4.7 "I have a meeting at 5" — capture from the user
The employee is the most reliable connector there is. Anything they mention in
passing is recorded into the same context everything else reasons over:

- *"I have a meeting at 5pm today"* becomes a calendar event — times like "5pm",
  "17:00" and "5:30 pm" are all understood, and clashes with existing meetings
  are reported
- *"A new course was assigned, due 30 September"* becomes a learning item, with
  the daily pace needed to finish it
- *"I need to review the migration doc, about an hour"* becomes a task, with
  effort estimated from the phrasing

Captured items take effect immediately. Add a 5 PM meeting and re-plan, and the
last window of the day shrinks — work that no longer fits is moved out of the
plan and something shorter takes its place.

### 4.8 Explainability, throughout
Every ranking decomposes into named components with numbers, and every factual
claim cites a record id. When Cadence says one task outranks another, it shows
the arithmetic rather than asserting a preference.

---

## 5. How it helps, concretely

Taking the demonstration scenario: an engineer returns from two days of leave to
a project whose architecture changed without them, a release pulled forward by a
week, two newly assigned tickets, a knowledge-transfer recording to absorb, and a
meeting at 3 pm they are presenting at but have not prepared for.

Without Cadence, reconstructing that situation is most of a morning.

With Cadence:

- **"What did I miss?"** surfaces the four things that actually changed, in seconds
- **"What should I work on?"** identifies that the position paper must come first —
  not because it is loudest, but because two other tasks depend on it *and* it is
  needed for a meeting today
- **"I need to finish the implementation today"** gets refused with numbers, before
  the day is wasted discovering it
- **"Prepare me for the 3 pm"** assembles six months of decisions into a briefing
- **The KT recording** stops being a 40-minute video nobody rewatches and becomes
  three specific skill gaps on the learning plan

The measurable claim is not "saves N hours." It is narrower and more defensible:
**the system will not hand you a schedule that violates a constraint you care
about**, and it can explain every ordering decision it makes.

---

## 6. Architecture

### 6.1 Shape

```
                     Cadence  (front man, AAOSA routing)
                              |
   +----------+---------+-----+-----+---------+-----------+
   |          |         |           |         |           |
TimeKeeper WorkTracker Learning  Memory    Capture    DayPlanner
   |          |        Coach     Keeper       |           |
   |          |         |           |         |       PlanBuilder
   |          |         |           |         |           |
   |          |         |           |         |       PlanCritic
   +----------+---------+-----------+---------+-----------+
                              |
                deterministic coded tools (Python)
  CalendarGaps  ContextQuery  PriorityScore  PlanBuilder
  PlanValidate  Capture  MemoryWrite
                              |
                    synthetic data (JSON on disk)
```

Eight agents, seven coded tools.

### 6.2 The eight agents

| Agent | Responsibility |
|---|---|
| **Cadence** | Front man. Routes each inquiry to the specialists that can contribute, using the AAOSA pattern, then composes one answer |
| **TimeKeeper** | Calendar, free windows, whether a given piece of work fits |
| **WorkTracker** | Backlog, tickets, mail, blocking relationships, ranking and its justification |
| **LearningCoach** | Learning obligations across all five origin types, and the trade-offs between them |
| **MemoryKeeper** | Decisions and their rationale, meeting history, transcripts, meeting preparation |
| **Capture** | Turns something the employee says into a stored meeting, task or learning item |
| **DayPlanner** | Builds a schedule with the planner tool, has it independently checked, explains it |
| **PlanCritic** | Reviews a proposed schedule against hard constraints and returns specific objections |

### 6.3 The central design decision: tools produce facts, agents reason over facts

Every number in the system comes from deterministic Python, never from a language
model. This is deliberate and it is the reason the system can be trusted:

- LLMs are unreliable at clock arithmetic. "How many minutes between 10:15 and
  11:30, and does a 45-minute task fit?" is exactly the kind of question models
  get subtly wrong.
- A hallucinated calendar is worse than no calendar.
- Deterministic scoring means the same inputs always produce the same ranking,
  which makes the system testable and the demo reproducible.

So `CalendarGaps` computes windows, `PriorityScore` computes rankings with a
component breakdown, and `PlanValidate` checks constraints — all in Python. The
agents decide *what to ask*, interpret results, weigh trade-offs and explain
themselves. Every agent carries an explicit instruction: **never state a fact a
tool did not return.**

### 6.4 The evaluation loop

This is the part that distinguishes Cadence from a chatbot over a database.

```
  DayPlanner
      |
      v
  PlanBuilder   (Python: constructs a constraint-satisfying schedule)
      |
      v
  PlanCritic --> PlanValidate   (Python: independently re-checks it)
      |
      +-- clean?    --> plan is presented, with what did not fit and why
      +-- blockers? --> reported honestly rather than hidden
```

**Why construction, not argument.** The first version had a language model
propose schedules and the critic reject them until one passed. It did not
converge: a single planning request produced 39 critic round-trips and timed out
without ever answering. Constructing the schedule in Python is instant and
correct by design, and the critic then validates *once*. Same guarantee,
a fraction of the calls, and it actually finishes — 57 seconds against a hang.

The critic is not decoration. It is a genuinely independent check: `PlanBuilder`
and `PlanValidate` are separate implementations, so a bug in the builder is
caught rather than rubber-stamped.

`PlanValidate` enforces ten families of constraint:

1. Blocks fall inside working hours
2. No collision with a meeting
3. No collision with another planned block
4. Deep work is allocated its full duration and is never split across gaps
5. Deep work is not fragmented below a viable block size
6. Nothing is scheduled to finish after its deadline
7. **Meeting preparation finishes before the meeting it prepares for**
8. Prerequisites are scheduled before the work that depends on them
9. Mandatory learning near its deadline is not silently dropped
10. Daily deep-work load stays within a sustainable ceiling

Constraint 7 is the one that catches the mistake humans and language models both
make: scheduling the preparation for a 3 pm review into the 4 pm slot.

The critic holds no opinions. It reports what the validator found, and it is
instructed not to soften a blocker or approve a plan that has one.

### 6.5 Adaptive activation, and where we deliberately turned it off

AAOSA lets the front man poll candidate agents so that a question only wakes the
agents that can contribute — genuine adaptive orchestration rather than a fixed
pipeline.

We use it at the top level only. `DayPlanner` and `PlanCritic` run as a fixed
chain, because planning is a *workflow*, not a routing decision. Polling coded
tools to ask whether they are "relevant" costs real latency and quota for no
information. Measured effect: an early build woke all five specialists for a
planning request and exceeded the 300-second execution ceiling. After the change,
the same request completes in around 140 seconds.

---

## 7. The data

All data is **synthetic**. No personal data, no real organisations, no
confidential material — consistent with the hackathon's data rules.

### 7.1 The scenario

One coherent storyline, so that cross-source reasoning has something real to
reason across:

| Date | Event |
|---|---|
| 18 Aug | ADR-014: Redis chosen for the Helix session store; PostgreSQL rejected on read latency |
| 24 Aug | Identity provider announces refresh-token lifetime dropping 90 days to 14, effective 18 Sep |
| 2 Sep | The outgoing service owner records a 40-minute knowledge-transfer session and rotates off |
| **3–4 Sep** | **The employee is on leave.** The architecture changes without them; the release is pulled forward a week; two tickets are assigned |
| 7 Sep | **Today.** Architecture review at 3 pm, which they are presenting at, unprepared |

The scenario is constructed so the constraints are real rather than convenient:
no free window on the demo day exceeds 90 minutes, while the most urgent
implementation task needs 180 uninterrupted minutes. The system cannot schedule
it, and has to say so.

### 7.2 Files

| File | Contents |
|---|---|
| `persona.json` | The employee, working preferences, colleagues, leave dates, pinned demo date |
| `calendar.json` | 13 events across three weeks |
| `tasks.json` | 12 tasks with effort, deep-work flag, interruptibility, dependencies, blocking relationships |
| `learning.json` | Learning items across all five origin types |
| `messages.json` | 15 mail and chat messages, weighted to the leave window |
| `decisions.json` | 5 decision records with rationale and rejected alternatives |
| `transcripts/auth_kt.txt` | The knowledge-transfer transcript |
| `learning.seed.json` | Pristine copy, so the demo can be reset between runs |

### 7.3 Why the task schema matters

The intelligence lives in these fields:

```json
{
  "effort_minutes": 180,
  "deep_work": true,
  "interruptibility": "low",
  "deadline": "2026-09-16T17:30",
  "blocks": ["Helix release train 2026-09-11"],
  "depends_on": ["AUTH-249"],
  "meeting_dependency": null
}
```

A task list with only titles and due dates cannot support fit reasoning. These
fields are what make "this does not fit today" a derivable conclusion rather than
a guess.

---

## 8. Requirements

### 8.1 Software

- **Python 3.13** (developed against 3.13.4)
- **neuro-san / neuro-san-studio**, installed in a virtual environment
- No additional packages beyond the neuro-san requirements. Groq is reached
  through its OpenAI-compatible endpoint using neuro-san's built-in `openai`
  provider class, so no provider-specific library is needed.

### 8.2 An LLM API key

At least one of:

| Provider | Env var | Notes |
|---|---|---|
| **Groq** (required) | `GROQ_API_KEY_1` ... `GROQ_API_KEY_4` | Reached via its OpenAI-compatible endpoint. Roughly 1,000 requests/day per key, sub-second tool calls |
| Google Gemini | `GEMINI_API_KEY` | Last-resort fallback. The free tier is **20 requests per day per model**, which a single planning run exceeds |

**Keys must come from separate accounts.** Four keys from one Groq account share
one quota - measured directly, not assumed. Four keys from four accounts give four
independent daily quotas.

**Load spreading, not just failover.** The four keys are declared as a *peer
group* (a nested list inside `fallbacks`), which neuro-san shuffles, so agents
start on different keys rather than all draining key 1. Escalation runs: random
key on the strong model, then any surviving key in that group, then the light
model across all four keys - eight targets in total. Gemini was removed: its
20-requests/day free tier is spent immediately, and its client's internal backoff
stalled any request that reached it for 30-60 seconds.

**Sizing note, learned the hard way:** a multi-agent network is call-hungry. One
planning request costs 15–25 model calls once routing, planning, critique and
revision are counted. Provider choice is an architectural constraint here, not an
afterthought — an early build on Gemini alone logged 93 rate-limit refusals and
could not complete a single planning run.

### 8.3 Layout assumption

```
NSA_HKTN/
  .virenv/             the Python environment
  neuro-san-studio/    the framework, used read-only and never modified
  My-Project/          this project
```

---

## 9. Running it

### 9.1 Configure

Create `My-Project/.env` (already gitignored — never commit it):

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

`ns run` reads this file from the working directory, so those first three lines
are what make the `cadence` network appear in the agent list.

### 9.2 Start

```powershell
.\run_cadence.ps1
```

Then open the nsflow UI at **http://localhost:4174** and select the `cadence`
network. The neuro-san server runs on port 8081.

Non-default ports are used deliberately so a default neuro-san instance on
8080/4173 can keep running alongside.

### 9.3 Ask it something

From the nsflow UI, or from the command line:

```bash
python scripts/ask.py "I have today - what should I work on, and when?"
python scripts/ask.py --trace "What did I miss?"
```

### 9.4 Reset between rehearsals

Transcript ingestion writes to disk on purpose. To return to a known state:

```bash
python scripts/reset_demo.py
```

### 9.5 How it stays out of the framework checkout

`neuro-san-studio` is treated as strictly read-only. Three mechanisms:

- `AGENT_MANIFEST_FILE` and `AGENT_TOOL_PATH` point at this project's own
  `registries/` and `cadence_tools/`
- The agent network HOCON is **self-contained** — the AAOSA substitutions are
  reproduced locally under Apache-2.0 attribution rather than included from the
  framework
- The server runs with `My-Project` as its working directory, so logs, thinking
  traces and `.env` loading all stay here

`git status` inside the framework checkout stays empty.

Two integration details worth knowing if you adapt this: the project root must be
on `PYTHONPATH`, because neuro-san derives a module prefix from the tool path; and
the tool package is named `cadence_tools`, **not** `coded_tools`, because the
latter would collide with the framework's own package on the import path.

---

## 10. Demonstration script

Five minutes, four beats. Reset first.

**Beat 1 — return from absence.**
> "I was on leave Thursday and Friday. What did I miss?"

Establishes the situation and shows cross-source triage.

**Beat 2 — planning, with the critic visible.**
> "I have today — what should I work on, and when?"

Watch the nsflow graph: the front man routes to DayPlanner, which calls the
calendar and scoring tools, then submits to PlanCritic before answering.

**Beat 3 — the honest refusal. The strongest moment.**
> "I need to get AUTH-247 finished today. Plan my day around that."

The system refuses with arithmetic — 180 uninterrupted minutes required, 90
available — schedules everything else, and recommends moving it. Most systems
would produce a confident, wrong plan.

**Beat 4 - the employee tells it something.**
> "I have a meeting at 5pm today with the vendor."
> "Now replan my day."

The meeting is recorded, the last free window shrinks, and a task that no longer
fits drops out of the plan while a shorter one takes its place. This is what
makes it a second brain rather than a report: it takes input, not only queries.

**Beat 5 - memory that changes.**
> "What should I learn next?" — note the answer.
> "Process Devika's KT transcript and update my learning plan."
> "What should I learn next?" — *the answer has changed.*

Asking the identical question twice and getting a different answer, because the
system learned something, is the closing point.

**Presenter's note:** responses take roughly 25-75 seconds. Run
`python scripts/reset_demo.py` before each rehearsal, since captured meetings and
extracted learning items persist to disk by design.

---

## 11. Judging criteria, addressed

| Criterion | How Cadence addresses it |
|---|---|
| **Problem relevance** | Fragmentation of an employee's working context is universal. The specific gap — nothing reasons about whether work fits available time — is real and unserved |
| **Innovation** | Fit reasoning rather than listing. An adversarial critic that can reject its own system's plan. Memory that writes back rather than only retrieving |
| **Effective use of Neuro SAN** | AAOSA adaptive routing where it pays, fixed workflow where it does not. Eight agents, seven coded tools, an independent validation step, per-agent model assignment, and fallbacks fanned across four API keys |
| **Technical implementation** | Deterministic tools for all arithmetic; agents constrained to tool-derived facts. Ten constraint families. Unit-tested tools, self-contained configuration, reproducible pinned demo date |
| **Impact potential** | The connector abstraction means the reasoning layer is independent of where data comes from — mock today, enterprise systems later, no change to the agents |
| **Presentation** | Four-beat script built on one coherent scenario, with the strongest beat being the system declining an impossible request |

---

## 12. Honest limitations

Stated plainly, because a demo that oversells is worse than one that does not.

- **The data is synthetic and there are no live integrations.** The connector
  abstraction is an architectural argument, not a shipped integration. Nothing
  here has touched Outlook, Teams or Jira.
- **Latency is 25-75 seconds per query.** Fine for a recorded demo, tolerable
  live if you narrate while it thinks.
- **Narration can drift even though tools are exact.** In one run the model
  described a September date as October. Coded-tool numbers are reliable; prose
  around them occasionally is not. Scripted questions are safer than improvised.
- **Learning extraction needed tuning in both directions.** An early version wrote
  twenty learning items from one transcript; over-correcting made it write zero.
  The constraint now has both a floor and a ceiling.
- **Capture parses times, not full sentences.** "5pm" and "17:00" work; "the day
  after tomorrow" does not. The agent fills in dates and durations and states
  what it assumed, but relative dates beyond today are a gap.
- **Effort estimates for captured tasks are guesses.** When you say "about an
  hour" it records 60 minutes. Nothing yet checks that against what the task
  actually took.
- **Single-user by design.** No multi-tenancy, no auth, no persistence layer
  beyond JSON files.
- **Task metadata is assumed.** Real backlogs rarely carry effort estimates or
  deep-work flags. In production these would need to be inferred or learned — that
  is real work, not a detail.

---

## 13. Where it would go next

1. **Real connectors** behind the existing abstraction — Microsoft Graph for
   calendar and mail first, since that is where the value concentrates.
2. **Learned effort estimation.** Track actual time against estimates and correct
   the model over time, so fit reasoning improves with use.
3. **Meeting-load negotiation.** Cadence can already see that no window is long
   enough for critical work. The next step is proposing which meeting to move.
4. **Team-level fit.** Extending blocking relationships across people to spot when
   one person's schedule is the critical path for several others.

---

## 14. Project layout

```
My-Project/
  README.md                     this document
  run_cadence.ps1               launcher
  .env                          API keys (gitignored, never committed)
  .gitignore
  registries/
    manifest.hocon              registers the network
    cadence.hocon               the agent network: 7 agents + 5 coded tools
  cadence_tools/
    cadence/
      cadence_store.py          shared data access
      calendar_gaps.py          free-window arithmetic
      context_query.py          unified retrieval across all sources
      priority_score.py         explainable ranking
      plan_builder.py           deterministic schedule construction
      plan_validate.py          the independent constraint checker
      capture.py                records what the employee tells the system
      memory_write.py           learning-plan write-back
      data/                     the synthetic corpus, plus *.seed.json
  scripts/
    ask.py                      command-line client
    reset_demo.py               restore pre-demo state
  logs/                         server and thinking traces
```

---

## 15. Credits and licence

Built on **Neuro SAN / neuro-san-studio**, Cognizant AI Lab, Apache-2.0.
The AAOSA instruction and call substitutions in `registries/cadence.hocon` are
reproduced from that project under Apache-2.0 with attribution.

All scenario data — people, company, projects, messages, decisions and the
knowledge-transfer transcript — is fabricated for demonstration. Any resemblance
to real individuals or organisations is coincidental.
=======
# NSA-HKTN
Neuro San AI Hackathon- Cadence
>>>>>>> e85c639400a70bdc14e52a8bcf26fc092e5a2605
