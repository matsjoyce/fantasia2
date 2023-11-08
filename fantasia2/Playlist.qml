import QtQml.Models as QQM
import QtQuick
import QtQuick.Controls as QQC
import QtQuick.Controls.Material as MatControls
import QtQuick.Layouts as QQL
import fantasia2.query_model as QueryModel

QQL.ColumnLayout {
    id: root

    required property QueryModel.PlaylistModel playlistModel
    required property int playingIndex

    signal clearPlaylist()

    spacing: 4

    QQL.RowLayout {
        QQL.Layout.fillHeight: false
        QQL.Layout.fillWidth: true

        QQC.ToolButton {
            text: "Clear playlist"
            icon.name: "edit-clear-symbolic"
            icon.width: 22
            icon.height: 22
            enabled: root.playlistModel.count > 0
            onClicked: root.clearPlaylist()
        }

        QQC.ToolButton {
            text: "Remove item"
            icon.name: "list-remove-symbolic"
            icon.width: 22
            icon.height: 22
            enabled: false
        }

        QQC.ToolSeparator {
        }

        QQC.ToolButton {
            text: "Randomize"
            icon.name: "media-playlist-shuffle-symbolic"
            icon.width: 22
            icon.height: 22
            enabled: false
        }

        QQC.ToolButton {
            text: "Loop"
            icon.name: "media-playlist-repeat-symbolic"
            icon.width: 22
            icon.height: 22
            enabled: false
        }

        Item {
            id: spacer
        }

    }

    QQL.ColumnLayout {
        spacing: 0
        MatControls.Material.background: Qt.lighter(parent.MatControls.Material.background)

        QQC.HorizontalHeaderView {
            QQL.Layout.fillWidth: true
            syncView: table
            clip: true
        }

        QQC.ScrollView {
            QQL.Layout.fillHeight: true
            QQL.Layout.fillWidth: true
            implicitHeight: 50

            TableView {
                id: table

                QQL.Layout.fillHeight: true
                QQL.Layout.fillWidth: true
                model: playlistModel
                columnWidthProvider: (column) => {
                    return [1, 2, 1, 0.5, 0.5][column] * table.width / model.columnCount();
                }
                clip: true

                selectionModel: QQM.ItemSelectionModel {
                }
                // selectionBehaviour: TableView.SelectRows

                QQC.ScrollBar.vertical: QQC.ScrollBar {
                }

                delegate: Rectangle {
                    required property bool selected
                    required property int row
                    required property int column

                    implicitWidth: 100
                    implicitHeight: 30
                    color: selected ? Qt.darker(MatControls.Material.accent) : MatControls.Material.background

                    QQC.IconLabel {
                        icon.name: row == playingIndex ? "media-playback-playing" : ""
                        icon.width: parent.height
                        icon.height: parent.height
                        icon.color: selected ? MatControls.Material.foreground : MatControls.Material.accent
                        visible: column == 0
                    }

                    QQC.Label {
                        anchors.fill: parent
                        anchors.leftMargin: parent.height
                        text: display
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                        padding: 2
                        font.bold: row == playingIndex
                        color: row != playingIndex || selected ? MatControls.Material.foreground : MatControls.Material.accent
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: table.selectionModel.select(table.model.index(row, column), QQM.ItemSelectionModel.SelectCurrent | QQM.ItemSelectionModel.Rows)
                    }

                }

            }

            QQC.SelectionRectangle {
                target: table
            }

            background: Rectangle {
                color: MatControls.Material.background
            }

        }

    }

}
