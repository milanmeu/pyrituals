from typing import List
import aiohttp

AUTH_URL = "https://rituals.sense-company.com/ocapi/login"
ACCOUNT_URL = "https://rituals.sense-company.com/api/account/hubs"
HUB_URL = "https://rituals.sense-company.com/api/account/hub"
UPDATE_URL = "https://rituals.sense-company.com/api/hub/update/attr"


class Diffuser:
    def __init__(self, data):
        """Initialize the diffuser."""
        self.data = data

    async def update_data(self, session: aiohttp.ClientSession, url: str = HUB_URL):
        """Get updated diffuser data."""
        async with session.get(f'{url}/{self.data["hub"]["hash"]}') as resp:
            resp.raise_for_status()
            self.data = await resp.json()

    async def turn_on(self, session: aiohttp.ClientSession, url: str = UPDATE_URL):
        """Turn the diffuser on."""
        async with session.post(url, data={'hub': self.data["hub"]["hash"], 'json': '{"attr":{"fanc":"1"}}'}) as resp:
            resp.raise_for_status()

    async def turn_off(self, session: aiohttp.ClientSession, url: str = UPDATE_URL):
        """Turn the diffuser off."""
        async with session.post(url, data={'hub': self.data["hub"]["hash"], 'json': '{"attr":{"fanc":"0"}}'}) as resp:
            resp.raise_for_status()


class Account:
    def __init__(self, email: str, password: str):
        """Initialize the account."""
        self._password = password
        self._email = email
        self.data = None

    async def authenticate(self, session: aiohttp.ClientSession, url: str = AUTH_URL):
        """Authenticate and save account data."""
        async with session.post(url, data={'email': self._email, 'password': self._password}) as resp:
            resp.raise_for_status()
            resp_data = await resp.json()
            if resp_data["logged_id"] != 1:
                raise AuthenticationException(resp_data["error"])
            self.data = resp_data

    async def get_devices(self, session: aiohttp.ClientSession, url: str = ACCOUNT_URL) -> List[Diffuser]:
        """Get all devices linked to the account."""
        async with session.get(f'{url}/{self.data["account_hash"]}') as resp:
            resp.raise_for_status()
            return [Diffuser(device_data) for device_data in await resp.json()]


class AuthenticationException(Exception):
    pass
