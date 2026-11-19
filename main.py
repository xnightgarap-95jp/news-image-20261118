#!/usr/bin/env python3
"""One-image summary of the world news of 18 November 2026.

The picture itself lives next to this file as entry.png: a single
1024-by-1024 PNG, no larger than one mebibyte, drawn while the entry
was being prepared. What this script does is deliberately small — it
checks that the picture is really the picture it claims to be, then
hands a byte-for-byte copy of it to wherever the grader expects it.

Nothing here reaches the network, rolls dice, or reads a clock, and
nothing outside the standard library is imported. Run it as many
times as you like: every run lands on exactly the same bytes.

Usage:
    python3 main.py [output-path]

When no output path is given on the command line, the script looks
for ENTRY_OUTPUT, then for a directory in MAKEFUN_OUTPUT_DIR or
ENTRY_OUTPUT_DIR, and finally falls back to /output/entry.png.

makefun anchor 9911ced4b498124398ff57a4bbee667af3c111c2 round 34085175
"""

import hashlib
import os
import struct
import sys

# The picture we ship, and the size it must be.
SOURCE_NAME = "entry.png"
EXPECTED_WIDTH = 1024
EXPECTED_HEIGHT = 1024
MAX_BYTES = 1024 * 1024
CHUNK = 64 * 1024

# First eight bytes of every PNG file, in order.
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def fail(message):
    """Print an error to stderr and return the failure exit code."""
    print("main.py: %s" % message, file=sys.stderr)
    return 1


def read_header(source_path):
    """Read the PNG signature and the IHDR chunk, and check the size.

    Returns the width and height found in IHDR. Raises ValueError
    with a plain-English reason when the file is not the 1024x1024
    PNG this entry promises.
    """
    with open(source_path, "rb") as handle:
        signature = handle.read(len(PNG_SIGNATURE))
        if signature != PNG_SIGNATURE:
            raise ValueError("entry.png does not start with a PNG signature")
        chunk_length_bytes = handle.read(4)
        chunk_type = handle.read(4)
        if len(chunk_length_bytes) != 4 or chunk_type != b"IHDR":
            raise ValueError("entry.png has no IHDR chunk where one belongs")
        (chunk_length,) = struct.unpack(">I", chunk_length_bytes)
        if chunk_length != 13:
            raise ValueError("IHDR chunk in entry.png is not 13 bytes long")
        ihdr = handle.read(13)
        if len(ihdr) != 13:
            raise ValueError("IHDR chunk in entry.png is cut short")
        width, height = struct.unpack(">II", ihdr[:8])
    if (width, height) != (EXPECTED_WIDTH, EXPECTED_HEIGHT):
        raise ValueError(
            "entry.png is %dx%d, expected %dx%d"
            % (width, height, EXPECTED_WIDTH, EXPECTED_HEIGHT)
        )
    return width, height


def pick_destination(argv):
    """Work out where the copy should go, in priority order."""
    if len(argv) > 1:
        return argv[1]
    direct = os.environ.get("ENTRY_OUTPUT")
    if direct:
        return direct
    directory = (
        os.environ.get("MAKEFUN_OUTPUT_DIR")
        or os.environ.get("ENTRY_OUTPUT_DIR")
        or "/output"
    )
    return os.path.join(directory, "entry.png")


def copy_with_hash(source_path, destination_path):
    """Copy the file 64 KiB at a time, hashing as we go.

    Returns the SHA-256 hex digest of the bytes written, so a caller
    can confirm the copy is identical to the source.
    """
    digest = hashlib.sha256()
    with open(source_path, "rb") as source, open(
        destination_path, "wb"
    ) as destination:
        while True:
            piece = source.read(CHUNK)
            if not piece:
                break
            digest.update(piece)
            destination.write(piece)
    return digest.hexdigest()


def main(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    source = os.path.join(here, SOURCE_NAME)
    if not os.path.isfile(source):
        return fail("cannot find %s next to main.py" % SOURCE_NAME)
    size = os.path.getsize(source)
    if size > MAX_BYTES:
        return fail(
            "entry.png is %d bytes, over the 1 MiB limit" % size
        )
    try:
        width, height = read_header(source)
    except (OSError, ValueError) as exc:
        return fail(str(exc))
    destination = pick_destination(argv)
    # Refuse to copy the picture onto itself: opening the target
    # for writing first would truncate the very file we are reading.
    if os.path.abspath(destination) == os.path.abspath(source):
        return fail("output path is the same file as entry.png")
    parent = os.path.dirname(os.path.abspath(destination))
    if parent:
        os.makedirs(parent, exist_ok=True)
    try:
        digest = copy_with_hash(source, destination)
    except OSError as exc:
        return fail("could not write %s: %s" % (destination, exc))
    written = os.path.getsize(destination)
    if written != size:
        return fail(
            "wrote %d bytes but entry.png holds %d" % (written, size)
        )
    # Double-check the copy itself: hash what landed on disk and
    # compare it with the hash taken while copying. A mismatch means
    # the write was interrupted or the disk misbehaved, and the
    # output must not be trusted.
    check = hashlib.sha256()
    with open(destination, "rb") as handle:
        while True:
            piece = handle.read(CHUNK)
            if not piece:
                break
            check.update(piece)
    if check.hexdigest() != digest:
        return fail(
            "output hash %s does not match source hash %s"
            % (check.hexdigest(), digest)
        )
    print(
        "wrote %s (%d bytes, %dx%d, sha256 %s)"
        % (destination, written, width, height, digest)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
