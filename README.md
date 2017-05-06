Lightweight helper for authenticating with Hubspot’s OAuth2.
Mimics a small part of Google’s oauth2client API for convenience.

### Install

    pip install hubspot_oauth2client

### Example usage

Here’s how you might use it in a Django view:

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
