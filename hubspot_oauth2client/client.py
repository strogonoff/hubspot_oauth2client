# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import urllib
import json
import datetime

import requests

try:
    urlencode = urllib.urlencode
except AttributeError:
    urlencode = urllib.parse.urlencode


TOKEN_REQUEST_HEADERS = {
    'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
}


def load_client_secrets(secrets_filename):
    with open(secrets_filename, 'r') as f:
        _blob = f.read()

    return json.loads(_blob)


def flow_from_clientsecrets(secrets_filename, scopes, redirect_uri):
    client_secrets = load_client_secrets(secrets_filename)

    client_id = client_secrets['client_id']
    client_secret = client_secrets['client_secret']

    return OAuth2Flow(client_id, client_secret, scopes, redirect_uri)


class OAuth2Flow:

    authorize_url = 'https://app.hubspot.com/oauth/authorize'

    code_exchange_url = 'https://api.hubapi.com/oauth/v1/token'

    def step1_get_authorize_url(self):
        params = {
            'client_id': self.client_id,
            'scope': ' '.join(self.scopes),
            'redirect_uri': self.redirect_uri,
        }

        url = '{base}?{params}'.format(
            base=self.authorize_url,
            params=urlencode(params))

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
            headers=TOKEN_REQUEST_HEADERS,
            params=params)

        return self.create_credentials_from_code_exchange(resp)

    def create_credentials_from_code_exchange(self, resp):
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
            access_token = str(datadict['access_token'])
            refresh_token = str(datadict['refresh_token'])
        except KeyError:
            raise BadCodeExchangeResponse("Missing access or refresh token")
        except UnicodeDecodeError:
            raise BadCodeExchangeResponse("Bad access or refresh token format")

        return OAuth2Credentials(
            client_id=self.client_id,
            client_secret=self.client_secret,
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

    token_refresh_url = 'https://api.hubapi.com/oauth/v1/token'

    def __init__(self, client_id, client_secret,
                 token_response,
                 access_token, refresh_token,
                 token_expiry, scopes):
        self.client_id = client_id
        self.client_secret = client_secret
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
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'token_response': self.token_response,
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'token_expiry':
                self.token_expiry.strftime(self.token_expiry_format),
            'scopes': self.scopes,
        }

        return json.dumps(data)

    def refresh(self):
        params = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }

        resp = requests.post(
            self.token_refresh_url,
            headers=TOKEN_REQUEST_HEADERS,
            params=params)

        datadict = resp.json()

        # TODO: This duplicates similar lines in the flow class
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
            access_token = str(datadict['access_token'])
            refresh_token = str(datadict['refresh_token'])
        except KeyError:
            raise BadCodeExchangeResponse("Missing access or refresh token")
        except UnicodeDecodeError:
            raise BadCodeExchangeResponse("Bad access or refresh token format")

        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expiry = token_expires_on

    @classmethod
    def from_json(cls, blob):
        """
        Creates an instance from JSON stored after code exchange.
        """
        data = json.loads(blob)

        return cls(
            data['client_id'],
            data['client_secret'],
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
