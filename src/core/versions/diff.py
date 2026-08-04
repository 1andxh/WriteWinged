import difflib


def compute_diff(old_content: str, new_content: str) -> tuple[list[dict], int, int]:
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

    lines: list[dict] = []
    additions = 0
    deletions = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            lines += [
                {"t": "ctx", "n": str(j1 + offset + 1), "text": line}
                for offset, line in enumerate(new_lines[j1:j2])
            ]
        if tag in ("replace", "delete"):
            lines += [
                {"t": "del", "n": str(i1 + offset + 1), "text": line}
                for offset, line in enumerate(old_lines[i1:i2])
            ]
            deletions += i2 - i1
        if tag in ("replace", "insert"):
            lines += [
                {"t": "add", "n": str(j1 + offset + 1), "text": line}
                for offset, line in enumerate(new_lines[j1:j2])
            ]
            additions += j2 - j1

    return lines, additions, deletions
