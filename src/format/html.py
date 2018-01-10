# -*- coding: utf-8 -*-

"""HTML check module."""

# standard imports
import logging
import re

# 3rd party imports
from bs4 import BeautifulSoup

# local imports
from fluidasserts import show_close
from fluidasserts import show_open
from fluidasserts.utils.decorators import track

LOGGER = logging.getLogger('FLUIDAsserts')


def __has_attribute(filename, selector, tag, attr, value):
    """Check attribute value.

    This method checks whether the code retrieved by the selector
    (selector) inside the file (file) has an attribute (attr) with the
    specific value (value)
    """
    handle = open(filename, 'r')
    html_doc = handle.read()
    handle.close()

    soup = BeautifulSoup(html_doc, 'html.parser')
    form = soup.select(selector)

    cache_rgx = r'<%s.+%s\s*=\s*["%s"|\'%s\'].*>' % (
        tag, attr, value, value)
    prog = re.compile('%s' % cache_rgx, flags=re.IGNORECASE)
    match = prog.search(str(form))

    return match is not None


@track
def has_not_autocomplete(filename, selector):
    """Check autocomplete attrubute."""
    attr = 'autocomplete'
    value = 'off'
    has_attr = __has_attribute(
        filename, selector, '[form|input]', attr, value)

    if has_attr is False:
        status = show_open()
        result = True
        LOGGER.info('%s: %s attribute in %s, Details=%s',
                    status, attr, filename, '')
    else:
        status = show_close()
        result = False
        LOGGER.info('%s: %s attribute in %s, Details=%s',
                    status, attr, filename, value)

    return result


@track
def is_cacheable(filename):
    """Check if cache is posible.

    Verifies if the file (filename) has the tags
    <META HTTP-EQUIV="Pragma" CONTENT="no-cache"> and
    <META HTTP-EQUIV="Expires" CONTENT="-1">
    """
    selector = 'html'
    tag = 'meta'

    attr = 'http-equiv'
    value = 'pragma'
    has_http_equiv = __has_attribute(
        filename, selector, tag, attr, value)

    if has_http_equiv is False:
        status = show_open()
        result = True
        LOGGER.info('%s: %s attribute in %s, Details=%s',
                    status, attr, filename, value)

        return result

    attr = 'content'
    value = r'no\-cache'
    has_content = __has_attribute(
        filename, selector, tag, attr, value)

    if has_content is False:
        status = show_open()
        result = True
        LOGGER.info('%s: %s attribute in %s, Details=%s',
                    status, attr, filename, value)

        return result

    attr = 'http-equiv'
    value = 'expires'
    has_http_equiv = __has_attribute(
        filename, selector, tag, attr, value)

    if has_http_equiv is False:
        status = show_open()
        result = True
        LOGGER.info('%s: %s attribute in %s, Details=%s',
                    status, attr, filename, value)

        return result

    attr = 'content'
    value = '-1'
    has_content = __has_attribute(
        filename, selector, tag, attr, value)

    if has_content is False:
        status = show_open()
        result = True
        LOGGER.info('%s: %s attribute in %s, Details=%s',
                    status, attr, filename, value)

        return result

    status = show_close()
    result = False
    LOGGER.info('%s: %s attribute in %s, Details=%s',
                status, attr, filename, value)

    return result
