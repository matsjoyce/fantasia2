import math

from PySide6 import QtCore, QtQml

QML_IMPORT_NAME = __name__
QML_IMPORT_MAJOR_VERSION = 1


def format_duration(seconds):
    mins, seconds = divmod(seconds, 60)
    return f"{round(mins):02}:{math.floor(seconds):02}"


@QtQml.QmlElement
@QtQml.QmlSingleton
class Utils(QtCore.QObject):
    @QtCore.Slot(float, result=str)
    def formatDuration(self, seconds):
        return format_duration(seconds)
