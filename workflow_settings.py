import os
import json

from utils import atomic_write, atomic, lock


class WorkflowSettings(dict):
    def __init__(self, path, defaults=None):
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
