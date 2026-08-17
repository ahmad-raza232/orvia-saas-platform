import re

RESERVED_SLUGS = frozenset(
    {
        "admin",
        "api",
        "app",
        "auth",
        "billing",
        "docs",
        "health",
        "invitations",
        "login",
        "me",
        "organizations",
        "platform",
        "register",
        "static",
        "support",
        "www",
    }
)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:80] or "org"


def is_reserved_slug(slug: str) -> bool:
    return slug in RESERVED_SLUGS
