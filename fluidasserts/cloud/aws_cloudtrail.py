# -*- coding: utf-8 -*-

"""
AWS cloud checks (CLOUDTRAIL).

The checks are based on CIS AWS Foundations Benchmark.
"""

# standard imports
# None

# 3rd party imports
# None

# local imports
from fluidasserts import show_close
from fluidasserts import show_open
from fluidasserts import show_unknown
from fluidasserts.utils.decorators import track, level
from fluidasserts.helper import aws


@level('low')
@track
def trails_not_multiregion(key_id: str, secret: str) -> bool:
    """
    Check if trails are multiregion.

    :param key_id: AWS Key Id
    :param secret: AWS Key Secret
    """
    result = False
    try:
        trails = aws.list_trails(key_id, secret)
    except aws.ConnError as exc:
        show_unknown('Could not connect',
                     details=dict(error=str(exc).replace(':', '')))
        return False
    except aws.ClientErr as exc:
        show_unknown('Error retrieving info. Check credentials.',
                     details=dict(error=str(exc).replace(':', '')))
        return False
    if not trails:
        show_close('Not trails were found')
        return False

    for trail in trails:
        if not trail['IsMultiRegionTrail']:
            show_open('Trail is not multiregion',
                      details=dict(trail_arn=trail['TrailARN']))
            result = True
        else:
            show_close('Trail is multiregion',
                       details=dict(trail_arn=trail['TrailARN']))
    return result
