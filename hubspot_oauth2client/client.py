# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import urllib
import json
import datetime

import requests


def flow_from_clientsecrets(secrets_filename, scopes, redirect_uri):

    with open(secrets_filename, 'r') as f:
        _blob = f.read()

    client_secrets = json.loads(_blob)

    client_id = client_secrets['client_id']
    client_secret = client_secrets['client_secret']

    return OAuth2Flow(client_id, client_secret, scopes, redirect_uri)


class OAuth2Flow:

    authorize_url = 'https://app.hubspot.com/oauth/authorize'

    code_exchange_url = 'https://api.hubapi.com/oauth/v1/token'

    code_exchange_req_headers = {
        'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
    }

    def step1_get_authorize_url(self):
        params = {
            'client_id': self.client_id,
            'scope': ' '.join(self.scopes),
            'redirect_uri': self.redirect_uri,
        }

        url = '{base}?{params}'.format(
            base=self.authorize_url,
            params=urllib.urlencode(params))

        return url

    def step2_exchange(self, auth_code):
        params = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
        }

        resp = requests.post(
            self.code_exchange_url,
            headers=self.code_exchange_req_headers,
            params=params)

        return self.create_credentials_from_code_exchange(resp)

    def credentials_from_code_exchange(self, resp):
        datadict = resp.json()

        if 'status' in datadict:
            # Hubspot OAuth2 returns JSON containing error code under "status"
            # in case code exchange wasn’t successful.
            raise CodeExchangeError(resp.text)

        try:
            token_lifetime_seconds = datetime.timedelta(
                seconds=datadict['expires_in'])
        except TypeError:
            raise BadCodeExchangeResponse("Bad token expiration format")

        token_obtained_on = datetime.datetime.utcnow()
        token_expires_on = token_obtained_on + token_lifetime_seconds

        try:
            access_token = unicode(datadict['access_token'])
            refresh_token = unicode(datadict['refresh_token'])
        except KeyError:
            raise BadCodeExchangeResponse("Missing access or refresh token")
        except UnicodeDecodeError:
            raise BadCodeExchangeResponse("Bad access or refresh token format")

        return OAuth2Credentials(
            token_response=datadict,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expires_on,
            scopes=self.scopes,
        )

    def __init__(self, client_id, client_secret, scopes, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes
        self.redirect_uri = redirect_uri.rstrip('/')


class OAuth2Credentials:
    """
    Wraps OAuth2 access & refresh tokens and supporting data.
    """

    token_expiry_format = '%Y-%m-%dT%H:%M:%SZ'

    def __init__(self, token_response,
                 access_token, refresh_token,
                 token_expiry, scopes):
        self.token_response = token_response
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expiry = token_expiry
        self.scopes = scopes

    @property
    def access_token_expired(self):
        return self.token_expiry <= datetime.datetime.utcnow()

    def to_json(self):
        """
        Serializes itself as JSON which can be stored
        for later authenticated calls.
        """
        data = {
            'token_response': self.token_response,
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'token_expiry':
                self.token_expiry.strftime(self.token_expiry_format),
            'scopes': self.scopes,
        }

        return json.dumps(data)

    @classmethod
    def from_json(cls, blob):
        """
        Creates an instance from JSON stored after code exchange.
        """
        data = json.loads(blob)

        return cls(
            data['token_response'],
            data['access_token'],
            data['refresh_token'],
            datetime.datetime.strptime(
                data['token_expiry'],
                cls.token_expiry_format),
            data['scopes'])


class CodeExchangeError(Exception):
    "API responded with an error when trying to obtain access/refresh tokens."


class BadCodeExchangeResponse(ValueError):
    "Unexpected API response when trying to obtain access/refresh tokens."
