"""Audio processing — Opus conversion, duration extraction, cover art.

Mirrors the Image class pattern: ffmpeg/ffprobe subprocess wrappers
with temp files, JSON metadata parsing, and error handling.
"""

import json
import logging
import shlex
import subprocess
from typing import Optional, Tuple

from szurubooru import errors
from szurubooru.func import mime, util

logger = logging.getLogger(__name__)


class Audio:
    """Wrap an audio file for conversion and metadata extraction."""

    def __init__(self, content: bytes) -> None:
        self.content = content
        self._reload_info()

    @property
    def duration(self) -> float:
        """Duration in seconds (float)."""
        return float(self.info["format"].get("duration", 0))

    @property
    def bitrate(self) -> int:
        """Overall bitrate in bits/sec (int)."""
        return int(self.info["format"].get("bit_rate", 0))

    @property
    def sample_rate(self) -> int:
        """Sample rate in Hz from the first audio stream."""
        streams = self.info.get("streams", [])
        for s in streams:
            if s.get("codec_type") == "audio":
                return int(s.get("sample_rate", 0))
        return 0

    @property
    def channels(self) -> int:
        """Number of channels from the first audio stream."""
        streams = self.info.get("streams", [])
        for s in streams:
            if s.get("codec_type") == "audio":
                return int(s.get("channels", 0))
        return 0

    @property
    def artist(self) -> Optional[str]:
        """Artist tag from metadata, if present."""
        tags = self.info.get("format", {}).get("tags", {})
        return tags.get("artist") or tags.get("ARTIST") or None

    @property
    def album(self) -> Optional[str]:
        """Album tag from metadata, if present."""
        tags = self.info.get("format", {}).get("tags", {})
        return tags.get("album") or tags.get("ALBUM") or None

    @property
    def title(self) -> Optional[str]:
        """Title tag from metadata, if present."""
        tags = self.info.get("format", {}).get("tags", {})
        return tags.get("title") or tags.get("TITLE") or None

    def to_opus(self, bitrate: int = 96) -> bytes:
        """Convert audio to Opus in Ogg container at given bitrate (kbps).

        Opus is transparent for music at 96kbps, speech at 64kbps.
        Uses libopus via ffmpeg.
        """
        with util.create_temp_file_path(suffix=".opus") as opus_temp_path:
            self._execute(
                [
                    "-i", "{path}",
                    "-c:a", "libopus",
                    "-b:a", "%dk" % bitrate,
                    "-vbr", "on",
                    "-compression_level", "10",
                    "-application", "audio",
                    "-map_metadata", "0",
                    "-f", "opus",
                    "-y", opus_temp_path,
                ]
            )
            with open(opus_temp_path, "rb") as f:
                return f.read()

    def extract_cover_art(self) -> Optional[bytes]:
        """Extract embedded cover art as PNG bytes, or None.

        Tries to extract the first attached picture stream.
        Falls back to generating a silent waveform placeholder.
        """
        # Try extracting embedded cover art via ffmpeg
        try:
            with util.create_temp_file_path(suffix=".png") as cover_path:
                self._execute(
                    [
                        "-i", "{path}",
                        "-an",            # no audio
                        "-vcodec", "png",
                        "-vframes", "1",
                        "-y", cover_path,
                    ],
                    ignore_error_if_data=True,
                )
                if util.file_has_content(cover_path):
                    with open(cover_path, "rb") as f:
                        return f.read()
        except Exception:
            pass

        # No cover art — return None, caller will use a placeholder
        return None

    def _execute(
        self,
        cli: list,
        program: str = "ffmpeg",
        ignore_error_if_data: bool = False,
    ) -> bytes:
        """Run ffmpeg/ffprobe, returning stdout bytes.

        Args:
            cli: ffmpeg argument list with {path} placeholder
            program: 'ffmpeg' or 'ffprobe'
            ignore_error_if_data: if True and we got output, don't raise

        Returns:
            stdout bytes from the process
        """
        mime_type = mime.get_mime_type(self.content)
        extension = mime.get_extension(mime_type)
        assert extension, "Unknown audio MIME: %s" % mime_type

        with util.create_temp_file(suffix="." + extension) as handle:
            handle.write(self.content)
            handle.flush()
            cli = [program, "-loglevel", "24"] + cli
            cli = [part.format(path=handle.name) for part in cli]
            proc = subprocess.Popen(
                cli,
                stdout=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            out, err = proc.communicate()
            if proc.returncode != 0:
                logger.warning(
                    "Failed to execute %s command (cli=%r, err=%r)",
                    program,
                    " ".join(shlex.quote(arg) for arg in cli),
                    err,
                )
                if (len(out) > 0 and not ignore_error_if_data) or len(out) == 0:
                    raise errors.ProcessingError(
                        "Error while processing audio.\n%s" % err.decode("utf-8", errors="replace")
                    )
            return out

    def _reload_info(self) -> None:
        """Load audio metadata via ffprobe JSON output."""
        self.info = json.loads(
            self._execute(
                [
                    "-i", "{path}",
                    "-of", "json",
                    "-show_format",
                    "-show_streams",
                ],
                program="ffprobe",
            ).decode("utf-8")
        )
        assert "format" in self.info, "ffprobe returned no format info"
        assert "streams" in self.info, "ffprobe returned no stream info"

        # Verify at least one audio stream
        has_audio = any(
            s.get("codec_type") == "audio" for s in self.info["streams"]
        )
        if not has_audio:
            raise errors.ProcessingError(
                "The uploaded file contains no audio streams."
            )
