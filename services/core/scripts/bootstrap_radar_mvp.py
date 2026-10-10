"""Idempotent bootstrap of one MVP Radar tenant/reader for controlled E2E.

Creates (if missing):
- radar_tenant (slug from env)
- radar_tenant_admin membership for an existing Admin owner email
- radar_reader with a fresh credential_key_id
- appends the secret into RADAR_READER_CREDENTIALS_PATH JSON file

Does not create sources/profiles/destinations — use the headless Admin API so
operators can approve Telegram peers and verify the Radar Bot chat without code
changes.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import uuid
from pathlib import Path

from sqlalchemy import select

from app.db.session import create_session_factory, session_scope
from app.models import AdminUser, RadarReader, RadarTenant, RadarTenantAdmin


async def _run() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    slug = os.environ.get("RADAR_MVP_TENANT_SLUG", "svetlana").strip()
    reader_key = os.environ.get("RADAR_MVP_READER_KEY", "technical-reader").strip()
    owner_email = os.environ.get("RADAR_MVP_OWNER_EMAIL", "").strip().lower()
    cred_path = Path(os.environ.get("RADAR_READER_CREDENTIALS_PATH", "")).expanduser()
    if not owner_email or not str(cred_path):
        raise SystemExit("RADAR_MVP_OWNER_EMAIL and RADAR_READER_CREDENTIALS_PATH are required")

    factory = create_session_factory(database_url)
    try:
        async with session_scope(factory) as session:
            owner = await session.scalar(select(AdminUser).where(AdminUser.email == owner_email))
            if owner is None:
                raise SystemExit(f"Admin user not found: {owner_email}")

            tenant = await session.scalar(select(RadarTenant).where(RadarTenant.slug == slug))
            if tenant is None:
                tenant = RadarTenant(slug=slug)
                session.add(tenant)
                await session.flush()
                print(f"created tenant {tenant.id} slug={slug}")
            else:
                print(f"reusing tenant {tenant.id} slug={slug}")

            membership = await session.get(RadarTenantAdmin, (tenant.id, owner.id))
            if membership is None:
                session.add(
                    RadarTenantAdmin(tenant_id=tenant.id, admin_user_id=owner.id, role="owner")
                )
                print(f"linked owner {owner_email}")

            reader = await session.scalar(
                select(RadarReader).where(
                    RadarReader.tenant_id == tenant.id, RadarReader.reader_key == reader_key
                )
            )
            secret = None
            if reader is None:
                key_id = f"rk_{uuid.uuid4().hex[:16]}"
                secret = secrets.token_urlsafe(32)
                reader = RadarReader(
                    tenant_id=tenant.id,
                    reader_key=reader_key,
                    credential_key_id=key_id,
                )
                session.add(reader)
                await session.flush()
                print(f"created reader {reader.id} key_id={key_id}")
            else:
                key_id = reader.credential_key_id
                print(f"reusing reader {reader.id} key_id={key_id}")
            tenant_id = tenant.id

        if secret is not None:
            cred_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            existing: dict = {}
            if cred_path.exists():
                existing = json.loads(cred_path.read_text(encoding="utf-8"))
            if not isinstance(existing, dict):
                raise SystemExit("credentials file must be a JSON object")
            existing[key_id] = secret
            cred_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
            try:
                cred_path.chmod(0o600)
            except OSError:
                pass
            print(f"wrote credential secret for {key_id} → {cred_path}")
            print("export for Reader:")
            print(f"  RADAR_READER_CREDENTIAL_KEY_ID={key_id}")
            print(f"  RADAR_READER_CREDENTIAL_SECRET={secret}")
        print(f"X-Radar-Tenant-Id: {tenant_id}")
    finally:
        await factory.kw["bind"].dispose()


if __name__ == "__main__":
    asyncio.run(_run())
