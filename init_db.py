"""Database initialization script."""
from src.models.database import init_db

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")
    print("Tables created: decision_runs")
