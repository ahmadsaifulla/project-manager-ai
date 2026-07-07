from services.chatbot.app.database import engine, Base
# This will drop all tables in the correct database and recreate them with the new schema
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("✅ Database tables dropped and recreated successfully with the new tenant schema!")
