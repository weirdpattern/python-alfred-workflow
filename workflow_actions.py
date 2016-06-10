"""
.. module:: workflow_actions
   :platform: Unix
   :synopsis: Controls the workflow actions.

.. moduleauthor:: Patricio Trevino <patricio@weirdpattern.com>

"""

import os
import shutil
import subprocess

from utils import bind, item_customizer


class WorkflowActions(dict):
    """A class that controls the workflow actions"""

    def __init__(self, workflow):
        """Initializes the :class:`WorkflowActions`.

        :param workflow: the :class:`workflow.Workflow` instance we want to control.
        :type workflow: :class:`workflow.Workflow`
        """

        super(WorkflowActions, self).__init__()

        self.workflow = workflow
        self['help'] = bind(self.help)
        self['workflow'] = bind(self.info)
        self['settings'] = bind(self.settings)

    def defaults(self, arg=None):
        """Adds the default actions to the workflow.

        :param arg: the argument the user is currently typing in the Alfred window.
        :type arg: ``str``.
        :return:  ``True`` to stop the normal execution of the workflow.
        :rtype: ``boolean``.
        """

        arg = arg or ''
        arg = arg.lower()

        count = 0
        if 'help'.startswith(arg):
            count += 1
            self.workflow.item('Help',
                               'Need a hand? This is the right place to get it',
                               item_customizer('help.png', autocomplete='> help'))

        if 'workflow'.startswith(arg):
            count += 1
            self.workflow.item('Workflow',
                               'Get to know your workflow',
                               item_customizer('info.png', autocomplete='> workflow'))

        if 'settings'.startswith(arg):
            count += 1
            self.workflow.item('Settings',
                               'Want to make it yours? Let\'s customize the workflow',
                               item_customizer('settings.png', autocomplete='> settings '))

        if count == 0:
            self.workflow.item('No match for {0}'.format(arg), 'Click to clear your filter',
                               item_customizer('sad.png', autocomplete='>'))

        return True

    def help(self):
        """Handles the ``> help`` action.

        .. note: this method reads the ``help`` url in the settings file; if no url exists, then if defaults to the
                 `README file <https://raw.githubusercontent.com/weirdpattern/alfred-python-workflow/master/README.md>`_
                 of the workflow framework (yeap, this framework).
        """

        url = self.workflow.setting('help')
        if not url:
            url = 'https://raw.githubusercontent.com/weirdpattern/alfred-python-workflow/master/README.md'

        subprocess.call(['open', url])
        self.workflow.close()

    def info(self, *args):
        """Handles the ``> workflow`` action.

        .. note::
           This method displays the following menu:
           - Running version x.x.x (to display the workflow version information).

           If update is available:
           - Proceed with update (proceed with workflow installation)

           Else:
           - Check for update (check if new versions are available)
           - Check for update and install (check and install any new version)

        :param args: the chain of commands that activated the action.
        :type args: ``n-tuple``.
        :return: ``True`` to stop the normal execution of the workflow.
        :rtype: ``boolean``.
        """

        arg = ''
        if len(args) > 0:
            arg = args[0].lower()
            if arg == 'check':
                self.workflow.check_update(True)
                return self.workflow.close()
            elif arg == 'update':
                self.workflow.install_update()
                return self.workflow.close()
            elif arg == 'force-update':
                self.workflow.check_and_install_update()
                return self.workflow.close()

        count = 0
        if 'version'.startswith(arg):
            count += 1
            if self.workflow.version:
                self.workflow.item('Running version {0}'.format(str(self.workflow.version)),
                                   'Workflow {0}'.format(self.workflow.name),
                                   item_customizer('info.png'))
            else:
                self.workflow.item('Version information not available',
                                   'Workflow {0}'.format(self.workflow.name),
                                   item_customizer('sad.png'))

        if self.workflow.updatable():
            if self.workflow.update_available():
                if 'update'.startswith(arg):
                    count += 1
                    self.workflow.item('Proceed with update', 'Ok, I\'m ready to install the newest version',
                                       item_customizer('download.png', autocomplete='> workflow update'))
            else:
                if 'check'.startswith(arg):
                    count += 1
                    self.workflow.item('Check for update', 'Check if there is anything new out there',
                                       item_customizer('check.png', autocomplete='> workflow check'))

                if 'force'.startswith(arg):
                    count += 1
                    self.workflow.item('Check for update and install',
                                       'Check if there is anything new out there and install without asking me',
                                       item_customizer('download.png', autocomplete='> workflow force-update'))

        return True

    def settings(self, *args):
        """Handles the ``> settings`` action.

        .. note::
           This method displays the following menu:
           - Workflow Data (opens the data operations menu)
           - Workflow Cache (opens the cache operations menu)

           If updates are enabled:
           - Workflow Update (opens the update operations menu)

        :param args: the chain of commands that activated the action.
        :type args: ``n-tuple``.
        :return: ``True`` to stop the normal execution of the workflow.
        :rtype: ``boolean``.
        """

        arg = ''
        if len(args) > 0:
            arg = args[0].lower()
            if arg == 'data':
                return self.settings_data_display(*args[1:])
            elif arg == 'cache':
                return self.settings_cache_display(*args[1:])
            elif arg == 'update':
                return self.settings_update_display(*args[1:])

        count = 0
        if 'data'.startswith(arg):
            count += 1
            self.workflow.item('Workflow Data', 'Use this to manage your workflow data',
                               item_customizer('data.png', autocomplete='> settings data '))

        if 'cache'.startswith(arg):
            count += 1
            self.workflow.item('Workflow Cache', 'Use this to manage your workflow cache',
                               item_customizer('cache.png', autocomplete='> settings cache '))

        if self.workflow.updatable(False):
            if 'update'.startswith(arg):
                count += 1
                self.workflow.item('Workflow Update', 'Use this to manage your workflow auto-update preferences',
                                   item_customizer('update.png', autocomplete='> settings update '))

        if count == 0:
            self.workflow.item('No match for {0}'.format(arg), 'Click to clear your filter',
                               item_customizer('sad.png', autocomplete='> settings '))

        return True

    def settings_data_display(self, *args):
        """Handles the ``> settings data`` action.

        .. note::
           This method displays the following menu:
           - Open Data Directory (opens the workflow data directory)
           - Clear Data Directory (clears the workflow data directory)

        :param args: the chain of commands that activated the action.
        :type args: ``n-tuple``.
        :return: ``True`` to stop the normal execution of the workflow.
        :rtype: ``boolean``.
        """

        arg = ''
        if len(args) > 0:
            arg = args[0].lower()
            if arg == 'open-data':
                return self.open_directory('data')
            elif arg == 'clear-data':
                return self.clear_directory('data')

        count = 0

        if 'open'.startswith(arg):
            count += 1
            self.workflow.item('Open Data Directory', 'Inspect the content of the data directory',
                               item_customizer('folder.png', autocomplete='> settings data open-data'))

        if 'clear'.startswith(arg):
            count += 1
            self.workflow.item('Clear Data Directory', 'Clears the content of the data directory',
                               item_customizer('clear.png', autocomplete='> settings data clear-data'))

        if count == 0:
            self.workflow.item('No match for {0}'.format(arg), 'Click to clear your filter',
                               item_customizer('sad.png', autocomplete='> settings data '))

        return True

    def settings_cache_display(self, *args):
        """Handles the ``> settings cache`` action.

        .. note::
           This method displays the following menu:
           - Open Cache Directory (opens the workflow cache directory)
           - Clear Cache Directory (clears the workflow cache directory)

        :param args: the chain of commands that activated the action.
        :type args: ``n-tuple``.
        :return: ``True`` to stop the normal execution of the workflow.
        :rtype: ``boolean``.
        """

        arg = ''
        if len(args) > 0:
            arg = args[0].lower()
            if arg == 'open-cache':
                return self.open_directory('cache')
            elif arg == 'clear-cache':
                return self.clear_directory('cache')

        count = 0
        if 'open'.startswith(arg):
            count += 1
            self.workflow.item('Open Cache Directory', 'Inspect the content of the cache directory',
                               item_customizer('folder.png', autocomplete='> settings cache open-cache'))

        if 'clear'.startswith(arg):
            count += 1
            self.workflow.item('Clear Cache Directory', 'Clears the content of the cache directory',
                               item_customizer('clear.png', autocomplete='> settings cache clear-cache'))

        if count == 0:
            self.workflow.item('No match for {0}'.format(arg), 'Click to clear your filter',
                               item_customizer('sad.png', autocomplete='> settings cache '))

        return True

    def settings_update_display(self, *args):
        """Handles the ``> settings update`` action.

        .. note::
           This method displays the following menu:
           - Auto update is [enabled/disabled].

           If the auto update feature is enabled
           - Workflow will check for updates every x days (check for updates with frequency x).

           Depending on the include-prerelease setting value
           - Update using only released code (include only releases).
           or
           - Update using pre-released code (include pre-releases).

        :param args: the chain of commands that activated the action.
        :type args: ``n-tuple``.
        :return: ``True`` to stop the normal execution of the workflow.
        :rtype: ``boolean``.
        """
        arg = ''
        if len(args) > 0:
            arg = args[0].lower()
            if arg == 'auto':
                return self.settings_update_auto_display(*args[1:])
            elif arg == 'frequency':
                return self.settings_update_frequency_display(*args[1:])
            elif arg == 'include':
                return self.settings_update_include_display(*args[1:])

        count = 0
        if 'enable'.startswith(arg):
            count += 1
            self.workflow.item('Auto update is {0}'.format(
                               'enable' if self.workflow.setting('update', 'enabled') else 'disable'),
                               'Select to change this value',
                               item_customizer('update.png', autocomplete='> settings update auto '))

        if self.workflow.setting('update', 'enabled'):
            if 'frequency'.startswith(arg):
                count += 1
                frequency = self.workflow.setting('update', 'frequency') or 1
                self.workflow.item('Workflow will check for updates every {0}'.format(
                                   'day' if frequency == 1 else '{0} days'.format(frequency)),
                                   'Select to change this value',
                                   item_customizer('time.png', autocomplete='> settings update frequency '))

            if 'include'.startswith(arg):
                count += 1
                self.workflow.item('Update using only released code'
                                   if not self.workflow.setting('update', 'include-prereleases')
                                   else 'Update using pre-released code',
                                   'Select to change this value',
                                   item_customizer('release.png', autocomplete='> settings update include '))

        if count == 0:
            self.workflow.item('No match for {0}'.format(arg), 'Click to clear your filter',
                               item_customizer('sad.png', autocomplete='> settings update '))

        return True

    def settings_update_auto_display(self, *args):
        """Handles the ``> settings update auto`` action.

        .. note::
           This method displays the following menu:
           If the auto updates setting is enabled:
           - Turn auto updates off (deactivates auto updates).

           Else:
           - Turn auto updates on (activates auto updates).

        :param args: the chain of commands that activated the action.
        :type args: ``n-tuple``.
        :return: ``True`` to stop the normal execution of the workflow.
        :rtype: ``boolean``.
        """

        arg = ''
        if len(args) > 0:
            arg = args[0].lower()
            if arg == 'on':
                return self.update_setting('update', 'enabled', True, 'Auto updates turned on')
            elif arg == 'off':
                return self.update_setting('update', 'enabled', False, 'Auto updates turned off')

        count = 0
        if self.workflow.setting('update', 'enabled'):
            if 'off'.startswith(arg):
                count += 1
                self.workflow.item('Turn auto updates off', 'I no longer want to receive updates',
                                   item_customizer('disable.png', autocomplete='> settings update auto off'))
        else:
            if 'on'.startswith(arg):
                count += 1
                self.workflow.item('Turn auto updates on', 'I want to keep my workflow up to date',
                                   item_customizer('ok.png', autocomplete='> settings update auto on'))

        if count == 0:
            self.workflow.item('No match for {0}'.format(arg), 'Click to clear your filter',
                               item_customizer('sad.png', autocomplete='> settings update auto '))

        return True

    def settings_update_frequency_display(self, *args):
        """Handles the ``> settings update frequency`` action.

        .. note::
           This method displays the following menu:
           - Check for updates daily (changes the setting to 1).
           - Check for updates weekly (changes the setting to 7).
           - Check for updates monthly (changes the setting to 30).
           - Check for updates yearly (changes the setting to 365).

        :param args: the chain of commands that activated the action.
        :type args: ``n-tuple``.
        :return: ``True`` to stop the normal execution of the workflow.
        :rtype: ``boolean``.
        """

        arg = ''
        if len(args) > 0:
            arg = args[0].lower()
            if arg == 'daily':
                return self.update_setting('update', 'frequency', 1, 'Update frequency changed to daily')
            elif arg == 'weekly':
                return self.update_setting('update', 'frequency', 7, 'Update frequency changed to weekly')
            elif arg == 'monthly':
                return self.update_setting('update', 'frequency', 30, 'Update frequency changed to monthly')
            elif arg == 'yearly':
                return self.update_setting('update', 'frequency', 365, 'Update frequency changed to yearly')

        count = 0
        frequency = self.workflow.setting('update', 'frequency') or 1
        if frequency != 1:
            if 'daily'.startswith(arg):
                count += 1
                self.workflow.item('Check for updates daily', 'I want to always be running the latest version',
                                   item_customizer('calendar.png', autocomplete='> settings update frequency daily'))

        if frequency != 7:
            if 'weekly'.startswith(arg):
                count += 1
                self.workflow.item('Check for updates weekly',
                                   'I want updates fast, but is ok if we wait a couple of days',
                                   item_customizer('calendar.png', autocomplete='> settings update frequency weekly'))

        if frequency != 30:
            if 'monthly'.startswith(arg):
                count += 1
                self.workflow.item('Check for updates monthly',
                                   'I want to update my workflow once in a while',
                                   item_customizer('calendar.png', autocomplete='> settings update frequency monthly'))

        if frequency != 365:
            if 'yearly'.startswith(arg):
                count += 1
                self.workflow.item('Check for updates yearly',
                                   'I don\'t really like to be bother with this stuff',
                                   item_customizer('calendar.png', autocomplete='> settings update frequency yearly'))

        if count == 0:
            self.workflow.item('No match for {0}'.format(arg), 'Click to clear your filter',
                               item_customizer('sad.png', autocomplete='> settings update frequency '))

        return True

    def settings_update_include_display(self, *args):
        """Handles the ``> settings update include`` action.

        .. note::
           This method displays the following menu:
           if the include-prerelease setting value is True:
           - Do not include pre-releases

           Else:
           - Include pre-releases

        :param args: the chain of commands that activated the action.
        :type args: ``n-tuple``.
        :return: ``True`` to stop the normal execution of the workflow.
        :rtype: ``boolean``.
        """

        arg = ''
        if len(args) > 0:
            arg = args[0].lower()
            if arg == 'on':
                return self.update_setting('update', 'include-prereleases', True,
                                           'Pre-releases will be included next time')
            elif arg == 'off':
                return self.update_setting('update', 'include-prereleases', False,
                                           'Pre-releases won\'t be included next time')

        count = 0
        if self.workflow.setting('update', 'include-prereleases'):
            if 'off'.startswith(arg):
                count += 1
                self.workflow.item('Do not include pre-releases', 'I want stable releases only',
                                   item_customizer('disable.png', autocomplete='> settings update include off'))
        else:
            if 'on'.startswith(arg):
                count += 1
                self.workflow.item('Include pre-releases', 'I want to experiment with pre-releases too',
                                   item_customizer('ok.png', autocomplete='> settings update include on'))

        if count == 0:
            self.workflow.item('No match for {0}'.format(arg), 'Click to clear your filter',
                               item_customizer('sad.png', autocomplete='> settings update include '))

        return True

    def open_directory(self, which):
        """Opens a directory.

        :param which: the directory to open (``data``, ``cache`` or ``workflow``)
        :type which: ``str``.
        :return: ``False`` as the application will close.
        :rtype: ``boolean``.
        """

        if which.lower() == 'data':
            path = self.workflow.data.directory
        elif which.lower() == 'cache':
            path = self.workflow.cache.directory
        else:
            path = self.workflow.directory

        subprocess.call(['open', path])
        return self.workflow.close()

    def clear_directory(self, which):
        """Clears a directory.

        :param which: the directory to open (``data`` or ``cache``)
        :type which: ``str``.
        :return: ``False`` as the application will close.
        :rtype: ``boolean``.
        """
        message = 'No data to be cleared'
        path = self.workflow.data.directory if which.lower() == 'data' else self.workflow.cache.directory
        if os.path.exists(os.path.expanduser(path)):
            for filename in os.listdir(path):
                current = os.path.join(path, filename)
                if os.path.isdir(current):
                    shutil.rmtree(current)
                else:
                    os.unlink(current)

            message = '{0} directory cleared!'.format(which.capitalize())

        self.workflow.notification(self.workflow.name, message)
        return self.workflow.close()

    def update_setting(self, setting, option, value, message):
        """Updates a setting.

        :param setting: the main setting to update.
        :type setting: ``str``.
        :param option: the option within the setting to update.
        :type option: ``str``.
        :param value: the new value of the setting.
        :type value: ``any``.
        :param message: the notification message to be used.
        :type message: ``str``.
        :return: ``False`` as the application will close.
        :rtype: ``boolean``.
        """
        if option:
            self.workflow.setting(setting)[option] = value
        else:
            self.workflow.settings[setting] = value

        self.workflow.settings.save()

        self.workflow.notification(self.workflow.name, message)
        return self.workflow.close()
