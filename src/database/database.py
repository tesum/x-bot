from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()



engine = create_engine('sqlite:///users.db', echo=False)
Session = sessionmaker(bind=engine)

async def init_db():
    Base.metadata.create_all(engine)
    logger.info("✅ Database tables created")

