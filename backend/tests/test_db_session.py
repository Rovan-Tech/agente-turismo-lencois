from app.db.session import engine, get_connect_args, get_pool_args


def test_get_connect_args_requires_ssl_for_asyncpg():
    args = get_connect_args("postgresql+asyncpg://user:pass@host/db")
    assert args == {"ssl": True}


def test_get_connect_args_empty_for_other_drivers():
    args = get_connect_args("sqlite+aiosqlite:///./local.db")
    assert args == {}


def test_pool_args_validate_connection_before_use():
    assert get_pool_args()["pool_pre_ping"] is True


def test_pool_args_recycle_before_neon_closes_idle_connections():
    recycle_seconds = get_pool_args()["pool_recycle"]
    assert 0 < recycle_seconds <= 300


def test_engine_is_built_with_pre_ping():
    assert engine.pool._pre_ping is True
