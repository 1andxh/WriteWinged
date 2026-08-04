import uuid
from datetime import datetime, timezone

import pytest

from src.auth.models import User, UserRole
from src.core.comments.models import CommentORM
from src.core.contributions.models import ContributionORM
from src.core.documents.models import DocumentORM, DocumentState, DocumentVisibility
from src.core.proposals.models import ProposalORM, ProposalState
from src.core.proposals.services import ProposalService
from src.exceptions import DocumentPermissionDenied


class DummyResult:
    def __init__(self, one=None, scalars_list=None, rows=None):
        self._one = one
        self._scalars_list = scalars_list or []
        self._rows = rows or []

    def scalar_one_or_none(self):
        return self._one

    def scalars(self):
        return self

    def all(self):
        return self._rows or self._scalars_list


class QueueSession:
    def __init__(self, results):
        self._results = list(results)
        self.added = []

    async def execute(self, statement):
        return self._results.pop(0)

    def add(self, obj):
        self.added.append(obj)
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now(timezone.utc)

    async def flush(self):
        return None

    async def commit(self):
        return None


def make_user(username: str = "writer") -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{username}@example.com",
        username=username,
        role=UserRole.USER,
    )


def make_document(owner_id: uuid.UUID) -> DocumentORM:
    return DocumentORM(
        id=uuid.uuid4(),
        title="Doc",
        owner_id=owner_id,
        state=DocumentState.ACTIVE,
        visibility=DocumentVisibility.PUBLIC,
    )


def make_proposal(document_id: uuid.UUID, author: User) -> ProposalORM:
    proposal = ProposalORM(
        id=uuid.uuid4(),
        document_id=document_id,
        author_id=author.id,
        content="proposed text",
        state=ProposalState.OPEN,
        created_at=datetime.now(timezone.utc),
    )
    proposal.author = author
    return proposal


@pytest.mark.asyncio
async def test_create_proposal_starts_with_zero_comment_counts():
    owner = make_user("owner")
    document = make_document(owner.id)
    contribution = ContributionORM(
        id=uuid.uuid4(), document_id=document.id, user_id=owner.id
    )

    session = QueueSession(
        results=[DummyResult(one=document), DummyResult(one=contribution)]
    )
    service = ProposalService(session)

    proposal = await service.create_proposal(
        document_id=document.id, actor=owner, content="new text", title="New proposal"
    )

    assert proposal.comment_count == 0
    assert proposal.resolved_count == 0


@pytest.mark.asyncio
async def test_get_proposal_attaches_comment_counts():
    owner = make_user("owner")
    document = make_document(owner.id)
    proposal = make_proposal(document.id, owner)

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=document),
            DummyResult(one=None),
            DummyResult(rows=[(proposal.id, 4, 2)]),
            DummyResult(scalars_list=[]),
        ]
    )
    service = ProposalService(session)

    result = await service.get_proposal(proposal_id=proposal.id, actor_id=owner.id)

    assert result.comment_count == 4
    assert result.resolved_count == 2


@pytest.mark.asyncio
async def test_get_proposal_includes_first_page_of_comments():
    owner = make_user("owner")
    document = make_document(owner.id)
    proposal = make_proposal(document.id, owner)
    commenter = make_user("commenter")
    comment = CommentORM(
        id=uuid.uuid4(),
        proposal_id=proposal.id,
        author_id=commenter.id,
        text="looks good",
        resolved=False,
        inline=False,
        line_number=None,
        parent_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    comment.author = commenter

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=document),
            DummyResult(one=None),
            DummyResult(rows=[]),
            DummyResult(scalars_list=[comment]),
        ]
    )
    service = ProposalService(session)

    result = await service.get_proposal(proposal_id=proposal.id, actor_id=owner.id)

    assert len(result.comments) == 1
    assert result.comments[0].text == "looks good"
    assert result.comments[0].author_name == "commenter"


@pytest.mark.asyncio
async def test_get_proposal_allows_reader_on_public_document():
    owner = make_user("owner")
    document = make_document(owner.id)
    proposal = make_proposal(document.id, owner)
    reader = make_user("reader")

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=document),
            DummyResult(one=None),
            DummyResult(rows=[]),
            DummyResult(scalars_list=[]),
        ]
    )
    service = ProposalService(session)

    result = await service.get_proposal(proposal_id=proposal.id, actor_id=reader.id)

    assert result.id == proposal.id


@pytest.mark.asyncio
async def test_get_proposal_denies_reader_on_private_document():
    owner = make_user("owner")
    document = make_document(owner.id)
    document.visibility = DocumentVisibility.PRIVATE
    proposal = make_proposal(document.id, owner)
    reader = make_user("reader")

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=document),
            DummyResult(one=None),
        ]
    )
    service = ProposalService(session)

    with pytest.raises(DocumentPermissionDenied):
        await service.get_proposal(proposal_id=proposal.id, actor_id=reader.id)


@pytest.mark.asyncio
async def test_list_proposals_attaches_counts_and_defaults_zero_when_no_comments():
    owner = make_user("owner")
    document = make_document(owner.id)
    commented = make_proposal(document.id, owner)
    uncommented = make_proposal(document.id, owner)

    session = QueueSession(
        results=[
            DummyResult(one=document),
            DummyResult(one=None),
            DummyResult(scalars_list=[commented, uncommented]),
            DummyResult(rows=[(commented.id, 3, 1)]),
        ]
    )
    service = ProposalService(session)

    proposals = await service.list_proposals(document_id=document.id, actor_id=owner.id)

    by_id = {p.id: p for p in proposals}
    assert by_id[commented.id].comment_count == 3
    assert by_id[commented.id].resolved_count == 1
    assert by_id[uncommented.id].comment_count == 0
    assert by_id[uncommented.id].resolved_count == 0


@pytest.mark.asyncio
async def test_list_proposals_skips_count_query_when_empty():
    owner = make_user("owner")
    document = make_document(owner.id)

    session = QueueSession(
        results=[
            DummyResult(one=document),
            DummyResult(one=None),
            DummyResult(scalars_list=[]),
        ]
    )
    service = ProposalService(session)

    proposals = await service.list_proposals(document_id=document.id, actor_id=owner.id)

    assert proposals == []


@pytest.mark.asyncio
async def test_list_proposals_allows_reader_on_public_document():
    owner = make_user("owner")
    document = make_document(owner.id)
    reader = make_user("reader")

    session = QueueSession(
        results=[
            DummyResult(one=document),
            DummyResult(one=None),
            DummyResult(scalars_list=[]),
        ]
    )
    service = ProposalService(session)

    proposals = await service.list_proposals(
        document_id=document.id, actor_id=reader.id
    )

    assert proposals == []


@pytest.mark.asyncio
async def test_list_proposals_denies_reader_on_private_document():
    owner = make_user("owner")
    document = make_document(owner.id)
    document.visibility = DocumentVisibility.PRIVATE
    reader = make_user("reader")

    session = QueueSession(
        results=[
            DummyResult(one=document),
            DummyResult(one=None),
        ]
    )
    service = ProposalService(session)

    with pytest.raises(DocumentPermissionDenied):
        await service.list_proposals(document_id=document.id, actor_id=reader.id)


@pytest.mark.asyncio
async def test_merge_proposal_resolves_open_comments():
    owner = make_user("owner")
    document = make_document(owner.id)
    document.versions = []
    proposal = make_proposal(document.id, owner)
    proposal.state = ProposalState.ACCEPTED
    proposal.title = "Some title"
    open_comment = CommentORM(
        id=uuid.uuid4(),
        proposal_id=proposal.id,
        author_id=owner.id,
        text="still open",
        resolved=False,
    )

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=document),
            DummyResult(scalars_list=[open_comment]),
        ]
    )
    service = ProposalService(session)

    await service.merge_proposal(proposal_id=proposal.id, actor_id=owner.id)

    assert open_comment.resolved is True
    assert open_comment.resolved_by == owner.id
    assert open_comment.resolved_at is not None


@pytest.mark.asyncio
async def test_reject_proposal_with_reason_creates_a_comment():
    owner = make_user("owner")
    document = make_document(owner.id)
    proposal = make_proposal(document.id, owner)

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=document),
        ]
    )
    service = ProposalService(session)

    await service.reject_proposal(
        proposal_id=proposal.id,
        actor_id=owner.id,
        reason="not aligned with style guide",
    )

    assert proposal.state == ProposalState.REJECTED
    assert len(session.added) == 1
    rejection_comment = session.added[0]
    assert rejection_comment.text == "Rejected: not aligned with style guide"
    assert rejection_comment.author_id == owner.id


@pytest.mark.asyncio
async def test_reject_proposal_without_reason_does_not_create_a_comment():
    owner = make_user("owner")
    document = make_document(owner.id)
    proposal = make_proposal(document.id, owner)

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=document),
        ]
    )
    service = ProposalService(session)

    await service.reject_proposal(proposal_id=proposal.id, actor_id=owner.id)

    assert proposal.state == ProposalState.REJECTED
    assert session.added == []
