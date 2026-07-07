"""
Seed script: inserts a test tenant into TenantDb and prints its UUID.
Run with: services/chatbot/venv/bin/python seed_tenant.py
"""
import sys
import os
import uuid

# Ensure the project root is on the path so the service package is importable
sys.path.insert(0, os.path.dirname(__file__))

from services.chatbot.app.database import SessionLocal, TenantDb, Base, engine

# Ensure all tables exist before inserting
Base.metadata.create_all(bind=engine)

tenant_id = uuid.uuid4()
tenant = TenantDb(
    id=tenant_id,
    name="Test Bakery",
    subscription_tier="free",
)

db = SessionLocal()
try:
    db.add(tenant)
    db.commit()
    print("\n✅  Tenant seeded successfully!")
    print(f"   Name             : {tenant.name}")
    print(f"   Subscription tier: {tenant.subscription_tier}")
    print(f"\n   ➡  X-Tenant-ID: {tenant_id}\n")
except Exception as e:
    db.rollback()
    print(f"❌  Error seeding tenant: {e}")
    sys.exit(1)
finally:
    db.close()
