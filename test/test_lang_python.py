# -*- coding: utf-8 -*-

"""Test methods of fluidasserts.code.python."""

# standard imports
import io
import sys

# 3rd party imports
# None

# local imports
from fluidasserts.lang import python
import fluidasserts.utils.decorators
import fluidasserts

# Constants
fluidasserts.utils.decorators.UNITTEST = True
CODE_DIR = 'test/static/lang/python/'
SECURE_CODE = CODE_DIR + 'exceptions_close.py'
INSECURE_CODE = CODE_DIR + 'exceptions_open.py'
LINES_FORMAT = 'lines[39;49;00m: [31;01m'


#
# Open tests
#

def test_has_generic_exceptions_open():
    """Code uses generic exceptions."""
    assert python.has_generic_exceptions(INSECURE_CODE)


def test_has_generic_exceptions_in_dir_open():
    """Code uses generic exceptions."""
    assert python.has_generic_exceptions(CODE_DIR)


def test_swallows_exceptions_open():
    """Code swallows exceptions."""
    capt_out = io.StringIO()
    fluidasserts.OUTFILE = capt_out
    expected = LINES_FORMAT + '13, 17, 21'
    assert python.swallows_exceptions(INSECURE_CODE)
    fluidasserts.OUTFILE = sys.stdout
    assert expected in capt_out.getvalue()


def test_swallows_exceptions_in_dir_open():
    """Search switch without default clause."""
    assert python.swallows_exceptions(CODE_DIR)


#
# Closing tests
#


def test_has_generic_exceptions_close():
    """Code uses generic exceptions."""
    assert not python.has_generic_exceptions(SECURE_CODE)


def test_swallows_exceptions_close():
    """Code swallows exceptions."""
    assert not python.swallows_exceptions(SECURE_CODE)
