import pyodbc
import logging
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.sqlalchemy_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


SCHEMA_SQL = """
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='Person')
BEGIN
    CREATE TABLE Person (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        Name NVARCHAR(100) NOT NULL UNIQUE
    );
    PRINT 'Created Person table';
END

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='FaceEmbedding')
BEGIN
    CREATE TABLE FaceEmbedding (
        Id INT IDENTITY(1,1) PRIMARY KEY,
        PersonId INT NOT NULL,
        Embedding VARBINARY(2048) NOT NULL,
        SourceRef NVARCHAR(500) NULL,
        Quality FLOAT NULL,
        CreatedAt DATETIME2 DEFAULT GETDATE(),
        CONSTRAINT FK_FaceEmbedding_Person FOREIGN KEY (PersonId) REFERENCES Person(Id)
    );
    CREATE INDEX IX_FaceEmbedding_PersonId ON FaceEmbedding(PersonId);
    PRINT 'Created FaceEmbedding table';
END
"""


def init_db():
    conn = pyodbc.connect(settings.connection_string, timeout=10)
    cursor = conn.cursor()
    for stmt in SCHEMA_SQL.strip().split("\n\n"):
        stmt = stmt.strip()
        if stmt:
            try:
                cursor.execute(stmt)
                conn.commit()
            except pyodbc.ProgrammingError as e:
                logger.warning("Schema stmt skipped: %s", e)
    conn.close()
    logger.info("Database schema initialized.")


def ensure_person(name: str) -> int:
    conn = pyodbc.connect(settings.connection_string, timeout=10)
    cursor = conn.cursor()
    cursor.execute("SELECT Id FROM Person WHERE Name=?", name)
    row = cursor.fetchone()
    if row:
        person_id = row[0]
    else:
        cursor.execute("INSERT INTO Person (Name) OUTPUT INSERTED.Id VALUES (?)", name)
        person_id = cursor.fetchone()[0]
        conn.commit()
    conn.close()
    return person_id
