import hashlib
import uuid


def compute_initials(name: str) -> str:
    parts = [p for p in name.split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    if parts:
        return parts[0][:2].upper()
    return "?"


def compute_author_color(user_id: uuid.UUID) -> str:
    digest = hashlib.md5(str(user_id).encode("utf-8")).hexdigest()
    return f"#{digest[:6]}"
