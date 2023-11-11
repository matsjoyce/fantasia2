"""
Usage:
    fantasia2 [<path>]
    fantasia2 init [<path>]
    fantasia2 sync [<path>]
    fantasia2 dbupgrade <path>
    fantasia2 dbupdate <path>
    fantasia2 dbdowngrade <path> <revision>
    fantasia2 export <path> <exportpath> [--exclude=<excluded_albums>]
"""

import pathlib
import sys

import docopt
from PySide6 import QtCore, QtGui, QtQml, QtQuickControls2, QtWidgets

from alembic import command as alembic_command

from . import controller, db, mpris, player, utils  # pylint: disable=unused-import


def main():
    args = docopt.docopt(__doc__)
    base_dir = (
        pathlib.Path(args["<path>"])
        if args["<path>"] is not None
        else utils.xdg_music_dir()
    )

    print("Using base directory", base_dir)

    if args["init"]:
        if not base_dir.exists():
            base_dir.mkdir()
        assert base_dir.is_dir()
        instance = db.F2Instance(
            base_dir=base_dir,
            db_addr=f"sqlite+pysqlite:///{base_dir.as_posix()}/db.sqlite3",
        )
        alembic_command.upgrade(utils.alembic_cfg(instance), "head")
        instance.initialize()
        return

    instance = db.F2Instance.from_path(base_dir)

    if args["dbupgrade"]:
        alembic_command.revision(utils.alembic_cfg(instance), "head", autogenerate=True)

    elif args["dbupdate"]:
        alembic_command.upgrade(utils.alembic_cfg(instance), "head")

    elif args["dbdowngrade"]:
        alembic_command.downgrade(utils.alembic_cfg(instance), args["<revision>"])

    elif args["sync"]:
        utils.sync_database_with_fs(instance)

    elif args["export"]:
        target_dir = pathlib.Path(args["<exportpath>"])
        excluded_albums = (
            [a.strip() for a in args["--exclude"].split(",")]
            if args["--exclude"]
            else []
        )
        utils.export_library_to_location(instance, target_dir, excluded_albums)

    else:
        print("Qt version", QtCore.qVersion())
        app = QtWidgets.QApplication(sys.argv)
        app.setApplicationName("Fantasia2")
        app.setWindowIcon(QtGui.QIcon.fromTheme("emblem-music-symbolic"))
        QtQuickControls2.QQuickStyle.setStyle("Material")
        engine = QtQml.QQmlApplicationEngine()
        with instance.session() as main_session:
            cont = controller.Controller(instance, main_session)
            engine.setInitialProperties({"controller": cont})
            engine.load(str(pathlib.Path(__file__).resolve().parent / "Main.qml"))

            if not engine.rootObjects():
                sys.exit(-1)
            sys.exit(app.exec())


if __name__ == "__main__":
    main()
