import re


UNSAFE_FILE_NAME_CHARACTERS = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')
FALLBACK_PDF_FILE_NAME = "play.pdf"


def pdf_file_name(title: str) -> str:
    """Return the play title made safe for a file name, with the extension .pdf; "play.pdf" if nothing is left."""
    cleaned = UNSAFE_FILE_NAME_CHARACTERS.sub(" ", title)
    cleaned = " ".join(cleaned.split())
    cleaned = cleaned.strip(". ")
    if not cleaned:
        return FALLBACK_PDF_FILE_NAME
    return f"{cleaned}.pdf"
