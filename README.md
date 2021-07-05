# PyRituals package 
[![PyPI](https://img.shields.io/pypi/v/pyrituals)](https://pypi.org/project/pyrituals/) ![PyPI - Downloads](https://img.shields.io/pypi/dm/pyrituals) [![PyPI - License](https://img.shields.io/pypi/l/pyrituals?color=blue)](https://github.com/milanmeu/pyrituals/blob/main/LICENSE)

An async Python wrapper for the Rituals Perfume Genie API.
It allows you to control the diffuser and retrieve its state.
The package supports the first and second version.

## Installation
```bash
pip install pyrituals
```

## Usage
### Import
```python
from pyrituals import Account, Diffuser, AuthenticationException
```

### Create a `aiohttp.ClientSession` to make requests
```python
from aiohttp import ClientSession
session = ClientSession()
```

### Endpoints
Default endpoints:
```python
AUTH_URL = "https://rituals.sense-company.com/ocapi/login"           # Account.authenticate()
ACCOUNT_URL = "https://rituals.sense-company.com/api/account/hubs"   # Account.get_devices()
HUB_URL = "https://rituals.sense-company.com/api/account/hub"        # Diffuser.update_data()
UPDATE_URL = "https://rituals.sense-company.com/api/hub/update/attr" # Diffuser.turn_*(), Diffuser.set_*()
```

To change the used API endpoints add an `url` parameter to the function. Example:
```python
LOGIN_URL = "https://rituals.sense-company.com/ocapi/login"
account = Account("name@example.com", "passw0rd", session)
await account.authenticate(url=LOGIN_URL)
```

### Account
#### Create an instance
```python
email = "name@example.com"
password = "passw0rd"

account = Account(email, password, session)
```

#### Authenticate
```python
try:
    await account.authenticate()
except AuthenticationException as e:
    print("Could not authenticate:", e)
```

#### Account data
The account data is only available after authentication.
```python
account.data
```

#### Get linked devices
`get_devices()` returns a list of `Diffuser`s. 
```python
devices = await account.get_devices()
```

### Diffuser
#### Diffuser data
The initial data and format is different from the data after executing `update_data()`.
Some properties require data that is only available after executing `update_data()`.
Therefore, it's required to execute `update_data()` before using the diffuser properties.
```python
diffuser.data
diffuser.battery_percentage
diffuser.charging
diffuser.has_battery
diffuser.has_cartridge
diffuser.hash
diffuser.hub_data
diffuser.hublot
diffuser.fill
diffuser.perfume
diffuser.perfume_amount
diffuser.room_size
diffuser.is_on
diffuser.is_online
diffuser.name
diffuser.version
diffuser.wifi_percentage
diffuser.room_size_square_meter
```

#### Get updated data
```python
await diffuser.update_data()
```

#### Turn the diffuser on
```python
await diffuser.turn_on()
```

#### Turn the diffuser off
```python
await diffuser.turn_off()
```

#### Set the diffuser perfume amount
Amount must be an integer between 1 and 3, inclusive.
```python
amount = 1
await diffuser.set_perfume_amount(amount)
```

#### Set the diffuser room size
Size must be an integer between 1 and 4, inclusive.
```python
size = 2
await diffuser.set_room_size(size)
```

#### Set the diffuser room size in square meters
Size must be the integer 15, 30, 60 or 100.
```python
size = 60
await diffuser.set_room_size_square_meter(size)
```

## Example
```python
from aiohttp import ClientSession
from asyncio import run

import pyrituals

async def main():
    async with ClientSession() as session:
        account = pyrituals.Account("name@example.com", "passw0rd", session)
        try:
            await account.authenticate()
        except pyrituals.AuthenticationException as ex:
            print("Could not authenticate:", ex)
            return
        print("Account data:", account.data)
        devices = await account.get_devices()
        for diffuser in devices:
            print("Diffuser data:", diffuser.data)
            await diffuser.turn_on()
            await diffuser.set_perfume_amount(1)
            await diffuser.set_room_size(4)
            await diffuser.update_data()
            print("Diffuser updated data:", diffuser.data)
            if diffuser.has_battery:
                print(f"Battery percentage: {diffuser.battery_percentage}%")

run(main())
```
