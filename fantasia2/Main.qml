pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls as QQC
import QtQuick.Layouts as QQL
import fantasia2.controller as Controller
import fantasia2.mpris as MPRIS
import fantasia2.player as Player
import fantasia2.query_model as QueryModel
import fantasia2.utils as Utils

QQC.ApplicationWindow {
    id: root

    required property Controller.Controller controller

    minimumHeight: 450
    minimumWidth: 800
    visible: true

    footer: QQL.RowLayout {
        QQC.Label {
            QQL.Layout.fillWidth: true
            QQL.Layout.margins: 4
            QQL.Layout.preferredWidth: 100
            elide: Text.ElideRight
            text: !player.stopped ? "Playing %1".arg(player.currentTrackName) : "Stopped"
        }

        QQC.Label {
            QQL.Layout.margins: 4
            text: "Syncing library..."
            visible: root.controller.syncingLibrary
        }

        QQC.Label {
            QQL.Layout.fillWidth: true
            QQL.Layout.margins: 4
            QQL.Layout.preferredWidth: 100
            horizontalAlignment: Text.AlignRight
            text: player.stopped ? "-- / --" : "%1 / %2".arg(Utils.Utils.formatDuration(player.position)).arg(Utils.Utils.formatDuration(player.duration))
        }
    }
    header: QQC.TabBar {
        id: tabBar

        Repeater {
            model: ["Playlist", "Library", "Albums"]

            QQC.TabButton {
                required property string modelData

                text: modelData
            }
        }
    }

    Player.Player {
        id: player

        playlistModel: root.controller.playlistModel
    }

    MPRIS.MPRIS {
        player: player

        onFullscreenRequested: root.showFullScreen()
        onRaiseRequested: root.raise()
    }

    Shortcut {
        sequence: StandardKey.Quit

        onActivated: root.close()
    }

    QQC.Action {
        id: playPauseAction

        enabled: root.controller.playlistModel.count > 0
        icon.name: player.playing ? "media-playback-pause" : player.stopped ? "media-playlist-repeat-symbolic" : "media-playback-start"
        shortcut: "Space"

        onTriggered: player.togglePlaying()
    }

    QQC.Action {
        id: stopAction

        enabled: root.controller.playlistModel.count > 0
        icon.name: "media-playback-stop"

        onTriggered: player.stop()
    }

    QQC.Action {
        id: skipBackwardAction

        enabled: root.controller.playlistModel.count > 0
        icon.name: "media-skip-backward"

        onTriggered: player.previous_track()
    }

    QQC.Action {
        id: seekBackwardAction

        enabled: !player.stopped
        icon.name: "media-seek-backward"
        shortcut: "Left"

        onTriggered: player.position -= 10
    }

    QQC.Action {
        id: seekForwardAction

        enabled: !player.stopped
        icon.name: "media-seek-forward"
        shortcut: "Right"

        onTriggered: player.position += 10
    }

    QQC.Action {
        id: skipForwardAction

        enabled: root.controller.playlistModel.count > 0
        icon.name: "media-skip-forward"

        onTriggered: player.next_track()
    }

    QQC.Action {
        id: trackAppendAction

        icon.name: "media-playlist-append"
        shortcut: "Return"

        onTriggered: {
            if (tabBar.currentIndex == 1) {
                root.controller.playlistModel.appendItems(library.selectedIndexes);
            } else if (tabBar.currentIndex == 2) {
                root.controller.playlistModel.appendItems(albums.selectedIndexes);
            }
        }
    }

    QQC.Action {
        id: clearAction

        icon.name: "edit-clear-list"
        shortcut: "Ctrl+C"

        onTriggered: root.controller.playlistModel.clear()
    }

    QQL.ColumnLayout {
        anchors.fill: parent

        QQL.StackLayout {
            QQL.Layout.fillHeight: true
            QQL.Layout.fillWidth: true
            currentIndex: tabBar.currentIndex

            Playlist {
                QQL.Layout.fillWidth: true
                playingIndex: player.currentTrackIndex
                playlistModel: root.controller.playlistModel

                onClearPlaylist: clearAction.trigger()
            }

            Library {
                id: library

                QQL.Layout.fillWidth: true
                queryModel: root.controller.queryModel
                tagModel: root.controller.tagModel

                onAddToPlaylist: trackAppendAction.trigger()
                onSyncLibrary: root.controller.syncLibrary()
            }

            Albums {
                id: albums

                QQL.Layout.fillWidth: true
                albumModel: root.controller.albumModel

                onAddAlbumToPlaylist: root.controller.playlistModel.appendAlbum(albumModel.rootId)
                onAddSelectedToPlaylist: trackAppendAction.trigger()
            }
        }

        QQC.ToolBar {
            QQL.Layout.fillHeight: false
            QQL.Layout.fillWidth: true
            padding: 8

            QQL.RowLayout {
                anchors.fill: parent

                QQC.ToolButton {
                    action: playPauseAction
                    icon.height: 36
                    icon.width: 36
                }

                QQC.ToolButton {
                    action: stopAction
                    icon.height: 36
                    icon.width: 36
                }

                QQC.ToolSeparator {
                }

                QQC.ToolButton {
                    action: skipBackwardAction
                    icon.height: 36
                    icon.width: 36
                }

                QQC.ToolButton {
                    action: seekBackwardAction
                    icon.height: 36
                    icon.width: 36
                }

                QQC.Slider {
                    QQL.Layout.fillWidth: true
                    enabled: !player.stopped
                    from: 0
                    stepSize: 5
                    to: player.duration
                    value: player.stopped ? 0 : player.position

                    onMoved: player.position = value
                }

                QQC.ToolButton {
                    action: seekForwardAction
                    icon.height: 36
                    icon.width: 36
                }

                QQC.ToolButton {
                    action: skipForwardAction
                    icon.height: 36
                    icon.width: 36
                }
            }
        }
    }
}
