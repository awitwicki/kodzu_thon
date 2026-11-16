import httpx
import pytest

from kodzu_thon.web.app import create_app
from kodzu_thon.web.config import WebSettings
from tests.unit.web.fake_repo import NOW, FakeRepository
from tests.unit.web.helpers import PASSWORD_HASH, login, set_now


@pytest.fixture(autouse=True)
def pinned_clock(mocker):
    """Pages default to "the last 30 days", so the seeded rows (dated around NOW) are only
    visible while the web clock is near NOW. Tests that need another time call set_now."""
    set_now(mocker, NOW)


@pytest.fixture
def web_settings() -> WebSettings:
    return WebSettings(
        database_url="postgresql://ro:pw@db:5432/kodzu_messages",
        admin_user="admin",
        admin_password_hash=PASSWORD_HASH,
        totp_secret=None,
        cookie_secure=False,
        timezone="Europe/Warsaw",
    )


@pytest.fixture
def fake_repo() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def app(web_settings, fake_repo):
    return create_app(web_settings, repo=fake_repo)


@pytest.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def authed_client(client):
    response = await login(client)
    assert response.status_code == 303, response.text
    return client
