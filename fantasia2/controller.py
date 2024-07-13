import threading

from PySide6 import QtCore, QtQml

from . import db, query_model, tag_model, utils

QML_IMPORT_NAME = __name__
QML_IMPORT_MAJOR_VERSION = 1


@QtQml.QmlElement
@QtQml.QmlUncreatable()
class Controller(QtCore.QObject):
    def __init__(self, instance: db.F2Instance, session) -> None:
        super().__init__()

        self._query_model = query_model.QueryModel(session)
        self._tag_model = tag_model.TagModel(session)
        self._album_model = query_model.AlbumModel(session)
        self._playlist_model = query_model.PlaylistModel(session)
        self._syncing = False
        self._instance = instance

        self._sync_timer = QtCore.QTimer(self)
        self._sync_timer.timeout.connect(self.syncLibrary)
        self._sync_timer.start(5 * 60 * 1000)  # Every 5 mins, resync

        self.syncingLibraryChanged.connect(self._refresh_model_when_sync_done)
        self.syncLibrary()

    @QtCore.Property(query_model.QueryModel, constant=True)
    def queryModel(self) -> query_model.QueryModel:
        return self._query_model

    @QtCore.Property(tag_model.TagModel, constant=True)
    def tagModel(self) -> tag_model.TagModel:
        return self._tag_model

    @QtCore.Property(query_model.AlbumModel, constant=True)
    def albumModel(self) -> query_model.AlbumModel:
        return self._album_model

    @QtCore.Property(query_model.PlaylistModel, constant=True)
    def playlistModel(self) -> query_model.PlaylistModel:
        return self._playlist_model

    @QtCore.Slot()
    def syncLibrary(self) -> None:
        threading.Thread(target=self._sync_library).start()

    syncingLibraryChanged = QtCore.Signal(bool, name="syncingLibraryChanged")

    @QtCore.Property(bool, notify=syncingLibraryChanged)
    def syncingLibrary(self) -> bool:
        return self._syncing

    def _set_syncing(self, value: bool) -> None:
        self._syncing = value
        self.syncingLibraryChanged.emit(value)

    def _sync_library(self) -> None:
        if self._syncing:
            return
        self._set_syncing(True)
        utils.sync_database_with_fs(self._instance)
        self._set_syncing(False)

    @QtCore.Slot()
    def _refresh_model_when_sync_done(self, syncing: bool) -> None:
        if not syncing:
            self._query_model.refresh()
