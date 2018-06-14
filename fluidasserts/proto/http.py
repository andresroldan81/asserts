# -*- coding: utf-8 -*-

"""This module allows to check HTTP-specific vulnerabilities."""

# standard imports
import re
import json
from copy import deepcopy
from datetime import datetime
from typing import Optional, List, Union

# 3rd party imports
from urllib.parse import parse_qsl as parse_qsl
from viewstate import ViewState, ViewStateException
from pytz import timezone
import ntplib
import requests

# local imports
from fluidasserts.helper import banner_helper
from fluidasserts.helper import http_helper
from fluidasserts import show_close
from fluidasserts import show_open
from fluidasserts import show_unknown
from fluidasserts.utils.decorators import track

# pylint: disable=C0302

HDR_RGX = {
    'access-control-allow-origin': '^https?:\\/\\/.*$',
    'cache-control': '(?=.*must-revalidate)(?=.*no-cache)(?=.*no-store)',
    'content-security-policy': '^([a-zA-Z]+\\-[a-zA-Z]+|sandbox).*$',
    'content-type': '^(\\s)*.+(\\/|-).+(\\s)*;(\\s)*charset.*$',
    'expires': '^\\s*0\\s*$',
    'pragma': '^\\s*no-cache\\s*$',
    'strict-transport-security': '^\\s*max-age=\\s*\\d+',
    'x-content-type-options': '^\\s*nosniff\\s*$',
    'x-frame-options': '^\\s*(deny|allow-from|sameorigin).*$',
    'server': '^[^0-9]*$',
    'x-permitted-cross-domain-policies': '^((?!all).)*$',
    'x-xss-protection': '^1(\\s*;\\s*mode=block)?$',
    'www-authenticate': '^((?!Basic).)*$',
    'x-powered-by': '^ASP.NET'
}  # type: dict

# Regex taken from SQLmap project
SQLI_ERROR_MSG = {
    r'SQL syntax.*MySQL',  # MySQL
    r'Warning.*mysql_.*',  # MySQL
    r'MySqlException \(0x',  # MySQL
    r'valid MySQL result',  # MySQL
    r'check the manual that corresponds to your (MySQL|MariaDB)',  # MySQL
    r'MySqlClient.',  # MySQL
    r'com.mysql.jdbc.exceptions',  # MySQL
    r'PostgreSQL.*ERROR',  # PostgreSQL
    r'Warning.*Wpg_.*',  # PostgreSQL
    r'valid PostgreSQL result',  # PostgreSQL
    r'Npgsql.',  # PostgreSQL
    r'PG::SyntaxError:',  # PostgreSQL
    r'org.postgresql.util.PSQLException',  # PostgreSQL
    r'ERROR:sssyntax error at or near ',  # PostgreSQL, MS SQL Server
    r'Driver.* SQL[-_ ]*Server',  # MS SQL Server
    r'OLE DB.* SQL Server',  # MS SQL Server
    r'\bSQL Server[^&lt;&quot;]+Driver',  # MS SQL Server
    r'Warning.*(mssql|sqlsrv)_',  # MS SQL Server
    r'\bSQL Server[^&lt;&quot;]+[0-9a-fA-F]{8}',  # MS SQL Server
    r'System.Data.SqlClient.SqlException',  # MS SQL Server
    r'(?s)Exception.*WRoadhouse.Cms.',  # MS SQL Server
    r'Microsoft SQL Native Client error \'[0-9a-fA-F]{8}',  # MS SQL Server
    r'com.microsoft.sqlserver.jdbc.SQLServerException',  # MS SQL Server
    r'ODBC SQL Server Driver',  # MS SQL Server
    r'SQLServer JDBC Driver',  # MS SQL Server
    r'macromedia.jdbc.sqlserver',  # MS SQL Server
    r'com.jnetdirect.jsql',  # MS SQL Server, Microsoft Access
    r'Microsoft Access (d+ )?Driver',  # Microsoft Access
    r'JET Database Engine',  # Microsoft Access
    r'Access Database Engine',  # Microsoft Access
    r'ODBC Microsoft Access',  # Microsoft Access
    r'Syntax error (missing operator) in query expression',  # MSAccess, Oracle
    r'\bORA-d{5}',  # Oracle
    r'Oracle error',  # Oracle
    r'Oracle.*Driver',  # Oracle
    r'Warning.*Woci_.*',  # Oracle
    r'Warning.*Wora_.*',  # Oracle
    r'oracle.jdbc.driver',  # Oracle
    r'quoted string not properly terminated',  # Oracle, IBM DB2
    r'CLI Driver.*DB2',  # IBM DB2
    r'DB2 SQL error',  # IBM DB2
    r'\bdb2_w+\(',  # IBM DB2
    r'SQLSTATE.+SQLCODE',  # IBM DB2, Informix
    r'Exception.*Informix',  # Informix
    r'Informix ODBC Driver',  # Informix
    r'com.informix.jdbc',  # Informix
    r'weblogic.jdbc.informix',  # Informix
    r'Dynamic SQL Error',  # Firebird
    r'Warning.*ibase_.*',  # Firebird, SQLite
    r'SQLite/JDBCDriver',  # SQLite
    r'SQLite.Exception',  # SQLite
    r'System.Data.SQLite.SQLiteException',  # SQLite
    r'Warning.*sqlite_.*',  # SQLite
    r'Warning.*SQLite3::',  # SQLite
    r'\[SQLITE_ERROR\]',  # SQLite
    r'SQL error.*POS([0-9]+).*',  # SAP MaxDB
    r'Warning.*maxdb.*',  # SAP MaxDB
    r'Warning.*sybase.*',  # Sybase
    r'Sybase message',  # Sybase
    r'Sybase.*Server message.*',  # Sybase
    r'SybSQLException',  # Sybase
    r'com.sybase.jdbc',  # Sybase
    r'Warning.*ingres_',  # Ingres
    r'Ingres SQLSTATE',  # Ingres
    r'IngresW.*Driver',  # Ingres
    r'Exception (condition )?d+. Transaction rollback.',  # Frontbase
    r'org.hsqldb.jdbc',  # HSQLDB
    r'Unexpected end of command in statement \[',  # HSQLDB
    r'Unexpected token.*in statement \[',  # HSQLDB
}


def _replace_dict_value(adict: dict, key: str, value: str) -> None:
    """
    Replace a `value` given a `key` in a complex dict.

    :param adict: Complex dict.
    :param key: Key of the value that is going to be replaced.
    :param value: Value to replace in dict where is the given key.
    """
    for rkey in adict.keys():
        if rkey == key:
            adict[rkey] = value
        elif isinstance(adict[rkey], dict):
            _replace_dict_value(adict[rkey], key, value)


def _create_dataset(field: str, value_list: List[str],
                    query_string: Union[str, dict]) -> List:
    """
    Create dataset from values in list.

    :param query_string: String or dict with query parameters.
    :param field: Field to be taken from each of the values.
    :param value_list: List of values from which fields are to be extracted.
    :return: A List containing incremental versions of a dict, which contains
             the data in the specified field from value_list.
    """
    dataset = []
    if isinstance(query_string, str):
        data_dict = dict(parse_qsl(query_string))
    else:
        data_dict = deepcopy(query_string)
    for value in value_list:
        _replace_dict_value(data_dict, field, value)
        dataset.append(deepcopy(data_dict))
    return dataset


def _request_dataset(url: str, dataset_list: List, *args, **kwargs) -> List:
    r"""
    Request datasets and gives the results in a list.

    :param url: URL to test.
    :param dataset_list: List of datasets. For each of these an ``HTTP``
       session is created and the response recorded in the returned list.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.

    Either ``params``, ``json`` or ``data`` must be present in ``kwargs``,
    if the request is ``GET`` or ``POST``, respectively.
    """
    kw_new = kwargs.copy()
    resp = list()
    for dataset in dataset_list:
        if 'data' in kw_new:
            kw_new['data'] = dataset
        elif 'params' in kw_new:
            kw_new['params'] = dataset
        elif 'json' in kw_new:
            kw_new['json'] = dataset
        sess = http_helper.HTTPSession(url, *args, **kw_new)
        resp.append((len(sess.response.text), sess.response.status_code))
    return resp


def _options_request(url: str, *args, **kwargs) -> Optional[requests.Response]:
    r"""
    Send an``HTTP OPTIONS`` request.

    Tests what kind of ``HTTP`` methods are supported on the given ``url``.

    :param url: URL to test.
    :param \*args: Optional arguments for :py:func:`requests.options`.
    :param \*\*kwargs: Optional arguments for :py:func:`requests.options`.
    """
    try:
        return requests.options(url, verify=False, *args, **kwargs)
    except requests.ConnectionError as exc:
        raise http_helper.ConnError(exc)


def _has_method(url: str, method: str, *args, **kwargs) -> bool:
    r"""
    Check if specific HTTP method is allowed in URL.

    :param url: URL to test.
    :param method: HTTP method to test.
    :param \*args: Optional arguments for :py:func:`requests.options`.
    :param \*\*kwargs: Optional arguments for :py:func:`requests.options`.
    """
    try:
        is_method_present = _options_request(url, *args, **kwargs).headers
    except http_helper.ConnError as exc:
        show_unknown('Could not connnect',
                     details=dict(url=url,
                                  error=str(exc).replace(':', ',')))
        return False
    result = True
    if 'allow' in is_method_present:
        if method in is_method_present['allow']:
            show_open('HTTP Method {} enabled'.format(method),
                      details=dict(url=url),
                      refs='apache/restringir-metodo-http')
        else:
            show_close('HTTP Method {} disabled'.format(method),
                       details=dict(url=url),
                       refs='apache/restringir-metodo-http')
            result = False
    else:
        show_close('HTTP Method {} disabled'.format(method),
                   details=dict(url=url),
                   refs='apache/restringir-metodo-http')
        result = False
    return result


# pylint: disable=too-many-branches
def _has_insecure_header(url: str, header: str,     # noqa
                         *args, **kwargs) -> bool:  # noqa
    r"""
    Check if an insecure header is present.

    :param url: URL to test.
    :param header: Header to test if present.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    try:
        http_session = http_helper.HTTPSession(url, *args, **kwargs)
        headers_info = http_session.response.headers
        fingerprint = http_session.get_fingerprint()
    except http_helper.ConnError as exc:
        show_unknown('Could not connnect',
                     details=dict(url=url,
                                  error=str(exc).replace(':', ',')))
        return False

    if header == 'Access-Control-Allow-Origin':
        if 'headers' in kwargs:
            kwargs['headers'].update({'Origin':
                                      'https://www.malicious.com'})
        else:
            kwargs = {'headers': {'Origin': 'https://www.malicious.com'}}

        if header in headers_info:
            value = headers_info[header]
            if not re.match(HDR_RGX[header.lower()], value, re.IGNORECASE):
                show_open('{} HTTP header is insecure'.
                          format(header),
                          details=dict(url=url, header=header, value=value,
                                       fingerprint=fingerprint),
                          refs='apache/habilitar-headers-seguridad')
                return True
            show_close('HTTP header {} value is secure'.
                       format(header),
                       details=dict(url=url, header=header, value=value,
                                    fingerprint=fingerprint),
                       refs='apache/habilitar-headers-seguridad')
            return False
        show_close('HTTP header {} not present which is secure \
by default'.format(header),
                   details=dict(url=url, header=header,
                                fingerprint=fingerprint),
                   refs='apache/habilitar-headers-seguridad')
        return False

    result = True

    if header == 'X-AspNet-Version' or header == 'Server':
        if header in headers_info:
            value = headers_info[header]
            show_open('{} HTTP insecure header present'.
                      format(header),
                      details=dict(url=url, header=header, value=value,
                                   fingerprint=fingerprint),
                      refs='apache/habilitar-headers-seguridad')
            result = True
        else:
            show_close('{} HTTP insecure header not present'.
                       format(header),
                       details=dict(url=url, header=header,
                                    fingerprint=fingerprint),
                       refs='apache/habilitar-headers-seguridad')
            result = False
        return result
    if header in headers_info:
        value = headers_info[header]
        if re.match(HDR_RGX[header.lower()], value, re.IGNORECASE):
            show_close('HTTP header {} is secure'.format(header),
                       details=dict(url=url, header=header, value=value,
                                    fingerprint=fingerprint),
                       refs='apache/habilitar-headers-seguridad')
            result = False
        else:
            show_open('{} HTTP header is insecure'.
                      format(header),
                      details=dict(url=url, header=header, value=value,
                                   fingerprint=fingerprint),
                      refs='apache/habilitar-headers-seguridad')
            result = True
    else:
        show_open('{} HTTP header not present'.
                  format(header),
                  details=dict(url=url, header=header,
                               fingerprint=fingerprint),
                  refs='apache/habilitar-headers-seguridad')
        result = True

    return result


def _generic_has_multiple_text(url: str, regex_list: List[str],
                               *args, **kwargs) -> bool:
    r"""
    Check if one of a list of bad texts is present.

    :param url: URL to test.
    :param regex_list: List of regexes to search.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    try:
        http_session = http_helper.HTTPSession(url, *args, **kwargs)
        response = http_session.response
        fingerprint = http_session.get_fingerprint()
        if response.status_code != 200:
            show_unknown('There was an error',
                         details=dict(url=url, status=response.status_code,
                                      fingerprint=fingerprint))
            return False
        the_page = response.text
        for regex in regex_list:
            if re.search(regex, the_page, re.IGNORECASE):
                show_open('A bad text was present',
                          details=dict(url=url,
                                       bad_text=regex,
                                       fingerprint=fingerprint))
                return True
        show_close('No bad text was present',
                   details=dict(url=url, fingerprint=fingerprint))
        return False
    except http_helper.ConnError as exc:
        show_unknown('Could not connnect',
                     details=dict(url=url,
                                  error=str(exc).replace(':', ',')))
        return False


def _generic_has_text(url: str, expected_text: str, *args, **kwargs) -> bool:
    r"""
    Check if a bad text is present.

    :param url: URL to test.
    :param expected_text: Text to search. Can be regex.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    try:
        http_session = http_helper.HTTPSession(url, *args, **kwargs)
        response = http_session.response
        fingerprint = http_session.get_fingerprint()
        the_page = response.text
        if response.status_code != 200:
            show_unknown('There was an error',
                         details=dict(url=url,
                                      status=response.status_code,
                                      fingerprint=fingerprint))
            return False
        if re.search(str(expected_text), the_page, re.IGNORECASE):
            show_open('Bad text present',
                      details=dict(url=url,
                                   bad_text=expected_text,
                                   fingerprint=fingerprint))
            return True
        show_close('Bad text not present',
                   details=dict(url=url,
                                bad_text=expected_text,
                                fingerprint=fingerprint))
        return False
    except http_helper.ConnError as exc:
        show_unknown('Could not connnect',
                     details=dict(url=url,
                                  error=str(exc).replace(':', ',')))
        return False


@track
def has_multiple_text(url: str, regex_list: List[str],
                      *args, **kwargs) -> bool:
    r"""
    Check if one of a list of bad texts is present.

    :param url: URL to test.
    :param regex_list: List of regexes to search.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _generic_has_multiple_text(url, regex_list, *args, **kwargs)


@track
def has_text(url: str, expected_text: str, *args, **kwargs) -> bool:
    r"""
    Check if a bad text is present.

    :param url: URL to test.
    :param expected_text: Text to search. Can be regex.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _generic_has_text(url, expected_text, *args, **kwargs)


@track
def has_not_text(url: str, expected_text: str, *args, **kwargs) -> bool:
    r"""
    Check if a required text is not present.

    :param url: URL to test.
    :param expected_text: Text to search. Can be regex.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    try:
        http_session = http_helper.HTTPSession(url, *args, **kwargs)
        response = http_session.response
        fingerprint = http_session.get_fingerprint()
        the_page = response.text
        if not re.search(str(expected_text), the_page, re.IGNORECASE):
            show_open('Expected text not present',
                      details=dict(url=url,
                                   expected_text=expected_text,
                                   fingerprint=fingerprint))
            return True
        show_close('Expected text present',
                   details=dict(url=url,
                                expected_text=expected_text,
                                fingerprint=fingerprint))
        return False
    except http_helper.ConnError as exc:
        show_unknown('Could not connnect',
                     details=dict(url=url,
                                  error=str(exc).replace(':', ',')))
        return False


@track
def is_header_x_asp_net_version_present(url: str, *args, **kwargs) -> bool:
    r"""
    Check if X-AspNet-Version header is missing.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _has_insecure_header(url, 'X-AspNet-Version', *args, **kwargs)


@track
def is_header_access_control_allow_origin_missing(url: str,
                                                  *args, **kwargs) -> bool:
    r"""
    Check if access-control-allow-origin header is missing.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _has_insecure_header(url, 'Access-Control-Allow-Origin',
                                *args, **kwargs)


@track
def is_header_cache_control_missing(url: str, *args, **kwargs) -> bool:
    r"""
    Check if cache-control header is missing.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _has_insecure_header(url, 'Cache-Control', *args, **kwargs)


@track
def is_header_content_security_policy_missing(url: str,
                                              *args, **kwargs) -> bool:
    r"""
    Check if content-security-policy header is missing.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _has_insecure_header(url, 'Content-Security-Policy',
                                *args, **kwargs)


@track
def is_header_content_type_missing(url: str, *args, **kwargs) -> bool:
    r"""
    Check if content-type header is missing.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _has_insecure_header(url, 'Content-Type', *args, **kwargs)


@track
def is_header_expires_missing(url: str, *args, **kwargs) -> bool:
    r"""
    Check if expires header is missing.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _has_insecure_header(url, 'Expires', *args, **kwargs)


@track
def is_header_pragma_missing(url: str, *args, **kwargs) -> bool:
    r"""
    Check if pragma header is missing.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _has_insecure_header(url, 'Pragma', *args, **kwargs)


@track
def is_header_server_present(url: str, *args, **kwargs) -> bool:
    r"""
    Check if server header is insecure.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _has_insecure_header(url, 'Server', *args, **kwargs)


@track
def is_header_x_content_type_options_missing(url: str, *args,
                                             **kwargs) -> bool:
    r"""
    Check if x-content-type-options header is missing.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _has_insecure_header(url, 'X-Content-Type-Options',
                                *args, **kwargs)


@track
def is_header_x_frame_options_missing(url: str, *args, **kwargs) -> bool:
    r"""
    Check if x-frame-options header is missing.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _has_insecure_header(url, 'X-Frame-Options', *args, **kwargs)


@track
def is_header_perm_cross_dom_pol_missing(url: str, *args, **kwargs) -> bool:
    r"""
    Check if permitted-cross-domain-policies header is missing.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _has_insecure_header(url, 'X-Permitted-Cross-Domain-Policies',
                                *args, **kwargs)


@track
def is_header_x_xxs_protection_missing(url: str, *args, **kwargs) -> bool:
    r"""
    Check if x-xss-protection header is missing.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _has_insecure_header(url, 'X-XSS-Protection', *args, **kwargs)


@track
def is_header_hsts_missing(url: str, *args, **kwargs) -> bool:
    r"""
    Check if strict-transport-security header is missing.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _has_insecure_header(url, 'Strict-Transport-Security',
                                *args, **kwargs)


@track
def is_basic_auth_enabled(url: str, *args, **kwargs) -> bool:
    r"""
    Check if BASIC authentication is enabled.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _has_insecure_header(url, 'WWW-Authenticate', *args, **kwargs)


@track
def has_trace_method(url: str, *args, **kwargs) -> bool:
    r"""
    Check HTTP TRACE.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _has_method(url, 'TRACE', *args, **kwargs)


@track
def has_delete_method(url: str, *args, **kwargs) -> bool:
    r"""
    Check HTTP DELETE.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _has_method(url, 'DELETE', *args, **kwargs)


@track
def has_put_method(url: str, *args, **kwargs) -> bool:
    r"""
    Check HTTP PUT.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _has_method(url, 'PUT', *args, **kwargs)


@track
def has_sqli(url: str, *args, **kwargs) -> bool:
    r"""
    Check SQLi vuln by checking expected string.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    expect = SQLI_ERROR_MSG

    return _generic_has_multiple_text(url, expect, *args, **kwargs)


@track
def has_xss(url: str, expect: str, *args, **kwargs) -> bool:
    r"""
    Check XSS vuln by checking expected string.

    :param url: URL to test.
    :param expect: Text to search in potential vulnerabilty .
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _generic_has_text(url, expect, *args, **kwargs)


@track
def has_command_injection(url: str, expect: str, *args, **kwargs) -> bool:
    r"""
    Check command injection vuln by checking expected string.

    :param url: URL to test.
    :param expect: Text to search in potential vulnerabilty .
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _generic_has_text(url, expect, *args, **kwargs)


@track
def has_php_command_injection(url: str, expect: str, *args, **kwargs) -> bool:
    r"""
    Check PHP command injection vuln by checking expected string.

    :param url: URL to test.
    :param expect: Text to search in potential vulnerabilty .
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _generic_has_text(url, expect, *args, **kwargs)


@track
def has_session_fixation(url: str, expect: str, *args, **kwargs) -> bool:
    r"""
    Check session fixation by no passing cookies and authenticating.

    :param url: URL to test.
    :param expect: Text to search in potential vulnerabilty .
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _generic_has_text(url, expect, *args, **kwargs)


@track
def has_insecure_dor(url: str, expect: str, *args, **kwargs) -> bool:
    r"""
    Check insecure direct object reference vuln.

    :param url: URL to test.
    :param expect: Text to search in potential vulnerabilty .
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _generic_has_text(url, expect, *args, **kwargs)


@track
def has_dirtraversal(url: str, expect: str, *args, **kwargs) -> bool:
    r"""
    Check directory traversal vuln by checking expected string.

    :param url: URL to test.
    :param expect: Text to search in potential vulnerabilty .
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _generic_has_text(url, expect, *args, **kwargs)


@track
def has_csrf(url: str, expect: str, *args, **kwargs) -> bool:
    r"""
    Check CSRF vuln by checking expected string.

    :param url: URL to test.
    :param expect: Text to search in potential vulnerabilty .
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _generic_has_text(url, expect, *args, **kwargs)


@track
def has_lfi(url: str, expect: str, *args, **kwargs) -> bool:
    r"""
    Check local file inclusion vuln by checking expected string.

    :param url: URL to test.
    :param expect: Text to search in potential vulnerabilty .
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _generic_has_text(url, expect, *args, **kwargs)


@track
def has_hpp(url: str, expect: str, *args, **kwargs) -> bool:
    r"""
    Check HTTP Parameter Pollution vuln.

    :param url: URL to test.
    :param expect: Text to search in potential vulnerabilty .
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    return _generic_has_text(url, expect, *args, **kwargs)


@track
def has_insecure_upload(url: str, expect: str, file_param: str,
                        file_path: str, *args, **kwargs) -> bool:
    r"""
    Check insecure upload vuln.

    :param url: URL to test.
    :param file_param: Name of a file to try to upload.
    :param file_path: Path to the actual file.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    exploit_file = {file_param: open(file_path)}
    return _generic_has_text(url, expect, files=exploit_file, *args, **kwargs)


# pylint: disable=keyword-arg-before-vararg
@track
def is_sessionid_exposed(url: str, argument: str = 'sessionid',
                         *args, **kwargs) -> bool:
    r"""
    Check if resulting URL has an exposed session ID.

    :param url: URL to test.
    :argument: Name of argument to search. Defaults to ``sessionid``.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    try:
        http_session = http_helper.HTTPSession(url, *args, **kwargs)
        response_url = http_session.response.url
        fingerprint = http_session.get_fingerprint()
    except http_helper.ConnError as exc:
        show_unknown('Could not connnect',
                     details=dict(url=url,
                                  error=str(exc).replace(':', ',')))
        return False

    regex = r'\b(' + argument + r')\b=([a-zA-Z0-9_-]+)'

    result = True
    match = re.search(regex, response_url)
    if match:
        result = True
        show_open('Session ID is exposed',
                  details=dict(url=response_url, session_id='{}: {}'.
                               format(argument, match.group(2)),
                               fingerprint=fingerprint))
    else:
        result = False
        show_close('Session ID is hidden',
                   details=dict(url=response_url, session_id=argument))
    return result


@track
def is_version_visible(ip_address: str, ssl: bool = False,
                       port: int = 80) -> bool:
    """
    Check if banner is visible.

    :param ip_address: IP address to test.
    :param ssl: Whether to use HTTP or HTTPS.
    :param port: If necessary, specify port to connect to.
    """
    if ssl:
        service = banner_helper.HTTPSService(port)
    else:
        service = banner_helper.HTTPService(port)
    version = service.get_version(ip_address)
    fingerprint = service.get_fingerprint(ip_address)

    result = True
    if version:
        result = True
        show_open('HTTP version visible',
                  details=dict(site=ip_address, port=port,
                               version=version, fingerprint=fingerprint),
                  refs='apache/restringir-banner')
    else:
        result = False
        show_close('HTTP version not visible',
                   details=dict(site=ip_address, port=port,
                                fingerprint=fingerprint),
                   refs='apache/restringir-banner')
    return result


@track
def is_not_https_required(url: str) -> bool:
    r"""
    Check if HTTPS is always forced on a given url.

    :param url: URL to test.
    """
    assert url.startswith('http://')
    try:
        http_session = http_helper.HTTPSession(url)
        fingerprint = http_session.get_fingerprint()
        if http_session.url.startswith('https'):
            show_close('HTTPS is forced on URL',
                       details=dict(url=http_session.url,
                                    fingerprint=fingerprint),
                       refs='apache/configurar-soporte-https')
            return False
        show_open('HTTPS is not forced on URL',
                  details=dict(url=http_session.url, fingerprint=fingerprint),
                  refs='apache/configurar-soporte-https')
        return True
    except http_helper.ConnError as exc:
        show_unknown('Could not connnect',
                     details=dict(url=url,
                                  error=str(exc).replace(':', ',')))
        return False


@track
def has_dirlisting(url: str, *args, **kwargs) -> bool:
    r"""
    Check if the given URL has directory listing enabled.

    Looks for the text "Index of" to test if directories can be listed.
    See our `blog entry on the topic
    <https://fluidattacks.com/web/es/blog/apache-ocultar-tienda/>`_.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    bad_text = 'Index of'
    try:
        http_session = http_helper.HTTPSession(url, *args, **kwargs)
        response = http_session.response
        fingerprint = http_session.get_fingerprint()
        the_page = response.text

        if re.search(str(bad_text), the_page, re.IGNORECASE):
            show_open('Directory listing enabled',
                      details=dict(url=url, fingerprint=fingerprint))
            return True
        show_close('Directory listing not enabled',
                   details=dict(url=url, fingerprint=fingerprint))
        return False
    except http_helper.ConnError as exc:
        show_unknown('Could not connnect',
                     details=dict(url=url,
                                  error=str(exc).replace(':', ',')))
        return False


@track
def is_resource_accessible(url: str, *args, **kwargs) -> bool:
    r"""
    Check if url is available by checking response code.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    try:
        http_session = http_helper.HTTPSession(url, *args, **kwargs)
        fingerprint = http_session.get_fingerprint()
    except http_helper.ConnError as exc:
        show_close('Could not connnect to resource',
                   details=dict(url=url,
                                message=str(exc).replace(':', ',')))
        return False
    if re.search(r'[4-5]\d\d', str(http_session.response.status_code)):
        show_close('Resource not available',
                   details=dict(url=http_session.url,
                                status=http_session.response.status_code,
                                fingerprint=fingerprint))
        return False
    show_open('Resource available',
              details=dict(url=http_session.url,
                           status=http_session.response.status_code,
                           fingerprint=fingerprint))
    return True


@track
def is_response_delayed(url: str, *args, **kwargs) -> bool:
    r"""
    Check if the response time is acceptable.

    Values taken from:
    https://www.nngroup.com/articles/response-times-3-important-limits/

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    max_response_time = 1
    try:
        http_session = http_helper.HTTPSession(url, *args, **kwargs)
        fingerprint = http_session.get_fingerprint()
    except http_helper.ConnError as exc:
        show_unknown('Could not connnect',
                     details=dict(url=url,
                                  error=str(exc).replace(':', ',')))
        return False

    response_time = http_session.response.elapsed.total_seconds()
    delta = max_response_time - response_time

    if delta >= 0:
        show_close('Response time is acceptable',
                   details=dict(url=http_session.url,
                                response_time=response_time,
                                fingerprint=fingerprint))
        return False
    show_close('Response time not acceptable',
               details=dict(url=http_session.url,
                            response_time=response_time,
                            fingerprint=fingerprint))
    return True


# pylint: disable=too-many-locals
# pylint: disable=keyword-arg-before-vararg
@track
def has_user_enumeration(url: str, user_field: str,
                         user_list: Optional[List] = None,
                         fake_users: Optional[List] = None,
                         *args, **kwargs) -> bool:
    r"""
    Check if URL has user enumeration.

    :param url: URL to test.
    :param user_field: Field corresponding to the username.
    :param user_list: List of users.
    :param fake_users: List of fake users.
    :param \*args: Optional arguments for :func:`~_request_dataset`.
    :param \*\*kwargs: Optional arguments for :func:`~_request_dataset`.

    Either ``params`` or ``data`` must be present in ``kwargs``,
    if the request is ``GET`` or ``POST``, respectively.
    They must be strings as they would appear in the request.
    """
    assert 'params' in kwargs or 'data' in kwargs or 'json' in kwargs
    if 'params' in kwargs:
        query_string = kwargs['params']
        assert user_field in query_string
    elif 'data' in kwargs:
        query_string = kwargs['data']
        assert user_field in query_string
    elif 'json' in kwargs:
        query_string = kwargs['json']
        assert user_field in json.dumps(query_string)

    if not user_list:
        user_list = ['admin', 'administrator', 'guest', 'test']

    if not fake_users:
        fake_users = ['iuaksiuiadbuqywdaskj1234', 'ajahdsjahdjhbaj',
                      'aksjdads@asd.com', 'osvtxodahidhiis@gmail.com',
                      'something@example.com', '12312314511231']

    # Evaluate the response with non-existant users
    fake_datasets = _create_dataset(user_field, fake_users, query_string)

    fake_res = _request_dataset(url, fake_datasets, *args, **kwargs)

    true_datasets = _create_dataset(user_field, user_list, query_string)

    user_res = _request_dataset(url, true_datasets, *args, **kwargs)

    num_comp = len(fake_res) * len(user_res)

    merged = [(x, y) for x in fake_res for y in user_res]

    from difflib import SequenceMatcher
    res = 0.0
    for resp_text, resp_time in merged:
        res += SequenceMatcher(None, resp_text, resp_time).ratio()

    rat = round(res / num_comp, 2)

    if rat > 0.95:
        show_close('User enumeration not possible',
                   details=dict(url=url, similar_answers_ratio=rat))
        return False
    show_open('User enumeration possible',
              details=dict(url=url, similar_answers_ratio=rat))
    return True


# pylint: disable=keyword-arg-before-vararg
# pylint: disable=too-many-arguments
@track  # noqa
def can_brute_force(url: str, ok_regex: str, user_field: str, pass_field: str,
                    user_list: List[str] = None, pass_list: List[str] = None,
                    *args, **kwargs) -> bool:
    r"""
    Check if URL allows brute forcing.

    :param url: URL to test.
    :param ok_regex: Regex to search in response text.
    :param user_field: Name of the field for username.
    :param pass_field: Name of the field for password.
    :param user_list: List of users to create dataset.
    :param pass_list: List of passwords.
    :param \*args: Optional arguments for :func:`~_request_dataset`.
    :param \*\*kwargs: Optional arguments for :func:`~_request_dataset`.

    Either ``params`` or ``data`` must be present in ``kwargs``,
    if the request is ``GET`` or ``POST``, respectively.
    They must be strings as they would appear in the request.
    """
    assert 'params' in kwargs or 'data' in kwargs
    if 'params' in kwargs:
        query_string = kwargs['params']
    if 'data' in kwargs:
        query_string = kwargs['data']

    assert isinstance(user_list, list)
    assert isinstance(pass_list, list)

    users_dataset = _create_dataset(user_field, user_list, query_string)

    dataset = []
    for password in pass_list:
        for user_ds in users_dataset:
            _datas = _create_dataset(pass_field, [password], user_ds)
            dataset.append(_datas[0])

    for _datas in dataset:
        if 'params' in kwargs:
            kwargs['params'] = _datas
        elif 'data' in kwargs:
            kwargs['data'] = _datas
        try:
            sess = http_helper.HTTPSession(url, *args, **kwargs)
            fingerprint = sess.get_fingerprint()
        except http_helper.ConnError as exc:
            show_unknown('Could not connect',
                         details=dict(url=url, data_used=_datas,
                                      error=str(exc).replace(':', ',')))
            return False
        if ok_regex in sess.response.text:
            show_open('Brute forcing possible',
                      details=dict(url=url, data_used=_datas,
                                   fingerprint=fingerprint))
            return True
    show_close('Brute forcing not possible',
               details=dict(url=url, fingerprint=fingerprint))
    return False


@track
def has_clear_viewstate(url: str, *args, **kwargs) -> bool:
    r"""
    Check if url has encrypted ViewState by checking response.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    try:
        http_session = http_helper.HTTPSession(url, *args, **kwargs)
        fingerprint = http_session.get_fingerprint()
    except http_helper.ConnError as exc:
        show_unknown('Could not connnect',
                     details=dict(url=url,
                                  error=str(exc).replace(':', ',')))
        return False

    vsb64 = http_session.get_html_value('input', '__VIEWSTATE')

    if not vsb64:
        show_close('ViewState not found',
                   details=dict(url=http_session.url,
                                fingerprint=fingerprint))
        return False
    try:
        vs_obj = ViewState(vsb64)
        decoded_vs = vs_obj.decode()
        show_open('ViewState is not encrypted',
                  details=dict(url=http_session.url,
                               ViewState=decoded_vs,
                               fingerprint=fingerprint))
        return True
    except ViewStateException:
        show_close('ViewState is encrypted',
                   details=dict(url=http_session.url,
                                fingerprint=fingerprint))
    return False


@track
def is_date_unsyncd(url: str, *args, **kwargs) -> bool:
    r"""
    Check if server's date is not syncronized with NTP servers.

    :param url: URL to test.
    :param \*args: Optional arguments for :class:`.HTTPSession`.
    :param \*\*kwargs: Optional arguments for :class:`.HTTPSession`.
    """
    try:
        sess = http_helper.HTTPSession(url, *args, **kwargs)
        fingerprint = sess.get_fingerprint()

        server_date = datetime.strptime(sess.response.headers['Date'],
                                        '%a, %d %b %Y %H:%M:%S GMT')
        server_ts = server_date.timestamp()
        ntpclient = ntplib.NTPClient()
        response = ntpclient.request('pool.ntp.org', port=123, version=3)
        ntp_date = datetime.fromtimestamp(response.tx_time, tz=timezone('GMT'))
        ntp_ts = datetime.utcfromtimestamp(ntp_date.timestamp()).timestamp()
    except (KeyError, http_helper.ConnError) as exc:
        show_unknown('Could not connnect',
                     details=dict(url=url,
                                  error=str(exc).replace(':', ',')))
        return False
    diff = ntp_ts - server_ts

    if diff < -3 or diff > 3:
        show_open("Server's clock is not syncronized with NTP",
                  details=dict(url=url,
                               server_date=server_date,
                               ntp_date=ntp_date,
                               offset=diff,
                               fingerprint=fingerprint))
        return True
    show_close("Server's clock is syncronized with NTP",
               details=dict(url=url,
                            server_date=server_date,
                            ntp_date=ntp_date,
                            offset=diff,
                            fingerprint=fingerprint))
    return False
