Lightweight helper for authenticating with Hubspot’s OAuth2.
Mimics a small part of Google’s oauth2client API for convenience.


## Install

    pip install hubspot_oauth2client


## Example usage with Django

### Prerequisites

Given your Django setup has an URL pattern
named "home" with no parameters,
and three following settings:

```python
HUBSPOT_OAUTH_SECRET = 'path/to/hubspot_client_secret.json'
"""
Path to a JSON file containing a single object
{"client_id": "...", "client_secret": "..."},
where ID and secret are specific to your Hubspot app
(find them in your developer’s dashboard).
"""

HUBSPOT_OAUTH_SCOPES = ['contacts']
"""
List of OAuth 2.0 scopes as string identifiers.
"""

HUBSPOT_OAUTH_CREDENTIALS_SESSION_KEY = 'hubspot_oauth_token'
"""
Key under which Django will store serialized access/refresh
credentials in ``request.session`` for later
authenticated API calls on behalf of the user.
"""
```

### View

A fairly complete implementation of a ``hubspot_oauth`` view
could look like this:

```python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import requests

from django import http
from django.urls import reverse
from django.conf import settings
from django.contrib import messages

from hubspot_oauth2client import client


log = logging.getLogger('django.hubspot_oauth')


def hubspot_oauth(request):
    """
    With no parameters, initiates OAuth 2.0 flow.

    If ``code`` parameter is present in GET query,
    assumes user has been redirected from Hubspot
    and attempts to exchange that code
    for access & refresh tokens.

    Obtained credentials are stored in session
    in serialized form.
    """
    flow = client.flow_from_clientsecrets(
        settings.HUBSPOT_OAUTH_SECRET,
        settings.HUBSPOT_OAUTH_SCOPES,
        redirect_uri=request.build_absolute_uri(reverse('hubspot_oauth')))

    auth_code = request.GET.get('code', None)

    if auth_code:
        if settings.HUBSPOT_OAUTH_CREDENTIALS_SESSION_KEY in request.session:
            del request.session[settings.HUBSPOT_OAUTH_CREDENTIALS_SESSION_KEY]

        try:
            credentials = flow.step2_exchange(auth_code)

        except client.CodeExchangeError:
            log.exception("Hubspot rejected OAuth2 code")
            messages.error(
                request,
                "Couldn’t authenticate Hubspot right now. Try again?")

        except client.BadCodeExchangeResponse:
            log.exception("Bad OAuth2 code exchange response")
            messages.error(
                request,
                "Couldn’t authenticate Hubspot right now. Try again?")

        except requests.exceptions.ConnectionError:
            log.exception("Error reaching Hubspot to exchange OAuth2 code")
            messages.error(
                request,
                "Couldn’t reach Hubspot to complete authentication. "
                "Try again?")

        else:
            request.session[settings.HUBSPOT_OAUTH_CREDENTIALS_SESSION_KEY] = (
                credentials.to_json())

        return http.HttpResponseRedirect(reverse('home'))

    else:
        auth_uri = flow.step1_get_authorize_url()
        return http.HttpResponseRedirect(auth_uri)
```

Given that you only need to define an URL pattern pointing to this view,
and your app can direct users to it when necessary to initiate
OAuth 2.0 flow.

### Making authenticated calls

Per our view implementation, access token is stored in ``request.session``
in serialized form after user completes the authentication successfully.
You can use those access credentials to make authenticated API calls later.

Here’s a somewhat abridged example in which we obtain
a list of all contacts available to the portal
user has selected during authentication:

```python
import urllib
import requests

from django import shortcuts

from hubspot_oauth2client import client


def get_contacts(request):
    creds_blob = request.session.get(settings.HUBSPOT_OAUTH_CREDENTIALS_SESSION_KEY)

    if creds_blob:
        creds = client.OAuth2Credentials.from_json(creds_blob)

        if not creds.access_token_expired:
            get_query = {'property': ['country', 'hs_lead_status']}

            requests.get('{hapi_base}/{area}/{endpoint}/?{query}'.format(
                hapi_base='https://api.hubapi.com',
                area='/contacts/v1',
                endpoint='/lists/all/contacts/all',
                query=urllib.urlencode(get_query, do_seq=True),
            ), headers={
                'Authorization': 'Bearer {0}'.format(creds.access_token),
            })

    return shortcuts.redirect('hubspot_oauth')
```

### Calling APIs without requiring user’s input

If you need to make authenticated Hubspot API calls
in absence of ``request.session`` (for example, from
an async task), you would want to:

* Alter the above code to use another storage
  (like a Redis key) and tie credentials
  to user identifier explicitly

* Use ``credentials.refresh_token`` when possible
  after access token expires (otherwise user
  would have to authenticate with Hubspot
  every few hours)


## Roadmap

* Implement token refresh functionality out of the box


## Changelog

### 0.1

* Fixed a method reference in OAuth2Credentials class

* Tested in production

### 0.1a0

* Initial implementation
