# -*- coding: utf-8 -*-

"""Modulo para pruebas de SSH.

Este modulo contiene las funciones necesarias para probar si el modulo de
SSH se encuentra adecuadamente implementado.
"""

# standard imports
from __future__ import print_function

# 3rd party imports
import pytest

# local imports
from fluidasserts.proto import ssh



#
# Constants
#

SSH_PORT = 22
ADMIN_USER = 'nonpriv'
ADMIN_PASS = 'ahgh7xee9eewaeGh'
NON_EXISTANT_SERVER = '0.0.0.0'

#
# Open tests
#


@pytest.mark.parametrize('run_mock',
                         [('os:hard', {'22/tcp': SSH_PORT})],
                         indirect=True)
def test_is_hmac_used_close(run_mock):
    """Server SSH uses HMAC?."""
    assert not ssh.is_hmac_used(run_mock, username=ADMIN_USER,
                                password=ADMIN_PASS)
    assert not ssh.is_hmac_used(run_mock, port=24, username=ADMIN_USER,
                                password=ADMIN_PASS)
    assert not ssh.is_hmac_used(NON_EXISTANT_SERVER, username=ADMIN_USER,
                                password=ADMIN_PASS)


def test_is_is_cbc_used_close(run_mock):
    """Server SSH uses CBC?."""
    assert not ssh.is_cbc_used(run_mock, username=ADMIN_USER,
                               password=ADMIN_PASS)
    assert not ssh.is_cbc_used(run_mock, port=24, username=ADMIN_USER,
                               password=ADMIN_PASS)
    assert not ssh.is_cbc_used(NON_EXISTANT_SERVER, username=ADMIN_USER,
                               password=ADMIN_PASS)
