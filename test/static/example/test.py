#/usr/bin/python
"""Test exploit."""

from fluidasserts.format import string

otp = '12345'
string.is_otp_token_insecure(otp)
