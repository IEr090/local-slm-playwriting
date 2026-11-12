from urllib.parse import quote


FALLBACK_FILE_NAME = "play.pdf"


def attachment_header(file_name: str) -> str:
    """Return a Content-Disposition value that downloads the file; non-ASCII names go in the RFC 5987 form too."""
    ascii_name = file_name.encode("ascii", errors="ignore").decode("ascii")
    ascii_name = ascii_name.replace("\\", "").replace('"', "")
    # Nothing but the extension is left when the title had no ASCII letters.
    if not ascii_name.removesuffix(".pdf").strip(". "):
        ascii_name = FALLBACK_FILE_NAME
    encoded_name = quote(file_name, safe="")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded_name}"
