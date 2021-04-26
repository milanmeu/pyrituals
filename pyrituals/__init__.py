import json
from typing import List
from aiohttp import ClientSession

AUTH_URL = "https://rituals.sense-company.com/ocapi/login"
ACCOUNT_URL = "https://rituals.sense-company.com/api/account/hubs"
HUB_URL = "https://rituals.sense-company.com/api/account/hub"
UPDATE_URL = "https://rituals.sense-company.com/api/hub/update/attr"


class Diffuser:
    def __init__(self, data, session: ClientSession = None) -> None:
        """Initialize the diffuser."""
        self.data = data
        self._session = session

    @property
    def battery_percentage(self) -> int:
        """Return the diffuser battery percentage."""
        # Use ICON because TITLE may change in the future.
        # ICON filename does not match the image.
        return {
            "battery-charge.png": 100,
            "battery-full.png": 100,
            "Battery-75.png": 50,
            "battery-50.png": 25,
            "battery-low.png": 10,
        }[self.hub_data["sensors"]["battc"]["icon"]]

    @property
    def charging(self) -> bool:
        """Return if the diffuser is charging."""
        return self.hub_data["sensors"]["battc"]["id"] == 21

    @property
    def has_battery(self) -> bool:
        """Return if the diffuser has a battery."""
        return "battc" in self.hub_data["sensors"]

    @property
    def hash(self) -> str:
        """Return the diffuser hash."""
        return self.hub_data["hash"]

    @property
    def hub_data(self):
        return self.data["hub"]

    @property
    def is_on(self):
        return self.hub_data["attributes"]["fanc"] == "1"

    @property
    def wifi_percentage(self) -> int:
        """Return the diffuser wifi percentage."""
        # Use ICON because TITLE may change in the future.
        return {
            "icon-signal.png": 100,
            "icon-signal-75.png": 75,
            "icon-signal-low.png": 25,
            "icon-signal-0.png": 0,
        }[self.hub_data["sensors"]["wific"]["icon"]]

    async def update_data(self, session: ClientSession = None, url: str = HUB_URL) -> None:
        """Get updated diffuser data."""
        if session is None:
            session = self._session
        async with session.get(f'{url}/{self.hash}') as resp:
            resp.raise_for_status()
            self.data = await resp.json()

    async def turn_on(self, session: ClientSession = None, url: str = UPDATE_URL) -> None:
        """Turn the diffuser on."""
        if session is None:
            session = self._session
        async with session.post(url, data={'hub': self.hash, 'json': '{"attr": {"fanc": "1"}}'}) as resp:
            resp.raise_for_status()

    async def turn_off(self, session: ClientSession = None, url: str = UPDATE_URL) -> None:
        """Turn the diffuser off."""
        if session is None:
            session = self._session
        async with session.post(url, data={'hub': self.hash, 'json': '{"attr": {"fanc": "0"}}'}) as resp:
            resp.raise_for_status()

    async def set_perfume_amount(self, amount: int, session: ClientSession = None, url: str = UPDATE_URL) -> None:
        """Set the diffuser perfume amount."""
        amount = int(amount)
        if amount not in range(1, 4):
            raise ValueError("Amount must be an integer between 1 and 3, inclusive.")
        if session is None:
            session = self._session
        async with session.post(url, data={'hub': self.hash, 'json': json.dumps({"attr": {"speedc": amount}})}) as resp:
            resp.raise_for_status()

    async def set_room_size(self, size: int, session: ClientSession = None, url: str = UPDATE_URL) -> None:
        """Set the diffuser room size."""
        size = int(size)
        if size not in range(1, 5):
            raise ValueError("Size must be an integer between 1 and 4, inclusive.")
        if session is None:
            session = self._session
        async with session.post(url, data={'hub': self.hash, 'json': json.dumps({"attr": {"roomc": size}})}) as resp:
            resp.raise_for_status()


class Account:
    def __init__(self, email: str = "", password: str = "", session: ClientSession = None) -> None:
        """Initialize the account."""
        self._password = password
        self._email = email
        self._session = session
        self.data = None

    async def authenticate(self, session: ClientSession = None, url: str = AUTH_URL) -> None:
        """Authenticate and save account data."""
        if session is None:
            session = self._session
        async with session.post(url, data={'email': self._email, 'password': self._password}) as resp:
            resp.raise_for_status()
            resp_data = await resp.json()
            if resp_data["logged_id"] != 1:
                raise AuthenticationException(resp_data["error"])
            self.data = resp_data

    async def get_devices(self, session: ClientSession = None, url: str = ACCOUNT_URL) -> List[Diffuser]:
        """Get all devices linked to the account."""
        if session is None:
            session = self._session
        async with session.get(f'{url}/{self.data["account_hash"]}') as resp:
            resp.raise_for_status()
            return [Diffuser(device_data, session) for device_data in await resp.json()]


class AuthenticationException(Exception):
    pass
