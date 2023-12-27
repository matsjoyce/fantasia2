pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls as QQC
import QtQuick.Controls.Material as MatControls
import QtQuick.Layouts as QQL
import fantasia2.controller as Controller
import fantasia2.mpris as MPRIS
import fantasia2.player as Player
import fantasia2.query_model as QueryModel
import fantasia2.utils as Utils

QQC.ApplicationWindow {
    id: root

    required property Controller.Controller controller

    MatControls.Material.accent: MatControls.Material.color(MatControls.Material.Red, MatControls.Material.Shade500)
    MatControls.Material.theme: MatControls.Material.Dark
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
            model: ["Playlist", "Library"]

            QQC.TabButton {
                required property string modelData

                text: modelData
            }
        }
    }

    QueryModel.PlaylistModel {
        id: playlistModel

    }

    Player.Player {
        id: player

        playlistModel: playlistModel
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

        enabled: playlistModel.count > 0
        icon.name: player.playing ? "media-playback-pause" : player.stopped ? "media-playlist-repeat-symbolic" : "media-playback-start"
        shortcut: "Space"

        onTriggered: player.togglePlaying()
    }

    QQC.Action {
        id: stopAction

        enabled: playlistModel.count > 0
        icon.name: "media-playback-stop"

        onTriggered: player.stop()
    }

    QQC.Action {
        id: skipBackwardAction

        enabled: playlistModel.count > 0
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

        enabled: playlistModel.count > 0
        icon.name: "media-skip-forward"

        onTriggered: player.next_track()
    }

    QQC.Action {
        id: trackAppendAction

        icon.name: "media-playlist-append"
        shortcut: "Return"

        onTriggered: tabBar.currentIndex == 1 && playlistModel.appendItems(library.selectedIndexes)
    }

    QQC.Action {
        id: clearAction

        icon.name: "edit-clear-list"
        shortcut: "Ctrl+C"

        onTriggered: playlistModel.clear()
    }

    QQL.ColumnLayout {
        anchors.fill: parent

        QQL.StackLayout {
            QQL.Layout.fillHeight: true
            QQL.Layout.fillWidth: true
            currentIndex: tabBar.currentIndex

            Playlist {
                playingIndex: player.currentTrackIndex
                playlistModel: playlistModel

                onClearPlaylist: clearAction.trigger()
            }

            Library {
                id: library

                queryModel: root.controller.queryModel
                tagModel: root.controller.tagModel

                onAddToPlaylist: trackAppendAction.trigger()
                onSyncLibrary: root.controller.syncLibrary()
            }
        }

        QQC.ToolBar {
            MatControls.Material.background: Qt.lighter(parent.MatControls.Material.background)
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
