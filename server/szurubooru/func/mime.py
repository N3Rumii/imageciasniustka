import re
from typing import Optional


def get_mime_type(content: bytes) -> str:
    if not content:
        return "application/octet-stream"

    if content[0:3] in (b"CWS", b"FWS", b"ZWS"):
        return "application/x-shockwave-flash"

    if content[0:3] == b"\xFF\xD8\xFF":
        return "image/jpeg"

    if content[0:6] == b"\x89PNG\x0D\x0A":
        return "image/png"

    if content[0:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"

    if content[8:12] == b"WEBP":
        return "image/webp"

    if content[0:2] == b"BM":
        return "image/bmp"

    if content[4:12] in (b"ftypavif", b"ftypavis"):
        return "image/avif"

    if content[4:12] == b"ftypmif1":
        return "image/heif"

    if content[4:12] in (b"ftypheic", b"ftypheix"):
        return "image/heic"

    if content[0:4] == b"\x1A\x45\xDF\xA3":
        return "video/webm"

    if content[4:12] in (b"ftypisom", b"ftypiso5", b"ftypiso6", b"ftypmp42", b"ftypM4V "):
        return "video/mp4"

    if content[4:12] == b"ftypqt  ":
        return "video/quicktime"

    # Audio formats — magic byte detection
    # MP3: ID3 tag or MPEG sync word
    if content[0:3] == b"ID3" or (
        len(content) >= 2 and content[0:2] == b"\xFF\xFB"
    ) or (
        len(content) >= 2 and content[0:2] == b"\xFF\xF3"
    ) or (
        len(content) >= 2 and content[0:2] == b"\xFF\xF2"
    ):
        return "audio/mpeg"

    # WAV: RIFF header with WAVE
    if content[0:4] == b"RIFF" and content[8:12] == b"WAVE":
        return "audio/wav"

    # FLAC: fLaC marker at offset 4
    if content[0:4] == b"fLaC":
        return "audio/flac"

    # Ogg (Vorbis or Opus)
    if content[0:4] == b"OggS":
        return "audio/ogg"

    # M4A / AAC (ftypM4A or similar)
    if len(content) >= 12 and content[4:8] == b"ftyp" and content[8:12] in (
        b"M4A ", b"M4B ", b"mp42", b"3gp5",
    ):
        return "audio/mp4"

    # Opus in Ogg container — detected above as audio/ogg
    # Raw Opus detection (unlikely in practice since Opus is usually in Ogg)

    return "application/octet-stream"


def get_extension(mime_type: str) -> Optional[str]:
    extension_map = {
        "application/x-shockwave-flash": "swf",
        "image/gif": "gif",
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/bmp": "bmp",
        "image/avif": "avif",
        "image/heif": "heif",
        "image/heic": "heic",
        "video/mp4": "mp4",
        "video/quicktime": "mov",
        "video/webm": "webm",
        "audio/mpeg": "mp3",
        "audio/wav": "wav",
        "audio/flac": "flac",
        "audio/ogg": "ogg",
        "audio/mp4": "m4a",
        "audio/opus": "opus",
        "application/octet-stream": "dat",
    }
    return extension_map.get((mime_type or "").strip().lower(), None)


def is_flash(mime_type: str) -> bool:
    return mime_type.lower() == "application/x-shockwave-flash"


def is_video(mime_type: str) -> bool:
    return mime_type.lower() in (
        "application/ogg",
        "video/mp4",
        "video/quicktime",
        "video/webm",
    )


def is_image(mime_type: str) -> bool:
    return mime_type.lower() in (
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/bmp",
        "image/avif",
        "image/heif",
        "image/heic",
    )


def is_animated_gif(content: bytes) -> bool:
    pattern = b"\x21\xF9\x04[\x00-\xFF]{4}\x00[\x2C\x21]"
    return (
        get_mime_type(content) == "image/gif"
        and len(re.findall(pattern, content)) > 1
    )


def is_heif(mime_type: str) -> bool:
    return mime_type.lower() in (
        "image/heif",
        "image/heic",
        "image/avif",
    )


def is_audio(mime_type: str) -> bool:
    return mime_type.lower() in (
        "audio/mpeg",
        "audio/wav",
        "audio/flac",
        "audio/ogg",
        "audio/mp4",
        "audio/opus",
        "audio/x-wav",
        "audio/wave",
        "audio/x-flac",
        "audio/x-m4a",
    )
