import sys

from PySide6 import QtCore, QtMultimedia, QtQml
from sqlalchemy.orm import object_session

from . import query_model

QML_IMPORT_NAME = __name__
QML_IMPORT_MAJOR_VERSION = 1


@QtQml.QmlElement
class Player(QtCore.QObject):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._playlist_model = None
        self._current_index = QtCore.QPersistentModelIndex()
        self._player = QtMultimedia.QMediaPlayer(self)

        audio_output = QtMultimedia.QAudioOutput(self._player)
        self._player.setAudioOutput(audio_output)

        print("Output device", audio_output.device().description())
        self._player.playbackStateChanged.connect(self.stateChanged)
        self._player.durationChanged.connect(self.durationChanged)
        self._player.positionChanged.connect(self.positionChanged)
        self._player.mediaStatusChanged.connect(self._logMediaStatus)
        self._player.playbackStateChanged.connect(self._logPlaybackState)
        self._player.errorChanged.connect(self._logError)

    @QtCore.Slot(QtMultimedia.QMediaPlayer.MediaStatus)
    def _logMediaStatus(self, status):
        print("Media status", status, file=sys.stderr)
        if status == QtMultimedia.QMediaPlayer.MediaStatus.EndOfMedia:
            self.next_track()

    @QtCore.Slot(QtMultimedia.QMediaPlayer.PlaybackState)
    def _logPlaybackState(self, state):
        print("Playback state", state)

    @QtCore.Slot()
    def _logError(self):
        print("Error state", self._player.error(), self._player.errorString())

    ### Model

    playlistModelChanged = QtCore.Signal(name="playlistModelChanged")

    @QtCore.Property(query_model.PlaylistModel, notify=playlistModelChanged)
    def playlistModel(self):
        return self._playlist_model

    @playlistModel.setter
    def playlistModel(self, value) -> None:
        if value is self._playlist_model:
            return

        if self._playlist_model is not None:
            self._playlist_model.modelReset.disconnect(self._check_current_index)
            self._playlist_model.rowsRemoved.disconnect(self._rows_removed)
            self._playlist_model.rowsInserted.disconnect(self._rows_inserted)

        self._playlist_model = value

        if self._playlist_model is not None:
            self._playlist_model.modelReset.connect(self._check_current_index)
            self._playlist_model.rowsRemoved.connect(self._rows_removed)
            self._playlist_model.rowsInserted.connect(self._rows_inserted)

        self._current_index = QtCore.QPersistentModelIndex(
            self._playlist_model.index(0, 0)
        )
        self.currentTrackChanged.emit()
        self.playlistModelChanged.emit()

    @QtCore.Slot()
    def _check_current_index(self) -> None:
        if not self._current_index.isValid():
            self.stop()

    @QtCore.Slot(QtCore.QModelIndex, int, int)
    def _rows_removed(self, parent, first, last) -> None:
        if not self._current_index.isValid():
            self._current_index = QtCore.QPersistentModelIndex(
                self._playlist_model.index(first, 0)
            )
            self.currentTrackChanged.emit()
            self._play()

    @QtCore.Slot(QtCore.QModelIndex, int, int)
    def _rows_inserted(self, parent, first, last) -> None:
        if self.stopped:
            self._current_index = QtCore.QPersistentModelIndex(
                self._playlist_model.index(first, 0)
            )
            self.currentTrackChanged.emit()
            self._play()

    ### State

    stateChanged = QtCore.Signal(name="stateChanged")

    @property
    def state(self) -> QtMultimedia.QMediaPlayer.PlaybackState:
        return self._player.playbackState()

    @QtCore.Property(bool, notify=stateChanged)
    def playing(self):
        return (
            self._player.playbackState()
            == QtMultimedia.QMediaPlayer.PlaybackState.PlayingState
        )

    @QtCore.Property(bool, notify=stateChanged)
    def paused(self):
        return (
            self._player.playbackState()
            == QtMultimedia.QMediaPlayer.PlaybackState.PausedState
        )

    @QtCore.Property(bool, notify=stateChanged)
    def stopped(self):
        return (
            self._player.playbackState()
            == QtMultimedia.QMediaPlayer.PlaybackState.StoppedState
        )

    durationChanged = QtCore.Signal(name="durationChanged")

    @QtCore.Property(float, notify=durationChanged)
    def duration(self):
        return self._player.duration() / 1000

    positionChanged = QtCore.Signal(name="positionChanged")

    @QtCore.Property(float, notify=positionChanged)
    def position(self):
        return self._player.position() / 1000

    @position.setter
    def position(self, value):
        self._player.setPosition(round(value * 1000))

    currentTrackChanged = QtCore.Signal(name="currentTrackChanged")

    @QtCore.Property(str, notify=currentTrackChanged)
    def currentTrackName(self):
        if not self._current_index.isValid():
            return ""
        return self._current_index.data(QtCore.Qt.ItemDataRole.UserRole).path.stem

    @QtCore.Property(int, notify=currentTrackChanged)
    def currentTrackIndex(self):
        if not self._current_index.isValid():
            return -1
        return self._current_index.row()

    ### Control

    def _play(self):
        if not self._current_index.isValid():
            print("Can't play, current index is not valid")
            self.stop()
            return
        obj = self._current_index.data(QtCore.Qt.ItemDataRole.UserRole)
        url = QtCore.QUrl.fromLocalFile(obj.path.as_posix())
        obj.listenings += 1
        object_session(obj).commit()
        self._player.setSource(url)
        self.currentTrackChanged.emit()
        self._player.play()

    @QtCore.Slot()
    def next_track(self):
        if not self._current_index.isValid():
            return
        self._current_index = QtCore.QPersistentModelIndex(
            self._playlist_model.index(self._current_index.row() + 1, 0)
        )
        self.currentTrackChanged.emit()
        self._play()

    @QtCore.Slot()
    def previous_track(self):
        if not self._current_index.isValid():
            return
        self._current_index = QtCore.QPersistentModelIndex(
            self._playlist_model.index(self._current_index.row() - 1, 0)
        )
        self.currentTrackChanged.emit()
        self._play()

    @QtCore.Slot()
    def togglePlaying(self) -> None:
        if self.playing:
            self.pause()
        else:
            self.play()

    @QtCore.Slot()
    def pause(self) -> None:
        if self.playing:
            self._player.pause()

    @QtCore.Slot()
    def play(self) -> None:
        if self.paused:
            self._player.play()
        else:
            self._current_index = QtCore.QPersistentModelIndex(
                self._playlist_model.index(0, 0)
            )
            self.currentTrackChanged.emit()
            self._play()

    @QtCore.Slot()
    def stop(self) -> None:
        self._player.stop()
