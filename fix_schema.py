from services.chatbot.app.database import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE tasks DROP COLUMN IF EXISTS tenant_id CASCADE;"))
        conn.execute(text("ALTER TABLE messages DROP COLUMN IF EXISTS tenant_id CASCADE;"))
        conn.commit()
    print("Successfully dropped 'tenant_id' from tasks and messages.")
except Exception as e:
    print(f"Error: {e}")