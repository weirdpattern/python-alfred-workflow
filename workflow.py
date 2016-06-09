"""
.. module:: workflow
   :platform: Unix
   :synopsis: Main class of the project.

.. moduleauthor:: Patricio Trevino <patricio@weirdpattern.com>

"""

from __future__ import print_function, unicode_literals

import os
import sys
import plistlib
import threading

from workflow_version import Version
from workflow_data import WorkflowData
from workflow_item import WorkflowItem
from workflow_cache import WorkflowCache
from workflow_actions import WorkflowActions
from workflow_settings import WorkflowSettings

from workflow_updater import check_update, install_update
from utils import decode, register_path, send_notification, item_customizer, request, close_alfred_window


class Workflow(object):
    """A class that provides an abstract representation of the Alfred workflow.

    .. note: to initialize the workflow do::
             if __name__ == '__main__':
                 sys.exit(Workflow.run(main, Workflow()))

    """

    def __init__(self, defaults=None):
        """Initializes the :class:`Workflow`

        :param defaults: the default settings to be used with the workflow.
        :type defaults: :class:`dict`.
        """

        self._environment = None
        self._directory = None

        self._info = None
        self._name = None
        self._bundle = None
        self._version = None

        self._defaults = defaults or {}

        self._items = []
        self._actions = None

        self._data = None
        self._cache = None
        self._updater = None
        self._settings = None

    @property
    def actions(self):
        """Gets the :class:`WorkflowActions` instance being used by the workflow.

        :return: the current instance of the :class:`WorkflowActions`.
        :rtype: :class:`WorkflowActions`.
        """

        if not self._actions:
            self._actions = WorkflowActions(self)

        return self._actions

    @property
    def args(self):
        """Gets the arguments passed to the workflow.

        .. note::
           The arguments are split using whitespace as delimiter for each argument;
           the method also handles the workflow actions when the workflow has been
           marked as ``actionable``.

           Every action can add new items to the workflow, in which case, the execution
           of the action workflow is stopped and the items in the action are displayed.

        .. seealso::
           :class:`WorkflowActions`
           :class:`WorkflowSettings`

        :return: a list of arguments.
        :rtype: :class:`list`.
        """

        feedback = False
        args = [decode(arg) for arg in sys.argv[1:]]
        if len(args) == 1:
            args = args[0].split(' ')

        if len(args) and self.setting('actionable'):
            index = args.index('>') if '>' in args else -1
            if index > -1:
                parameters = args[index + 1:]
                if len(parameters) > 0:
                    command = parameters.pop(0)
                    if command in self.actions:
                        feedback = self.actions.get(command)(*parameters)
                    else:
                        feedback = self.actions.defaults(command)
                else:
                    feedback = self.actions.defaults()

            if feedback:
                self.feedback()
                sys.exit(0)

        return args

    @property
    def directory(self):
        """Gets the workflow working directory.

        .. note: the directory is calculated based off of the location of the ``info.plist`` of the workflow
                 of the location of the ``settings.json`` of the workflow.

        :return: the workflow working directory.
        :rtype: ``str``.
        """

        if not self._directory:
            candidates = [
                os.path.abspath(os.getcwdu()),
                os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
            ]

            for candidate in candidates:
                path = decode(candidate)
                while True:
                    if os.path.exists(os.path.join(path, 'info.plist')):
                        self._directory = path
                        break
                    elif os.path.exists(os.path.join(path, 'settings.json')):
                        self._directory = path
                        break
                    elif path == '/':
                        break

                    path = os.path.dirname(path)

                if self._directory:
                    break

            if not self._directory:
                raise IOError('No info.plist for the workflow')

        return self._directory

    @property
    def data(self):
        """Gets the :class:`WorkflowData` instance being used by the workflow.

        :return: the current instance of the :class:`WorkflowData`.
        :rtype: :class:`WorkflowData`.
        """

        if not self._data:
            self._data = WorkflowData(self)

        return self._data

    @property
    def cache(self):
        """Gets the :class:`WorkflowCache` instance being used by the workflow.

        :return: the current instance of the :class:`WorkflowCache`.
        :rtype: :class:`WorkflowCache`.
        """

        if not self._cache:
            self._cache = WorkflowCache(self)

        return self._cache

    @property
    def info(self):
        """Reads the ``info.plist`` file and extracts the information from it, making it available to anyone.

        :return: a dictionary with all the workflow information.
        :rtype: :class:`dict`.
        """

        if not self._info:
            if os.path.exists(os.path.join(self.directory, 'info.plist')):
                self._info = plistlib.readPlist(os.path.join(self.directory, 'info.plist'))
            else:
                self._info = {}

        return self._info

    @property
    def name(self):
        """Gets the name of the workflow.

        .. note::
           The name is obtained from one of these sources (in this order):
           1. The environment variables
           2. The workflow information (info.plist)
           3. The workflow settings file (settings.json)

           If not defined in any of these, it defaults to ``workflow``.

        :return: the name of the workflow.
        :rtype: ``str``.
        """

        if not self._name:
            if self.environment('workflow_name'):
                self._name = decode(self.environment('workflow_name'))
            elif self.info.get('name'):
                self._name = decode(self.info.get('name'))
            elif self.setting('name'):
                self._name = decode(self.setting('name'))
            else:
                self._name = 'workflow'

        return self._name

    @property
    def bundle(self):
        """Gets the bundle id of the workflow.

        .. note::
           The bundle id is obtained from one of these sources (in this order):
           1. The environment variables
           2. The workflow information (info.plist)
           3. The workflow settings file (settings.json)

           If not defined in any of these, it defaults to ````.

        :return: the bundle id of the workflow.
        :rtype: ``str``.
        """
        if not self._bundle:
            if self.environment('workflow_bundleid'):
                self._bundle = decode(self.environment('workflow_bundleid'))
            elif self.info.get('bundleid'):
                self._bundle = decode(self.info.get('bundleid'))
            elif self.setting('bundleid'):
                self._bundle = decode(self.setting('bundleid'))
            else:
                self._bundle = ''

        return self._bundle

    @property
    def version(self):
        """Gets the version of the workflow.

        .. note::
           The version is obtained from one of these sources (in this order):
           1. The workflow settings file (settings.json)
           2. The VERSION file (version - no extension)

           And it is used to update the workflow.

        .. seealso: :class:`Version`.

        :return: the version of the workflow.
        :rtype: :class: `Version`.
        """
        if not self._version:
            version = None

            if self.setting('version'):
                version = self.setting('version')

            if not version:
                path = os.path.join(self.directory, 'version')
                if os.path.exists(path):
                    with open(path, 'rb') as handle:
                        version = handle.read()

            if version:
                self._version = Version(version)

        return self._version

    @property
    def settings(self):
        """Gets the :class:`WorkflowSettings` instance being used by the workflow.

        :return: the current instance of the :class:`WorkflowSettings`.
        :rtype: :class:`WorkflowSettings`.
        """

        if not self._settings:
            path = os.path.join(self.directory, 'settings.json')

            if 'path' in self._defaults:
                path = self._defaults['path']

            self._settings = WorkflowSettings(path, self._defaults)

        return self._settings

    def setting(self, *args):
        """Gets a setting from the workflow settings.

        .. note::
           If more than one argument is provided, then the arguments are chained together
           to extract the child setting.

           i.e.
           calling ``self.setting('update', 'enabled')``, will be interpreted as
           1. Get ``update`` from the workflow settings.
           2. Get ``enabled`` from the ``update`` setting obtained previously.

           If a setting in the path does not exists, then ``None`` is returned.

        :param args: the setting or setting chain to be returned.
        :type args: ``n-tuple``.
        :return: the value of the setting or setting chain.
        :rtype: ``any``.
        """

        setting = self.settings

        params = list(args)
        while setting and len(params) > 0:
            param = params.pop(0)
            setting = setting[param] if param in setting else None

        return setting

    def environment(self, variable):
        """Gets information about the environment (Alfred environment variables)

        .. note::
           The table below describes the environment variables that are collected by the workflow.

           +--------------------------+-------------------+
           | Alfred Env Variable      | Workflow Variable |
           +==========================+===================+
           | alfred_version           | version           |
           +--------------------------+-------------------+
           | alfred_version_build     | version_build     |
           +--------------------------+-------------------+
           | alfred_workflow_bundleid | workflow_bundleid |
           +--------------------------+-------------------+
           | alfred_workflow_uid      | workflow_uid      |
           +--------------------------+-------------------+
           | alfred_workflow_name     | workflow_name     |
           +--------------------------+-------------------+
           | alfred_workflow_cache    | workflow_cache    |
           +--------------------------+-------------------+
           | alfred_workflow_data     | workflow_data     |
           +--------------------------+-------------------+

        .. seealso::
           `Alfred Environment Variables <https://www.alfredapp.com/help/workflows/script-environment-variables/>`_

        :param variable: the variable we are looking for.
        :type variable: ``str``.
        :return: the value of the variable.
        :rtype: ``int`` for ``version_build``; ``str`` for the rest of the variables.
        """

        if not self._environment:
            if not sys.stdout.isatty():
                self._environment = {
                    'version': decode(os.getenv('alfred_version')),
                    'version_build': int(os.getenv('alfred_version_build')),
                    'workflow_bundleid': decode(os.getenv('alfred_workflow_bundleid')),
                    'workflow_uid': decode(os.getenv('alfred_workflow_uid')),
                    'workflow_name': decode(os.getenv('alfred_workflow_name')),
                    'workflow_cache': decode(os.getenv('alfred_workflow_cache')),
                    'workflow_data': decode(os.getenv('alfred_workflow_data'))
                }
            else:
                self._environment = {}

        return self._environment[variable] if variable in self._environment else None

    def resource(self, resource):
        """Gets a workflow resource path.

        .. note: basically appends the workflow directory to whatever you send.

        .. seealso: :func:`directory`

        :param resource: the sub-path to your resource (or just the name if the resource is
                         located in the workflow root folder.
        :type resource: ``str``.
        :return: the absolute path to the workflow resource.
        :rtype: ``str``.
        """

        return os.path.join(self.directory, resource)

    def updatable(self, include_enabled_flag=True):
        """Determines if the workflow can be updated

        :param include_enabled_flag: a flag indicating if the ``update.enabled`` setting should be considered too.
        :type include_enabled_flag: ``boolean``.
        :return: ``True`` if the workflow can be updated; ``False`` otherwise.
        :rtype: ``boolean``.
        """

        enabled = self.setting('update', 'enabled')
        github_setting = self.setting('update', 'repository', 'github')

        if include_enabled_flag:
            return enabled and github_setting and 'username' in github_setting and 'repository' in github_setting

        return github_setting and 'username' in github_setting and 'repository' in github_setting

    def update_available(self):
        """Determines if an update is ready to install.

        .. note: this method reads the ``.workflow_updater`` cache file and determines if a new
                 version is available. Still needs a ``check_update`` call either from the user (through
                 the ``> workflow check`` action) or the workflow (through an automatic check).

        :return: the information of the new version if available or ``None`` if no new version is available.
        :rtype: :class:`dict`.
        """

        if self.updatable():
            frequency = int(self.setting('update', 'frequency') or 1) * 86400
            cached = self.cache.read('.workflow_updater', None, frequency)
            if cached and 'version' in cached:
                newest = Version(cached['version'])
                if newest > self.version:
                    return cached

        return None

    def check_update(self, forced=False, auto_install=False):
        """Calls the workflow repository to check for new versions.

        .. note: this method uses the ``update.repository.github`` configuration to call home.

        .. seealso: :func:`workflow_updater.check_update`.

        :param forced: a flag indicating whether we are forcing the check (through the ``> workflow check`` action).
        :type forced: ``boolean``.
        :param auto_install: a flag indicating whether we want to install without confirmation if a new version
                             is available (through the ``> workflow force-update`` action).
        :type auto_install: ``boolean``.
        :return: ``True`` if a check operation was triggered successfully; ``False`` otherwise.
        :rtype: ``boolean``
        """

        cached = self.update_available()
        if self.updatable() and (forced or not cached):
            mode = 'never'

            if forced:
                mode = 'always'
            elif cached:
                mode = 'only_when_available'

            Workflow.background(check_update, 'check_update', self, mode, auto_install)
            return True

        return False

    def install_update(self):
        """Installs an available update.

        .. note: this method is the second part of the :func:`check_update` method.

        .. seealso: :func:`workflow_updater.install_update`

        :return: ``True`` if the installation was triggered successfully; ``False`` otherwise.
        :rtype: ``boolean``.
        """

        cached = self.update_available()
        if self.updatable() and cached:
            Workflow.background(install_update, 'install_update', self, cached['url'])
            return True

        return False

    def check_and_install_update(self):
        """Checks for updates and install them if available.

        .. note: basically :func:`check_update` followed by :func:`install_update`.
        """

        if not self.install_update():
            self.check_update(True, True)

    def item(self, title, subtitle, customizer=None):
        """Creates and adds a new item to the workflow.

        :param title: the title of the item.
        :type title: ``str``.
        :param subtitle: the subtitle of the item.
        :type subtitle: ``str``.
        :param customizer: a function to customize the item (adding icon, mods, etc).
        :type customizer: ``callable``.
        :return: the item just added.
        :rtype: :class:`WorkflowItem`.
        """

        item = WorkflowItem(title, subtitle)

        if customizer:
            customizer(item)

        self._items.append(item)
        return item

    def feedback(self):
        """Outputs the workflow feedback (items)"""

        sys.stdout.write('<?xml version="1.0" encoding="utf-8"?>\n')
        sys.stdout.write('<items>\n')

        for item in self._items:
            item.feedback()

        sys.stdout.write('</items>')
        sys.stdout.flush()

    @staticmethod
    def library(path):
        """Adds a new library to the workflow.

        .. seealso: :func:`utils.register_path`.

        :param path: the path to the library.
        :type path: ``str``.
        """

        register_path(path)

    @staticmethod
    def background(func, title, *args):
        """Spawns a new thread to execute func.

        :param func: the function to be executed.
        :type func: ``callable``.
        :param title: the title of the thread.
        :type title: ``str``.
        :param args: the arguments of the function.
        :type args: ``n-tuple``.
        """

        threading.Thread(None, func, title, args).start()

    @staticmethod
    def notification(title, message):
        """Sends a new OS X notification

        .. seealso: :func:`utils.send_notification`.

        :param title: the title of the notification.
        :type title: ``str``.
        :param message:  the message to be displayed in the notification.
        :type message: ``str``.
        """
        send_notification(title, message)

    @staticmethod
    def getRaw(url, params=None, headers=None, cookies=None, auth=None, redirection=True, timeout=60):
        """A shortcut to :func:`utils.request` that performs a ``GET`` operation and returns raw content.

        :param url: the url of the request.
        :type url: ``str``.
        :param params: mapping of url parameters.
        :type params: :class:`dict`.
        :param headers: the headers of the request.
        :type headers: :class:`dict`.
        :param cookies: the cookies of the request.
        :type cookies: :class:`dict`.
        :param auth: the authentication information to be used.
        :type auth: :class:`dict`.
        :param redirection: a flag indicating whether redirection is allowed or not.
        :type redirection: ``boolean``.
        :param timeout: a timeout for the request.
        :type timeout: ``int``.
        :return: the content obtained from executing the request.
        :rtype: ``json``.
        """

        return request('GET', url, 'raw', None, params, headers, cookies, auth, redirection, timeout)

    @staticmethod
    def getJSON(url, params=None, headers=None, cookies=None, auth=None, redirection=True, timeout=60):
        """A shortcut to :func:`utils.request` that performs a ``GET`` operation and returns json content.

        :param url: the url of the request.
        :type url: ``str``.
        :param params: mapping of url parameters.
        :type params: :class:`dict`.
        :param headers: the headers of the request.
        :type headers: :class:`dict`.
        :param cookies: the cookies of the request.
        :type cookies: :class:`dict`.
        :param auth: the authentication information to be used.
        :type auth: :class:`dict`.
        :param redirection: a flag indicating whether redirection is allowed or not.
        :type redirection: ``boolean``.
        :param timeout: a timeout for the request.
        :type timeout: ``int``.
        :return: the content obtained from executing the request.
        :rtype: ``json``.
        """

        return request('GET', url, 'json', None, params, headers, cookies, auth, redirection, timeout)

    @staticmethod
    def close():
        """Closes the current Alfred window.

        .. seealso: :func:`utils.close_alfred_window`.
        """

        close_alfred_window()
        return False

    @staticmethod
    def run(main, workflow):
        """Entry point for all workflows.

        :param main: the main function (of the alfred workflow) to run.
        :type main: ``callable``.
        :param workflow: the instance of the workflow to be send to main.
        :type workflow: :class:`Workflow`.
        :return: the exit status of the workflow.
        """
        try:
            workflow.check_update(False)
            main(workflow)
            return 0
        except Exception as ex:
            workflow.item('Oops, something went wrong',
                          'Workflow {0} failed with exception - {1}'.format(workflow.name, ex.message),
                          item_customizer('sad.png'))

            workflow.feedback()
            return 1
