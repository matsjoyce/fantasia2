import QtQuick
import QtQuick.Controls as QQC
import QtQuick.Controls.Material
import QtQuick.Layouts as QQL
import fantasia2.mpris as MPRIS
import fantasia2.player as Player
import fantasia2.query_model as QueryModel
import fantasia2.tag_model as TagModel
import fantasia2.utils as Utils

QQC.ApplicationWindow {
    id: root

    required property QueryModel.QueryModel queryModel
    required property TagModel.TagModel tagModel

    visible: true
    minimumWidth: 1000
    minimumHeight: 600
    Material.theme: Material.Dark
    Material.accent: Material.color(Material.Red, Material.Shade500)

    QueryModel.PlaylistModel {
        id: playlistModel
    }

    Player.Player {
        id: player

        playlistModel: playlistModel
    }

    MPRIS.MPRIS {
        player: player
        onRaiseRequested: root.raise()
        onFullscreenRequested: root.showFullScreen()
    }

    Shortcut {
        sequence: StandardKey.Quit
        onActivated: root.close()
    }

    QQC.Action {
        id: playPauseAction

        icon.name: player.playing ? "media-playback-pause" : player.stopped ? "media-playlist-repeat-symbolic" : "media-playback-start"
        onTriggered: player.togglePlaying()
        enabled: playlistModel.count > 0
        shortcut: "Space"
    }

    QQC.Action {
        id: stopAction

        icon.name: "media-playback-stop"
        onTriggered: player.stop()
        enabled: playlistModel.count > 0
    }

    QQC.Action {
        id: skipBackwardAction

        icon.name: "media-skip-backward"
        onTriggered: player.previous_track()
        enabled: playlistModel.count > 0
    }

    QQC.Action {
        id: seekBackwardAction

        icon.name: "media-seek-backward"
        onTriggered: player.position -= 10
        enabled: !player.stopped
        shortcut: "Left"
    }

    QQC.Action {
        id: seekForwardAction

        icon.name: "media-seek-forward"
        onTriggered: player.position += 10
        enabled: !player.stopped
        shortcut: "Right"
    }

    QQC.Action {
        id: skipForwardAction

        icon.name: "media-skip-forward"
        onTriggered: player.next_track()
        enabled: playlistModel.count > 0
    }

    QQC.Action {
        id: trackAppendAction

        icon.name: "media-playlist-append"
        onTriggered: tabBar.currentIndex == 1 && playlistModel.appendItems(library.selectedIndexes)
        shortcut: "Return"
    }

    QQC.Action {
        id: clearAction

        icon.name: "edit-clear-list"
        onTriggered: playlistModel.clear()
        shortcut: "Ctrl+C"
    }

    QQL.ColumnLayout {
        anchors.fill: parent
        anchors.topMargin: 4

        QQC.TabBar {
            id: tabBar

            QQL.Layout.fillWidth: true

            Repeater {
                model: ["Playlist", "Library"]

                QQC.TabButton {
                    required property string modelData

                    text: modelData
                    implicitWidth: tabBar.width / 2
                }

            }

        }

        QQC.Frame {
            QQL.Layout.fillHeight: true
            QQL.Layout.fillWidth: true

            QQL.StackLayout {
                anchors.fill: parent
                currentIndex: tabBar.currentIndex

                Playlist {
                    playlistModel: playlistModel
                    playingIndex: player.currentTrackIndex
                    onClearPlaylist: clearAction.trigger()
                }

                Library {
                    id: library

                    queryModel: root.queryModel
                    tagModel: root.tagModel
                    onAddToPlaylist: trackAppendAction.trigger()
                }

            }

        }

        QQL.RowLayout {
            QQL.Layout.fillHeight: false
            QQL.Layout.fillWidth: true
            QQL.Layout.minimumHeight: 64
            QQL.Layout.leftMargin: 8
            QQL.Layout.rightMargin: 8

            QQC.ToolButton {
                action: playPauseAction
                icon.width: 36
                icon.height: 36
            }

            QQC.ToolButton {
                action: stopAction
                icon.width: 36
                icon.height: 36
            }

            QQC.ToolSeparator {
            }

            QQC.ToolButton {
                action: skipBackwardAction
                icon.width: 36
                icon.height: 36
            }

            QQC.ToolButton {
                action: seekBackwardAction
                icon.width: 36
                icon.height: 36
            }

            QQC.Slider {
                QQL.Layout.fillWidth: true
                from: 0
                to: player.duration
                value: player.stopped ? 0 : player.position
                onMoved: player.position = value
                stepSize: 5
                enabled: !player.stopped
            }

            QQC.ToolButton {
                action: seekForwardAction
                icon.width: 36
                icon.height: 36
            }

            QQC.ToolButton {
                action: skipForwardAction
                icon.width: 36
                icon.height: 36
            }

        }

        QQC.Frame {
            QQL.Layout.fillWidth: true

            QQL.RowLayout {
                anchors.fill: parent

                QQC.Label {
                    text: !player.stopped ? "Playing %1".arg(player.currentTrackName) : "Stopped"
                    QQL.Layout.fillWidth: true
                }

                QQC.Label {
                    text: "%1 / %2".arg(player.stopped ? "--" : Utils.Utils.formatDuration(player.position)).arg(player.stopped ? "--" : Utils.Utils.formatDuration(player.duration))
                }

            }

            background: Rectangle {
                color: "black"
            }

        }

    }

}
