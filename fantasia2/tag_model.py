from typing import Sequence

from PySide6 import QtCore, QtQml

from . import db

QML_IMPORT_NAME = __name__
QML_IMPORT_MAJOR_VERSION = 1


@QtQml.QmlElement
@QtQml.QmlUncreatable()
class TagModel(QtCore.QAbstractListModel):
    def __init__(self, session) -> None:
        super().__init__()
        self._session = session
        self._items: Sequence[db.Tag] = (
            session.query(db.Tag).order_by(db.Tag.name).all()
        )
        self.layoutChanged.connect(self.countChanged)
        self.rowsInserted.connect(self.countChanged)
        self.modelReset.connect(self.countChanged)

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

        if role == QtCore.Qt.ItemDataRole.BackgroundRole:
            return self._items[index.row()].color

        if role == QtCore.Qt.ItemDataRole.UserRole:
            return self._items[index.row()]

        if role == QtCore.Qt.ItemDataRole.UserRole + 1:
            return self._items[index.row()].id

        return None

    def roleNames(self):
        return {
            QtCore.Qt.ItemDataRole.DisplayRole: b"name",
            QtCore.Qt.ItemDataRole.BackgroundRole: b"color",
            QtCore.Qt.ItemDataRole.UserRole + 1: b"id",
        }

    countChanged = QtCore.Signal()

    @QtCore.Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._items)
