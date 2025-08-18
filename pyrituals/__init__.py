# Implementation for Rituals Perfume Genie integration.
from __future__ import annotations

import json, re
from typing import Any, Optional, List
from aiohttp import ClientSession, ClientError

# Constants used in the Rituals Perfume Genie integration.
AUTH_URL   = "https://rituals.sense-company.com/ocapi/login"
ACCOUNT_URL= "https://rituals.sense-company.com/api/account/hubs"
HUB_URL    = "https://rituals.sense-company.com/api/account/hub"
UPDATE_URL = "https://rituals.sense-company.com/api/hub/update/attr"

# Update to support pyrituals v0.0.7 (API v2).
_BASE      = "https://rituals.apiv2.sense-company.com"
_AUTH_V2   = f"{_BASE}/apiv2/account/token"
_HUBS_V2   = f"{_BASE}/apiv2/account/hubs"
_ATTR_V2   = f"{_BASE}/apiv2/hubs/{{hub}}/attributes/{{attr}}"
_SENS_V2   = f"{_BASE}/apiv2/hubs/{{hub}}/sensors/{{sensor}}"

class AuthenticationException(Exception):
    pass

class _Api:
    def __init__(self, session: Optional[ClientSession]) -> None:
        self._session = session
        self._own = False
        self._token: Optional[str] = None

    async def __aenter__(self) -> "_Api":
        if self._session is None:
            self._session = ClientSession()
            self._own = True
        return self

    async def __aexit__(self, *exc) -> None:
        if self._own and self._session:
            await self._session.close()

    @property
    def session(self) -> ClientSession:
        assert self._session is not None
        return self._session

    def set_token(self, token: str) -> None:
        self._token = token

    def _headers(self) -> dict:
        h = {"Accept": "*/*"}
        if self._token:
            h["Authorization"] = self._token
        return h

    async def get_json(self, url: str) -> Any:
        async with self.session.get(url, headers=self._headers(), timeout=10) as r:
            if r.status == 401:
                raise AuthenticationException("Unauthorized (401)")
            r.raise_for_status()
            return await r.json()

    async def post_form(self, url: str, form: dict[str, str]) -> Any:
        from aiohttp import FormData
        fd = FormData()
        for k, v in form.items():
            fd.add_field(k, str(v))
        h = self._headers()
        h["Content-Type"] = "application/x-www-form-urlencoded"
        async with self.session.post(url, headers=h, data=fd, timeout=10) as r:
            if r.status == 401:
                raise AuthenticationException("Unauthorized (401)")
            r.raise_for_status()
            if "application/json" in (r.headers.get("Content-Type") or ""):
                return await r.json()
            return await r.text()

    async def post_json(self, url: str, body: dict) -> Any:
        h = self._headers()
        h["Content-Type"] = "application/json"
        async with self.session.post(url, headers=h, json=body, timeout=10) as r:
            r.raise_for_status()
            return await r.json()

class Account:
    def __init__(
        self,
        email: str = "",
        password: str = "",
        session: ClientSession | None = None,
        account_hash: str = ""  # bleibt für compat, wird in V2 nicht genutzt
    ) -> None:
        self._password = password
        self._email = email
        self._session = session
        self.data: dict[str, Any] | None = None
        self.account_hash: str = account_hash  # Dummy
        self._api = _Api(session)

    @property
    def email(self) -> str:
        return self._email

    async def authenticate(self, session: ClientSession = None, url: str = AUTH_URL) -> None:
        """V2: POST /apiv2/account/token → {success: <TOKEN>}  (Signatur bleibt)"""
        if session is None:
            session = self._session
        # use internal API client
        self._api._session = session or self._api._session
        try:
            res = await self._api.post_json(_AUTH_V2, {"email": self._email, "password": self._password})
        except ClientError as e:
            raise AuthenticationException(f"Auth HTTP error: {e}") from e

        token = res.get("success")
        if not token:
            raise AuthenticationException(res.get("message") or "No success token")
        self._api.set_token(token)
        # Compatible minimal data (previously more was returned)
        self.data = {"email": self._email}
        # account_hash no longer exists in V2 – leave empty:
        self.account_hash = ""

    async def get_devices(self, session: ClientSession = None, url: str = ACCOUNT_URL) -> list["Diffuser"]:
        """Compat: ignoriert url/account_hash und nutzt V2 /apiv2/account/hubs"""
        if session is None:
            session = self._session
        self._api._session = session or self._api._session
        hubs = await self._api.get_json(_HUBS_V2)
        if not isinstance(hubs, list):
            raise RuntimeError("Invalid hubs response")
        return [Diffuser({"hub": _v2_hub_to_v1_shape(h)}, self._api) for h in hubs]  # v1-Shape synth.

def _v2_hub_to_v1_shape(h: dict) -> dict:
    """Erzeuge alte v1-Struktur unter 'hub' aus V2-Hub-Element."""
    # We only know master data here. Attributes/sensors are added during update_data().
    return {
        "hash":   h.get("hash",""),
        "hublot": h.get("hublot",""),
        "status": 1,  # conservative "online", will be clarified later if necessary
        "attributes": {
            "roomnamec": (h.get("attributeValues") or {}).get("roomnamec","Genie"),
            # fanc/speedc werden bei update_data() per GET befüllt
        },
        "sensors": {
            # rfidc/fillc/battc/wific/versionc are filled with update_data()
        }
    }

class Diffuser:
    def __init__(self, data: dict, api: _Api) -> None:
        self.data = data            # v1-Shape: {"hub": {...}}
        self._api = api

    # --- v1 Properties (use self.hub_data, which we fill synthetically) ---
    @property
    def hub_data(self) -> dict:
        return self.data["hub"]

    @property
    def hash(self) -> str:
        return self.hub_data["hash"]

    @property
    def hublot(self) -> str:
        return self.hub_data["hublot"]

    @property
    def name(self) -> str:
        return self.hub_data["attributes"].get("roomnamec","Genie")

    @property
    def is_online(self) -> bool:
        return self.hub_data.get("status",1) == 1

    @property
    def is_on(self) -> bool:
        return self.hub_data.get("attributes",{}).get("fanc","0") == "1"

    @property
    def perfume_amount(self) -> int:
        try:
            return int(self.hub_data.get("attributes",{}).get("speedc","1"))
        except ValueError:
            return 1

    @property
    def fill(self) -> str:
        return self.hub_data.get("sensors",{}).get("fillc",{}).get("title","")

    @property
    def perfume(self) -> str:
        return self.hub_data.get("sensors",{}).get("rfidc",{}).get("title","")

    @property
    def has_cartridge(self) -> bool:
        # Compatible: id!=19 ⇒ Cartridge present; if unknown: True
        rid = self.hub_data.get("sensors",{}).get("rfidc",{}).get("id")
        return True if rid is None else (rid != 19)

    @property
    def has_battery(self) -> bool:
        return "battc" in self.hub_data.get("sensors",{})

    @property
    def charging(self) -> bool:
        # id==21 wie früher – wenn unbekannt: False
        return self.hub_data.get("sensors",{}).get("battc",{}).get("id") == 21

    @property
    def battery_percentage(self) -> int:
        icon = self.hub_data.get("sensors",{}).get("battc",{}).get("icon")
        mapping = {
            "battery-charge.png": 100,
            "battery-full.png": 100,
            "Battery-75.png": 50,
            "battery-50.png": 25,
            "battery-low.png": 10,
        }
        if icon not in mapping:
            raise KeyError("Battery info not available")
        return mapping[icon]

    @property
    def wifi_percentage(self) -> int:
        icon = self.hub_data.get("sensors",{}).get("wific",{}).get("icon")
        mapping = {
            "icon-signal.png": 100,
            "icon-signal-75.png": 75,
            "icon-signal-low.png": 25,
            "icon-signal-0.png": 0,
        }
        if icon not in mapping:
            raise KeyError("WiFi info not available")
        return mapping[icon]

    @property
    def room_size(self) -> int:
        try:
            return int(self.hub_data.get("attributes",{}).get("roomc","1"))
        except ValueError:
            return 1

    @property
    def room_size_square_meter(self) -> int:
        return {1:15, 2:30, 3:60, 4:100}[self.room_size]

    @property
    def version(self) -> str:
        # If available – otherwise empty
        return self.hub_data.get("sensors",{}).get("versionc","")

    # --- v1 methods: same signatures, internal V2 ---
    async def update_data(self, session: ClientSession = None, url: str = HUB_URL) -> None:
        """
        Compatible update: retrieves V2 single endpoints and populates self.data in the old format.
        """
        if session is not None:
            self._api._session = session

        hub = self.hash

        # Attribute
        fanc  = await self._api.get_json(_ATTR_V2.format(hub=hub, attr="fanc"))
        speed = await self._api.get_json(_ATTR_V2.format(hub=hub, attr="speedc"))
        # Optional roomc
        try:
            roomc = await self._api.get_json(_ATTR_V2.format(hub=hub, attr="roomc"))
            roomv = roomc.get("value")
        except Exception:
            roomv = None

        # Sensors
        fillc = await self._safe_get_json(_SENS_V2.format(hub=hub, sensor="fillc"))
        rfidc = await self._safe_get_json(_SENS_V2.format(hub=hub, sensor="rfidc"))
        battc = await self._safe_get_json(_SENS_V2.format(hub=hub, sensor="battc"))
        wific = await self._safe_get_json(_SENS_V2.format(hub=hub, sensor="wific"))
        versc = await self._safe_get_json(_SENS_V2.format(hub=hub, sensor="versionc"))

        # Reassemble old structure
        sensors = {}
        if isinstance(fillc, dict): sensors["fillc"] = fillc
        if isinstance(rfidc, dict): sensors["rfidc"] = rfidc
        if isinstance(battc, dict): sensors["battc"] = battc
        if isinstance(wific, dict): sensors["wific"] = wific
        if isinstance(versc, dict): sensors["versionc"] = versc

        attrs = self.hub_data.get("attributes", {}).copy()
        attrs["fanc"] = str(fanc.get("value","0"))
        attrs["speedc"] = str(speed.get("value","1"))
        if roomv is not None:
            attrs["roomc"] = str(roomv)

        self.data = {
            "hub": {
                "hash": hub,
                "hublot": self.hublot,
                "status": 1,
                "attributes": attrs,
                "sensors": sensors
            }
        }

    async def turn_on(self, session: ClientSession = None, url: str = UPDATE_URL) -> None:
        if session is not None:
            self._api._session = session
        await self._api.post_form(_ATTR_V2.format(hub=self.hash, attr="fanc"), {"fanc":"1"})
        # Keep local state consistent
        self.hub_data.setdefault("attributes", {})["fanc"] = "1"

    async def turn_off(self, session: ClientSession = None, url: str = UPDATE_URL) -> None:
        if session is not None:
            self._api._session = session
        await self._api.post_form(_ATTR_V2.format(hub=self.hash, attr="fanc"), {"fanc":"0"})
        self.hub_data.setdefault("attributes", {})["fanc"] = "0"

    async def set_perfume_amount(self, amount: int, session: ClientSession = None, url: str = UPDATE_URL) -> None:
        """Compat: 1..3; does NOT turn on automatically as usual (retains behavior)."""
        amount = int(amount)
        if amount not in (1,2,3):
            raise ValueError("Amount must be 1..3")
        if session is not None:
            self._api._session = session
        await self._api.post_form(_ATTR_V2.format(hub=self.hash, attr="speedc"), {"speedc": str(amount)})
        self.hub_data.setdefault("attributes", {})["speedc"] = str(amount)

    async def set_room_size(self, size: int, session: ClientSession = None, url: str = UPDATE_URL) -> None:
        size = int(size)
        if size not in (1,2,3,4):
            raise ValueError("Size must be 1..4")
        if session is not None:
            self._api._session = session
        await self._api.post_form(_ATTR_V2.format(hub=self.hash, attr="roomc"), {"roomc": str(size)})
        self.hub_data.setdefault("attributes", {})["roomc"] = str(size)

    async def set_room_size_square_meter(self, size: int, session: ClientSession = None, url: str = UPDATE_URL) -> None:
        size = int(size)
        mapping = {15:1, 30:2, 60:3, 100:4}
        if size not in mapping:
            raise ValueError("Size must be 15, 30, 60 or 100")
        await self.set_room_size(mapping[size], session=session, url=url)

    # --- Helfer ---
    async def _safe_get_json(self, url: str) -> Optional[dict]:
        try:
            return await self._api.get_json(url)
        except Exception:
            return None