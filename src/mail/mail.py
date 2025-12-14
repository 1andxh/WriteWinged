from fastapi_mail import FastMail, ConnectionConfig, MessageSchema, MessageType
from src.config import config
from typing import List

mail_config = ConnectionConfig(
    MAIL_USERNAME=config.MAIL_USERNAME,
    MAIL_PASSWORD=config.MAIL_PASSWORD,
    MAIL_PORT=587,
    MAIL_SERVER=config.MAIL_SERVER,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    MAIL_FROM=config.MAIL_FROM,
    MAIL_FROM_NAME=config.MAIL_FROM_NAME,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

mail = FastMail(config=mail_config)


def create_message(recepients, subject: str, body: str):
    message = MessageSchema(
        recipients=recepients, subject=subject, body=body, subtype=MessageType.html
    )
    return message
