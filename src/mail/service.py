from datetime import datetime, timezone
from typing import TYPE_CHECKING
from urllib.parse import quote

from itsdangerous import URLSafeTimedSerializer

from ..auth.models import User
from ..auth.templates import templates
from ..exceptions import InvalidTokenException
from .mail import create_message, mail
from .utils import decode_url_safe_token

if TYPE_CHECKING:
    from ..core.contributions.models import ContributionRequestORM
    from ..core.documents.models import DocumentORM
    from ..core.proposals.models import ProposalORM

INVITE_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7  # 7 days


class MailService:
    def __init__(self, config) -> None:
        email_secret = config.EMAIL_SECRET or config.JWT_SECRET
        reset_secret = config.PASSWORD_RESET_SECRET or config.JWT_SECRET
        self.frontend_base = config.FRONTEND_URL or "http://localhost:5173"
        self.email_serializer = URLSafeTimedSerializer(
            secret_key=email_secret, salt="email-verification"
        )
        self.password_reset_serializer = URLSafeTimedSerializer(
            secret_key=reset_secret, salt="password-reset"
        )
        self.invite_serializer = URLSafeTimedSerializer(
            secret_key=email_secret, salt="contributor-invite"
        )

    def create_email_verification_token(self, data: dict) -> str:
        return self.email_serializer.dumps(data)

    def create_password_reset_token(self, data: dict) -> str:
        return self.password_reset_serializer.dumps(data)

    def create_invite_token(self, data: dict) -> str:
        return self.invite_serializer.dumps(data)

    def decode_email_verification_token(self, token: str) -> str:
        data = decode_url_safe_token(token, self.email_serializer)
        email = data.get("email")
        if not email:
            raise InvalidTokenException()
        return email

    def decode_password_reset_token(self, token: str) -> str:
        data = decode_url_safe_token(token, self.password_reset_serializer)
        if data.get("type") != "password-reset" or not data.get("email"):
            raise InvalidTokenException()
        return data["email"]

    def decode_invite_token(self, token: str) -> dict:
        data = decode_url_safe_token(
            token, self.invite_serializer, max_age=INVITE_TOKEN_MAX_AGE_SECONDS
        )
        if (
            data.get("type") != "contributor-invite"
            or not data.get("email")
            or not data.get("document_id")
        ):
            raise InvalidTokenException()
        return data

    async def _send(self, recipients: list[str], subject: str, html: str) -> None:
        message = create_message(recipients=recipients, subject=subject, body=html)
        await mail.send_message(message)

    async def send_verification_email(self, user: User) -> None:
        token = self.create_email_verification_token({"email": user.email})
        link = f"{self.frontend_base}/verify?token={quote(token, safe='')}"
        html = templates.get_template("verify_email.html").render(
            username=user.username, link=link, year=datetime.now(timezone.utc).year
        )
        await self._send([user.email], "Verify your email address", html)

    async def send_password_reset_email(self, email: str) -> None:
        token = self.create_password_reset_token(
            {"email": email, "type": "password-reset"}
        )
        link = f"{self.frontend_base}/reset-password?token={quote(token, safe='')}"
        html = templates.get_template("password_reset.html").render(
            link=link, year=datetime.now(timezone.utc).year
        )
        await self._send([email], "Reset your password", html)

    async def send_contributor_invite_email(
        self,
        invitee_email: str,
        inviter_name: str,
        document_id,
        document_title: str,
    ) -> None:
        token = self.create_invite_token(
            {
                "email": invitee_email,
                "document_id": str(document_id),
                "type": "contributor-invite",
            }
        )
        link = f"{self.frontend_base}/invite?token={quote(token, safe='')}"
        html = templates.get_template("contributor_invite.html").render(
            inviter_name=inviter_name,
            document_title=document_title,
            link=link,
            year=datetime.now(timezone.utc).year,
        )
        subject = f"{inviter_name} invited you to collaborate on Limarr"
        await self._send([invitee_email], subject, html)

    async def send_proposal_created_email(
        self, owner: User, document: "DocumentORM", proposal: "ProposalORM"
    ) -> None:
        link = f"{self.frontend_base}/app/{document.id}/proposals"
        html = templates.get_template("proposal_created.html").render(
            owner_name=owner.username,
            contributor_name=proposal.author.username,
            document_title=document.title,
            proposal_title=proposal.title,
            link=link,
            year=datetime.now(timezone.utc).year,
        )
        await self._send([owner.email], f"New proposal on “{document.title}”", html)

    async def send_contribution_requested_email(
        self,
        owner: User,
        document: "DocumentORM",
        request: "ContributionRequestORM",
        requester: User,
    ) -> None:
        link = f"{self.frontend_base}/app/{document.id}/contributors"
        html = templates.get_template("contribution_requested.html").render(
            owner_name=owner.username,
            requester_name=requester.username,
            document_title=document.title,
            message=request.message,
            link=link,
            year=datetime.now(timezone.utc).year,
        )
        await self._send(
            [owner.email],
            f"{requester.username} wants to collaborate on “{document.title}”",
            html,
        )
