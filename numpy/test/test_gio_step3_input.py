#!/usr/bin/env python
#
#
# test_gio_step3_input.py
#
# purpose:
# author:   Filipe P. A. Fernandes
# e-mail:   ocefpaf@gmail
# web:      http://ocefpaf.tiddlyspot.com/
# created:  03-Aug-2011
# modified: Wed 03 Aug 2011 12:27:58 PM EDT
#
# obs:
#

"""Unit test for too.gio
   A proper unittest would be one with compare values.
   However, here I just run a "stable code" vs development code.

   The input data for the test:
   http://ccc-gistemp.googlecode.com/files/ccc-gistemp-input-20110222.zip
"""

import unittest

from CCCgistemp.tool import gio

class Test_gio(unittest.TestCase):
    """Test gio."""

    def test_short_step2_v2(self):
        """Test reading short version of step2.v2"""
        # Stable
        records = list(gio.GHCNV2Reader("work/step2_short.v2",
                                        meta=gio.v2meta()))

        # Numpy
        records_array = gio.GHCNV2Reader_array("work/step2_short.v2",
                                               meta=gio.v2meta())

        # TODO: assert something once I make Series object

    def test_long_step2_v2(self):
        """Test reading short version of step2.v2"""
        # Stable
        records = list(gio.GHCNV2Reader("work/step2_long.v2",
                                        meta=gio.v2meta()))

        # Numpy
        records = gio.GHCNV2Reader_array("work/step2_long.v2",
                                          meta=gio.v2meta())
