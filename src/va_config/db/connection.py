from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


class DBConnection:
    """
    A simple database connection handler for SQLAlchemy.

    Initializes a database engine and a session factory (SessionLocal) based on
    either a full database URL (`db_url`) or individual connection parameters
    (`db_user`, `db_password`, `db_host`, `db_port`, `db_name`).

    Attributes:
        db_url (str): The full database URL or constructed from parts if not provided.
        engine (Engine): The SQLAlchemy engine instance.
        SessionLocal (sessionmaker): A preconfigured sessionmaker bound to the engine.
    """

    def __init__(
        self,
        db_user: str = None,
        db_password: str = None,
        db_host: str = None,
        db_port: int = None,
        db_name: str = None,
        db_url: str = None,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
    ):
        """
        Initialize the database connection.

        Args:
            db_user (str): Database username.
            db_password (str): Database password.
            db_host (str): Database host.
            db_port (int): Database port.
            db_name (str): Database name.
            db_url (str, optional): Full database URL; overrides individual params if provided.
            echo (bool, optional): If True, SQLAlchemy logs all SQL statements.
            pool_size (int, optional): The size of the connection pool.
            max_overflow (int, optional): The number of connections to allow above `pool_size`.
        """
        self.db_url = db_url or f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        self.engine = create_engine(
            self.db_url,
            echo=echo,
            future=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
        )

        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )

    def get_session(self, autocommit: bool = False, autoflush: bool = False) -> Session:
        """
        Create and return a new SQLAlchemy session.

        This method creates a new session using a fresh `sessionmaker`
        configured with the current engine. It immediately returns a live
        `Session` instance (not just the factory) so you can use it directly:

        Example:
            db = DBConnection(db_user="postgres", db_password="pass", db_host="localhost", db_port=5432, db_name="mydb")
            session = db.get_session()
            result = session.execute("SELECT 1")
            session.close()

        Args:
            autocommit (bool, optional): Enable/disable autocommit mode for the session.
            autoflush (bool, optional): Enable/disable autoflush mode for the session.

        Returns:
            Session: A SQLAlchemy `Session` object bound to the engine.
        """
        return sessionmaker(
            bind=self.engine,
            autocommit=autocommit,
            autoflush=autoflush,
            future=True
        )()
