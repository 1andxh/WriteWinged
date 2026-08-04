import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from src.auth.models import User, UserRole  # noqa: E402
from src.auth.utils import hash_password  # noqa: E402
from src.core.comments.models import CommentORM  # noqa: E402
from src.core.documents.models import (  # noqa: E402
    DocumentORM,
    DocumentState,
    DocumentVisibility,
)
from src.core.proposals.models import ProposalORM, ProposalState  # noqa: E402
from src.db.main import Session, async_engine  # noqa: E402

DEMO_PASSWORD = "demo-password-123"

DEMO_USERS = [
    {"username": "Demo Owner", "email": "owner@limarr.demo"},
    {"username": "Tunde Mensah", "email": "tunde@limarr.demo"},
    {"username": "Amara K.", "email": "amara@limarr.demo"},
    {"username": "Remi Osei", "email": "remi@limarr.demo"},
    {"username": "Kwame A.", "email": "kwame@limarr.demo"},
]

DOCUMENT_TITLE = "Tone, Consonants, and Contested Claims"

PROPOSALS = [
    {
        "title": "Revised opening — paralinguistic framing",
        "author": "Tunde Mensah",
        "content": (
            "Mandarin ma with a falling tone yields 'mother'; with a rising "
            "tone, it yields 'scolds'. This tonal contrast is not a curiosity "
            "buried in a footnote - it is the clearest possible demonstration "
            "that pitch can carry lexical meaning, and it belongs in the "
            "opening paragraph, not section II."
        ),
        "comments": [
            {
                "author": "Tunde Mensah",
                "text": (
                    "The mā/mǎ example was buried in §II. Moving it inline "
                    "makes the opening argument self-contained. Readers "
                    "shouldn't have to wait 800 words for the tonal payoff."
                ),
                "resolved": False,
            },
            {
                "author": "Amara K.",
                "text": (
                    'Good call. But "yields mother; a falling tone, to scold" '
                    "- the parallel structure breaks. Can we keep the rhythm?"
                ),
                "resolved": False,
            },
            {
                "author": "Tunde Mensah",
                "text": (
                    'Revised: "yields mother; a falling tone, scolds." See '
                    "updated diff above."
                ),
                "resolved": True,
            },
        ],
    },
    {
        "title": "Correct Ubykh consonant count",
        "author": "Remi Osei",
        "content": (
            "Ubykh is frequently cited as having 84 consonant phonemes, one "
            "of the largest consonant inventories of any documented "
            "language, contrasted with just two or three vowels."
        ),
        "comments": [
            {
                "author": "Remi Osei",
                "text": (
                    "Source: Comrie & Matthews (1990) and later work by "
                    "Fenwick. The 84 count includes lateral fricative "
                    "variants that some analyses treat as allophones."
                ),
                "resolved": False,
            },
        ],
    },
    {
        "title": "Soften the Everett claim",
        "author": "Kwame A.",
        "content": (
            "Everett's account of Pirahã grammar, while influential, "
            "remains contested; subsequent responses have challenged "
            "several of its central claims about recursion."
        ),
        "comments": [
            {
                "author": "Kwame A.",
                "text": (
                    "The original phrasing made it sound like Everett's view "
                    "was settled. The 2009 Nevins et al. response and "
                    "subsequent back-and-forth needs to be acknowledged."
                ),
                "resolved": False,
            },
            {
                "author": "Amara K.",
                "text": (
                    "@Kwame A. Agreed. I'd also suggest we mention that "
                    "Everett's 2005 paper was the original claim, not 2009. "
                    "The 2009 date refers to the counter-response."
                ),
                "resolved": False,
            },
        ],
    },
]


async def get_or_create_user(session, username: str, email: str) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is not None:
        return user
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(DEMO_PASSWORD),
        role=UserRole.USER,
    )
    session.add(user)
    await session.flush()
    return user


async def seed() -> None:
    async with Session() as session:
        users = {}
        for spec in DEMO_USERS:
            users[spec["username"]] = await get_or_create_user(
                session, spec["username"], spec["email"]
            )

        owner = users["Demo Owner"]

        result = await session.execute(
            select(DocumentORM).where(
                DocumentORM.owner_id == owner.id, DocumentORM.title == DOCUMENT_TITLE
            )
        )
        document = result.scalar_one_or_none()
        if document is None:
            document = DocumentORM(
                title=DOCUMENT_TITLE,
                owner_id=owner.id,
                state=DocumentState.ACTIVE,
                visibility=DocumentVisibility.PUBLIC,
            )
            session.add(document)
            await session.flush()

        for spec in PROPOSALS:
            result = await session.execute(
                select(ProposalORM).where(
                    ProposalORM.document_id == document.id,
                    ProposalORM.content == spec["content"],
                )
            )
            if result.scalar_one_or_none() is not None:
                print(f"skip (already seeded): {spec['title']}")
                continue

            author = users[spec["author"]]
            proposal = ProposalORM(
                document_id=document.id,
                author_id=author.id,
                title=spec["title"],
                content=spec["content"],
                state=ProposalState.OPEN,
            )
            session.add(proposal)
            await session.flush()

            for comment_spec in spec["comments"]:
                comment_author = users[comment_spec["author"]]
                comment = CommentORM(
                    proposal_id=proposal.id,
                    author_id=comment_author.id,
                    text=comment_spec["text"],
                    inline=False,
                    resolved=comment_spec["resolved"],
                )
                if comment_spec["resolved"]:
                    comment.resolved_by = owner.id
                    comment.resolved_at = datetime.now(timezone.utc)
                session.add(comment)

            print(f"seeded: {spec['title']} ({len(spec['comments'])} comments)")

        await session.commit()

    await async_engine.dispose()
    print("done.")


if __name__ == "__main__":
    asyncio.run(seed())
