"""
.. module:: workflow_settings
   :platform: Unix
   :synopsis: Controls the workflow settings.

.. moduleauthor:: Patricio Trevino <patricio@weirdpattern.com>

"""

import os
import json

from utils import atomic_write, atomic, lock


class WorkflowSettings(dict):
    """A class that provides a way to interact with a workflow settings"""

    def __init__(self, path, defaults=None):
        """Initializes the :class:`WorkflowSettings`.

        :param path: the path where the settings are located.
        :type path: ``str``.
        :param defaults: the default settings to be used in case no other settings are provided.
        :type defaults: :class:`dict`.
        """

        super(WorkflowSettings, self).__init__()

        self._path = path
        self._original = {}
        self._defaults = defaults or {}

        for key, value in defaults.items():
            self._original[key] = value

        if os.path.exists(path):
            with open(path, 'rb') as handle:
                for key, value in json.load(handle, encoding='utf-8').items():
                    self._original[key] = value

        self.update(self._original)
        self.save()

    def save(self):
        """Saves the settings.

        :return: ``True`` if the operation completes successfully; ``False`` otherwise.
        :rtype: ``boolean``.
        """

        @atomic
        def atomic_save():
            try:
                data = {}
                data.update(self)

                with lock(self._path):
                    with atomic_write(self._path, 'wb') as handle:
                        json.dump(data, handle, sort_keys=True, indent=2, encoding='utf-8')

                return True
            except (OSError, IOError):
                return False

        return atomic_save()
