import uuid
from datetime import datetime, timezone

import pytest

from src.auth.models import User, UserRole
from src.core.comments.models import CommentORM
from src.core.comments.schemas import CommentCreate, CommentUpdate
from src.core.comments.service import CommentService
from src.core.documents.models import DocumentORM, DocumentState, DocumentVisibility
from src.core.proposals.models import ProposalORM, ProposalState
from src.exceptions import (
    CommentNotFound,
    DocumentPermissionDenied,
    InvalidDocumentState,
    ProposalNotFound,
)


class DummyResult:
    def __init__(self, one=None, scalars_list=None):
        self._one = one
        self._scalars_list = scalars_list or []

    def scalar_one_or_none(self):
        return self._one

    def scalars(self):
        return self

    def all(self):
        return self._scalars_list


class QueueSession:
    """Fake AsyncSession that returns queued results in call order."""

    def __init__(self, results):
        self._results = list(results)
        self.added = []
        self.deleted = []

    async def execute(self, statement):
        return self._results.pop(0)

    def add(self, obj):
        self.added.append(obj)
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        if getattr(obj, "created_at", None) is None:
            obj.created_at = now
        if getattr(obj, "updated_at", None) is None:
            obj.updated_at = now

    async def delete(self, obj):
        self.deleted.append(obj)

    async def flush(self):
        return None


def make_user(username: str = "writer") -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{username}@example.com",
        username=username,
        role=UserRole.USER,
    )


def make_document(owner_id: uuid.UUID, *, archived: bool = False) -> DocumentORM:
    return DocumentORM(
        id=uuid.uuid4(),
        title="Doc",
        owner_id=owner_id,
        state=DocumentState.ARCHIVED if archived else DocumentState.ACTIVE,
        visibility=DocumentVisibility.PUBLIC,
    )


def make_proposal(document_id: uuid.UUID, author_id: uuid.UUID) -> ProposalORM:
    return ProposalORM(
        id=uuid.uuid4(),
        document_id=document_id,
        author_id=author_id,
        content="proposed text",
        state=ProposalState.OPEN,
    )


def make_comment(proposal_id: uuid.UUID, author: User) -> CommentORM:
    comment = CommentORM(
        id=uuid.uuid4(),
        proposal_id=proposal_id,
        author_id=author.id,
        text="hello",
        inline=False,
        resolved=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    comment.author = author
    return comment


@pytest.mark.asyncio
async def test_create_comment_rejects_non_owner_non_contributor():
    owner = make_user("owner")
    outsider = make_user("outsider")
    document = make_document(owner.id)
    proposal = make_proposal(document.id, owner.id)

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=document),
            DummyResult(one=None),
        ]
    )
    service = CommentService(session)

    with pytest.raises(DocumentPermissionDenied):
        await service.create_comment(
            document_id=document.id,
            proposal_id=proposal.id,
            actor=outsider,
            payload=CommentCreate(text="hi"),
        )


@pytest.mark.asyncio
async def test_create_comment_succeeds_for_owner():
    owner = make_user("owner")
    document = make_document(owner.id)
    proposal = make_proposal(document.id, owner.id)

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=document),
            DummyResult(one=None),
        ]
    )
    service = CommentService(session)

    response = await service.create_comment(
        document_id=document.id,
        proposal_id=proposal.id,
        actor=owner,
        payload=CommentCreate(text="Looks good"),
    )

    assert response.text == "Looks good"
    assert response.author_id == owner.id
    assert response.author_name == "owner"
    assert len(session.added) == 1


@pytest.mark.asyncio
async def test_create_comment_rejects_archived_document():
    owner = make_user("owner")
    document = make_document(owner.id, archived=True)
    proposal = make_proposal(document.id, owner.id)

    session = QueueSession(
        results=[DummyResult(one=proposal), DummyResult(one=document)]
    )
    service = CommentService(session)

    with pytest.raises(InvalidDocumentState):
        await service.create_comment(
            document_id=document.id,
            proposal_id=proposal.id,
            actor=owner,
            payload=CommentCreate(text="hi"),
        )


@pytest.mark.asyncio
async def test_create_comment_rejects_parent_from_other_proposal():
    owner = make_user("owner")
    document = make_document(owner.id)
    proposal = make_proposal(document.id, owner.id)
    parent = make_comment(uuid.uuid4(), owner)  # belongs to a different proposal

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=document),
            DummyResult(one=None),
            DummyResult(one=parent),
        ]
    )
    service = CommentService(session)

    with pytest.raises(CommentNotFound):
        await service.create_comment(
            document_id=document.id,
            proposal_id=proposal.id,
            actor=owner,
            payload=CommentCreate(text="reply", parent_id=parent.id),
        )


@pytest.mark.asyncio
async def test_create_comment_rejects_proposal_from_wrong_document():
    owner = make_user("owner")
    document = make_document(owner.id)
    proposal = make_proposal(uuid.uuid4(), owner.id)  # different document

    session = QueueSession(results=[DummyResult(one=proposal)])
    service = CommentService(session)

    with pytest.raises(ProposalNotFound):
        await service.create_comment(
            document_id=document.id,
            proposal_id=proposal.id,
            actor=owner,
            payload=CommentCreate(text="hi"),
        )


@pytest.mark.asyncio
async def test_update_comment_text_requires_comment_author():
    owner = make_user("owner")
    author = make_user("author")
    document = make_document(owner.id)
    proposal = make_proposal(document.id, owner.id)
    comment = make_comment(proposal.id, author)

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=comment),
            DummyResult(one=document),
        ]
    )
    service = CommentService(session)

    with pytest.raises(DocumentPermissionDenied):
        await service.update_comment(
            document_id=document.id,
            proposal_id=proposal.id,
            comment_id=comment.id,
            actor_id=owner.id,
            payload=CommentUpdate(text="edited"),
        )


@pytest.mark.asyncio
async def test_update_comment_text_succeeds_for_author():
    author = make_user("author")
    document = make_document(uuid.uuid4())
    proposal = make_proposal(document.id, author.id)
    comment = make_comment(proposal.id, author)

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=comment),
            DummyResult(one=document),
        ]
    )
    service = CommentService(session)

    response = await service.update_comment(
        document_id=document.id,
        proposal_id=proposal.id,
        comment_id=comment.id,
        actor_id=author.id,
        payload=CommentUpdate(text="edited"),
    )

    assert response.text == "edited"


@pytest.mark.asyncio
async def test_update_comment_resolved_requires_document_owner():
    owner = make_user("owner")
    author = make_user("author")
    document = make_document(owner.id)
    proposal = make_proposal(document.id, owner.id)
    comment = make_comment(proposal.id, author)

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=comment),
            DummyResult(one=document),
        ]
    )
    service = CommentService(session)

    with pytest.raises(DocumentPermissionDenied):
        await service.update_comment(
            document_id=document.id,
            proposal_id=proposal.id,
            comment_id=comment.id,
            actor_id=author.id,
            payload=CommentUpdate(resolved=True),
        )


@pytest.mark.asyncio
async def test_update_comment_resolved_succeeds_for_owner_and_sets_fields():
    owner = make_user("owner")
    author = make_user("author")
    document = make_document(owner.id)
    proposal = make_proposal(document.id, owner.id)
    comment = make_comment(proposal.id, author)

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=comment),
            DummyResult(one=document),
        ]
    )
    service = CommentService(session)

    response = await service.update_comment(
        document_id=document.id,
        proposal_id=proposal.id,
        comment_id=comment.id,
        actor_id=owner.id,
        payload=CommentUpdate(resolved=True),
    )

    assert response.resolved is True
    assert response.resolved_by == owner.id
    assert response.resolved_at is not None


@pytest.mark.asyncio
async def test_update_comment_unresolve_clears_resolution_fields():
    owner = make_user("owner")
    document = make_document(owner.id)
    proposal = make_proposal(document.id, owner.id)
    comment = make_comment(proposal.id, owner)
    comment.resolved = True
    comment.resolved_at = datetime.now(timezone.utc)
    comment.resolved_by = owner.id

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=comment),
            DummyResult(one=document),
        ]
    )
    service = CommentService(session)

    response = await service.update_comment(
        document_id=document.id,
        proposal_id=proposal.id,
        comment_id=comment.id,
        actor_id=owner.id,
        payload=CommentUpdate(resolved=False),
    )

    assert response.resolved is False
    assert response.resolved_by is None
    assert response.resolved_at is None


@pytest.mark.asyncio
async def test_delete_comment_allows_comment_author():
    author = make_user("author")
    document = make_document(uuid.uuid4())
    proposal = make_proposal(document.id, author.id)
    comment = make_comment(proposal.id, author)

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=comment),
            DummyResult(one=document),
        ]
    )
    service = CommentService(session)

    await service.delete_comment(
        document_id=document.id,
        proposal_id=proposal.id,
        comment_id=comment.id,
        actor_id=author.id,
    )

    assert session.deleted == [comment]


@pytest.mark.asyncio
async def test_delete_comment_allows_document_owner():
    owner = make_user("owner")
    author = make_user("author")
    document = make_document(owner.id)
    proposal = make_proposal(document.id, owner.id)
    comment = make_comment(proposal.id, author)

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=comment),
            DummyResult(one=document),
        ]
    )
    service = CommentService(session)

    await service.delete_comment(
        document_id=document.id,
        proposal_id=proposal.id,
        comment_id=comment.id,
        actor_id=owner.id,
    )

    assert session.deleted == [comment]


@pytest.mark.asyncio
async def test_delete_comment_rejects_unrelated_contributor():
    owner = make_user("owner")
    author = make_user("author")
    outsider = make_user("outsider")
    document = make_document(owner.id)
    proposal = make_proposal(document.id, owner.id)
    comment = make_comment(proposal.id, author)

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=comment),
            DummyResult(one=document),
        ]
    )
    service = CommentService(session)

    with pytest.raises(DocumentPermissionDenied):
        await service.delete_comment(
            document_id=document.id,
            proposal_id=proposal.id,
            comment_id=comment.id,
            actor_id=outsider.id,
        )


@pytest.mark.asyncio
async def test_list_comments_rejects_non_owner_non_contributor():
    owner = make_user("owner")
    outsider = make_user("outsider")
    document = make_document(owner.id)
    proposal = make_proposal(document.id, owner.id)

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=document),
            DummyResult(one=None),
        ]
    )
    service = CommentService(session)

    with pytest.raises(DocumentPermissionDenied):
        await service.list_comments(
            document_id=document.id, proposal_id=proposal.id, actor_id=outsider.id
        )


@pytest.mark.asyncio
async def test_list_comments_rejects_archived_document():
    owner = make_user("owner")
    document = make_document(owner.id, archived=True)
    proposal = make_proposal(document.id, owner.id)

    session = QueueSession(
        results=[DummyResult(one=proposal), DummyResult(one=document)]
    )
    service = CommentService(session)

    with pytest.raises(InvalidDocumentState):
        await service.list_comments(
            document_id=document.id, proposal_id=proposal.id, actor_id=owner.id
        )


@pytest.mark.asyncio
async def test_list_comments_returns_counts_for_owner():
    owner = make_user("owner")
    document = make_document(owner.id)
    proposal = make_proposal(document.id, owner.id)
    c1 = make_comment(proposal.id, owner)
    c2 = make_comment(proposal.id, owner)
    c2.resolved = True

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=document),
            DummyResult(one=None),
            DummyResult(scalars_list=[c1, c2]),
        ]
    )
    service = CommentService(session)

    result = await service.list_comments(
        document_id=document.id, proposal_id=proposal.id, actor_id=owner.id
    )

    assert result.total == 2
    assert result.resolved_count == 1
    assert {c.id for c in result.comments} == {c1.id, c2.id}
