from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware
from .config import config

secret_key = config.MIDDLEWARE_SECRET


def register_middleware(app: FastAPI):

    app.add_middleware(SessionMiddleware, secret_key)  # required for OAuth to work
