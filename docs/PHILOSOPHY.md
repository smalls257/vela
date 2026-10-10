# What this tool is for

## The problem

A big piece of work usually starts as one sentence from someone senior. "One customer, one journey, one account across ferry and rail by next summer." "An AI coach that teaches people to trade one stock or option at a time, and trades for them when they're ready, live by March."

Someone, usually a solution lead, is handed that sentence and told to make it happen. Nobody has said what it means. Several teams, several systems, outside partners, rules and money are involved, and nobody has the whole picture.

What normally happens next is meetings, slides, chat threads and a few documents. It feels like progress. But a few things go wrong almost every time:

- **The important questions get asked too late.** Can we legally use this customer data? Does the partner contract allow it? Who carries the money customers have built up? Is this advice that needs a licence? Nobody meant to skip them; they just never came up. They surface months later, when changing course is expensive.
- **Decisions are made but not written down.** Someone says "yes, let's do that" in a meeting. Three weeks later two people remember it differently.
- **Open questions have no owner.** "We need to check with legal" gets said, and then nobody checks, because nobody was named and no date was set.
- **Beliefs pass for facts.** "The backtest shows 31% a year, so the model works." Nobody asks how the backtest was done.
- **The split between teams is fuzzy.** Each team builds its part, and a piece that falls between two teams gets built twice, or not at all.
- **The written record decays.** Notes describe what people thought in March, not what is true now.

None of this is about lack of skill. A vague goal, many people, and many unknowns produce these failures on their own unless something pushes back.

## What the tool is

It's two things working together.

1. **A shared folder of plain documents** (we call it the vault) kept in git. It holds the goals, the constraints, what exists today, the chosen direction, the apps and how they talk to each other, the open questions, the risks, and finally the work broken into epics. Anyone can read it, and every change goes through a reviewed pull request.
2. **A set of guided working sessions** you run in Claude Code. Each session has one job, such as "find out what exists" or "decide this". It runs that job with you, writes the results into the documents, checks them, and opens the pull request.

You bring the knowledge and the decisions. The tool brings the questions, the discipline and the record keeping.

## How it helps

**It asks the questions people forget.** It keeps a checklist of questions that matter in this kind of work: money owed to customers, data use, partner contracts, regulation, and who runs things out of hours. It also sends separate fresh reviewers over the documents, each looking at one area only. In our test projects, this is how the tool raised things like "the hotel contracts forbid sharing customer data" and "is a trade suggestion legally advice?" before anyone had to remember them.

**Nothing becomes decided by accident.** Only a decision session can mark something decided, and only after reading it back to you and getting a clear yes. You can always overrule this, for example to decide on someone's behalf because a deadline won't wait. The tool lets you, and writes down that you did and why, so the owner can confirm or challenge it later.

**Every open question gets an owner and a date.** "Check with legal" becomes a question with a named person and an ask-by date. When the answer comes back, the tool closes the question and records the answer with where it came from. It asks you first whether you already know before treating anything as waiting on someone else, and it never drafts emails for you to send.

**It keeps facts and beliefs apart.** A fact needs a source you can point to. A belief is recorded as a belief, with what would prove it wrong. When a document and a person disagree, the tool records both sides instead of quietly picking one.

**It splits the work cleanly between teams.** Once the direction is decided, the tool helps you cut it into apps. For each app it records what the app does, what it does not do, what it promises to other apps, and how it behaves when something fails. Each business requirement is then shared out among the apps and the agreements between them, so every requirement has an owner and nothing falls between teams.

**It hands each app over properly.** When an app is ready, the team that will build it takes it with a record of exactly what they accepted. If any of that changes later, the tool can show precisely what moved. The team then does its own technical design in its own repository, starting from that record.

**The documents read as the current state.** Each page opens with plain paragraphs saying what is true now. How it got that way, with the decisions, overrides and options considered, is kept at the bottom, folded away for anyone who wants it.

**It checks itself with code, not just with instructions.** Instructions to an AI are suggestions. So wherever possible the rules are checked by code: a page can't claim to be decided without a recorded decision, every open question needs an owner, and every requirement needs a team. Those checks run on every change.

## What it is not

It doesn't replace the people. It can't decide for you, it won't invent facts, and it doesn't talk to anyone outside the session. It can't make a vague goal clear on its own: it can only make sure the right questions get asked, the answers get written down, and the gaps stay visible until someone closes them.

## A worked example

The trading coach started as the CEO's single sentence. Over a few dozen sessions, the tool did the following:

- **It found what exists today.** There's a news app with 400,000 readers, a broker partner that only covers stocks, a market-data licence that only allows delayed quotes, and a model whose impressive backtest turned out to use hindsight.
- **It surfaced the hard questions.** Is a trade suggestion legally advice? Does "trades for them" count as acting on a customer's behalf, which needs written authority? Can readers' data be used to train the model, or is that a new use that needs their consent?
- **It recorded the decision and the reasons.** Release one is lessons and practice trading on paper only, nothing done on anyone's behalf, and a private demo for the board.
- **It cut the work in two.** That gave a new Coach service and a small change to the news app, each with its agreements written down.
- **It shared out the requirements, split the work into team-sized pieces, and handed Coach to its team lead.** It passed on 15 items to take forward, including the questions still open.
- **The Coach team then wrote its own technical design and a breakdown** of 15 stories and 70 tasks, from that hand-over.

## How we know it works

We test it with simulated projects. A simulated lead plays the person with the vague goal. They know some things, believe some wrong things, and are unaware of some hidden problems we planted. Replies from other people arrive partway through, as they would in real life. After each run we score what the tool uncovered and what it missed, and we read the documents it produced.

Those runs keep finding things to fix. For a long time no session ever wrote the app pages, so no project could reach handoff. Open questions were never closed when answers arrived. The list of questions kept growing faster than anyone could answer it. Each of those is now fixed and checked.

The simulated people aren't perfect either. They sometimes invent replies, so the scores are a guide, not proof. We also haven't yet compared the tool against plain Claude Code with no tool at all, which is the comparison that would really show its value.

## What's still open

- **Thorough versus overwhelming.** The tool can raise a lot of questions. We've cut that back so it raises new ones only about what changed, and doesn't reopen decided things unless something serious comes up. Whether that balance is right is still a judgement call.
- **What "done" means.** A design can be complete with gaps that everyone has accepted, which is different from complete with no gaps. The tool should say which.
- **Who writes.** Should the tool draft the documents from what you say, or mainly interview you and leave the writing to you? Today it drafts, and you review.
