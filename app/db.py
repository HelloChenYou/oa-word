import sys
from functools import reduce
from operator import or_

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.util import typing as sa_typing

from app.config import settings


if sys.version_info >= (3, 14):
    # SQLAlchemy 2.0.35 still uses typing.Union.__getitem__, which breaks on Python 3.14.
    def _make_union_type_compat(*types):
        return reduce(or_, types)

    sa_typing.make_union_type = _make_union_type_compat


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass
