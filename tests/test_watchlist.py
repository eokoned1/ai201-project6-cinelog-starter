"""
tests/test_watchlist.py — CineLog

Reproduction test for Comment 2 on the watchlist PR:
"What happens if a user adds a film that's already on their watchlist?"

On the current feature/watchlist branch, adding the same film twice silently
creates a SECOND WatchlistEntry row — there is no service-level guard and no
unique constraint on the model. This test documents the expected behavior
(at most one entry per user/film) and therefore FAILS on this branch until the
bug is fixed. It mirrors the happy-path / duplicate structure in
tests/test_collection.py.
"""

import pytest
from app import create_app, db
from models import User, Film, WatchlistEntry
from services.watchlist_service import save_to_watchlist


@pytest.fixture
def app():
    """Create an isolated test app with an in-memory database."""
    app = create_app(config={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def sample_user(app):
    """A user to use in tests."""
    with app.app_context():
        user = User(username="testuser", email="test@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def sample_film(app):
    """A film to use in tests."""
    with app.app_context():
        film = Film(title="Paddington 2", year=2017, genre="Comedy")
        db.session.add(film)
        db.session.commit()
        return film.id


# ── Happy path ───────────────────────────────────────────────────────────────

def test_add_to_watchlist_creates_entry(app, sample_user, sample_film):
    """Adding a valid film should create exactly one WatchlistEntry."""
    with app.app_context():
        save_to_watchlist(user_id=sample_user, film_id=sample_film)

        count = WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).count()
        assert count == 1


# ── Reproduction: duplicate add (Comment 2) ──────────────────────────────────

def test_duplicate_add_does_not_create_second_row(app, sample_user, sample_film):
    """
    REPRODUCTION of Comment 2.

    Adding the same film to the same user's watchlist twice must NOT create a
    second row. Expected: at most one entry (a duplicate add should be rejected).

    Actual on feature/watchlist: the second add succeeds silently and the row
    count is 2 — so this assertion fails, reproducing the bug.
    """
    with app.app_context():
        save_to_watchlist(user_id=sample_user, film_id=sample_film)
        save_to_watchlist(user_id=sample_user, film_id=sample_film)

        count = WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).count()
        assert count == 1, (
            f"expected at most one watchlist entry per user/film, found {count} "
            "(duplicate was created silently)"
        )
