"""Langfuse client initialization and configuration."""
import os
from typing import Optional
from langfuse import Langfuse
from dotenv import load_dotenv

load_dotenv()


class LangfuseClient:
    """Singleton Langfuse client for observability."""

    _instance: Optional[Langfuse] = None
    _enabled: bool = True

    @classmethod
    def get_client(cls) -> Optional[Langfuse]:
        """
        Get or create Langfuse client instance.

        Returns:
            Langfuse client if enabled and configured, None otherwise
        """
        if not cls._enabled:
            return None

        if cls._instance is None:
            # Check if Langfuse is configured
            public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
            secret_key = os.getenv("LANGFUSE_SECRET_KEY")
            host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

            if not public_key or not secret_key:
                print("[WARNING] Langfuse not configured. Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY.")
                cls._enabled = False
                return None

            try:
                cls._instance = Langfuse(
                    public_key=public_key,
                    secret_key=secret_key,
                    host=host
                )
                print(f"[INFO] Langfuse client initialized: {host}")
            except Exception as e:
                print(f"[WARNING] Failed to initialize Langfuse: {e}")
                cls._enabled = False
                return None

        return cls._instance

    @classmethod
    def disable(cls):
        """Disable Langfuse tracing."""
        cls._enabled = False

    @classmethod
    def enable(cls):
        """Enable Langfuse tracing."""
        cls._enabled = True

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if Langfuse is enabled."""
        return cls._enabled and (cls._instance is not None or cls.get_client() is not None)


# Convenience function
def get_langfuse() -> Optional[Langfuse]:
    """Get Langfuse client instance."""
    return LangfuseClient.get_client()
