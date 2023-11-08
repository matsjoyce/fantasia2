import contextlib
import hashlib
import json
import logging
import pathlib

from PySide6 import QtGui
from sqlalchemy import BINARY, Column, Float, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import session as session_mod
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


def hash_file(fname: pathlib.Path) -> bytes:
    with fname.open("rb") as fopen:
        hasher = hashlib.sha256()
        for chunk in iter(lambda: fopen.read(2**20), b""):
            hasher.update(chunk)
        return hasher.digest()


Base = declarative_base()


class TrackToTags(Base):
    __tablename__ = "track_to_tags"
    track_id = Column(Integer, ForeignKey("track.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tag.id"), primary_key=True)


class Tag(Base):
    __tablename__ = "tag"
    id = Column(Integer, primary_key=True)

    parent_id = Column(Integer, ForeignKey("tag.id"))
    children = relationship("Tag", back_populates="parent")
    parent = relationship("Tag", back_populates="children", remote_side=[id])

    tracks = relationship("Track", secondary="track_to_tags", back_populates="tags")

    name = Column(String(100), nullable=False)
    color_bytes = Column(BINARY(3))

    @property
    def color(self) -> QtGui.QColor:
        return QtGui.QColor(*self.color_bytes) if self.color_bytes else QtGui.QColor()

    @color.setter
    def color(self, value: QtGui.QColor) -> None:
        self.color_bytes = bytes((value.r(), value.g(), value.b()))


class Track(Base):
    __tablename__ = "track"
    id = Column(Integer, primary_key=True)
    folder = Column(String(256), nullable=False)
    name = Column(String(100), nullable=False)
    extension = Column(String(100), nullable=False)
    duration = Column(Float, nullable=False)
    file_hash = Column(BINARY(32))
    rating = Column(Integer)
    tags = relationship("Tag", secondary="track_to_tags", back_populates="tracks")
    listenings = Column(Integer, nullable=False, server_default="0")

    @property
    def path(self) -> pathlib.Path:
        session = session_mod.Session.object_session(self)
        return (
            session.info["instance"].base_dir
            / self.folder
            / (self.name + self.extension)
        )


class F2Instance:
    SPECFILE_NAME = "fantasia2.json"

    def __init__(self, base_dir, db_addr):
        self._db_addr = db_addr
        self._engine = create_engine(
            db_addr, pool_recycle=100, isolation_level="READ UNCOMMITTED"
        )
        self._session_cls = sessionmaker(bind=self._engine, autoflush=False)
        self._base_dir = base_dir.resolve()

    def __repr__(self) -> str:
        return f"F2Instance({self._base_dir!r}, {self._db_addr!r})"

    @classmethod
    def from_path(cls, path: pathlib.Path):
        with (path / cls.SPECFILE_NAME).open() as metaf:
            args = json.load(metaf)
        assert args.pop("version") == 1
        return cls(base_dir=path, **args)

    @property
    def base_dir(self):
        return self._base_dir

    @property
    def db_addr(self):
        return self._db_addr

    @property
    def engine(self):
        return self._engine

    @property
    def spec_file(self):
        return self._base_dir / self.SPECFILE_NAME

    @contextlib.contextmanager
    def session(self):
        session = self._session_cls(info={"instance": self})
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def initialize(self):
        with (self._base_dir / self.SPECFILE_NAME).open("w") as metaf:
            json.dump({"db_addr": self._db_addr, "version": 1}, metaf)
