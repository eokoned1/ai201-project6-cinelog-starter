# JOURNAL

Project 6 — CineLog watchlist code review. Working branch: `feature/watchlist`.

## Week 8 — Reproduction & solution planning

**Reproduction commit link:** https://github.com/eokoned1/ai201-project6-cinelog-starter/commit/1072d64

**Reproduction summary:**
Added a failing test, `tests/test_watchlist.py::test_duplicate_add_does_not_create_second_row`,
that adds the same film to a user's watchlist twice and asserts only one entry
should exist. On `feature/watchlist` it fails with `found 2 (duplicate was
created silently)` — confirming `save_to_watchlist()` has no dedup guard and
`WatchlistEntry` has no unique constraint. The happy-path test passes.

**PLAN.md link:** https://github.com/eokoned1/ai201-project6-cinelog-starter/blob/feature/watchlist/PLAN.md

**Walkthrough video (recommended):** <!-- optional Loom link -->

**Blockers or open questions:**
- Adding the unique constraint won't apply to an existing `cinelog.db` that
  already holds duplicate rows — planning to document a local DB reset rather
  than add migration tooling. Want to confirm that's acceptable for this project.
- `get_watchlist()` is separately broken (`WatchlistEntry` has no `film`
  relationship → `AttributeError`), so a full "add then view" manual test
  depends on fixing that first. Tracking it as a dependency, not part of this
  bug's scope.
