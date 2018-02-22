# -*- coding: utf-8 -*-

"""HTTP Cookie module."""


# standard imports
# None

# 3rd party imports
# None

# local imports
from fluidasserts import show_close
from fluidasserts import show_open
from fluidasserts import show_unknown
from fluidasserts.helper import http_helper
from fluidasserts.utils.decorators import track


def __has_not_http_only(cookie_name, url, cookie_jar, *args, **kwargs):
    """Verifica si la cookie tiene el atributo httponly."""
    if url is None and cookie_jar is None:
        show_unknown('Cookie check for "{}", Details={}'.
                     format(cookie_name, 'HttpOnly'))
        return True
    if url is not None:
        sess = http_helper.HTTPSession(url, *args, **kwargs)
        cookielist = sess.cookies
    else:
        cookielist = cookie_jar
    if cookielist is None:
        show_unknown('{} Cookies not present'.format(cookie_name))
        return True
    for cookie in cookielist:
        if cookie.name == cookie_name:
            if cookie.has_nonstandard_attr('HttpOnly') or \
               cookie.has_nonstandard_attr('httponly'):
                show_close('Cookie check for "{}", Details={}'.
                           format(cookie_name, 'HttpOnly'))
                result = False
            else:
                show_open('Cookie check for "{}", Details={}'.
                          format(cookie_name, 'HttpOnly'))
                result = True
            return result
    show_unknown('Cookie "{}" not found, Details={}'.
                 format(cookie_name, 'HttpOnly'))
    return True


def __has_not_secure(cookie_name, url, cookie_jar, *args, **kwargs):
    """Verifica si la cookie tiene el atributo secure."""
    if url is None and cookie_jar is None:
        show_unknown('Cookie check for "{}", Details={}'.
                     format(cookie_name, 'Secure'))
        return True
    if url is not None:
        sess = http_helper.HTTPSession(url, *args, **kwargs)
        cookielist = sess.cookies
    else:
        cookielist = cookie_jar
    if cookielist is None:
        show_unknown('{} Cookies not present'.format(cookie_name))
        return True
    for cookie in cookielist:
        if cookie.name == cookie_name:
            if cookie.secure:
                show_close('Cookie check for "{}", Details={}'.
                           format(cookie_name, 'Secure'))
                result = False
            else:
                show_open('Cookie check for "{}", Details={}'.
                          format(cookie_name, 'Secure'))
                result = True
            return result
    show_unknown('Cookie "{}" not found, Details={}'.
                 format(cookie_name, 'Secure'))
    return True


@track
def has_not_httponly_set(cookie_name, url, *args, **kwargs):
    """Verifica si la cookie tiene el atributo httponly."""
    return __has_not_http_only(cookie_name, url, None, *args, **kwargs)


@track
def has_not_httponly_in_cookiejar(cookie_name, cookie_jar, *args, **kwargs):
    """Verifica si la cookie tiene el atributo httponly."""
    return __has_not_http_only(cookie_name, None, cookie_jar,
                               *args, **kwargs)


@track
def has_not_secure_set(cookie_name, url, *args, **kwargs):
    """Verifica si la cookie tiene el atributo secure."""
    return __has_not_secure(cookie_name, url, None, *args, **kwargs)


@track
def has_not_secure_in_cookiejar(cookie_name, cookie_jar, *args, **kwargs):
    """Verifica si la cookie tiene el atributo secure."""
    return __has_not_secure(cookie_name, None, cookie_jar
                            *args, **kwargs)
