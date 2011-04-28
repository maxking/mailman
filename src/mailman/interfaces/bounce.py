# Copyright (C) 2010-2011 by the Free Software Foundation, Inc.
#
# This file is part of GNU Mailman.
#
# GNU Mailman is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# GNU Mailman is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.

"""Interface to bounce detection components."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'BounceStatus',
    'IBounceDetector',
    ]


from flufl.enum import Enum
from zope.interface import Interface



class BounceStatus(Enum):
    """Special bounce statuses."""

    # Matching addresses were found, but they were determined to be non-fatal.
    # In this case, processing is halted but no bounces are registered.
    non_fatal = 1

    # If a bounce detector returns Stop, that means to just discard the
    # message.  An example is warning messages for temporary delivery
    # problems.  These shouldn't trigger a bounce notification, but we also
    # don't want to send them on to the list administrator.
    stop = 2



class IBounceDetector(Interface):
    """Detect a bounce in an email message."""

    def process(self, msg):
        """Scan an email message looking for bounce addresses.

        :param msg: An email message.
        :type msg: `Message`
        :return: The detected bouncing addresses.  When bouncing addresses are
            found but are determined to be non-fatal, the enum
            `BounceStatus.non_fatal` can be returned to halt any bounce
            processing pipeline.  When bounce processing should stop, a
            `BounceStatus.stop` is returned.
        :rtype: A set strings, or a `BounceStatus`
        """
