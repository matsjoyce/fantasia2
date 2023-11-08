"""
Usage:
    fantasia2 [<path>]
    fantasia2 init <path>
    fantasia2 sync <path> [--resync]
    fantasia2 dbupgrade <path>
    fantasia2 dbupdate <path>
    fantasia2 dbdowngrade <path> <revision>
    fantasia2 export <path> <exportpath> [--exclude=<excluded_albums>]
"""

import pathlib
import re
import shutil
import subprocess
import sys

import docopt
from alembic import command as alembic_command
from alembic import config as alembic_config
from PySide6 import QtCore, QtGui, QtQml, QtQuickControls2, QtWidgets
from tqdm import tqdm

from . import query_model  # pylint: disable=unused-import
from . import db, mpris, player, tag_model, utils

SUPPORTED_EXTS = {".mp3", ".wav", ".flac", ".ogg", ".opus", ".m4a", ".mp4"}


def alembic_cfg(instance):
    cfg = alembic_config.Config(pathlib.Path(__file__).parent / "alembic.ini")
    cfg.set_main_option(
        "script_location", str(pathlib.Path(__file__).parent / "alembic")
    )
    cfg.attributes["connection"] = instance.engine
    return cfg


def export_name_trans(name, strip_dot=False):
    name = re.sub(r'[<>:"\\|?*\0-\x1f]', "_", name)
    if strip_dot:
        name = name.rstrip(".")
    return name


def export_ext(ext):
    # https://www.seatcupra.net/forums/threads/sd-card-media-format-type-and-useful-information.468327/#post-4998551
    if ext in {
        ".mp2",
        ".mp3",
        ".wav",
        ".wma",
        ".m4a",
        ".m4b",
        ".aac",
        ".ogg",
        ".flac",
        ".mka",
    }:
        return ext
    if ext in {".opus"}:
        return ".m4a"
    if ext in {".mp4"}:
        return ".m4a"
    raise RuntimeError(f"Encoding for {ext}?")


def convert_ffmpeg(src, dst):
    extra_args = []
    if src.suffix != ".opus":
        extra_args.extend(["-c:a", "copy"])
    try:
        subprocess.run(
            ["ffmpeg", "-i", src, *extra_args, dst], check=True, capture_output=True
        )
    except subprocess.CalledProcessError as exc:
        print(exc.stderr.decode())
        raise RuntimeError("Transcoding failed")


def main():
    args = docopt.docopt(__doc__)

    if args["init"]:
        base_dir = pathlib.Path(args["<path>"])
        if not base_dir.exists():
            base_dir.mkdir()
        assert base_dir.is_dir()
        instance = db.F2Instance(
            base_dir=base_dir,
            db_addr=f"sqlite+pysqlite:///{base_dir.as_posix()}/db.sqlite3",
        )
        alembic_command.upgrade(alembic_cfg(instance), "head")
        instance.initialize()

    if args["dbupgrade"]:
        base_dir = pathlib.Path(args["<path>"])
        instance = db.F2Instance.from_path(base_dir)
        alembic_command.revision(alembic_cfg(instance), "head", autogenerate=True)

    elif args["dbupdate"]:
        base_dir = pathlib.Path(args["<path>"])
        instance = db.F2Instance.from_path(base_dir)
        alembic_command.upgrade(alembic_cfg(instance), "head")

    elif args["dbdowngrade"]:
        base_dir = pathlib.Path(args["<path>"])
        instance = db.F2Instance.from_path(base_dir)
        alembic_command.downgrade(alembic_cfg(instance), args["<revision>"])

    elif args["sync"]:
        base_dir = pathlib.Path(args["<path>"])
        instance = db.F2Instance.from_path(base_dir)
        if args["--resync"]:
            db.Base.metadata.drop_all(instance.engine)
            db.Base.metadata.create_all(instance.engine)
        with instance.session() as session:
            tracks_on_fs = {
                f
                for f in base_dir.rglob("*")
                if f.is_file() and f.suffix in SUPPORTED_EXTS
            }
            tracks_in_db = {t.path: t for t in session.query(db.Track).all()}
            print(tracks_on_fs - set(tracks_in_db))
            new_track_hashes = {
                db.hash_file(base_dir / f): f for f in tracks_on_fs - set(tracks_in_db)
            }

            for removed_path in set(tracks_in_db) - tracks_on_fs:
                removed_track = tracks_in_db[removed_path]
                if removed_track.file_hash in new_track_hashes:
                    tracks_in_db.pop(removed_path)
                    new_path = new_track_hashes[removed_track.file_hash]
                    print(
                        f"Moved {removed_track.path.relative_to(base_dir)} to {new_path.relative_to(base_dir)}"
                    )

                    removed_track.name = new_path.stem
                    removed_track.folder = new_path.parent.relative_to(
                        base_dir
                    ).as_posix()
                    removed_track.extension = new_path.suffix
                    tracks_in_db[new_path] = removed_track
                else:
                    print(f"Deleted {removed_track.path.relative_to(base_dir)}")
                    session.delete(removed_track)

            for added_path in tracks_on_fs - set(tracks_in_db):
                print(f"Added {added_path}")
                try:
                    duration = subprocess.check_output(
                        [
                            "ffprobe",
                            "-i",
                            added_path,
                            "-show_entries",
                            "format=duration",
                            "-v",
                            "quiet",
                            "-of",
                            "csv=p=0",
                        ]
                    ).decode()
                except subprocess.CalledProcessError as exc:
                    print(added_path, exc.output.decode())
                    print()
                    duration = "nan"

                session.add(
                    db.Track(
                        name=added_path.stem,
                        folder=added_path.parent.relative_to(base_dir).as_posix(),
                        extension=added_path.suffix,
                        duration=float(duration),
                        rating=None,
                    )
                )

    elif args["export"]:
        base_dir = pathlib.Path(args["<path>"])
        target_dir = pathlib.Path(args["<exportpath>"])
        excluded_albums = (
            [a.strip() for a in args["--exclude"].split(",")]
            if args["--exclude"]
            else []
        )
        instance = db.F2Instance.from_path(base_dir)
        with instance.session() as session:
            print("Rendering directory structure")
            paths = {}
            all_paths = set()

            for track in session.query(db.Track).all():
                if track.folder in excluded_albums or any(
                    str(p) in excluded_albums
                    for p in pathlib.Path(track.folder).parents
                ):
                    continue
                export_name = (
                    pathlib.Path()
                    / export_name_trans(track.folder, strip_dot=True)
                    / (export_name_trans(track.name) + export_ext(track.extension))
                )
                paths[export_name] = track.path
                all_paths.add(export_name)
                all_paths.update(export_name.parents)

            all_paths.remove(pathlib.Path())

            print(len(paths), "tracks")

            print("Scanning target structure")
            existing_export_paths = set(
                x.relative_to(target_dir) for x in target_dir.rglob("*")
            )

            to_remove = existing_export_paths - all_paths
            to_add = all_paths - existing_export_paths

            print("Found", len(existing_export_paths), "paths")
            print("Targeting", len(all_paths), "paths")
            print("Will remove", len(to_remove), "paths")
            print("Will add", len(to_add), "paths")
            input("Continue? ")

            print("Removing excess paths")
            for path in sorted(
                existing_export_paths - all_paths,
                key=lambda p: len(p.parents),
                reverse=True,
            ):
                assert (target_dir / path).exists()
                if (target_dir / path).is_dir():
                    (target_dir / path).rmdir()
                else:
                    (target_dir / path).unlink()

            input("Continue? ")

            print("Adding new paths")
            for dest_path, src_path in tqdm(
                [(d, s) for d, s in paths.items() if d in to_add], unit="file"
            ):
                if (target_dir / dest_path).exists():
                    continue
                (target_dir / dest_path).parent.mkdir(exist_ok=True, parents=True)
                if src_path.suffix == dest_path.suffix:
                    shutil.copyfile(src_path, target_dir / dest_path)
                else:
                    convert_ffmpeg(src_path, target_dir / dest_path)

    else:
        print("Qt version", QtCore.qVersion())
        app = QtWidgets.QApplication(sys.argv)
        app.setApplicationName("Fantasia2")
        app.setWindowIcon(QtGui.QIcon.fromTheme("emblem-music-symbolic"))
        QtQuickControls2.QQuickStyle.setStyle("Material")
        engine = QtQml.QQmlApplicationEngine()
        base_dir = pathlib.Path(args["<path>"])
        instance = db.F2Instance.from_path(base_dir)
        with instance.session() as main_session:
            q_model = query_model.QueryModel(main_session)
            tg_model = tag_model.TagModel(main_session)
            engine.setInitialProperties(
                {
                    "queryModel": q_model,
                    "tagModel": tg_model,
                }
            )
            engine.load(str(pathlib.Path(__file__).resolve().parent / "Main.qml"))

            if not engine.rootObjects():
                sys.exit(-1)
            sys.exit(app.exec())


if __name__ == "__main__":
    main()
