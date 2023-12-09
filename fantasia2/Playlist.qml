pragma ComponentBehavior: Bound
import QtQml.Models as QQM
import QtQuick
import QtQuick.Controls as QQC
import QtQuick.Controls.Material as MatControls
import QtQuick.Layouts as QQL
import fantasia2.query_model as QueryModel

QQL.ColumnLayout {
    id: root

    required property int playingIndex
    required property QueryModel.PlaylistModel playlistModel

    signal clearPlaylist

    spacing: 0

    QQC.ToolBar {
        MatControls.Material.background: Qt.lighter(parent.MatControls.Material.background)
        QQL.Layout.fillHeight: false
        QQL.Layout.fillWidth: true
        leftPadding: 4
        rightPadding: 4

        QQL.RowLayout {
            anchors.fill: parent

            QQC.ToolButton {
                enabled: root.playlistModel.count > 0
                icon.height: 22
                icon.name: "edit-clear-symbolic"
                icon.width: 22
                text: "Clear playlist"

                onClicked: root.clearPlaylist()
            }

            QQC.ToolButton {
                enabled: false
                icon.height: 22
                icon.name: "list-remove-symbolic"
                icon.width: 22
                text: "Remove item"
            }

            QQC.ToolSeparator {
            }

            QQC.ToolButton {
                enabled: false
                icon.height: 22
                icon.name: "media-playlist-shuffle-symbolic"
                icon.width: 22
                text: "Randomize"
            }

            QQC.ToolButton {
                enabled: false
                icon.height: 22
                icon.name: "media-playlist-repeat-symbolic"
                icon.width: 22
                text: "Loop"
            }

            Item {
                id: spacer

                QQL.Layout.fillWidth: true
            }
        }
    }

    QQL.ColumnLayout {
        QQL.Layout.margins: 4
        spacing: 0

        QQC.HorizontalHeaderView {
            QQL.Layout.fillWidth: true
            clip: true
            syncView: table
        }

        Rectangle {
            QQL.Layout.fillWidth: true
            color: Qt.lighter(parent.MatControls.Material.background)
            implicitHeight: 2
        }

        QQC.ScrollView {
            QQL.Layout.fillHeight: true
            QQL.Layout.fillWidth: true
            implicitHeight: 50

            TableView {
                id: table

                QQL.Layout.fillHeight: true
                QQL.Layout.fillWidth: true
                boundsBehavior: Flickable.StopAtBounds
                clip: true
                columnWidthProvider: column => {
                    return [1, 2, 1, 0.5, 0.5][column] * table.width / model.columnCount();
                }
                flickableDirection: Flickable.VerticalFlick
                model: root.playlistModel
                selectionBehavior: TableView.SelectRows

                QQC.ScrollBar.vertical: QQC.ScrollBar {
                }
                delegate: Rectangle {
                    id: delegate

                    required property int column
                    required property string display
                    required property int row
                    required property bool selected

                    color: selected ? Qt.darker(MatControls.Material.accent) : MatControls.Material.background
                    implicitHeight: 30
                    implicitWidth: 100

                    QQC.IconLabel {
                        icon.color: delegate.selected ? MatControls.Material.foreground : MatControls.Material.accent
                        icon.height: parent.height
                        icon.name: delegate.row == root.playingIndex ? "media-playback-playing" : ""
                        icon.width: parent.height
                        visible: delegate.column == 0
                    }

                    QQC.Label {
                        anchors.fill: parent
                        anchors.leftMargin: parent.height
                        color: delegate.row != root.playingIndex || delegate.selected ? MatControls.Material.foreground : MatControls.Material.accent
                        elide: Text.ElideRight
                        font.bold: delegate.row == root.playingIndex
                        padding: 2
                        text: delegate.display
                        verticalAlignment: Text.AlignVCenter
                    }

                    MouseArea {
                        anchors.fill: parent

                        onClicked: table.selectionModel.select(table.model.index(delegate.row, delegate.column), QQM.ItemSelectionModel.SelectCurrent | QQM.ItemSelectionModel.Rows)
                    }
                }
                selectionModel: QQM.ItemSelectionModel {
                }
            }

            QQC.SelectionRectangle {
                target: table
            }
        }
    }
}
