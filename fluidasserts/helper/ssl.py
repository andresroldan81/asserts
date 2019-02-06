# -*- coding: utf-8 -*-
"""This module enables connections via SSL."""

# standard imports
from __future__ import absolute_import
from contextlib import contextmanager
from typing import Generator, Tuple, List
import copy
import socket
import ssl

# 3rd party imports
import tlslite

# local imports
# None

PORT = 443

ORIG_METHOD = copy.deepcopy(tlslite.recordlayer.RecordLayer.addPadding)


def _my_add_padding(self, data: bytes) -> bytes:
    """
    Add padding to data so that it is multiple of block size.

    :param data: Original bytestring to pad.
    """
    current_length = len(data)
    block_length = self.blockSize
    padding_length = block_length - 1 - (current_length % block_length)
    padding_bytes = bytearray([padding_length] * (padding_length + 1))
    padding_bytes = bytearray(x ^ 42 for x in padding_bytes[0:-1])
    padding_bytes.append(padding_length)
    data += padding_bytes
    return data


@contextmanager
def connect_legacy(hostname: str, port: int = PORT,
                   ciphers: str = 'HIGH:!DH:!aNULL',
                   validate_cert: bool = False) \
        -> Generator[ssl.SSLSocket, None, None]:
    """
    Establish a legacy SSL/TLS connection.

    :param hostname: Host name to connect to.
    :param port: Port to connect. Defaults to 443.
    :param ciphers: Encryption algorithms. Defaults to (as per Python's SSL)
                    ``'DEFAULT:!aNULL:!eNULL:!LOW:!EXPORT:!SSLv2'``.
    """
    if validate_cert:
        flags = ssl.VERIFY_X509_STRICT
    else:
        flags = ssl.VERIFY_DEFAULT

    context = ssl.create_default_context()
    context.verify_flags = flags
    context.check_hostname = False
    context.verify_mode = ssl.CERT_OPTIONAL
    if ciphers:
        context.set_ciphers(ciphers)
    context.load_default_certs()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    ssock = context.wrap_socket(sock=sock, server_hostname=hostname)
    ssock.connect((hostname, port))
    yield ssock
    ssock.close()


# pylint: disable=too-many-arguments
@contextmanager
def connect(hostname, port: int = PORT, check_poodle_tls: bool = False,
            min_version: Tuple[int, int] = (3, 0),
            max_version: Tuple[int, int] = (3, 3),
            cipher_names: List[str] = None,
            key_exchange_names: List[str] = None,
            anon: bool = False)\
        -> Generator[tlslite.TLSConnection, None, None]:
    """
    Establish a SSL/TLS connection.

    :param hostname: Host name to connect to.
    :param port: Port to connect. Defaults to 443.
    :param check_poodle_tls: Depending on this, choose padding method.
    :param min_version: Minimum SSL/TLS version acceptable. (Default TLS 1.0)
    :param max_version: Minimum SSL/TLS version acceptable. (Default TLS 1.2)
    :param cipher_names: List of allowed ciphers.
    :param key_exchange_names: List of exchange names.
    :param anon: Whether to make the handshake anonymously.
    """
    if check_poodle_tls:
        tlslite.recordlayer.RecordLayer.addPadding = _my_add_padding
    else:
        tlslite.recordlayer.RecordLayer.addPadding = ORIG_METHOD

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((hostname, port))

    connection = tlslite.TLSConnection(sock)
    connection.ignoreAbruptClose = True

    settings = tlslite.HandshakeSettings()
    settings.minVersion = min_version
    settings.maxVersion = max_version
    if cipher_names:
        settings.cipherNames = cipher_names
    if key_exchange_names:
        settings.keyExchangeNames = key_exchange_names

    if anon:
        connection.handshakeClientAnonymous(settings=settings)
    else:
        connection.handshakeClientCert(settings=settings)
    yield connection
    connection.close()
