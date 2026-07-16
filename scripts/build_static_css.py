from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "static" / "css" / "styles.css"
TARGET = ROOT / "static" / "css" / "styles.min.css"


def strip_css_comments(source: str) -> str:
    """Remove CSS comments without touching quoted content or rule ordering."""
    output: list[str] = []
    index = 0
    quote = ""

    while index < len(source):
        char = source[index]
        if quote:
            output.append(char)
            if char == "\\" and index + 1 < len(source):
                index += 1
                output.append(source[index])
            elif char == quote:
                quote = ""
            index += 1
            continue

        if char in {'"', "'"}:
            quote = char
            output.append(char)
            index += 1
            continue

        if char == "/" and index + 1 < len(source) and source[index + 1] == "*":
            end = source.find("*/", index + 2)
            if end < 0:
                raise ValueError("unterminated CSS comment")
            index = end + 2
            continue

        output.append(char)
        index += 1

    stripped = "".join(output)
    return "\n".join("" if line.isspace() else line for line in stripped.split("\n"))


def collapse_css_whitespace(source: str) -> str:
    """Collapse formatting whitespace while preserving quoted CSS content."""
    output: list[str] = []
    index = 0
    quote = ""
    pending_space = False

    while index < len(source):
        char = source[index]
        if quote:
            output.append(char)
            if char == "\\" and index + 1 < len(source):
                index += 1
                output.append(source[index])
            elif char == quote:
                quote = ""
            index += 1
            continue

        if char in {'"', "'"}:
            if pending_space and output:
                output.append(" ")
            pending_space = False
            quote = char
            output.append(char)
        elif char.isspace():
            pending_space = True
        else:
            if pending_space and output:
                output.append(" ")
            pending_space = False
            output.append(char)
        index += 1

    return "".join(output).strip() + "\n"


def minify_css(source: str) -> str:
    """Build CSS without changing selector or declaration ordering."""
    return collapse_css_whitespace(strip_css_comments(source))


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    TARGET.write_text(minify_css(source), encoding="utf-8")


if __name__ == "__main__":
    main()
