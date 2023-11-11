import math
import pathlib
import re
import shutil
import subprocess
from typing import Sequence

import tqdm
from PySide6 import QtCore, QtQml

from alembic import config as alembic_config

from . import db

QML_IMPORT_NAME = __name__
QML_IMPORT_MAJOR_VERSION = 1


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


def sync_database_with_fs(instance: db.F2Instance):
    with instance.session() as session:
        base_dir = instance.base_dir
        tracks_on_fs = {
            f for f in base_dir.rglob("*") if f.is_file() and f.suffix in SUPPORTED_EXTS
        }
        tracks_in_db = {t.path: t for t in session.query(db.Track).all()}
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
                removed_track.folder = new_path.parent.relative_to(base_dir).as_posix()
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


def export_library_to_location(
    instance: db.F2Instance, target_dir: pathlib.Path, excluded_albums: Sequence[str]
):
    with instance.session() as session:
        print("Rendering directory structure")
        paths = {}
        all_paths = set()

        for track in session.query(db.Track).all():
            if track.folder in excluded_albums or any(
                str(p) in excluded_albums for p in pathlib.Path(track.folder).parents
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
        for dest_path, src_path in tqdm.tqdm(
            [(d, s) for d, s in paths.items() if d in to_add], unit="file"
        ):
            if (target_dir / dest_path).exists():
                continue
            (target_dir / dest_path).parent.mkdir(exist_ok=True, parents=True)
            if src_path.suffix == dest_path.suffix:
                shutil.copyfile(src_path, target_dir / dest_path)
            else:
                convert_ffmpeg(src_path, target_dir / dest_path)


def xdg_music_dir() -> pathlib.Path:
    return pathlib.Path(
        subprocess.check_output(["xdg-user-dir", "MUSIC"]).decode().strip()
    )


def format_duration(seconds):
    mins, seconds = divmod(seconds, 60)
    return f"{round(mins):02}:{math.floor(seconds):02}"


@QtQml.QmlElement
@QtQml.QmlSingleton
class Utils(QtCore.QObject):
    @QtCore.Slot(float, result=str)
    def formatDuration(self, seconds):
        return format_duration(seconds)
