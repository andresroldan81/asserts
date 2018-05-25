# -*- coding: utf-8 -*-

"""Test methods of fluidasserts.code.java."""

# standard imports
import io
import sys

# 3rd party imports
# None

# local imports
from fluidasserts.lang import java
import fluidasserts.utils.decorators

# Constants
fluidasserts.utils.decorators.UNITTEST = True
CODE_DIR = 'test/static/lang/java/'
SECURE_CODE = CODE_DIR + 'GenericExceptionsClose.java'
INSECURE_CODE = CODE_DIR + 'GenericExceptionsOpen.java'
SECURE_EMPTY_CATCH = CODE_DIR + 'GenericExceptionsOpen.java'
INSECURE_EMPTY_CATCH = CODE_DIR + 'EmptyCatchOpen.java'
INSECURE_SWITCH = CODE_DIR + 'SwitchDefaultOpen.java'
SECURE_SWITCH = CODE_DIR + 'SwitchDefaultClose.java'
SECURE_RANDOM = CODE_DIR + 'GenericExceptionsClose.java'
INSECURE_RANDOM = CODE_DIR + 'EmptyCatchOpen.java'
SECURE_HASH = CODE_DIR + 'GenericExceptionsClose.java'
INSECURE_HASH = CODE_DIR + 'GenericExceptionsOpen.java'
NON_EXISTANT_CODE = CODE_DIR + 'NotExists.java'
LINES_FORMAT = 'lines[39;49;00m: [31;01m'

#
# Open tests
#


def test_has_generic_exceptions_open():
    """Code uses generic exceptions."""
    assert java.has_generic_exceptions(INSECURE_CODE)


def test_has_generic_exceptions_in_dir_open():
    """Code uses generic exceptions."""
    assert java.has_generic_exceptions(CODE_DIR)


def test_uses_print_stack_trace_open():
    """Search printStackTrace calls."""
    assert java.uses_print_stack_trace(INSECURE_CODE)


def test_uses_print_stack_trace_in_dir_open():
    """Search printStackTrace calls."""
    assert java.uses_print_stack_trace(CODE_DIR)


def test_swallows_exceptions_open():
    """Search empty catches."""
    capt_out = io.StringIO()
    fluidasserts.OUTFILE = capt_out
    expected = LINES_FORMAT + '12, 15'
    assert java.swallows_exceptions(INSECURE_EMPTY_CATCH)
    fluidasserts.OUTFILE = sys.stdout
    assert expected in capt_out.getvalue()


def test_has_empty_catches_in_dir_open():
    """Search empty catches."""
    assert java.swallows_exceptions(CODE_DIR)


def test_has_switch_without_default_open():
    """Search switch without default clause."""
    assert java.has_switch_without_default(INSECURE_SWITCH)


def test_has_switch_without_default_in_dir_open():
    """Search switch without default clause."""
    assert java.has_switch_without_default(CODE_DIR)


def test_has_insecure_randoms_open():
    """Search Math.random() calls."""
    assert java.has_insecure_randoms(INSECURE_RANDOM)


def test_has_insecure_randoms_in_dir_open():
    """Search Math.random() calls."""
    assert java.has_insecure_randoms(CODE_DIR)


def test_has_if_without_else_open():
    """Search conditionals without an else option."""
    assert java.has_if_without_else(INSECURE_CODE)


def test_has_if_without_else_in_dir_open():
    """Search conditionals without an else option."""
    assert java.has_if_without_else(CODE_DIR)


def test_uses_md5_hash_open():
    """Search MD5 hash algorithm."""
    assert java.uses_md5_hash(INSECURE_HASH)


def test_uses_md5_hash_open_in_dir():
    """Search MD5 hash algorithm."""
    assert java.uses_md5_hash(CODE_DIR)


def test_uses_sha1_hash_open():
    """Search SHA-1 hash algorithm."""
    assert java.uses_sha1_hash(INSECURE_HASH)


def test_uses_sha1_hash_open_in_dir():
    """Search SHA-1 hash algorithm."""
    assert java.uses_sha1_hash(CODE_DIR)

#
# Closing tests
#


def test_has_generic_exceptions_close():
    """Code uses generic exceptions."""
    assert not java.has_generic_exceptions(SECURE_CODE)
    assert not java.has_generic_exceptions(NON_EXISTANT_CODE)


def test_uses_print_stack_trace_close():
    """Search printStackTrace calls."""
    assert not java.uses_print_stack_trace(SECURE_CODE)
    assert not java.uses_print_stack_trace(NON_EXISTANT_CODE)


def test_has_empty_catches_close():
    """Search empty catches."""
    assert not java.swallows_exceptions(SECURE_EMPTY_CATCH)
    assert not java.swallows_exceptions(NON_EXISTANT_CODE)


def test_has_switch_without_default_close():
    """Search switch without default clause."""
    assert not java.has_switch_without_default(SECURE_SWITCH)
    assert not java.has_switch_without_default(NON_EXISTANT_CODE)


def test_has_insecure_randoms_close():
    """Search conditionals without an else option."""
    assert not java.has_insecure_randoms(SECURE_CODE)
    assert not java.has_insecure_randoms(NON_EXISTANT_CODE)


def test_uses_md5_hash_close():
    """Search MD5 hash algorithm."""
    assert not java.uses_md5_hash(SECURE_HASH)
    assert not java.uses_md5_hash(NON_EXISTANT_CODE)


def test_uses_sha1_hash_close():
    """Search SHA-1 hash algorithm."""
    assert not java.uses_sha1_hash(SECURE_HASH)
    assert not java.uses_sha1_hash(NON_EXISTANT_CODE)
