from pathlib import Path
from pydantic import SecretStr


from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from src.config import config

BASE_DIR = Path(__file__).resolve().parent.parent

mail_config = ConnectionConfig(
    MAIL_USERNAME=config.MAIL_USERNAME,
    MAIL_PASSWORD=SecretStr(config.MAIL_PASSWORD),
    MAIL_PORT=config.MAIL_PORT,
    MAIL_SERVER=config.MAIL_SERVER,
    MAIL_STARTTLS=config.MAIL_STARTTLS,
    MAIL_SSL_TLS=config.MAIL_SSL_TLS,
    MAIL_FROM=config.MAIL_FROM,
    MAIL_FROM_NAME=config.MAIL_FROM_NAME,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=Path(BASE_DIR, "templates"),
)

mail = FastMail(config=mail_config)


def create_message(recipients, subject: str, body: str) -> MessageSchema:
    return MessageSchema(
        recipients=recipients, subject=subject, body=body, subtype=MessageType.html
    )
