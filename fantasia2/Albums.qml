pragma ComponentBehavior: Bound
import QtQml.Models as QQM
import QtQuick 6.4
import QtQuick.Controls as QQC
import QtQuick.Layouts as QQL
import QtQuick.Effects as QQE
import fantasia2.query_model as QueryModel

QQC.ScrollView {
    id: root

    required property QueryModel.AlbumModel albumModel
    property alias selectedIndexes: table.selectionModel.selectedIndexes

    signal addAlbumToPlaylist
    signal addSelectedToPlaylist

    contentWidth: availableWidth

    QQL.ColumnLayout {
        height: Math.max(root.height, implicitHeight)
        spacing: 0
        width: root.availableWidth

        Rectangle {
            QQL.Layout.fillWidth: true
            color: "#222222"
            implicitHeight: 300
            visible: root.albumModel.hasRoot

            Column {
                anchors.left: parent.left
                anchors.margins: 16
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width / 2
                z: 10

                QQC.Label {
                    color: "white"
                    font.pixelSize: 48
                    text: root.albumModel.rootName
                    width: parent.width
                    wrapMode: Text.Wrap
                }

                QQC.Label {
                    color: "white"
                    text: "%1 tracks".arg(root.albumModel.rootTracks)
                }
            }

            Repeater {
                id: coversRepeater

                model: root.albumModel.rootCovers.slice(0, Math.max(0, Math.floor((parent.width / 2 - parent.height * 1.5) / 72 + 1)))

                Item {
                    required property int index
                    required property url modelData

                    anchors.margins: 16
                    anchors.right: parent.right
                    anchors.rightMargin: 16 + 72 * (coversRepeater.count - index - 1)
                    anchors.verticalCenter: parent.verticalCenter
                    height: parent.height
                    width: parent.height * 1.5
                    z: coversRepeater.count - index

                    Image {
                        id: coverImg

                        anchors.fill: parent
                        anchors.margins: 16
                        fillMode: Image.PreserveAspectFit
                        horizontalAlignment: Image.AlignRight
                        source: modelData
                        visible: false
                    }

                    QQE.MultiEffect {
                        anchors.fill: coverImg
                        autoPaddingEnabled: false
                        paddingRect: Qt.rect(32, 16, 64, 32)
                        shadowEnabled: true
                        shadowScale: 1.05
                        source: coverImg
                    }
                }
            }
        }

        QQC.ToolBar {
            QQL.Layout.fillHeight: false
            QQL.Layout.fillWidth: true
            leftPadding: 4
            rightPadding: 4

            QQL.RowLayout {
                anchors.fill: parent

                QQC.ToolButton {
                    enabled: root.albumModel.hasRoot
                    icon.height: 22
                    icon.name: "arrow-up"
                    icon.width: 22
                    text: "Up"

                    onClicked: root.albumModel.exitAlbum()
                }

                Item {
                    id: spacer

                    QQL.Layout.fillWidth: true
                }

                QQC.ToolButton {
                    enabled: root.albumModel.rootTracks > 0
                    icon.height: 22
                    icon.name: "folder-add"
                    icon.width: 22
                    text: "Add all to playlist"

                    onClicked: root.addAlbumToPlaylist()
                }

                QQC.ToolButton {
                    enabled: root.albumModel.rootTracks > 0
                    icon.height: 22
                    icon.name: "list-add-symbolic"
                    icon.width: 22
                    text: "Add selected to playlist"

                    onClicked: root.addSelectedToPlaylist()
                }
            }
        }

        GridView {
            QQL.Layout.fillHeight: true
            QQL.Layout.fillWidth: true
            cellHeight: 100
            cellWidth: 150
            clip: true
            implicitHeight: Math.ceil(root.albumModel.count / Math.floor(width / cellWidth)) * cellHeight
            interactive: false
            model: root.albumModel
            visible: root.albumModel.count > 0

            delegate: Item {
                required property string display
                required property int index

                implicitHeight: 100
                implicitWidth: 150

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 4
                    border.color: "#aaa"
                    color: albumMouseArea.containsMouse ? palette.highlight : "transparent"
                    radius: 4

                    QQC.Label {
                        anchors.fill: parent
                        anchors.margins: 4
                        horizontalAlignment: Text.AlignHCenter
                        text: display
                        verticalAlignment: Text.AlignVCenter
                        wrapMode: Text.Wrap
                    }

                    MouseArea {
                        id: albumMouseArea

                        anchors.fill: parent
                        hoverEnabled: true

                        onPressed: root.albumModel.enterAlbum(index)
                    }
                }
            }
        }

        QQL.ColumnLayout {
            QQL.Layout.margins: 4
            spacing: 0
            visible: root.albumModel.trackModel.count > 0

            QQC.HorizontalHeaderView {
                QQL.Layout.fillWidth: true
                clip: true
                syncView: table
            }

            Item {
                QQL.Layout.fillHeight: true
                QQL.Layout.fillWidth: true
                implicitHeight: table.implicitHeight

                TableView {
                    id: table

                    anchors.fill: parent
                    boundsBehavior: Flickable.StopAtBounds
                    clip: true
                    columnWidthProvider: column => {
                        return [0, 2.5, 1.5, 0.5, 0.5][column] * table.width / model.columnCount();
                    }
                    flickableDirection: Flickable.VerticalFlick
                    implicitHeight: root.albumModel.trackModel.count * 30
                    interactive: false
                    model: root.albumModel.trackModel
                    selectionBehavior: TableView.SelectRows

                    delegate: Rectangle {
                        id: delegate

                        required property int column
                        required property bool current
                        required property string display
                        required property int row
                        required property bool selected

                        color: selected ? palette.highlight : "transparent"
                        implicitHeight: 30
                        implicitWidth: 100

                        QQC.Label {
                            anchors.fill: parent
                            elide: Text.ElideRight
                            horizontalAlignment: delegate.column >= 3 ? Text.AlignHCenter : Text.AlignLeft
                            padding: 2
                            text: delegate.display
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    selectionModel: QQM.ItemSelectionModel {
                        model: table.model

                        onCurrentChanged: (curr, prev) => {
                            return select(curr, ItemSelectionModel.Select | ItemSelectionModel.Rows);
                        }
                    }
                }

                QQC.SelectionRectangle {
                    target: table
                }
            }
        }
    }
}
