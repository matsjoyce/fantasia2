from typing import Any, Optional
import contextlib
import os

from PySide6 import QtDBus, QtCore, QtQml, QtMultimedia

from . import player as player_mod


SERVICE_NAME = "org.mpris.MediaPlayer2.Fantasia2"
MEDIAPLAYER2_PATH = "/org/mpris/MediaPlayer2"
MP2_IFACE = "org.mpris.MediaPlayer2"
MP2_PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"

QML_IMPORT_NAME = __name__
QML_IMPORT_MAJOR_VERSION = 1


@QtCore.ClassInfo({"D-Bus Interface": MP2_IFACE})
class MediaPlayer2Interface(QtDBus.QDBusAbstractAdaptor):
    # https://specifications.freedesktop.org/mpris-spec/2.2/Media_Player.html

    raiseRequested = QtCore.Signal(name="raiseRequested")
    fullscreenRequested = QtCore.Signal(name="fullscreenRequested")

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)

    @QtCore.Slot()
    def Raise(self):
        self.raiseRequested.emit()

    @QtCore.Slot()
    def Quit(self):
        QtCore.QCoreApplication.instance().quit()

    @QtCore.Property(bool)
    def CanQuit(self) -> bool:
        return True

    @QtCore.Property(bool)
    def Fullscreen(self) -> bool:
        return True

    @Fullscreen.setter
    def Fullscreen(self, value: bool) -> None:
        self.fullscreenRequested.emit()

    @QtCore.Property(bool)
    def CanSetFullscreen(self) -> bool:
        return True

    @QtCore.Property(bool)
    def CanRaise(self) -> bool:
        return True

    @QtCore.Property(bool)
    def HasTrackList(self) -> bool:
        return False

    @QtCore.Property(str)
    def Identity(self) -> str:
        return "Fantasia2"

    @QtCore.Property(str)
    def DesktopEntry(self) -> str:
        return "Fantasia2"

    @QtCore.Property("QStringList")
    def SupportedUriSchemes(self) -> list[str]:
        return ["file"]

    @QtCore.Property("QStringList")
    def SupportedMimeTypes(self) -> list[str]:
        return ["audio/mp3"]


@QtCore.ClassInfo({"D-Bus Interface": MP2_PLAYER_IFACE})
class MediaPlayer2PlayerInterface(QtDBus.QDBusAbstractAdaptor):
    # https://specifications.freedesktop.org/mpris-spec/2.2/Player_Interface.html

    def __init__(
        self, bus: QtDBus.QDBusConnection, parent: QtCore.QObject | None = None
    ) -> None:
        super().__init__(parent)

        self._player: Optional[player_mod.Player] = None
        self._bus = bus

        self._changed_properties = set()
        self._send_prop_changed_timer = QtCore.QTimer()
        self._send_prop_changed_timer.setSingleShot(True)
        self._send_prop_changed_timer.timeout.connect(self._sendPropChanged)

        self.PlaybackStatusChanged.connect(self._propChanged)
        self.MetadataChanged.connect(self._propChanged)

    @QtCore.Slot()
    def _propChanged(self) -> None:
        signal_idx = self.senderSignalIndex()
        signal_name = bytes(self.metaObject().method(signal_idx).name()).decode()
        self._changed_properties.add(signal_name.removesuffix("Changed"))
        self._send_prop_changed_timer.start(0)

    @QtCore.Slot()
    def _sendPropChanged(self) -> None:
        changed_props = {n: getattr(self, n) for n in self._changed_properties}
        msg = QtDBus.QDBusMessage.createSignal(
            MEDIAPLAYER2_PATH, PROPERTIES_IFACE, "PropertiesChanged"
        )
        msg.setArguments([MP2_PLAYER_IFACE, changed_props, []])
        self._bus.send(msg)
        self._changed_properties = set()

    playerChanged = QtCore.Signal(name="playerChanged")

    @QtCore.Property(player_mod.Player, notify=playerChanged)
    def player(self) -> Optional[player_mod.Player]:
        return self._player

    @player.setter
    def player(self, player: Optional[player_mod.Player]) -> None:
        if self._player:
            self._player.stateChanged.disconnect(self.PlaybackStatusChanged)
            self._player.durationChanged.disconnect(self.MetadataChanged)
            self._player.currentTrackChanged.disconnect(self.MetadataChanged)
        self._player = player
        if self._player:
            self._player.stateChanged.connect(self.PlaybackStatusChanged)
            self._player.durationChanged.connect(self.MetadataChanged)
            self._player.currentTrackChanged.connect(self.MetadataChanged)
        self.playerChanged.emit()

    @QtCore.Slot()
    def Next(self) -> None:
        if self._player is not None:
            self._player.next_track()

    @QtCore.Slot()
    def Previous(self) -> None:
        if self._player is not None:
            self._player.previous_track()

    @QtCore.Slot()
    def Pause(self) -> None:
        if self._player is not None:
            self._player.pause()

    @QtCore.Slot()
    def PlayPause(self) -> None:
        if self._player is not None:
            self._player.togglePlaying()

    @QtCore.Slot()
    def Stop(self) -> None:
        if self._player is not None:
            self._player.stop()

    @QtCore.Slot()
    def Play(self) -> None:
        if self._player is not None:
            self._player.play()

    @QtCore.Slot("qint64")
    def Seek(self, Offset: int) -> None:
        if self._player is not None:
            self._player.position += Offset / 1000000

    @QtCore.Slot(QtDBus.QDBusObjectPath, "qint64")
    def SetPosition(self, TrackID: QtDBus.QDBusObjectPath, Position: int) -> None:
        if self._player is not None:
            self._player.position = Position / 1000000

    @QtCore.Slot(str)
    def OpenUri(self, Uri: str) -> None:
        ...

    Seeked = QtCore.Signal("qint64", name="Seeked")

    PlaybackStatusChanged = QtCore.Signal(name="PlaybackStatusChanged")

    @QtCore.Property(str, notify=PlaybackStatusChanged)
    def PlaybackStatus(self) -> str:
        match self._player.state:
            case QtMultimedia.QMediaPlayer.PlaybackState.PlayingState:
                return "Playing"
            case QtMultimedia.QMediaPlayer.PlaybackState.PausedState:
                return "Paused"
            case QtMultimedia.QMediaPlayer.PlaybackState.StoppedState:
                return "Stopped"

    @QtCore.Property(str)
    def LoopStatus(self) -> str:
        return "None"

    @LoopStatus.setter
    def LoopStatus(self, value: str) -> None:
        ...

    @QtCore.Property(float)
    def Rate(self) -> float:
        return 1.0

    @Rate.setter
    def Rate(self, value: float) -> None:
        ...

    @QtCore.Property(bool)
    def Shuffle(self) -> str:
        return False

    @Shuffle.setter
    def Shuffle(self, value: bool) -> None:
        ...

    MetadataChanged = QtCore.Signal(name="MetadataChanged")

    @QtCore.Property(dict)
    def Metadata(self) -> dict[str, Any]:
        # https://www.freedesktop.org/wiki/Specifications/mpris-spec/metadata/
        if self._player is None or self._player.currentTrackIndex == -1:
            return {}
        return {
            "mpris:trackid": QtDBus.QDBusObjectPath("/Tracks/0"),
            "mpris:length": round(self._player.duration * 1000000),
            # "xesam:album": "Batman",
            "xesam:title": self._player.currentTrackName,
            # "xesam:url": "file://home/matthew/thing.mp3"
        }

    @QtCore.Property(float)
    def Volume(self) -> float:
        return 1.0

    @Volume.setter
    def Volume(self, value: float) -> None:
        ...

    @QtCore.Property("qint64")
    def Position(self) -> int:
        if self._player is not None:
            return round(self._player.position * 1000000)

    @QtCore.Property(float)
    def MinimumRate(self) -> float:
        return 1.0

    @QtCore.Property(float)
    def MaximumRate(self) -> float:
        return 1.0

    @QtCore.Property(bool)
    def CanGoNext(self) -> bool:
        return True

    @QtCore.Property(bool)
    def CanGoPrevious(self) -> bool:
        return True

    @QtCore.Property(bool)
    def CanPlay(self) -> bool:
        return True

    @QtCore.Property(bool)
    def CanPause(self) -> bool:
        return True

    @QtCore.Property(bool)
    def CanSeek(self) -> bool:
        return True

    @QtCore.Property(bool)
    def CanControl(self) -> bool:
        return True


@QtQml.QmlElement
class MPRIS(QtCore.QObject, QtDBus.QDBusContext):
    raiseRequested = QtCore.Signal(name="raiseRequested")
    fullscreenRequested = QtCore.Signal(name="fullscreenRequested")

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)

        self._session_bus = QtDBus.QDBusConnection.sessionBus()
        if not self._session_bus.isConnected():
            print("Could not connect to session bus")
            return

        if not self._session_bus.registerService(
            f"org.mpris.MediaPlayer2.Fantasia2.instance{os.getpid()}"
        ):
            print(self._session_bus.lastError().message())
            return

        self._mp2_iface = MediaPlayer2Interface(self)
        self._mp2player_iface = MediaPlayer2PlayerInterface(self._session_bus, self)

        self._mp2player_iface.playerChanged.connect(self.playerChanged)
        self._mp2_iface.raiseRequested.connect(self.raiseRequested)
        self._mp2_iface.fullscreenRequested.connect(self.fullscreenRequested)

        self._session_bus.registerObject(MEDIAPLAYER2_PATH, self)

    playerChanged = QtCore.Signal(name="playerChanged")

    @QtCore.Property(player_mod.Player, notify=playerChanged)
    def player(self) -> Optional[player_mod.Player]:
        return self._mp2player_iface.player

    @player.setter
    def player(self, player: player_mod.Player) -> None:
        self._mp2player_iface.player = player
