"""Non-destructive schema rollback proof on the dedicated disposable DB only."""
import asyncio
import os
from pathlib import Path
import uuid
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from app.core.settings import get_settings
from app.db.session import create_session_factory, session_scope


def test_intake_upgrade_rollback_preserves_legacy_and_refuses_new_data_loss(monkeypatch):
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("dedicated test PostgreSQL required")
    assert url.startswith("postgresql+asyncpg://") and "ai_my_time_test" in url
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    uid, did, cid, rid = (uuid.uuid4() for _ in range(4))

    async def sql(statement, params=None):
        factory = create_session_factory(url)
        try:
            async with session_scope(factory) as s:
                rows = await s.execute(text(statement), params or {})
                return rows.all() if rows.returns_rows else None
        finally:
            await factory.kw["bind"].dispose()

    try:
        asyncio.run(sql("TRUNCATE users CASCADE"))
        command.downgrade(config, "20261010_26")
        asyncio.run(sql("INSERT INTO users(id) VALUES (:id)", {"id": uid}))
        asyncio.run(sql("INSERT INTO diagnostic_sessions(id,user_id,status,input_snapshot_json) VALUES (:id,:uid,'diagnostic_completed','{}')", {"id": did, "uid": uid}))
        asyncio.run(sql("INSERT INTO consultation_requests(id,user_id,diagnostic_session_id) VALUES (:id,:uid,:did)", {"id": cid, "uid": uid, "did": did}))
        command.upgrade(config, "head")
        assert asyncio.run(sql("SELECT diagnostic_session_id FROM consultation_requests WHERE id=:id", {"id": cid})) == [(did,)]
        command.downgrade(config, "20261010_26")
        assert asyncio.run(sql("SELECT diagnostic_session_id FROM consultation_requests WHERE id=:id", {"id": cid})) == [(did,)]
        command.upgrade(config, "head")
        asyncio.run(sql("INSERT INTO lead_flow_runs(id,user_id,kind,state,source_json,answers_json) VALUES (:id,:uid,'ai_assistant','work_setup','{}','{}')", {"id": rid, "uid": uid}))
        with pytest.raises(RuntimeError, match="New intake data exists"):
            command.downgrade(config, "20261010_26")
        assert asyncio.run(sql("SELECT version_num FROM alembic_version")) == [("20261015_27",)]
        assert asyncio.run(sql("SELECT id FROM lead_flow_runs")) == [(rid,)]
        assert asyncio.run(sql("SELECT diagnostic_session_id FROM consultation_requests WHERE id=:id", {"id": cid})) == [(did,)]
    finally:
        command.upgrade(config, "head")
        get_settings.cache_clear()
