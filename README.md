# Cadence

### The Second Brain for an Employee

**Built on Cognizant's Neuro AI Multi-Agent Accelerator (neuro-san)**
**Agentic AI Hackathon 2026 · Track 2 — Vibing + Grounding**

---

# 1. The Idea

## Cadence — The Second Brain for an Employee

**It's a guide.
It's a personal assistant.
It's a manager for your workday.**

Cadence is designed around a simple idea:

> **An employee should not have to manually manage the complexity of their entire working life.**

Every working day, employees make dozens of small decisions:

* What should I work on first?
* Can I finish this task before my next meeting?
* What did I miss while I was away?
* Which deadline is becoming critical?
* Should I attend this meeting or can something else take priority?
* When can I actually complete this learning?
* What do I need to know before my next meeting?
* What changed while I wasn't looking?
* What should I focus on right now?

Cadence brings these decisions together into one intelligent work companion.

It doesn't simply answer questions.

**It understands the employee's context, reasons across it, and helps decide what should happen next.**

---

# 2. The Problem We Face Every Day

The problem statement came from a very familiar experience for us as employees.

Imagine you come to the office and start your workday.

Before you even begin, there is already a lot waiting for you.

You may have:

* Tasks assigned to you
* User stories to develop
* Tickets to work on
* A calendar full of meetings
* Client calls
* Meeting preparations
* Documentation
* Approvals and reviews
* Emails and messages
* Follow-ups from previous conversations
* Work that somebody else is waiting for

And then there is another category that is easy to overlook:

## Learning.

In an organization, learning doesn't come from just one place.

We may have:

* Organization-mandated learning
* Project or deliverable-related learning
* Role-related learning
* Development-plan learning
* Manager-assigned learning
* Self-interested learning
* Learning with deadlines
* Learning that becomes important because our project or technology changes

Now imagine trying to keep track of **all of this at the same time**.

We have to remember what is pending.

We have to decide what is important.

We have to understand what is urgent.

We have to look at our calendar.

We have to estimate how much time a task will take.

We have to remember dependencies.

We have to prepare for meetings.

We have to track learning deadlines.

We have to remember what happened while we were away.

And then we have to decide:

> **"So... what should I actually do now?"**

This sounds simple.

In reality, it becomes uncomfortable.

There are days when we miss deadlines.

There are times when we realize too late that a task was much larger than the available time.

There are meetings we become unavailable for because something else took longer.

There are important messages we discover only after the moment has passed.

There are learning deadlines that suddenly become urgent.

And sometimes we spend more time **organizing our work than actually doing it.**

The problem isn't that we don't have systems.

**We have too many systems.**

---

# 3. The Systems Are Disconnected

Today, different parts of our working life live in different systems.

| System                | Knows about                               |
| --------------------- | ----------------------------------------- |
| Calendar              | When we are busy or free                  |
| Task / Project System | What work is pending                      |
| Email                 | Communication                             |
| Teams / Chat          | Conversations and updates                 |
| Learning Portal       | Courses and learning deadlines            |
| Documents             | Knowledge and information                 |
| Meeting Recordings    | Knowledge transfer                        |
| Project Tools         | User stories, work items and dependencies |

Each system does its own job well.

But they don't collectively answer the question that matters most:

> **"Given everything happening in my workday, what should I actually do — and can I realistically do it?"**

The calendar knows **when** we are free.

The task system knows **what** is pending.

The learning platform knows **what** we need to learn.

Communication systems know **what** changed.

Documents contain **knowledge**.

But none of them naturally reason across all of these things.

---

# 4. The Missing Layer

Consider a simple example.

You have:

**90 minutes free before your next meeting.**

Your highest-priority task requires:

**3 hours of uninterrupted work.**

Your calendar says:

> "You're free for 90 minutes."

Your task system says:

> "This is your most important task."

Both systems are correct.

But neither system tells you:

> **"Don't start it. You cannot finish it in this window."**

That missing reasoning layer is what we wanted to build.

---

# 5. Introducing Cadence

## Cadence is the layer between information and action.

Instead of making the employee manually connect information from different systems, Cadence reasons across the employee's context.

```text
                    EMPLOYEE
                        │
                        ▼
                   ┌─────────┐
                   │ CADENCE │
                   └────┬────┘
                        │
       ┌────────────────┼────────────────┐
       │                │                │
       ▼                ▼                ▼
      TIME             WORK           KNOWLEDGE
       │                │                │
    Calendar          Tasks          Decisions
    Meetings          Projects       Documents
    Free time         Dependencies   Transcripts
       │                │                │
       └────────────────┼────────────────┘
                        │
                        ▼
                    REASONING
                        │
                        ▼
                  DECISION / PLAN
                        │
                        ▼
                   ACTION / UPDATE
```

Cadence turns fragmented information into contextual decisions.

It can answer questions such as:

> **What did I miss while I was on leave?**

> **What should I work on today, and when?**

> **Can I actually finish this task today?**

> **What should I prioritize?**

> **Prepare me for my next meeting.**

> **What should I learn next?**

And importantly:

> **"I have a meeting at 5 PM."**

isn't just another question.

It is a change to the employee's world.

Cadence captures it, updates its state, and can change the next plan accordingly.

---

# 6. What Makes Cadence Different?

Cadence is not designed to simply produce an answer.

It is designed to produce an answer that **survives reality**.

That means it considers:

* Available time
* Task duration
* Deep-work requirements
* Interruptibility
* Deadlines
* Dependencies
* Meeting dependencies
* Work blocking other people
* Learning obligations
* Existing commitments
* Sustainable workload

And when something doesn't fit:

## Cadence can say no.

Not:

> "You might want to consider doing this tomorrow."

But:

> **"This cannot be completed today because it requires 180 uninterrupted minutes and your longest available window is only 90 minutes."**

Then it works with what *is* possible.

That is the core idea behind Cadence.

---

# 7. How Cadence Thinks

Cadence is built using **8 agents and 7 deterministic Python tools**, orchestrated through Neuro-SAN.

The agents are responsible for reasoning and specialization.

The tools are responsible for reliable computation and data operations.

### Agents

| Agent             | Responsibility                                                        |
| ----------------- | --------------------------------------------------------------------- |
| **Cadence**       | Frontman — understands the request, routes it and composes the answer |
| **TimeKeeper**    | Time, meetings and available work windows                             |
| **WorkTracker**   | Tasks, priorities, dependencies and competing work                    |
| **LearningCoach** | Learning obligations and deadlines                                    |
| **MemoryKeeper**  | Decisions, history, transcripts and knowledge                         |
| **Capture**       | Converts employee statements into structured records                  |
| **DayPlanner**    | Builds the daily work plan                                            |
| **PlanCritic**    | Independently checks the proposed plan                                |

---

# 8. Agents Reason. Tools Calculate.

This is one of the most important design decisions in Cadence.

We do **not** ask the language model to perform critical calculations.

For example:

> "How many minutes are available between these meetings?"

> "Does a 75-minute task fit into this window?"

> "Which task has the highest priority?"

> "Does this schedule violate a deadline?"

These are deterministic problems.

So Cadence uses Python tools.

The language model decides:

> **What information do I need?**

The tool determines:

> **What are the actual facts?**

And the agent then determines:

> **What does this mean for the employee?**

This creates a clear separation:

```text
              AGENT
        Reasoning / Orchestration
                  │
                  ▼
              PYTHON TOOL
           Facts / Calculation
                  │
                  ▼
              AGENT
          Interpretation
                  │
                  ▼
             EMPLOYEE
```

Every number Cadence presents — free windows, durations, priority scores and constraint violations — comes from deterministic code rather than being invented by the model.

---

# 9. The Planning Loop

Planning is where the system becomes especially interesting.

Cadence doesn't simply ask an LLM:

> "Create a schedule."

Instead:

```text
Employee Request
       │
       ▼
   DayPlanner
       │
       ▼
  PlanBuilder
       │
       │  deterministic scheduling
       ▼
 Proposed Schedule
       │
       ▼
   PlanCritic
       │
       ▼
 PlanValidate
       │
       ▼
 10 Hard Constraints
       │
    ┌──┴──┐
    │     │
   PASS  BLOCK
    │     │
    ▼     ▼
 Answer  Revise
```

The validator checks constraints such as:

1. Work stays within working hours
2. No meeting collisions
3. No overlapping work blocks
4. Deep work receives its full duration
5. Deep work isn't fragmented into unusable windows
6. Deadlines are respected
7. Meeting preparation occurs before the meeting
8. Dependencies are completed in the correct order
9. Mandatory learning is not silently dropped
10. Daily deep-work load remains sustainable

This means the planner isn't allowed to simply produce something that **looks reasonable**.

The plan has to satisfy the rules.

---

# 10. The Application

Now we move from architecture to the employee's experience.

## Scenario 1 — Returning From Leave

The employee asks:

> **"I was on leave Thursday and Friday. What did I miss?"**

Cadence searches the employee's relevant context and identifies what changed during the absence.

It can surface:

* Important decisions
* New assignments
* Changes to project direction
* New deadlines
* People waiting for the employee
* Information that is simply useful to know

Instead of manually searching through messages, the employee gets a contextual summary of what matters.

---

## Scenario 2 — Planning the Day

The employee asks:

> **"I have today. What should I work on, and when?"**

Cadence looks at:

* Calendar
* Free windows
* Task priorities
* Dependencies
* Deadlines
* Meeting preparation
* Learning obligations
* Deep-work requirements

It then constructs a schedule that fits inside the actual day.

---

# 11. The Key Moment — Honest Refusal

Now we give Cadence a request that sounds reasonable:

> **"I need to get AUTH-247 finished today. Plan my day around that."**

AUTH-247 requires:

**180 minutes of uninterrupted work.**

But the employee's calendar contains several meetings.

The longest available uninterrupted window is:

**90 minutes.**

So Cadence does something unusual.

## It refuses.

```text
AUTH-247
Required:       180 minutes
Available:       90 minutes

             ❌ CANNOT FIT
```

But it doesn't stop there.

It explains why.

Then it creates the best possible plan for everything else that **can** fit.

And it recommends moving the impossible work to a time where it can actually be completed.

The important part isn't that Cadence says "no."

The important part is **why it knows to say no.**

---

# 12. The Employee Can Change the World

Cadence is not read-only.

The employee can tell it something new.

For example:

> **"I have a meeting at 5 PM today with the vendor."**

Cadence captures that information.

The calendar state changes.

Now the employee asks:

> **"Replan my day."**

And Cadence produces a different plan.

The available window has changed.

Therefore the plan changes.

```text
OLD WORLD
     │
     ▼
Available time
     │
     ▼
Plan A


Employee adds:
"Meeting at 5 PM"
     │
     ▼
NEW WORLD
     │
     ▼
Available time changes
     │
     ▼
Plan B
```

This is an important distinction.

Cadence isn't just answering questions about data.

**The employee can teach Cadence something, and that changes future decisions.**

---

# 13. Knowledge Becomes Learning

Cadence can also connect knowledge with employee development.

An employee can provide a knowledge-transfer transcript:

> **"Process this KT transcript and update my learning plan."**

Cadence can extract:

* Concepts
* Decisions
* Dependencies
* Risks
* Action items
* Unanswered questions
* Skill gaps

The identified skill gaps can then be written back into the learning plan.

So:

```text
KT Transcript
      │
      ▼
Knowledge Extraction
      │
      ▼
Skill Gaps
      │
      ▼
Learning Plan
      │
      ▼
"What should I learn next?"
```

The answer can therefore change because the system has learned something new.

---

# 14. Why This Is Agentic

Cadence is not simply one LLM answering questions over a database.

A request can involve:

```text
Employee
   │
   ▼
Cadence Frontman
   │
   ├── determines relevant specialists
   │
   ▼
Specialist Agents
   │
   ├── request relevant context
   │
   ▼
Deterministic Tools
   │
   ├── retrieve
   ├── calculate
   ├── score
   ├── build
   └── validate
   │
   ▼
Agent Reasoning
   │
   ▼
Decision
   │
   ├── answer
   ├── create/update state
   └── re-plan
```

Different questions take different paths through the network.

Planning follows a planning workflow.

Memory questions use historical context.

Learning questions use learning intelligence.

Capture requests change system state.

Planning is independently validated before the result is presented.

This is where Neuro-SAN's multi-agent orchestration becomes meaningful to the product rather than simply being present for the sake of the hackathon.

---

# 15. From Prototype to Enterprise

For the hackathon, Cadence uses completely synthetic data.

This allows us to demonstrate the intelligence without exposing employee information or using a real enterprise tenant.

The architecture, however, is designed around a connector boundary.

Today:

```text
                 Cadence
                    │
                    ▼
              Python Tools
                    │
                    ▼
             Synthetic JSON
```

Tomorrow:

```text
                 Cadence
                    │
                    ▼
              Python Tools
                    │
                    ▼
          Connector / Provider Layer
             │       │       │
             ▼       ▼       ▼
          Outlook   Teams   Jira
```

The reasoning layer should not need to know whether its facts came from a JSON file or an enterprise system.

Potential integrations include:

* Outlook / Microsoft Graph
* Microsoft Teams
* Jira
* Enterprise learning platforms
* SharePoint / Confluence
* Meeting transcripts
* Other organizational knowledge sources

The prototype therefore focuses on proving the **intelligence and reasoning layer first**.

---

# 16. What We Have Proven

The prototype demonstrates:

* Multi-agent orchestration through Neuro-SAN
* Context-aware work reasoning
* Deterministic calendar-gap computation
* Deterministic priority scoring
* Constraint-based planning
* Independent plan validation
* Honest refusal when work cannot fit
* Employee-driven state changes
* Automatic replanning
* Return-from-leave intelligence
* Meeting preparation
* Knowledge-to-learning feedback
* Persistent synthetic memory
* Explainable decisions
* Connector-ready architecture

---

# 17. What We Have Not Claimed

This prototype intentionally does **not** claim to be a production enterprise deployment.

Current limitations include:

* Synthetic data rather than live enterprise integrations
* Single-user prototype
* Local JSON persistence
* Keyword and structured retrieval rather than enterprise-scale semantic retrieval
* Estimated task effort rather than learned historical estimates
* Prototype-level authentication and security
* Model latency that is suitable for a recorded demonstration but needs optimization for production

These are engineering steps for the next phase, not hidden assumptions.

---

# 18. The Vision

The long-term vision is larger than a smarter task manager.

We want Cadence to become the employee's **personal work intelligence layer**.

A system that understands:

```text
        WHAT YOU HAVE
             +
        WHAT CHANGED
             +
        WHAT YOU NEED
             +
        WHAT YOU KNOW
             +
        WHAT YOU DON'T KNOW
             +
        HOW MUCH TIME YOU HAVE
             +
        WHAT OTHERS ARE WAITING FOR
             +
        WHAT IS COMING NEXT
             │
             ▼
       PERSONAL WORK
        INTELLIGENCE
             │
             ▼
       WHAT SHOULD I
         DO NEXT?
```

The goal is not to replace the systems employees already use.

The goal is to connect the intelligence between them.

---

# 19. Closing

At the beginning, we started with a simple situation:

You have **90 minutes available**.

You have a task that needs **3 hours**.

Your existing tools can tell you that you are free.

They can tell you that the task is important.

But they cannot tell you that **the task doesn't fit**.

Cadence can.

Because Cadence doesn't just ask:

> **"What do you have to do?"**

It asks:

> **"Given everything happening in your workday, what can you realistically do — and what should happen next?"**

## Cadence doesn't just tell you what you can do.

## **It tells you what you can't do — before you waste the day.**

---

**Built on Neuro SAN / neuro-san-studio · Cognizant AI Lab · Apache-2.0**

All demonstration data is synthetic and fabricated for the hackathon.
