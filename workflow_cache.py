"""
.. module:: workflow_cache
   :platform: Unix
   :synopsis: Controls the workflow cache operations.

.. moduleauthor:: Patricio Trevino <patricio@weirdpattern.com>

"""

import os
import time
from utils import PickleSerializer, ensure_path, atomic_write, atomic


class WorkflowCache(object):
    """A class that provides a way to interact with a workflow cache"""

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
        """Gets the workflow cache directory.

        .. note::
           The directory is calculated based off of the workflow environment variable. If such variable
           is not defined, then it defaults to:

           Alfred 3:
           ~/Library/Caches/com.runningwithcrayons.Alfred-3/Workflow Data/

           Alfred 2:
           ~/Library/Caches/com.runningwithcrayons.Alfred-2/Workflow Data/'

        :return: the workflow cache directory.
        :rtype: ``str``.
        """

        if not self._directory:
            if self.workflow.environment('workflow_cache'):
                self._directory = self.workflow.environment('workflow_cache')
            elif self.workflow.environment('version_build') >= 652:
                self._directory = os.path.join(
                    os.path.expanduser('~/Library/Caches/com.runningwithcrayons.Alfred-3/Workflow Data/'),
                    self.workflow.bundle
                )
            elif self.workflow.environment('version_build') < 652:
                self._directory = os.path.join(
                    os.path.expanduser('~/Library/Caches/com.runningwithcrayons.Alfred-2/Workflow Data/'),
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

    def stale(self, filename, threshold=60):
        """Determines if the given file is stale.

        :param filename: the filename to be inspected.
        :type filename: ``str``.
        :param threshold: the threshold in minutes to be evaluated.
        :type threshold: ``int``.
        :return: ``True`` if the file is older than the provided threshold; ``False`` otherwise.
        :rtype: ``boolean``.
        """

        age = 0
        path = os.path.join(self.directory, '{0}.{1}'.format(filename, self.serializer.name or 'custom'))
        if os.path.exists(path):
            age = time.time() - os.stat(path).st_mtime

        return age > threshold > 0

    def read(self, filename, regenerator, threshold=60):
        """Reads the given file, regenerating its content using ``regenerator`` if the file is already stale.

        :param filename: the filename to be read.
        :type filename: ``str``.
        :param regenerator: the function to be used to regenerate the file.
        :type regenerator: ``callable``.
        :param threshold: the threshold in minutes to be evaluated.
                          If -1, then read the file no matter how old it is.
        :type threshold: ``int``.
        :return: the data contained in the file.
        :rtype: ``any``.
        """

        path = os.path.join(self.directory, '{0}.{1}'.format(filename, self.serializer.name or 'custom'))

        if os.path.exists(path) and (threshold == -1 or not self.stale(filename, threshold)):
            with open(path, 'rb') as handle:
                return self.serializer.load(handle)

        if not regenerator:
            return None

        data = regenerator()
        self.save(filename, data)

        return data

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

