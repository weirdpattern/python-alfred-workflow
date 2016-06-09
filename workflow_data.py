"""
.. module:: workflow_data
   :platform: Unix
   :synopsis: Controls the workflow data operations.

.. moduleauthor:: Patricio Trevino <patricio@weirdpattern.com>

"""

import os

from utils import PickleSerializer, ensure_path, atomic_write, atomic


class SerializationException(Exception):
    """Serialization error"""


class WorkflowData(object):
    """A class that provides a way to interact with a workflow data"""

    def __init__(self, workflow):
        """Initializes the :class:`WorkflowCache`.

        :param workflow: the :class:`workflow.Workflow` instance we want to control.
        :type workflow: :class:`workflow.Workflow`
        """

        self._workflow = workflow
        self._directory = None
        self._serializer = PickleSerializer()

    @property
    def workflow(self):
        """Gets the :class:`workflow.Workflow` instance.

        :return: the :class:`workflow.Workflow` instance.
        :rtype: :class:`workflow.Workflow`.
        """

        return self._workflow

    @property
    def directory(self):
        """Gets the workflow data directory.

        .. note::
           The directory is calculated based off of the workflow environment variable. If such variable
           is not defined, then it defaults to:

           Alfred 3:
           ~/Library/Application Support/Alfred-3/Workflow Data/

           Alfred 2:
           ~/Library/Application Support/Alfred-2/Workflow Data/

        :return: the workflow data directory.
        :rtype: ``str``.
        """

        if not self._directory:
            if self.workflow.environment('workflow_data'):
                self._directory = self.workflow.environment('workflow_data')
            elif self.workflow.environment('version_build') >= 652:
                self._directory = os.path.join(
                    os.path.expanduser('~/Library/Application Support/Alfred-3/Workflow Data/'),
                    self.workflow.bundle
                )
            elif self.workflow.environment('version_build') < 652:
                self._directory = os.path.join(
                    os.path.expanduser('~/Library/Application Support/Alfred-2/Workflow Data/'),
                    self.workflow.bundle
                )

        return ensure_path(self._directory)

    @property
    def serializer(self):
        """Gets the serializer being used.

        .. note: by default the class uses :class:`Pickle` or :class:`CPickle`
                 depending on the Python version being used.

        :return: the serializer being used.
        :rtype: ``any``.
        """

        return self._serializer

    @serializer.setter
    def serializer(self, serializer):
        """Sets a new serializer.

        :param serializer: the serializer to be used.
        :rtype: ``any``.
        """

        getattr(serializer, 'name')
        self._serializer = serializer

    def read(self, filename):
        """Reads the given file.

        :param filename: the filename to be read.
        :type filename: ``str``.
        :return: the data contained in the file.
        :rtype: ``any``.
        """

        path = os.path.join(self.directory, '{0}.{1}'.format(filename, self.serializer.name or 'custom'))
        with open(path, 'rb') as handler:
            return self.serializer.load(handler)

    def save(self, filename, data):
        """Saves the provided data.

        :param filename: the filename to be used.
        :type filename: ``str``.
        :param data: the data to be saved.
        :type data: ``any``.
        :return: ``True`` if the operation completes successfully; ``False`` otherwise.
        :rtype: ``boolean``.
        """

        @atomic
        def atomic_save():
            try:
                path = os.path.join(self.directory, '{0}.{1}'.format(filename, self.serializer.name or 'custom'))
                settings = os.path.join(self.workflow.directory, 'settings.json')
                if path == settings:
                    raise SerializationException('Settings file is maintained automatically')

                with atomic_write(path, 'wb') as handle:
                    self.serializer.dump(data, handle)

                return True
            except (OSError, IOError):
                return False

        return atomic_save()

    def clear(self, filename):
        """Clears the content of the file.

        :param filename: the filename to be used.
        :type filename: ``str``.
        :return: ``True`` if the file exists and the data was removed successfully; ``False`` otherwise.
        :rtype: ``boolean``.
        """

        path = os.path.join(self.directory, '{0}.{1}'.format(filename, self.serializer.name or 'custom'))
        if os.path.exists(path):
            os.unlink(path)
            return True

        return False
