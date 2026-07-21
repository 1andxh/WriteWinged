from src.config import config

from .service import MailService


def get_mail_service() -> MailService:
    return MailService(config)
