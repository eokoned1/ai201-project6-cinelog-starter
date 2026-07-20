# Solution plan

**Issue:** Comment 2 on the watchlist PR — "What happens if a user adds a film
that's already on their watchlist?"
(feature/watchlist branch of `eokoned1/ai201-project6-cinelog-starter`)

### Understand

**Root cause.** `save_to_watchlist()` in `services/watchlist_service.py` looks
up the film, then unconditionally constructs and commits a new
`WatchlistEntry`. There is no check for an existing `(user_id, film_id)` pair,
and the `WatchlistEntry` model in `models.py` has no unique constraint on that
pair. So nothing — in the service *or* the database — stops a second identical
row from being created.

**Expected vs. actual.**
- *Expected:* a user's watchlist holds each film at most once. Re-adding a film
  already on the list is rejected (no new row), and the API surfaces that as a
  conflict rather than a fresh 201.
- *Actual:* the second add succeeds silently and returns 201. The watchlist now
  contains two entries for the same film. Reproduced via
  `tests/test_watchlist.py::test_duplicate_add_does_not_create_second_row`,
  which finds a row count of 2 where 1 is expected.

This is the exact gap the existing collection feature already closes:
`add_to_collection()` raises `AlreadyInCollectionError` and
`CollectionEntry` carries a `unique_user_film_collection` constraint. The
watchlist should mirror that.

### Map

Files I expect to touch:

- `models.py` — `WatchlistEntry`: add a `UniqueConstraint("user_id", "film_id")`
  (mirroring `CollectionEntry.__table_args__`).
- `services/watchlist_service.py` — define `AlreadyInWatchlistError`; in
  `save_to_watchlist()`, query for an existing entry before insert and raise it.
- `routes/watchlist/watchlist.py` — catch `AlreadyInWatchlistError` in
  `add_film()` and return HTTP 409.
- `tests/test_watchlist.py` — flip the reproduction test to assert the new
  behavior (raises + row count stays 1); add coverage for a distinct film still
  being addable.

Reference (do not edit): `services/collection_service.py`,
`tests/test_collection.py` — the established pattern to match.

### Plan

1. **Model constraint.** Add
   `db.UniqueConstraint("user_id", "film_id", name="unique_user_film_watchlist")`
   to `WatchlistEntry.__table_args__` so duplicates are impossible even outside
   the service layer.
2. **Service guard.** Add an `AlreadyInWatchlistError` exception. In
   `save_to_watchlist()`, after the film-exists check, query
   `WatchlistEntry.query.filter_by(user_id=..., film_id=...).first()` and raise
   if one exists — before adding/committing.
3. **Route handling.** In `add_film()`, wrap the service call and translate
   `AlreadyInWatchlistError` → `409`, keeping the existing `FilmNotFoundError`
   → `404` behavior.
4. **Tests.** Update `test_watchlist.py`: the duplicate test now asserts
   `AlreadyInWatchlistError` is raised and the row count stays 1; keep the
   happy-path test green.
5. **Verify.** Run `pytest tests/` (all green) and manually exercise
   add → add-again (409) → view via curl against a seeded film.

### Inputs & outputs

- **Input:** a `POST /watchlist/<user_id>/add` with `{ "film_id": "<id>" }`, or
  a direct `save_to_watchlist(user_id, film_id)` call.
- **Output / change:** first add → one `WatchlistEntry`, HTTP 201. Repeat add
  of the same film → no new row, `AlreadyInWatchlistError` raised, HTTP 409.
  A different film for the same user still adds normally.

### Risks & unknowns

- **Constraint on a table that already has dup rows.** `db.create_all()` won't
  add a constraint to an existing `cinelog.db` that already contains duplicate
  watchlist rows. For local dev the fix is to delete `cinelog.db` and recreate;
  I'll note this rather than write a migration (the project has no migration
  tooling).
- **Race condition.** Two concurrent adds could both pass the service-level
  `.first()` check before either commits. The DB unique constraint is the real
  backstop; the service check is for a clean error message. I should confirm the
  route surfaces the `IntegrityError` path sanely if the constraint fires.
- **Interaction with Comment 6 (UUID rebase).** This branch still uses integer
  `film_id`. If I rebase onto `main` (UUIDs) the constraint/guard logic is
  unchanged, but the tests' `film_id` fixtures change type. Keeping this fix
  independent of the rebase where possible.
- **`get_watchlist()` is separately broken** (`WatchlistEntry` has no `film`
  relationship, so viewing a watchlist raises `AttributeError`). Out of scope
  for this bug, but it means an end-to-end "add then view" manual test needs
  that relationship added first — noting it as a dependency.

### Edge cases

- Same user, same film, added twice → rejected (the core case).
- Same film added by two *different* users → both allowed (constraint is on the
  pair, not on `film_id` alone).
- Same user adds two *different* films → both allowed.
- Adding a film that doesn't exist → still `FilmNotFoundError` / 404 (unchanged).
- Duplicate created before the constraint existed → surfaced at recreate time;
  documented as a local-DB reset step.
