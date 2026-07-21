import uuid

import pytest

from src.auth.models import User, UserRole
from src.core.contributions.models import ContributionORM
from src.core.documents.models import DocumentORM, DocumentState, DocumentVisibility
from src.core.proposals.models import ProposalORM, ProposalState
from src.core.proposals.services import ProposalService


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

    async def flush(self):
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


def make_proposal(document_id: uuid.UUID, author_id: uuid.UUID) -> ProposalORM:
    return ProposalORM(
        id=uuid.uuid4(),
        document_id=document_id,
        author_id=author_id,
        content="proposed text",
        state=ProposalState.OPEN,
    )


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
        document_id=document.id, actor_id=owner.id, content="new text"
    )

    assert proposal.comment_count == 0
    assert proposal.resolved_count == 0


@pytest.mark.asyncio
async def test_get_proposal_attaches_comment_counts():
    owner = make_user("owner")
    document = make_document(owner.id)
    proposal = make_proposal(document.id, owner.id)

    session = QueueSession(
        results=[
            DummyResult(one=proposal),
            DummyResult(one=document),
            DummyResult(one=None),
            DummyResult(rows=[(proposal.id, 4, 2)]),
        ]
    )
    service = ProposalService(session)

    result = await service.get_proposal(proposal_id=proposal.id, actor_id=owner.id)

    assert result.comment_count == 4
    assert result.resolved_count == 2


@pytest.mark.asyncio
async def test_list_proposals_attaches_counts_and_defaults_zero_when_no_comments():
    owner = make_user("owner")
    document = make_document(owner.id)
    commented = make_proposal(document.id, owner.id)
    uncommented = make_proposal(document.id, owner.id)

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
