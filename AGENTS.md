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

The mirror carried a map with no row for the workshop that writes the articles,
and named an agent that no longer exists. A router that is wrong is worse than
no router, because it is followed.

So there is one router now, and this is a pointer to it. If your harness does
not load `CLAUDE.md` on its own, load it before doing anything else: it carries
the map of which document owns which subject, the commands (starting with
`bin/py`, the only interpreter of this project), and the constraints that are
true everywhere.
