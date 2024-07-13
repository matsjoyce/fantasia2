import enum
from typing import Sequence

import sqlalchemy.orm
from PySide6 import QtCore, QtQml
from sqlalchemy.sql import expression

from . import db, utils

QML_IMPORT_NAME = __name__
QML_IMPORT_MAJOR_VERSION = 1


@QtQml.QmlElement
class TrackModel(QtCore.QAbstractTableModel):
    HEADERS = ["Album", "Title", "Tags", "Rating", "Duration"]
    ALBUM_COLUMN, TITLE_COLUMN, TAGS_COLUMN, RATING_COLUMN, DURATION_COLUMN = range(
        len(HEADERS)
    )

    def __init__(self) -> None:
        super().__init__()
        self._items: Sequence[db.Track] = []
        self.layoutChanged.connect(self.countChanged)
        self.rowsInserted.connect(self.countChanged)
        self.modelReset.connect(self.countChanged)

    def columnCount(self, parent: QtCore.QModelIndex) -> int:
        return len(self.HEADERS) if not parent.isValid() else None

    def rowCount(self, parent: QtCore.QModelIndex) -> int:
        return len(self._items) if not parent.isValid() else None

    def headerData(self, section, orientation, role):
        if (
            orientation == QtCore.Qt.Orientation.Horizontal
            and role == QtCore.Qt.ItemDataRole.DisplayRole
        ):
            return self.HEADERS[section]
        return None

    def flags(self, index):
        return (
            QtCore.Qt.ItemIsSelectable
            | QtCore.Qt.ItemIsEnabled
            | QtCore.Qt.ItemNeverHasChildren
        )

    def data(self, index, role):
        if not self.checkIndex(index):
            return None

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            match index.column():
                case self.ALBUM_COLUMN:
                    return self._items[index.row()].folder
                case self.TITLE_COLUMN:
                    return self._items[index.row()].name
                case self.TAGS_COLUMN:
                    return ", ".join(t.name for t in self._items[index.row()].tags)
                case self.RATING_COLUMN:
                    if self._items[index.row()].rating is None:
                        return ""
                    return "★" * self._items[index.row()].rating + "☆" * (
                        5 - self._items[index.row()].rating
                    )
                case self.DURATION_COLUMN:
                    return utils.format_duration(self._items[index.row()].duration)
                case _:
                    return ""

        elif role == QtCore.Qt.ItemDataRole.UserRole:
            return self._items[index.row()]

        return None

    def setData(self, index, value, role=QtCore.Qt.ItemDataRole.EditRole):
        if not self.checkIndex(index):
            return False

        if role == QtCore.Qt.ItemDataRole.EditRole:
            match index.column():
                case self.ALBUM_COLUMN:
                    return False
                case self.TITLE_COLUMN:
                    return False
                case self.TAGS_COLUMN:
                    return False
                case self.RATING_COLUMN:
                    self._items[index.row()].rating = (
                        int(value) if value is not None else None
                    )
                    sqlalchemy.orm.object_session(self._items[index.row()]).commit()
                case self.DURATION_COLUMN:
                    return False
                case _:
                    return False
            self.dataChanged.emit(
                index,
                index,
                [QtCore.Qt.ItemDataRole.DisplayRole, QtCore.Qt.ItemDataRole.UserRole],
            )
            return True
        return False

    countChanged = QtCore.Signal()

    @QtCore.Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._items)

    @QtCore.Slot(QtCore.QModelIndex, int)
    def addTag(self, index, tag_id):
        if not self.checkIndex(index):
            return

        assert index.column() == self.TAGS_COLUMN
        sesh = sqlalchemy.orm.object_session(self._items[index.row()])
        self._items[index.row()].tags.append(sesh.query(db.Tag).get(tag_id))
        sesh.commit()
        self.dataChanged.emit(
            index,
            index,
            [QtCore.Qt.ItemDataRole.DisplayRole, QtCore.Qt.ItemDataRole.UserRole],
        )

    @QtCore.Slot(QtCore.QModelIndex, int)
    def removeTag(self, index, tag_id):
        if not self.checkIndex(index):
            return

        assert index.column() == self.TAGS_COLUMN
        sesh = sqlalchemy.orm.object_session(self._items[index.row()])
        self._items[index.row()].tags.remove(sesh.query(db.Tag).get(tag_id))
        sesh.commit()
        self.dataChanged.emit(
            index,
            index,
            [QtCore.Qt.ItemDataRole.DisplayRole, QtCore.Qt.ItemDataRole.UserRole],
        )


@QtQml.QmlElement
@QtQml.QmlUncreatable()
class QueryModel(TrackModel):
    @QtCore.QEnum
    class SortOrder(enum.IntEnum):
        ALPHABETICAL = enum.auto()
        MOST_PLAYED = enum.auto()
        RATING = enum.auto()
        DURATION = enum.auto()

        @property
        def sql(self):
            match self:
                case self.ALPHABETICAL:
                    return db.Track.folder, db.Track.name
                case self.MOST_PLAYED:
                    return (
                        -db.Track.listenings * db.Track.duration,
                        -expression.nullslast(db.Track.rating),
                        db.Track.folder,
                        db.Track.name,
                    )
                case self.RATING:
                    return (
                        -expression.nullslast(db.Track.rating),
                        db.Track.folder,
                        db.Track.name,
                    )
                case self.DURATION:
                    return (
                        -db.Track.duration,
                        db.Track.folder,
                        db.Track.name,
                    )

    def __init__(self, session) -> None:
        super().__init__()
        self._session = session
        self._query = ""
        self._ordering = QueryModel.SortOrder.ALPHABETICAL
        self._items = []
        self.refresh()

    queryChanged = QtCore.Signal(name="queryChanged")

    @QtCore.Property(str, notify=queryChanged)
    def query(self) -> str:
        return self._query

    @query.setter
    def query(self, value: str) -> None:
        self._query = value
        self.queryChanged.emit()
        self.refresh()

    orderingChanged = QtCore.Signal(name="orderingChanged")

    @QtCore.Property(int, notify=orderingChanged)
    def ordering(self) -> int:
        return self._ordering

    @ordering.setter
    def ordering(self, value: int) -> None:
        self._ordering = QueryModel.SortOrder(value)
        self.orderingChanged.emit()
        self.refresh()

    def refresh(self):
        self._set(
            self._session.query(db.Track)
            .filter(
                db.Track.name.ilike("%" + self._query + "%")
                | db.Track.folder.ilike("%" + self._query + "%")
                | db.Track.tags.any(db.Tag.name.ilike("%" + self._query + "%"))
            )
            .order_by(*self._ordering.sql)
            .all()
        )

    def _set(self, items):
        # FIXME Maybe layoutChanged does not imply rowCount changed strongly enough?
        self.layoutAboutToBeChanged.emit()
        indexList = self.persistentIndexList()
        ids = {}
        for i, index in enumerate(indexList):
            ids.setdefault(self._items[index.row()].id, []).append(i)
        self._items = items
        newIndexList = [QtCore.QModelIndex()] * len(indexList)
        for row, item in enumerate(items):
            if item.id in ids:
                for idx in ids[item.id]:
                    newIndexList[idx] = self.index(row, indexList[idx].column())
        self.changePersistentIndexList(indexList, newIndexList)
        self.layoutChanged.emit()


@QtQml.QmlElement
@QtQml.QmlUncreatable()
class PlaylistModel(TrackModel):
    def __init__(self, session) -> None:
        super().__init__()
        self._session = session

    @QtCore.Slot(list)
    def appendItems(self, indexes) -> None:
        # Remove duplicates
        new_items = []
        seen_ids = set()

        for idx in indexes:
            item = idx.data(QtCore.Qt.ItemDataRole.UserRole)
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                new_items.append(item)

        self.beginInsertRows(
            QtCore.QModelIndex(),
            len(self._items),
            len(self._items) + len(new_items) - 1,
        )
        self._items = list(self._items) + new_items
        self.endInsertRows()

    @QtCore.Slot(int)
    def appendAlbum(self, album_id: int) -> None:
        album = self._session.query(db.Album).filter_by(id=album_id).one_or_none()
        if album is None:
            return
        new_items = (
            self._session.query(db.Track)
            .filter_by(album_id=album.self_and_children().c.id)
            .order_by(*QueryModel.SortOrder.ALPHABETICAL.sql)
            .all()
        )
        self.beginInsertRows(
            QtCore.QModelIndex(),
            len(self._items),
            len(self._items) + len(new_items) - 1,
        )
        self._items = list(self._items) + new_items
        self.endInsertRows()

    def removeRows(self, row, count, parent=QtCore.QModelIndex()) -> bool:
        self.beginRemoveRows(parent, row, row + count - 1)
        self._items = self._items[:row] + self._items[row + count :]
        self.endRemoveRows()
        return True

    @QtCore.Slot()
    def clear(self) -> None:
        self.beginResetModel()
        self._items = []
        self.endResetModel()


@QtQml.QmlElement
@QtQml.QmlUncreatable()
class AlbumModel(QtCore.QAbstractListModel):
    def __init__(self, session) -> None:
        super().__init__()
        self._session = session
        self._items: Sequence[db.Album] = []
        self.layoutChanged.connect(self.countChanged)
        self.rowsInserted.connect(self.countChanged)
        self.modelReset.connect(self.countChanged)

        self._root_album = None
        self._tracks_model = TrackModel()
        self._refresh()

    def _refresh(self) -> None:
        self.beginResetModel()
        self._items = list(
            self._session.query(db.Album)
            .filter_by(parent=self._root_album)
            .order_by(db.Album.name)
            .all()
        )
        self.endResetModel()
        self.rootChanged.emit()
        self._tracks_model.beginResetModel()
        self._tracks_model._items = list(
            self._session.query(db.Track)
            .filter_by(album=self._root_album)
            .order_by(db.Track.name)
            .all()
        )
        self._tracks_model.endResetModel()

    def rowCount(self, parent: QtCore.QModelIndex) -> int:
        return len(self._items) if not parent.isValid() else None

    def flags(self, index):
        return (
            QtCore.Qt.ItemIsSelectable
            | QtCore.Qt.ItemIsEnabled
            | QtCore.Qt.ItemNeverHasChildren
        )

    def data(self, index, role):
        if not self.checkIndex(index):
            return None

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self._items[index.row()].name

        elif role == QtCore.Qt.ItemDataRole.UserRole:
            return self._items[index.row()]

        return None

    def setData(self, index, value, role=QtCore.Qt.ItemDataRole.EditRole):
        if not self.checkIndex(index):
            return False

        if role == QtCore.Qt.ItemDataRole.EditRole:
            return False
        return False

    countChanged = QtCore.Signal()

    @QtCore.Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._items)

    rootChanged = QtCore.Signal()

    @QtCore.Property(str, notify=rootChanged)
    def rootName(self) -> str:
        return self._root_album.folder if self._root_album else ""

    @QtCore.Property(int, notify=rootChanged)
    def rootId(self) -> int:
        return self._root_album.id if self._root_album else -1

    @QtCore.Property(bool, notify=rootChanged)
    def hasRoot(self) -> bool:
        return self._root_album is not None

    @QtCore.Property(list, notify=rootChanged)
    def rootCovers(self) -> list[QtCore.QUrl]:
        if self._root_album is None:
            return []
        return [
            QtCore.QUrl.fromLocalFile(cover.path)
            for cover in self._session.query(db.Cover)
            .filter_by(album_id=self._root_album.self_and_children().c.id)
            .all()
        ]

    @QtCore.Property(int, notify=rootChanged)
    def rootTracks(self) -> int:
        if self._root_album is None:
            return 0
        return (
            self._session.query(db.Track)
            .filter_by(album_id=self._root_album.self_and_children().c.id)
            .count()
        )

    @QtCore.Slot(int)
    def enterAlbum(self, index: int) -> None:
        self._root_album = self._items[index]
        self._refresh()

    @QtCore.Slot()
    def exitAlbum(self) -> None:
        self._root_album = self._root_album.parent if self._root_album else None
        self._refresh()

    @QtCore.Property(TrackModel, constant=True)
    def trackModel(self):
        return self._tracks_model
