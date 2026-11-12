/**
 * The file name in a Content-Disposition header. `filename*=UTF-8''…` (RFC 5987, percent-encoded) wins over the
 * plain `filename="…"`, because only it can carry non-ASCII letters. Returns null when the header names no file.
 */
export function fileNameFromDisposition(header: string | null): string | null {
  if (!header) return null;

  const encoded = /filename\*\s*=\s*UTF-8''([^;]+)/i.exec(header);
  if (encoded) {
    try {
      return decodeURIComponent(encoded[1].trim());
    } catch {
      // a broken escape: fall back to the plain name
    }
  }

  const quoted = /filename\s*=\s*"((?:[^"\\]|\\.)*)"/i.exec(header);
  if (quoted) return quoted[1].replace(/\\(.)/g, "$1");

  const bare = /filename\s*=\s*([^;]+)/i.exec(header);
  return bare ? bare[1].trim() : null;
}
