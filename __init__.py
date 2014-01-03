__author__ = 'tarzan'

from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember, forget
from pyramid.authentication import AuthTktAuthenticationPolicy
from urllib import quote_plus
import requests
import json
import models

def vgid_velruse_callback_view(context, request):
    token = request.params.get('token', '')
    get_auth_info_url = request.registry.settings.get('vgid_velruse_client.auth_info',
                                                      'https://id.vatgia.com/velruse/auth_info')
    httpusr = request.registry.settings.get('vgid_velruse_client.rest_user')
    httppwd = request.registry.settings.get('vgid_velruse_client.rest_pass')
    get_auth_info_url += ('&' if '?' in get_auth_info_url else '?') + "token=" + token
    r = requests.get(get_auth_info_url,
                     auth=requests.auth.HTTPDigestAuth(httpusr, httppwd))
    if r.status_code == 200:
        profile = json.loads(r.text)
        profile = profile["profile"]
        profile = {
            "name": profile["displayName"],
            "email": profile["verifiedEmail"],
        }
        user = models.User.import_from_dict(profile)
        redirect_url = request.params.get('_cont',
                                          request.referer or request.resource_url(request.root))
        return HTTPFound(redirect_url, headers=remember(request, user.id))
    return 'abc'

def logout_view(request):
    redirect_url = request.referer or request.resource_url(request.root)
    return HTTPFound(redirect_url, headers=forget(request))

def login_url(request, provider_name="google"):
    velruse_url = request.registry.settings.get('vgid_velruse_client.login_url',
                                                'https://id.vatgia.com/velruse/request_login/')
    velruse_url += provider_name
    callback_url = quote_plus(request.route_url('vgid_velruse_client_login_callback',
                                                _query={'_cont':request.url}))
    return velruse_url + ('?' if '?' not in velruse_url else '&') + "_cont=" + callback_url

def logout_url(request):
    return request.route_url('vgid_velruse_client_logout')

def includeme(config):
    """
    @type config: pyramid.config.Configurator
    """
    settings = config.registry.settings
    pkg_settings = {k[20:]:v
                    for k,v in settings.items()
                    if k.startswith('vgid_velruse_client.')}
    models.import_settings(pkg_settings)

    auth_policy = AuthTktAuthenticationPolicy(
        settings.get('vgid_velruse_client.auth_tkt_secret', 'ZU0b@KH>AtQ/8Wu?39~S'),
        callback=models.get_user_groups,
        hashalg='sha512',
    )
    config.set_authentication_policy(auth_policy)
    config.set_request_property(models.get_user, 'authenticated_user', reify=True)

    config.add_route('vgid_velruse_client_logout',
                     '/vgid_velruse_client/logout')
    config.add_route('vgid_velruse_client_login_callback',
                     'vgid_velruse_client/login/callback')

    config.add_view(vgid_velruse_callback_view, route_name='vgid_velruse_client_login_callback',
                    renderer='json')
    config.add_view(logout_view, route_name='vgid_velruse_client_logout')

