# AGENTS.md

**Read [`CLAUDE.md`](CLAUDE.md). It is the router for every agent in this
repository, not only for Claude Code.**

This file used to mirror it: same map, same commands, same constraints, kept in
two places by hand. It had already drifted, and it drifted on the subject both
files open by warning about:

> a rule copied into two places goes out of sync without anyone noticing, and
> this project has already paid for that once (a scheduled agent spent weeks
> writing into a file the app no longer read, because its prompt repeated a
> contract instead of pointing at it).

The mirror named agents that no longer exist and a stage of the chain that had
already been retired. A router that is wrong is worse than no router, because
it is followed.

So there is one router now, and this is a pointer to it. If your harness does
not load `CLAUDE.md` on its own, load it before doing anything else: it carries
the map of which document owns which subject, the commands (starting with
`bin/py`, the only interpreter of this project, because `python3` here is a
shell function without the dependencies), and the constraints that are true
everywhere.

One thing worth stating twice, because it is the fastest way to do damage
without noticing: the chain that writes the indicator articles is **one
workflow** (`.claude/workflows/indicatore-lite.js`) over the six `lab-*` agents,
and it publishes to `content/indicators/`, which is the public site. Its
contract is [`lab/README.md`](lab/README.md).
