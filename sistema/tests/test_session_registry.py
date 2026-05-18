import time
import threading
from unittest.mock import MagicMock
from app.ai.graph.session_registry import SessionRegistry


def _make_db():
    return MagicMock(name="db")


def _make_user():
    return MagicMock(name="user", empresa_id=42)


def test_register_and_get():
    db = _make_db()
    user = _make_user()
    SessionRegistry.register("thread-1", db=db, current_user=user)
    result = SessionRegistry.get("thread-1")
    assert result is not None
    got_db, got_user = result
    assert got_db is db
    assert got_user is user


def test_get_unknown_thread_returns_none():
    result = SessionRegistry.get("nao-existe-xyz")
    assert result is None


def test_ttl_expiry():
    db = _make_db()
    user = _make_user()
    SessionRegistry.register("thread-ttl", db=db, current_user=user, ttl_seconds=0)
    time.sleep(0.01)
    result = SessionRegistry.get("thread-ttl")
    assert result is None


def test_overwrite_existing():
    db1 = _make_db()
    db2 = _make_db()
    user = _make_user()
    SessionRegistry.register("thread-ow", db=db1, current_user=user)
    SessionRegistry.register("thread-ow", db=db2, current_user=user)
    got_db, _ = SessionRegistry.get("thread-ow")
    assert got_db is db2


def test_thread_safe():
    errors = []
    def _worker(thread_id):
        try:
            db = _make_db()
            user = _make_user()
            SessionRegistry.register(thread_id, db=db, current_user=user)
            result = SessionRegistry.get(thread_id)
            assert result is not None
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=_worker, args=(f"t-{i}",)) for i in range(20)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert not errors
