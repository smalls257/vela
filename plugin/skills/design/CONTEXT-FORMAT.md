# CONTEXT.md format

Path: `CONTEXT.md` at the root of the folder the design runs in.

## What it is for

The app's own words. In a vault the initiative's glossary (`12-glossary.md`) owns every term it defines, so `CONTEXT.md` points to it and holds only the terms the app adds: its own data, states and parts that the vault never needed. Two glossaries defining one word drift apart, and then a reader can't tell which one is right. Standalone, `CONTEXT.md` is the whole glossary, seeded from the requirements doc's.

Create it when the first term settles, add each term as it settles, and say so when the code and `CONTEXT.md` disagree.

## Template

~~~markdown
# Project Context

> The <app> design's own terms. The initiative's terms are in the glossary of the <initiative> planning vault (as of <date in words>), which owns them.

## Glossary

### <Term>
**Definition:** <one paragraph in domain language>
**Not to be confused with:** <near-miss terms>
**Examples:** <one or two>

## Boundaries

**This project owns:** <list>
**This project consumes:** <list>
**This project does not concern itself with:** <list>

## Conventions

- <anything that affects how terms or types are named>
~~~

Only terms that mean something in the domain belong here, not class names.

Cite the vault by name and date, "the Heron planning vault (as of October 12)", never by its ID and commit.
