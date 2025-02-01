import math
import pathlib
import re
import shutil
import subprocess
from typing import Sequence

import tqdm
from alembic import config as alembic_config
from PySide6 import QtCore, QtQml

from . import db

QML_IMPORT_NAME = __name__
QML_IMPORT_MAJOR_VERSION = 1


SUPPORTED_EXTS = {".mp3", ".wav", ".flac", ".ogg", ".opus", ".m4a", ".mp4"}
SUPPORTED_COVER_EXTS = {".jpg", ".jpeg", ".png"}


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


def sync_database_with_fs(instance: db.F2Instance) -> None:
    with instance.session() as session:
        base_dir = instance.base_dir
        paths_on_fs = set(base_dir.rglob("*"))

        tracks_on_fs = {
            f for f in paths_on_fs if f.is_file() and f.suffix in SUPPORTED_EXTS
        }
        tracks_in_db = {t.path: t for t in session.query(db.Track).all()}
        albums_on_fs = set(
            f for tf in tracks_on_fs for f in tf.parents if f in paths_on_fs
        )
        albums_in_db = {t.path: t for t in session.query(db.Album).all()}
        covers_on_fs = {
            f
            for f in paths_on_fs
            if f.is_file()
            and f.suffix in SUPPORTED_COVER_EXTS
            and f.parent in albums_on_fs
        }
        covers_in_db = {t.path: t for t in session.query(db.Cover).all()}

        # print(paths_on_fs - tracks_on_fs - albums_on_fs - covers_on_fs)

        new_track_hashes = {
            f: db.hash_file(base_dir / f) for f in tracks_on_fs - set(tracks_in_db)
        }
        reverse_track_hashes = {h: f for f, h in new_track_hashes.items()}

        for removed_path in set(tracks_in_db) - tracks_on_fs:
            removed_track = tracks_in_db[removed_path]
            if removed_track.file_hash in reverse_track_hashes:
                tracks_in_db.pop(removed_path)
                new_path = reverse_track_hashes[removed_track.file_hash]
                print(
                    f"Moved {removed_track.path.relative_to(base_dir)} to {new_path.relative_to(base_dir)}"
                )

                removed_track.name = new_path.stem
                removed_track.folder = new_path.parent.relative_to(base_dir).as_posix()
                removed_track.extension = new_path.suffix
                removed_track.album = db.Album.get_for_path(session, new_path.parent)
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
                    file_hash=new_track_hashes[added_path],
                    file_size=added_path.stat().st_size,
                    album=db.Album.get_for_path(session, added_path.parent),
                )
            )

        for removed_cover_path in set(covers_in_db) - covers_on_fs:
            removed_cover = covers_in_db[removed_cover_path]
            print(f"Deleted {removed_cover_path.relative_to(base_dir)}")
            session.delete(removed_cover)

        for added_cover_path in covers_on_fs - set(covers_in_db):
            print(f"Added {added_cover_path}")

            session.add(
                db.Cover(
                    name=added_cover_path.stem,
                    folder=added_cover_path.parent.relative_to(base_dir).as_posix(),
                    extension=added_cover_path.suffix,
                    album=db.Album.get_for_path(session, added_cover_path.parent),
                )
            )

        for removed_album in sorted(
            set(albums_in_db) - albums_on_fs, key=lambda x: len(x.parts), reverse=True
        ):
            print(f"Deleted {removed_album.relative_to(base_dir)}")
            session.remove(db.Album.get_for_path(session, added_path.parent))


def export_library_to_location(
    instance: db.F2Instance, target_dir: pathlib.Path, excluded_albums: Sequence[str]
) -> None:
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

        print("Found", sum(f.suffix != "" for f in existing_export_paths), "paths")
        print("Targeting", sum(f.suffix != "" for f in all_paths), "paths")
        print("Will remove", sum(f.suffix != "" for f in to_remove), "paths")
        print("Will add", sum(f.suffix != "" for f in to_add), "paths")
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


def print_stats(instance: db.F2Instance) -> None:
    num_tracks = 0
    tracks_size = 0

    with instance.session() as session:
        for track in session.query(db.Track).all():
            num_tracks += 1
            tracks_size += track.path.stat().st_size

    print(f"{num_tracks} tracks, totalling {tracks_size/2**30:.2f} GiB")

    album_counts = {}
    with instance.session() as session:
        for album in session.query(db.Album).all():
            album_counts[album.folder] = (
                session.query(db.Track).filter_by(album=album).count()
            )

    print("Most tracks:")
    for album, count in sorted(album_counts.items(), key=lambda x: x[1], reverse=True)[
        :10
    ]:
        print(f"    - {album}: {count} tracks")


def format_duration(seconds: float) -> str:
    mins, seconds = divmod(seconds, 60)
    if mins <= 60:
        return f"{round(mins):02}:{math.floor(seconds):02}"
    hours, mins = divmod(mins, 60)
    return f"{round(hours):02}:{round(mins):02}:{math.floor(seconds):02}"


@QtQml.QmlElement
@QtQml.QmlSingleton
class Utils(QtCore.QObject):
    @QtCore.Slot(float, result=str)
    def formatDuration(self, seconds: float) -> str:
        return format_duration(seconds)
