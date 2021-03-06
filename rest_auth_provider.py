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

            display_name = localpart
            if r[self.attributes["display_name"]]:
               display_name = r[self.attributes["display_name"]]
			
            emails = []			
            if r[self.attributes["email"]]:
                emails = [r[self.attributes["email"]]]
			   
            (yield self.account_handler.register(localpart=localpart, displayname=display_name, emails=emails))
            registration = True
            logger.info("Registration based on REST data was successful for %s", user_id)
        else:
            logger.info("User %s already exists, registration skipped", user_id)

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

        data = {self.rest["email"]:address, self.rest["password"]:password}
        r = requests.post(self.endpoint + self.loginuri, json = data)

        if not r.ok:
            logger.info("User not authenticated")
            defer.returnValue(False)

        r = r.json()

        user_id = r[self.rest["user_id"]]
        display_name = user_id
		
        registration = False
        if not (yield self.account_handler.check_user_exists(user_id)):
            logger.info("User %s does not exist yet, creating...", user_id)

            if localpart != localpart.lower() and self.regLower:
                logger.info('User %s was cannot be created due to username lowercase policy', localpart)
                defer.returnValue(False)
				
            if r[self.attributes["display_name"]]:
                display_name = r[self.attributes["display_name"]]
				
            user_id, access_token = (yield self.account_handler.register(localpart=user_id, displayname=display_name, emails=[email]))
            registration = True
            logger.info("Registration based on REST data was successful for %s", user_id)
        else:
            logger.info("User %s already exists, registration skipped", user_id)

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
        rest_config.loginuri = config["loginuri"]
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
