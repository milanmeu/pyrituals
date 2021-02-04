# PyRituals package 
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
### Create a `aiohttp.ClientSession()` to make requests
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
UPDATE_URL = "https://rituals.sense-company.com/api/hub/update/attr" # Diffuser.turn_on(), Diffuser.turn_off()
```

To change the used API endpoints add an `url` parameter to the function. Example:
```python
LOGIN_URL = "https://rituals.sense-company.com/ocapi/login"
account = Account("name@example.com", "passw0rd")
await account.authenticate(session, url=LOGIN_URL)
```


### Account
#### Create an instance
```python
email = "name@example.com"
password = "passw0rd"

account = Account(email, password)
```

#### Authenticate
```python
try:
    await account.authenticate(session)
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
devices = await account.get_devices(session)
```

### Diffuser
#### Diffuser data
The initial data and format is different from the data after executing `update_data()`.
Therefore, it's recommended to execute `update_data()` before using the diffuser data.
```python
diffuser.data
```

#### Get updated data
```python
await diffuser.update_data(session)
```

#### Turn the diffuser on
```python
await diffuser.turn_on(session)
```

#### Turn the diffuser on
```python
await diffuser.turn_off(session)
```

## Example

```python
from aiohttp import ClientSession
from asyncio import run

import pyrituals


async def main():
    async with ClientSession() as session:
        account = pyrituals.Account("name@example.com", "passw0rd")
        try:
            await account.authenticate(session, url=)
        except pyrituals.AuthenticationException as e:
            print("Could not authenticate:", e)
            return
        print("Account data:", account.data)
        devices = await account.get_devices(session)
        for diffuser in devices:
            print("Diffuser data:", diffuser.data)
            await diffuser.turn_on(session)
            await diffuser.update_data(session)
            print("Diffuser updated data:", diffuser.data)


run(main())
```
