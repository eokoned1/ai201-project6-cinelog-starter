# PR Response — Add watchlist feature

## What this feature does

Adds a **watchlist**: a list of films a user wants to watch later, kept
separate from their collection of already-watched films. Users can add a film
to their watchlist, view it (newest first), and each entry tracks when it was
added and whether it is publicly visible.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/watchlist/<user_id>` | Return a user's watchlist, newest first |
| POST | `/watchlist/<user_id>/add` | Add a film to the watchlist (body: `{ "film_id": "<uuid>" }`) |

## Design decisions

- **Default visibility is private (`public=False`).** See Comment 1 below.
- **Default sort order is "date added", newest first.** See Comment 3 below.
- **A film can appear on a watchlist at most once**, enforced both in the
  service layer and by a `(user_id, film_id)` unique constraint. See Comment 2.

## How to test manually, end to end

```bash
pip install -r requirements.txt
python app.py            # starts on http://localhost:5000

# Seed a user and a film via a Python shell, or reuse existing IDs, then:
curl -X POST http://localhost:5000/watchlist/<user_id>/add \
     -H "Content-Type: application/json" -d '{"film_id": "<film_uuid>"}'      # 201

curl -X POST http://localhost:5000/watchlist/<user_id>/add \
     -H "Content-Type: application/json" -d '{"film_id": "<film_uuid>"}'      # 409 (duplicate)

curl -X POST http://localhost:5000/watchlist/<user_id>/add \
     -H "Content-Type: application/json" -d '{"film_id": "does-not-exist"}'   # 404

curl http://localhost:5000/watchlist/<user_id>                                # newest-first list
```

Automated coverage lives in `tests/test_watchlist.py`:
`pytest tests/`.

---

## Responses to review comments

### Comment 1 — Naming convention (`save_to_watchlist`)
> *"Rename to `add_to_watchlist()` and update all call sites."*

Renamed `save_to_watchlist()` → `add_to_watchlist()` to match the project's
`verb_to_noun` service convention (`add_to_collection`, `remove_from_collection`,
`get_collection`). Updated the sole call site in the add endpoint. Confirmed no
remaining references to the old name.

*Addressed in commit `refactor: rename save_to_watchlist to add_to_watchlist`.*

### Comment 2 — Duplicate entries
> *"What happens if a user adds a film that's already on their watchlist?"*

Adding a film that is already on the watchlist now raises
`AlreadyInWatchlistError`, which the endpoint returns as **HTTP 409**, instead of
silently creating a second row. This mirrors `add_to_collection`'s
`AlreadyInCollectionError` behavior. Backed by a `(user_id, film_id)` unique
constraint on `WatchlistEntry` so duplicates can't be created even outside the
service. A regression test asserts only one entry exists after a repeat add.

*Addressed in commit `fix: prevent duplicate films on a watchlist`.*

### Comment 3 — Sort order
> *"I'd prefer 'date added' order rather than alphabetical… let's make a decision and document it."*

**Agreed.** Changed `get_watchlist()` to order by `date_added` descending
(newest first) instead of alphabetically by title. This matches what users
expect from a watchlist (see what you added recently) and is consistent with how
`get_collection()` already sorts.

*Addressed in commit `fix: order watchlist by date added instead of title`.*

### Comment 4 — Default visibility (`public=True`)
> *"I notice watchlists default to `public=True`… add a note explaining your reasoning."*

**Decision: default to private (`public=False`).** Changed the model default and
documented it here.

Reasoning: a *collection* records films a user has already watched — a factual
log. A *watchlist* records **intent**: what someone plans to watch. Intent is
more sensitive (it can reveal interests a user hasn't acted on yet), so the safe
default is to keep it private and let users **opt in** to sharing, rather than
publishing by default and making them discover it after the fact. This follows
privacy-by-default / principle-of-least-surprise. A future PR can add a
visibility toggle on the add endpoint.

*Addressed in commit `feat: default new watchlists to private visibility`.*

### Comment 5 — Missing test for nonexistent `film_id`
> *"Add a test for the case where `film_id` doesn't exist."*

Added `test_add_to_watchlist_nonexistent_film_raises`, which asserts
`FilmNotFoundError` is raised for an unknown UUID — following the pattern in
`test_collection.py`. The new `tests/test_watchlist.py` also covers the happy
path, duplicate handling, sort order, and the private-by-default visibility, per
`CONTRIBUTING.md`'s testing requirements.

*Addressed in commit `test: add watchlist service tests`.*

### Comment 6 — Rebase on `main` (UUID migration)
> *"`main` changed film IDs from integers to UUIDs. Your watchlist code still references integer IDs. Please rebase."*

Rebased this branch onto `main`. As part of the rebase:
- `WatchlistEntry.film_id` is now `db.String(36)` (UUID), matching
  `CollectionEntry.film_id` and `Film.id`.
- Route/request documentation now describes `film_id` as a UUID string, not an
  integer.
- Film lookups use `db.session.get(Film, film_id)`.

The branch history is linear with Conventional Commit messages and no merge
commits, per `CONTRIBUTING.md`.
