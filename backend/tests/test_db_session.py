from app.db.session import get_connect_args


def test_get_connect_args_requires_ssl_for_asyncpg():
    args = get_connect_args("postgresql+asyncpg://user:pass@host/db")
    assert args == {"ssl": True}


def test_get_connect_args_empty_for_other_drivers():
    args = get_connect_args("sqlite+aiosqlite:///./local.db")
    assert args == {}
