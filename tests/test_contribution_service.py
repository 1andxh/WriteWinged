import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from src.auth.models import User, UserRole
from src.core.contributions.models import ContributionORM
from src.core.contributions.services import ContributionService
from src.core.documents.models import DocumentORM, DocumentState, DocumentVisibility
from src.exceptions import (
    ContributionAlreadyExists,
    DocumentPermissionDenied,
    InvalidContributionTarget,
    InvalidDocumentState,
    InvitationEmailMismatch,
    UserNotFoundException,
)


class DummyResult:
    def __init__(self, one=None):
        self._one = one

    def scalar_one_or_none(self):
        return self._one


class QueueSession:
    def __init__(self, results, users_by_id=None, raise_integrity_error=False):
        self._results = list(results)
        self.added = []
        self._users_by_id = users_by_id or {}
        self._raise_integrity_error = raise_integrity_error

    async def execute(self, statement):
        return self._results.pop(0)

    async def get(self, model, obj_id):
        return self._users_by_id.get(obj_id)

    def add(self, obj):
        self.added.append(obj)
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()

    async def flush(self):
        if self._raise_integrity_error:
            raise IntegrityError("insert", {}, Exception("duplicate key"))
        return None


class FakeMailService:
    def __init__(self, invite_data=None):
        self._invite_data = invite_data

    def decode_invite_token(self, token: str) -> dict:
        return self._invite_data

    async def send_contributor_invite_email(self, **kwargs) -> None:
        return None


class FakeBackgroundTasks:
    def __init__(self):
        self.tasks = []

    def add_task(self, func, *args, **kwargs):
        self.tasks.append((func, args, kwargs))


def make_user(username: str = "user") -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{username}@example.com",
        username=username,
        role=UserRole.USER,
    )


def make_document(owner_id: uuid.UUID, state=DocumentState.ACTIVE) -> DocumentORM:
    return DocumentORM(
        id=uuid.uuid4(),
        title="Doc",
        owner_id=owner_id,
        state=state,
        visibility=DocumentVisibility.PUBLIC,
        deleted_at=None,
    )


def invite_data(email: str, document_id: uuid.UUID) -> dict:
    return {
        "email": email,
        "document_id": str(document_id),
        "type": "contributor-invite",
    }


# ── invite_contributor ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invite_contributor_sends_email_and_returns_receipt():
    owner = make_user("owner")
    invitee = make_user("invitee")
    document = make_document(owner.id)

    session = QueueSession(
        # order: get_user_by_email, document lookup, existing-contribution check
        results=[
            DummyResult(one=invitee),
            DummyResult(one=document),
            DummyResult(one=None),
        ],
        users_by_id={owner.id: owner},
    )
    mail_service = FakeMailService()
    background_tasks = FakeBackgroundTasks()
    service = ContributionService(session, mail_service)

    result = await service.invite_contributor(
        document_id=document.id,
        email=invitee.email,
        actor_id=owner.id,
        background_tasks=background_tasks,
    )

    assert result.message == "Invitation sent"
    assert result.email == invitee.email
    assert len(background_tasks.tasks) == 1
    func, args, kwargs = background_tasks.tasks[0]
    assert func == mail_service.send_contributor_invite_email
    assert kwargs["invitee_email"] == invitee.email
    assert kwargs["inviter_name"] == owner.username
    assert kwargs["document_id"] == document.id


@pytest.mark.asyncio
async def test_invite_contributor_rejects_non_owner():
    owner = make_user("owner")
    not_owner = make_user("not-owner")
    invitee = make_user("invitee")
    document = make_document(owner.id)

    session = QueueSession(
        results=[DummyResult(one=invitee), DummyResult(one=document)]
    )
    service = ContributionService(session, FakeMailService())

    with pytest.raises(DocumentPermissionDenied):
        await service.invite_contributor(
            document_id=document.id,
            email=invitee.email,
            actor_id=not_owner.id,
            background_tasks=FakeBackgroundTasks(),
        )


@pytest.mark.asyncio
async def test_invite_contributor_rejects_unknown_email():
    owner = make_user("owner")
    document = make_document(owner.id)

    session = QueueSession(results=[DummyResult(one=None)])
    service = ContributionService(session, FakeMailService())

    with pytest.raises(UserNotFoundException):
        await service.invite_contributor(
            document_id=document.id,
            email="nobody@example.com",
            actor_id=owner.id,
            background_tasks=FakeBackgroundTasks(),
        )


# ── preview_invitation ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_preview_invitation_returns_document_and_inviter():
    owner = make_user("owner")
    invitee = make_user("invitee")
    document = make_document(owner.id)

    session = QueueSession(
        results=[DummyResult(one=document)],
        users_by_id={owner.id: owner},
    )
    mail_service = FakeMailService(invite_data(invitee.email, document.id))
    service = ContributionService(session, mail_service)

    preview = await service.preview_invitation(token="tok", actor=invitee)

    assert preview.document_id == document.id
    assert preview.document_title == document.title
    assert preview.inviter_name == owner.username
    assert preview.invitee_email == invitee.email


@pytest.mark.asyncio
async def test_preview_invitation_rejects_email_mismatch():
    owner = make_user("owner")
    invitee = make_user("invitee")
    wrong_user = make_user("someone-else")
    document = make_document(owner.id)

    session = QueueSession(results=[])
    mail_service = FakeMailService(invite_data(invitee.email, document.id))
    service = ContributionService(session, mail_service)

    with pytest.raises(InvitationEmailMismatch):
        await service.preview_invitation(token="tok", actor=wrong_user)


# ── accept_invitation ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_accept_invitation_creates_contribution():
    owner = make_user("owner")
    invitee = make_user("invitee")
    document = make_document(owner.id)

    session = QueueSession(
        results=[DummyResult(one=document), DummyResult(one=None)],
    )
    mail_service = FakeMailService(invite_data(invitee.email, document.id))
    service = ContributionService(session, mail_service)

    contributor = await service.accept_invitation(token="tok", actor=invitee)

    assert contributor.id == invitee.id
    assert contributor.email == invitee.email
    assert len(session.added) == 1


@pytest.mark.asyncio
async def test_accept_invitation_rejects_when_actor_is_now_the_owner():
    owner = make_user("owner")
    document = make_document(owner.id)

    session = QueueSession(results=[DummyResult(one=document)])
    mail_service = FakeMailService(invite_data(owner.email, document.id))
    service = ContributionService(session, mail_service)

    with pytest.raises(InvalidContributionTarget):
        await service.accept_invitation(token="tok", actor=owner)


@pytest.mark.asyncio
async def test_accept_invitation_rejects_archived_document():
    owner = make_user("owner")
    invitee = make_user("invitee")
    document = make_document(owner.id, state=DocumentState.ARCHIVED)

    session = QueueSession(results=[DummyResult(one=document)])
    mail_service = FakeMailService(invite_data(invitee.email, document.id))
    service = ContributionService(session, mail_service)

    with pytest.raises(InvalidDocumentState):
        await service.accept_invitation(token="tok", actor=invitee)


@pytest.mark.asyncio
async def test_accept_invitation_rejects_duplicate_via_precheck():
    owner = make_user("owner")
    invitee = make_user("invitee")
    document = make_document(owner.id)
    existing = ContributionORM(
        id=uuid.uuid4(), document_id=document.id, user_id=invitee.id
    )

    session = QueueSession(
        results=[DummyResult(one=document), DummyResult(one=existing)],
    )
    mail_service = FakeMailService(invite_data(invitee.email, document.id))
    service = ContributionService(session, mail_service)

    with pytest.raises(ContributionAlreadyExists):
        await service.accept_invitation(token="tok", actor=invitee)


@pytest.mark.asyncio
async def test_accept_invitation_double_click_race_returns_conflict_not_500():
    """The pre-check can pass and still race with a concurrent accept; the
    DB's uq_contribution_document_user constraint is the real guard, and a
    raised IntegrityError must be translated into the same 409, not bubble
    up as an unhandled 500."""
    owner = make_user("owner")
    invitee = make_user("invitee")
    document = make_document(owner.id)

    session = QueueSession(
        results=[DummyResult(one=document), DummyResult(one=None)],
        raise_integrity_error=True,
    )
    mail_service = FakeMailService(invite_data(invitee.email, document.id))
    service = ContributionService(session, mail_service)

    with pytest.raises(ContributionAlreadyExists):
        await service.accept_invitation(token="tok", actor=invitee)
