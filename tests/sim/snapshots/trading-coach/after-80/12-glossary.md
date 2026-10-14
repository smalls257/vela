---
id: glossary
type: initiative-section
title: Glossary
arc42: "§12"
state: inkling
owner: "@solution-lead"
authored: authored
---

# Glossary

One paragraph per term: the term in bold, then what it means in this initiative.

**Paper trading** means practicing a trade with pretend money. In release one a reader places paper trades on stocks from the fixed list, Coach keeps the record of each reader's paper balance and trades, and Brightwater's sandbox only fills the orders. Paper balances are not money, and options are taught as reading only, never paper-traded.

**Pending order** means a paper order that Coach has sent to Brightwater's sandbox and the sandbox has not yet answered. Coach never sends it again, asks the sandbox for its status when it can, and moves the reader's balance only when the order fills at its fill price.

**Ready** is the mark that lets a reader move on to the paper track. The product lead defines it as three graded paper trades on different stocks from the list, plus every lesson written for them. What the CEO means by it is still an open question.

**Signal** is the ML team's model that picks stocks. Its backtest showed 31% a year against 11% for the index, and the later re-run against the S&P 500 total return shows an edge of about 2% a year before costs. It stays out of release one.

**Sandbox** is the set of test accounts Brightwater gives for practice orders. Brightwater provides ten, run by its integration QA engineer, and whether that limit holds for beta readers is an open question.

**Reader ID** means the opaque identifier TickerTalk uses for a signed-in reader. It is not the email. TickerTalk sends it to Coach, and nothing else of its own data, only for a reader who has opted in, and Coach keys the reader's lessons, progress and paper record to it. Whether it stays the same when a reader changes email or device is an open question for the mobile lead.

**Display use** is Quoteline's name for showing its delayed quotes to people, which the license allows. Quoteline says showing quotes inside lessons and valuing paper balances and positions on them are display use. Using its prices to train or run a model is non-display use, which needs an addendum with its own fees under clause 9. Whether filling a paper order at a delayed price counts is not yet answered.
