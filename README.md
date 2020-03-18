# Synapse REST Password provider
- [Overview](#overview)
- [Install](#install)
- [Configure](#configure)
- [Integrate](#integrate)
- [Support](#support)
---

CREDITS FOR kamax-matrix

https://github.com/kamax-matrix/matrix-synapse-rest-password-provider

---

## Overview
This synapse's password provider allows you to validate a password for a given username and return a user profile using an existing backend, like:

- Forums (phpBB, Discourse, etc.)
- Custom Identity stores (Keycloak, ...)
- CRMs (Wordpress, ...)
- self-hosted clouds (Nextcloud, ownCloud, ...)


**NOTE:** You can integrate it with a backend any backend changing the config, rest and attributes sections.
**IMPORTANT:** The provider only uses ONLY ONE email to add to 3PIDs and does it at registration.

## Install
### From Synapse v0.34.0/py3
Copy in whichever directory python3.x can pick it up as a module.  

If you installed synapse using the Matrix CentOS repos:
```
sudo curl https://github.com/gfiury/matrix-synapse-rest-password-provider/master/rest_auth_provider.py -o /path-to-synapse/env/lib/python3.6/site-packages/rest_auth_provider.py
```
If the command fail, double check that the python version still matches. If not, please open an issue.

## Configure
Add or amend the `password_providers` entry like so:
```yaml
password_providers:
  - module: "rest_auth_provider.RestAuthProvider"
    config:
      endpoint: "http://change.me.example.com:12345"
	  loginuir: "/provider/login"
     rest:
	  user_id: "username"
	  password: "password"
      email: "email"
    attributes:
      display_name: "fullname"
      username: "username"
      email: "email"
```
Set `endpoint` with the endpoint provider.
Set `loginuri` with the authentication uri provider.
Set `user_id`  with the name of the json property of the username to authenticate in the provider.
Set `password`  with the name of the json property of the password to authenticate in the provider.

## Use
1. Install, configure, restart synapse
2. Try to login with a valid username and password for the endpoint configured

## Next steps
### Lowercase username enforcement
**NOTE**: This is no longer relevant as synapse natively enforces lowercase.

To avoid creating users accounts with uppercase characters in their usernames and running into known
issues regarding case sensitivity in synapse, attempting to login with such username will fail.

It is highly recommended to keep this feature enable, but in case you would like to disable it:
```yaml
    config:
      policy:
        registration:
          username:
            enforceLowercase: false
```

### Profile auto-fill
By default, on first login, the display name is set to the one returned by the backend.  
If none is given, the display name is not set.  
Upon subsequent login, the display name is not changed.

If you would like to change the behaviour, you can use the following configuration items:
```yaml
    config:
      policy:
        registration:
          profile:
            name: true
        login:
          profile:
            name: false
```

3PIDs received from the backend are merged with the ones already linked to the account.
If you would like to change this behaviour, you can use the following configuration items:
```yaml
    config:
      policy:
        all:
          threepid:
            update: false
            replace: false
```
If update is set to `false`, the 3PIDs will not be changed at all. If replace is set to `true`, all 3PIDs not available in the backend anymore will be deleted from synapse.

## Integrate
To use this module with your back-end, you will need to implement a single REST endpoint:

Assumption of the request auth provider
```json
{
  "username": "@username:domain"
  "password": "somepassword"
}
```
or/and

```json
{
  "email": "someemail"
  "password": "somepassword"
}
```

Assumption of the returned json of the provider
```json
{
  "fullname": "Name and Lastname"
  "username": "someusername",
  "email": "someemail"
}
```

The json's above must have every attribute on the first level, if you have another type of json you must
fork the repo and change .py file.
