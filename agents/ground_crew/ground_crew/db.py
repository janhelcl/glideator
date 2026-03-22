"""Database helpers for Ground Crew."""

import os
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import create_engine


@lru_cache(maxsize=1)
def get_engine():
    """Return a SQLAlchemy engine configured from environment variables."""
    load_dotenv()

    connection_string = "postgresql://{user}:{password}@{host}:{port}/{db}".format(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        db=os.getenv("DB_NAME"),
    )
    return create_engine(connection_string)


