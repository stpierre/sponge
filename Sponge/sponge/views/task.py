#!/usr/bin/python -Ott
""" Brief summary of the script
 
Maintainer: Chris St Pierre <stpierreca@ornl.gov>
Purpose: 
Where/How/When: 
Return Values: 
Expected Output: 
Assumptions/Dependencies: 
"""

__author__ = "Chris St Pierre"
__credits__ = ["Chris St Pierre"]
__version__ = "$Id$"
__maintainer__ = "Chris St Pierre"
__email__ = "stpierreca@ornl.gov"

import sys
import logging
from optparse import OptionParser, OptionError

LOGGER = None

def get_logger(verbose=0):
    """ set up logging according to the verbose level given on the
    command line """
    global LOGGER
    if LOGGER is None:
        LOGGER = logging.getLogger(sys.argv[0])
        stderr = logging.StreamHandler()
        level = logging.WARNING
        lformat = "%(message)s"
        if verbose == 1:
            level = logging.INFO
        elif verbose > 1:
            stderr.setFormatter(logging.Formatter("%(asctime)s: %(levelname)s: %(message)s"))
            level = logging.DEBUG
        LOGGER.setLevel(level)
        LOGGER.addHandler(stderr)
        syslog = logging.handlers.SysLogHandler("/dev/log")
        syslog.setFormatter(logging.Formatter("%(name)s: %(message)s"))
        LOGGER.addHandler(syslog)
        LOGGER.debug("Setting verbose to %s", verbose)
    return LOGGER

def main():
    """main subroutine"""

    parser = OptionParser()
    parser.add_option("-v", "--verbose", help="Be verbose", action="count")
    # add parser.add_option() calls here
    try:
        # options contains the options understood by OptionParser
        # (including options.verbose); args contains other positional
        # arguments
        (options, args) = parser.parse_args()
    except OptionError:
        parser.print_help()
        return 1

    logger = get_logger(options.verbose)

    # your program goes here

if __name__ == "__main__":
    sys.exit(main())


