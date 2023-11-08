import QtQml.Models as QQM
import QtQuick 6.4
import QtQuick.Controls as QQC
import QtQuick.Controls.Material as MatControls
import QtQuick.Layouts as QQL
import fantasia2.query_model as QueryModel
import fantasia2.tag_model as TagModel

QQL.ColumnLayout {
    id: root

    required property QueryModel.QueryModel queryModel
    required property TagModel.TagModel tagModel
    property alias selectedIndexes: table.selectionModel.selectedIndexes

    signal addToPlaylist()

    spacing: 4

    QQL.RowLayout {
        QQL.Layout.fillHeight: false
        QQL.Layout.fillWidth: true

        QQC.ToolButton {
            text: "Add to playlist"
            icon.name: "list-add-symbolic"
            icon.width: 22
            icon.height: 22
            enabled: root.selectedIndexes.length > 0
            onClicked: root.addToPlaylist()
        }

        QQC.ToolSeparator {
        }

        QQC.ToolButton {
            text: "Add tag"
            icon.name: "tag-new"
            icon.width: 22
            icon.height: 22
            enabled: root.selectedIndexes.length > 0
            onClicked: addTagMenu.open()

            QQC.Menu {
                id: addTagMenu

                y: parent.height

                Repeater {
                    model: root.tagModel

                    QQC.MenuItem {
                        required property string name
                        required property color color
                        required property int id

                        text: name
                        onClicked: root.selectedIndexes.filter((idx) => {
                            return idx.column == 2;
                        }).forEach((idx) => {
                            return idx.model.addTag(idx, id);
                        })

                        background: Rectangle {
                            color: parent.color
                        }

                    }

                }

            }

        }

        QQC.ToolButton {
            text: "Remove tag"
            icon.name: "tag-delete"
            icon.width: 22
            icon.height: 22
            enabled: root.selectedIndexes.length > 0
            onClicked: removeTagMenu.open()

            QQC.Menu {
                id: removeTagMenu

                y: parent.height

                Repeater {
                    model: root.tagModel

                    QQC.MenuItem {
                        required property string name
                        required property color color
                        required property int id

                        text: name
                        onClicked: root.selectedIndexes.filter((idx) => {
                            return idx.column == 2;
                        }).forEach((idx) => {
                            return idx.model.removeTag(idx, id);
                        })

                        background: Rectangle {
                            color: parent.color
                        }

                    }

                }

            }

        }

        QQC.ToolSeparator {
        }

        QQC.ToolButton {
            text: "Rate"
            icon.name: "rating-half"
            icon.width: 22
            icon.height: 22
            enabled: root.selectedIndexes.length > 0
            onClicked: ratingMenu.open()

            QQC.Menu {
                id: ratingMenu

                y: parent.height

                Repeater {
                    model: 6

                    QQC.MenuItem {
                        text: "★".repeat(5 - index) + "☆".repeat(index)
                        onClicked: root.selectedIndexes.filter((idx) => {
                            return idx.column == 3;
                        }).forEach((idx) => {
                            return idx.model.setData(idx, 5 - index);
                        })
                    }

                }

                QQC.MenuItem {
                    text: "No rating"
                    onClicked: root.selectedIndexes.filter((idx) => {
                        return idx.column == 3;
                    }).forEach((idx) => {
                        return idx.model.setData(idx, null);
                    })
                }

            }

        }

        Item {
            id: spacer

            QQL.Layout.fillWidth: true
        }

        QQC.ComboBox {
            QQL.Layout.minimumWidth: 200
            implicitHeight: 40
            textRole: "text"
            valueRole: "value"
            onActivated: root.queryModel.ordering = currentValue
            Component.onCompleted: currentIndex = indexOfValue(root.queryModel.ordering)
            model: [{
                "value": QueryModel.QueryModel.SortOrder.ALPHABETICAL,
                "text": qsTr("Alphabetical")
            }, {
                "value": QueryModel.QueryModel.SortOrder.MOST_PLAYED,
                "text": qsTr("Most played")
            }, {
                "value": QueryModel.QueryModel.SortOrder.RATING,
                "text": qsTr("Rating")
            }, {
                "value": QueryModel.QueryModel.SortOrder.DURATION,
                "text": qsTr("Duration")
            }]
        }

    }

    QQL.ColumnLayout {
        spacing: 0
        MatControls.Material.background: Qt.lighter(parent.MatControls.Material.background)

        QQC.HorizontalHeaderView {
            QQL.Layout.fillWidth: true
            syncView: table
            implicitHeight: 30
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
                model: queryModel
                // interactive: false
                columnWidthProvider: (column) => {
                    return [1, 2, 1, 0.5, 0.5][column] * table.width / model.columnCount();
                }
                clip: true
                selectionBehavior: TableView.SelectRows

                selectionModel: QQM.ItemSelectionModel {
                    model: table.model
                    onCurrentChanged: (curr, prev) => {
                        return select(curr, ItemSelectionModel.Select | ItemSelectionModel.Rows);
                    }
                }

                QQC.ScrollBar.vertical: QQC.ScrollBar {
                }

                delegate: Rectangle {
                    required property bool selected
                    required property bool current
                    required property int row
                    required property int column

                    implicitWidth: 100
                    implicitHeight: 30
                    color: selected ? Qt.darker(MatControls.Material.accent) : "transparent"

                    QQC.Label {
                        anchors.fill: parent
                        text: display
                        verticalAlignment: Text.AlignVCenter
                        horizontalAlignment: column >= 3 ? Text.AlignHCenter : Text.AlignLeft
                        elide: Text.ElideRight
                        padding: 2
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

    Item {
        implicitHeight: 4
    }

    QQC.TextField {
        QQL.Layout.fillWidth: true
        text: root.queryModel.query
        onTextEdited: root.queryModel.query = text
        placeholderText: qsTr("Search library")
    }

}
