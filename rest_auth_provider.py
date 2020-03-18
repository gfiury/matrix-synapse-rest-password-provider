# -*- coding: utf-8 -*-
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import logging
from twisted.internet import defer
import requests
import json

logger = logging.getLogger(__name__)

class RestAuthProvider(object):

    def __init__(self, config, account_handler):
        self.account_handler = account_handler

        if not config.endpoint:
            raise RuntimeError('Missing endpoint config')

        self.endpoint = config.endpoint
        self.loginuri = config.loginuri
        self.regLower = config.regLower
        self.attributes = config.attributes
        self.rest = config.rest
        self.config = config

        logger.info('Endpoint: %s', self.endpoint)
        logger.info('Enforce lowercase username during registration: %s', self.regLower)

    @defer.inlineCallbacks
    def check_password(self, user_id, password):
        logger.info("Got password check for " + user_id)
        data = {self.rest["user_id"]:user_id, self.rest["password"]:password}
        r = requests.post(self.endpoint + self.loginuri, json = data)
        # raise an exception for error codes (4xx or 5xx)
        r.raise_for_status()

        if not r.ok:
            logger.info("User not authenticated")
            defer.returnValue(False)

        r = r.json()

        localpart = user_id.split(":", 1)[0][1:]
        logger.info("User %s authenticated", user_id)

        registration = False
        if not (yield self.account_handler.check_user_exists(user_id)):
            logger.info("User %s does not exist yet, creating...", user_id)

            if localpart != localpart.lower() and self.regLower:
                logger.info('User %s was cannot be created due to username lowercase policy', localpart)
                defer.returnValue(False)

            user_id, access_token = (yield self.account_handler.register(localpart=localpart))
            registration = True
            logger.info("Registration based on REST data was successful for %s", user_id)
        else:
            logger.info("User %s already exists, registration skipped", user_id)

        logger.info("Handling user info")
        if r[self.attributes["display_name"]]:

            store = yield self.account_handler.hs.get_profile_handler().store
            if ((registration and self.config.setNameOnRegister) or (self.config.setNameOnLogin)):
                display_name = r[self.attributes["display_name"]]
                logger.info("Setting display name to '%s' based on profile data", display_name)
                yield store.set_profile_displayname(localpart, display_name)
            else:
                logger.info("Display name was not set because it was not given or policy restricted it")

        # The email is not updated by self.config.updateThreepid
        # The email is like the user_id, cant be changed
        if (registration):
            if r[self.attributes["email"]]:
                logger.info("Handling 3PIDs for user %s with email %s", user_id, address)

                medium = "email"
                address = r[self.attributes["email"]]
                logger.info("Looking for 3PID %s:%s in user profile", medium, address)

                validated_at = self.account_handler.hs.get_clock().time_msec()
                if not (yield store.get_user_id_by_threepid(medium, address)):
                    logger.info("3PID is not present, adding")
                    yield store.user_add_threepid(
                        user_id,
                        medium,
                        address,
                        validated_at,
                        validated_at
                    )
            else:
                logger.info("3PID is present, skipping")
        else:
            logger.info("3PIDs were not updated due to policy")

        defer.returnValue(True)
		
	@defer.inlineCallbacks
    def check_3pid_auth(self, medium, address, password):
        """ Handle authentication against thirdparty login types, such as email
            Args:
                medium (str): Medium of the 3PID (e.g email, msisdn).
                address (str): Address of the 3PID (e.g bob@example.com for email).
                password (str): The provided password of the user.
            Returns:
                user_id (str|None): ID of the user if authentication
                    successful. None otherwise.
        """

        # We currently only support email
        if medium != "email":
            defer.returnValue(None)

        # Talk to LDAP and check if this email/password combo is correct
        try:

            data = {self.rest["email"]:address, self.rest["password"]:password}
            r = requests.post(self.endpoint + self.loginuri, json = data)
            # raise an exception for error codes (4xx or 5xx)
            r.raise_for_status()

            if not r.ok:
                logger.info("User not authenticated")
                defer.returnValue(False)

            r = r.json()

            registration = False
            if not (yield self.account_handler.check_user_exists(user_id)):
                logger.info("User %s does not exist yet, creating...", user_id)

                if localpart != localpart.lower() and self.regLower:
                    logger.info('User %s was cannot be created due to username lowercase policy', localpart)
                    defer.returnValue(False)

                user_id, access_token = (yield self.account_handler.register(localpart=localpart))
                registration = True
                logger.info("Registration based on REST data was successful for %s", user_id)
            else:
                logger.info("User %s already exists, registration skipped", user_id)

            logger.info("Handling user info")
            if r[self.attributes["display_name"]]:

                store = yield self.account_handler.hs.get_profile_handler().store
                if ((registration and self.config.setNameOnRegister) or (self.config.setNameOnLogin)):
                    display_name = r[self.attributes["display_name"]]
                    logger.info("Setting display name to '%s' based on profile data", display_name)
                    yield store.set_profile_displayname(localpart, display_name)
                else:
                    logger.info("Display name was not set because it was not given or policy restricted it")

            # The email is not updated by self.config.updateThreepid
            # The email is like the user_id, cant be changed
            if (registration):
                    logger.info("Handling 3PIDs for user %s with email %s", user_id, address)

                    medium = "email"
                    logger.info("Looking for 3PID %s:%s in user profile", medium, address)

                    validated_at = self.account_handler.hs.get_clock().time_msec()
                    # Just in case, it should not be present
                    if not (yield store.get_user_id_by_threepid(medium, address)):
                        logger.info("3PID is not present, adding")
                        yield store.user_add_threepid(
                            user_id,
                            medium,
                            address,
                            validated_at,
                            validated_at
                        )
                    else:
                        logger.info("3PID is present, skipping")
            else:
                logger.info("3PIDs were not updated due to policy")

            defer.returnValue(True)

    @staticmethod
    def parse_config(config):
        # verify config sanity
        _require_keys(config, ["endpoint", "rest", "attributes"])

        class _RestConfig(object):
            endpoint = ''
            regLower = True
            setNameOnRegister = True
            setNameOnLogin = False
            updateThreepid = True
            replaceThreepid = False

        rest_config = _RestConfig()
        rest_config.endpoint = config["endpoint"]
		rest_config.rest = config["rest"]
		rest_config.attributes = config["attributes"]

        try:
            rest_config.regLower = config['policy']['registration']['username']['enforceLowercase']
        except TypeError:
            # we don't care
            pass
        except KeyError:
            # we don't care
            pass

        try:
            rest_config.setNameOnRegister = config['policy']['registration']['profile']['name']
        except TypeError:
            # we don't care
            pass
        except KeyError:
            # we don't care
            pass
        
        try:
            rest_config.setNameOnLogin = config['policy']['login']['profile']['name']
        except TypeError:
            # we don't care
            pass
        except KeyError:
            # we don't care
            pass

        try:
            rest_config.updateThreepid = config['policy']['all']['threepid']['update']
        except TypeError:
            # we don't care
            pass
        except KeyError:
            # we don't care
            pass

        try:
            rest_config.replaceThreepid = config['policy']['all']['threepid']['replace']
        except TypeError:
            # we don't care
            pass
        except KeyError:
            # we don't care
            pass

        return rest_config

def _require_keys(config, required):
    missing = [key for key in required if key not in config]
    if missing:
        raise Exception(
            "REST Auth enabled but missing required config values: {}".format(
                ", ".join(missing)
            )
        )
