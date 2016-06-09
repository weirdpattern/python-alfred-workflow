"""
.. module:: workflow_version
   :platform: Unix
   :synopsis: Provides an easy way to handle versions.

.. moduleauthor:: Patricio Trevino <patricio@weirdpattern.com>

"""

from utils import parse_version


class Version(object):
    """A class that provides an easy way to handle versions.

    .. note: this class follows the `SEMVER <http://semver.org/>`_ format.
    """

    def __init__(self, version):
        """Initializes the :class:`Version`.

        :param version: the string representation of the version.
        :type version: ``str``.
        """

        self.version = version

        segments = parse_version(version)

        self.major = segments[0]
        self.minor = segments[1]
        self.patch = segments[2]
        self.release = segments[3]
        self.build = segments[4]

    @property
    def segments(self):
        """Gets the segments comprising this version.

        .. note::
           The segments are returned in the following order:
           1. major version
           2. Minor version
           3. Patch version
           4. Release (if any)
           5. Build (if any)


        :return: a ``5-tuple`` with the version information.
        :rtype: ``5-tuple``.
        """

        return self.major, self.minor, self.patch, self.release, self.build

    def __eq__(self, other):
        """Handles the eq operator"""

        if not isinstance(other, Version):
            raise ValueError('Not a Version instance: {0!r}'.format(other))

        return self.segments == other.segments

    def __ne__(self, other):
        """Handles the ne operator"""

        return not self.__eq__(other)

    def __gt__(self, other):
        """Handles the gt operator"""

        if not isinstance(other, Version):
            raise ValueError('Not a Version instance: {0!r}'.format(other))

        left = self.segments[:3]
        right = other.segments[:3]

        if left > right:
            return True

        if left == right:
            if not self.release and not other.release:
                return False
            elif self.release and not other.release:
                return False
            elif other.release and not self.release:
                return True

            leftnumber = -1
            leftsegments = self.release.split('.')
            if len(leftsegments) == 2:
                leftnumber = leftsegments[1]

            rightnumber = 0
            rightsegments = other.release.split('.')
            if len(rightsegments) == 2:
                rightnumber = rightsegments[1]

            return leftnumber > rightnumber

        return False

    def __ge__(self, other):
        """Handles the ge operator"""

        if not isinstance(other, Version):
            raise ValueError('Not a Version instance: {0!r}'.format(other))

        return not other.__gt__(self)

    def __lt__(self, other):
        """Handles the lt operator"""

        if not isinstance(other, Version):
            raise ValueError('Not a Version instance: {0!r}'.format(other))

        return other.__gt__(self)

    def __le__(self, other):
        """Handles the le operator"""

        if not isinstance(other, Version):
            raise ValueError('Not a Version instance: {0!r}'.format(other))

        return not self.__gt__(other)

    def __str__(self):
        """Handles the str operator"""

        version = '{0}.{1}.{2}'.format(self.major, self.minor, self.patch)

        if self.release:
            version += '-{0}'.format(self.release)

        if self.build:
            version += '+{0}'.format(self.build)

        return version

    def __repr__(self):
        """Handles the repr operator"""

        return "Version('{0}')".format(str(self))
