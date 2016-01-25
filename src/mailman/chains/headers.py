# Copyright (C) 2007-2016 by the Free Software Foundation, Inc.
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

"""The header-matching chain."""

__all__ = [
    'HeaderMatchChain',
    ]


import re
import logging

from mailman.chains.base import Chain, Link
from mailman.config import config
from mailman.core.i18n import _
from mailman.interfaces.chain import LinkAction
from mailman.interfaces.rules import IRule
from zope.interface import implementer


log = logging.getLogger('mailman.error')



def make_link(header, pattern, chain=None):
    """Create a Link object.

    The link action is to defer by default, since at the end of all the
    header checks, we'll jump to the chain defined in the configuration
    file, should any of them have matched.  However, it is possible to
    create a link which jumps to a specific chain.

    :param header: The email header name to check, e.g. X-Spam.
    :type header: string
    :param pattern: A regular expression for matching the header value.
    :type pattern: string
    :param chain: When given, this is the name of the chain to jump to if the
        pattern matches the header.
    :type chain: string
    :return: The link representing this rule check.
    :rtype: `ILink`
    """
    rule = HeaderMatchRule(header, pattern)
    if chain is None:
        return Link(rule)
    return Link(rule, LinkAction.jump, chain)



@implementer(IRule)
class HeaderMatchRule:
    """Header matching rule used by header-match chain."""

    # Sequential rule counter.
    _count = 1

    def __init__(self, header, pattern):
        self.header = header
        self.pattern = pattern
        self.name = 'header-match-{0:02}'.format(HeaderMatchRule._count)
        HeaderMatchRule._count += 1
        self.description = '{0}: {1}'.format(header, pattern)
        # XXX I think we should do better here, somehow recording that a
        # particular header matched a particular pattern, but that gets ugly
        # with RFC 2822 headers.  It also doesn't match well with the rule
        # name concept.  For now, we just record the rather useless numeric
        # rule name.  I suppose we could do the better hit recording in the
        # check() method, and set self.record = False.
        self.record = True
        # Register this rule so that other parts of the system can query it.
        assert self.name not in config.rules, (
            'Duplicate HeaderMatchRule: {} [{}: {}]'.format(
                self.name, self.header, self.pattern))
        config.rules[self.name] = self

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        for value in msg.get_all(self.header, []):
            if re.search(self.pattern, value, re.IGNORECASE):
                return True
        return False



class HeaderMatchChain(Chain):
    """Default header matching chain.

    This could be extended by header match rules in the database.
    """

    def __init__(self):
        super(HeaderMatchChain, self).__init__(
            'header-match', _('The built-in header matching chain'))
        # This chain will dynamically calculate the links from the
        # configuration file, the database, and any explicitly added header
        # checks (via the .extend() method).
        self._extended_links = []

    def extend(self, header, pattern):
        """Extend the existing header matches.

        :param header: The case-insensitive header field name.
        :param pattern: The pattern to match the header's value again.  The
            match is not anchored and is done case-insensitively.
        """
        self._extended_links.append(make_link(header, pattern))

    def flush(self):
        """See `IMutableChain`."""
        # Remove all dynamically created rules.  Use the keys so we can mutate
        # the dictionary inside the loop.
        for rule_name in list(config.rules):
            if rule_name.startswith('header-match-'):
                del config.rules[rule_name]
        self._extended_links = []

    def get_links(self, mlist, msg, msgdata):
        """See `IChain`."""
        # First return all the configuration file links.
        for line in config.antispam.header_checks.splitlines():
            if len(line.strip()) == 0:
                continue
            parts = line.split(':', 1)
            if len(parts) != 2:
                log.error('Configuration error: [antispam]header_checks '
                          'contains bogus line: {}'.format(line))
                continue
            yield make_link(parts[0], parts[1].lstrip())
        # Then return all the explicitly added links.
        yield from self._extended_links
        # If any of the above rules matched, they will have deferred their
        # action until now, so jump to the chain defined in the configuration
        # file.  For security considerations, this takes precedence over
        # list-specific matches.
        yield Link('any', LinkAction.jump, config.antispam.jump_chain)
        # Then return all the list-specific header matches.
        for entry in mlist.header_matches:
            yield make_link(entry.header, entry.pattern, entry.chain)
