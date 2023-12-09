pragma ComponentBehavior: Bound
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
    property alias selectedIndexes: table.selectionModel.selectedIndexes
    required property TagModel.TagModel tagModel

    signal addToPlaylist

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
                enabled: root.selectedIndexes.length > 0
                icon.height: 22
                icon.name: "list-add-symbolic"
                icon.width: 22
                text: "Add to playlist"

                onClicked: root.addToPlaylist()
            }

            QQC.ToolSeparator {
            }

            QQC.ToolButton {
                enabled: root.selectedIndexes.length > 0
                icon.height: 22
                icon.name: "tag-new"
                icon.width: 22
                text: "Add tag"

                onClicked: addTagMenu.open()

                QQC.Menu {
                    id: addTagMenu

                    y: parent.height

                    Repeater {
                        model: root.tagModel

                        QQC.MenuItem {
                            id: addTagDelegate

                            required property color color
                            required property int id
                            required property string name

                            text: name

                            background: Rectangle {
                                color: addTagDelegate.color
                            }

                            onClicked: root.selectedIndexes.filter(idx => {
                                    return idx.column == 2;
                                }).forEach(idx => {
                                    return idx.model.addTag(idx, id);
                                })
                        }
                    }
                }
            }

            QQC.ToolButton {
                enabled: root.selectedIndexes.length > 0
                icon.height: 22
                icon.name: "tag-delete"
                icon.width: 22
                text: "Remove tag"

                onClicked: removeTagMenu.open()

                QQC.Menu {
                    id: removeTagMenu

                    y: parent.height

                    Repeater {
                        model: root.tagModel

                        QQC.MenuItem {
                            id: removeTagDelegate

                            required property color color
                            required property int id
                            required property string name

                            text: name

                            background: Rectangle {
                                color: removeTagDelegate.color
                            }

                            onClicked: root.selectedIndexes.filter(idx => {
                                    return idx.column == 2;
                                }).forEach(idx => {
                                    return idx.model.removeTag(idx, id);
                                })
                        }
                    }
                }
            }

            QQC.ToolSeparator {
            }

            QQC.ToolButton {
                enabled: root.selectedIndexes.length > 0
                icon.height: 22
                icon.name: "rating-half"
                icon.width: 22
                text: "Rate"

                onClicked: ratingMenu.open()

                QQC.Menu {
                    id: ratingMenu

                    y: parent.height

                    Repeater {
                        model: 6

                        QQC.MenuItem {
                            required property int index

                            text: "★".repeat(5 - index) + "☆".repeat(index)

                            onClicked: root.selectedIndexes.filter(idx => {
                                    return idx.column == 3;
                                }).forEach(idx => {
                                    return idx.model.setData(idx, 5 - index);
                                })
                        }
                    }

                    QQC.MenuItem {
                        text: "No rating"

                        onClicked: root.selectedIndexes.filter(idx => {
                                return idx.column == 3;
                            }).forEach(idx => {
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
                textRole: "text"
                valueRole: "value"

                Component.onCompleted: currentIndex = indexOfValue(root.queryModel.ordering)
                onActivated: root.queryModel.ordering = currentValue
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
                // interactive: false
                columnWidthProvider: column => {
                    return [1, 2, 1, 0.5, 0.5][column] * table.width / model.columnCount();
                }
                flickableDirection: Flickable.VerticalFlick
                model: root.queryModel
                selectionBehavior: TableView.SelectRows

                QQC.ScrollBar.vertical: QQC.ScrollBar {
                }
                delegate: Rectangle {
                    id: delegate

                    required property int column
                    required property bool current
                    required property string display
                    required property int row
                    required property bool selected

                    color: selected ? Qt.darker(MatControls.Material.accent) : "transparent"
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

    QQC.TextField {
        QQL.Layout.fillWidth: true
        QQL.Layout.margins: 4
        placeholderText: qsTr("Search library")
        text: root.queryModel.query

        onTextEdited: root.queryModel.query = text
    }
}
