import os
import shutil
import subprocess

from utils import bind, item_customizer


class WorkflowActions(dict):
    def __init__(self, workflow):
        super(WorkflowActions, self).__init__()

        self.workflow = workflow
        self['help'] = bind(self.help)
        self['workflow'] = bind(self.info)
        self['settings'] = bind(self.settings)

    def defaults(self, arg=None):
        arg = arg or ''

        count = 0
        if 'help'.startswith(arg.lower()):
            count += 1
            self.workflow.item('Help',
                               'Need a hand? This is the right place to get it',
                               item_customizer('help.png', autocomplete='> help'))

        if 'workflow'.startswith(arg.lower()):
            count += 1
            self.workflow.item('Workflow',
                               'Get to know your workflow',
                               item_customizer('info.png', autocomplete='> workflow'))

        if 'settings'.startswith(arg.lower()):
            count += 1
            self.workflow.item('Settings',
                               'Want to make it yours? Let\'s customize the workflow',
                               item_customizer('settings.png', autocomplete='> settings '))

        if count == 0:
            self.workflow.item('No match for {0}'.format(arg), 'Click to clear your filter',
                               item_customizer('sad.png', autocomplete='>'))

        return True

    def help(self):
        pass

    def info(self, *args):
        arg = ''
        if len(args) > 0:
            arg = args[0]
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
        arg = ''
        if len(args) > 0:
            arg = args[0]
            if arg == 'data':
                return self.settings_data_display(*args[1:])
            elif arg == 'cache':
                return self.settings_cache_display(*args[1:])
            elif arg == 'update':
                return self.settings_update_display(*args[1:])

        count = 0
        if 'data'.startswith(arg.lower()):
            count += 1
            self.workflow.item('Workflow Data', 'Use this to manage your workflow data',
                               item_customizer('data.png', autocomplete='> settings data '))

        if 'cache'.startswith(arg.lower()):
            count += 1
            self.workflow.item('Workflow Cache', 'Use this to manage your workflow cache',
                               item_customizer('cache.png', autocomplete='> settings cache '))

        if self.workflow.updatable(False):
            if 'update'.startswith(arg.lower()):
                count += 1
                self.workflow.item('Workflow Update', 'Use this to manage your workflow auto-update preferences',
                                   item_customizer('update.png', autocomplete='> settings update '))

        if count == 0:
            self.workflow.item('No match for {0}'.format(arg), 'Click to clear your filter',
                               item_customizer('sad.png', autocomplete='> settings '))

        return True

    def settings_data_display(self, *args):
        arg = ''
        if len(args) > 0:
            arg = args[0]
            if arg == 'open-data':
                return self.open_directory('data')
            elif arg == 'clear-data':
                return self.clear_directory('data')

        count = 0

        if 'open'.startswith(arg.lower()):
            count += 1
            self.workflow.item('Open Data Directory', 'Inspect the content of the data directory',
                               item_customizer('folder.png', autocomplete='> settings data open-data'))

        if 'clear'.startswith(arg.lower()):
            count += 1
            self.workflow.item('Clear Data Directory', 'Clears the content of the data directory',
                               item_customizer('clear.png', autocomplete='> settings data clear-data'))

        if count == 0:
            self.workflow.item('No match for {0}'.format(arg), 'Click to clear your filter',
                               item_customizer('sad.png', autocomplete='> settings data '))

        return True

    def settings_cache_display(self, *args):
        arg = ''
        if len(args) > 0:
            arg = args[0]
            if arg == 'open-cache':
                return self.open_directory('cache')
            elif arg == 'clear-cache':
                return self.clear_directory('cache')

        count = 0
        if 'open'.startswith(arg.lower()):
            count += 1
            self.workflow.item('Open Cache Directory', 'Inspect the content of the cache directory',
                               item_customizer('folder.png', autocomplete='> settings cache open-cache'))

        if 'clear'.startswith(arg.lower()):
            count += 1
            self.workflow.item('Clear Cache Directory', 'Clears the content of the cache directory',
                               item_customizer('clear.png', autocomplete='> settings cache clear-cache'))

        if count == 0:
            self.workflow.item('No match for {0}'.format(arg), 'Click to clear your filter',
                               item_customizer('sad.png', autocomplete='> settings cache '))

        return True

    def settings_update_display(self, *args):
        arg = ''
        if len(args) > 0:
            arg = args[0]
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
        arg = ''
        if len(args) > 0:
            arg = args[0]
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
        arg = ''
        if len(args) > 0:
            arg = args[0]
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
        arg = ''
        if len(args) > 0:
            arg = args[0]
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
        if which.lower() == 'data':
            path = self.workflow.data.directory
        elif which.lower() == 'cache':
            path = self.workflow.cache.directory
        else:
            path = self.workflow.directory

        subprocess.call(['open', path])
        return self.workflow.close()

    def clear_directory(self, which):
        message = 'No data to be cleared'
        path = self.workflow.data.directory if which == 'data' else self.workflow.cache.directory
        if os.path.exists(path):
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
        if option:
            self.workflow.setting(setting)[option] = value
        else:
            self.workflow.settings[setting] = value

        self.workflow.settings.save()

        self.workflow.notification(self.workflow.name, message)
        return self.workflow.close()
