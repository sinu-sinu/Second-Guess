"""Database models and connection setup."""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, UniqueConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/second_guess.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class DecisionRunDB(Base):
    """Database model for decision evaluation runs."""
    __tablename__ = "decision_runs"

    id = Column(Integer, primary_key=True, index=True)
    decision_id = Column(String, index=True, nullable=False)
    version = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    input_json = Column(Text, nullable=False)  # Stores DecisionInput as JSON
    output_json = Column(Text, nullable=False)  # Stores complete evaluation output as JSON

    # Add unique constraint on (decision_id, version) for version tracking
    __table_args__ = (
        UniqueConstraint('decision_id', 'version', name='uix_decision_version'),
        Index('ix_decision_id_version', 'decision_id', 'version'),
    )


def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
