import os
import shutil
import subprocess

from utils import command, item_customizer


class WorkflowActions(dict):
    def __init__(self, workflow):
        super(WorkflowActions, self).__init__()

        self.workflow = workflow
        self.actions = {
            'help': command(None, self.help),
            'version': command(None, self.version),
            'settings': command(None, self.settings)
        }

        for key, descriptor in self.actions.items():
            self[key] = descriptor.get('executor')

    def defaults(self, arg=None):
        arg = arg or ''

        count = 0
        if 'help'.startswith(arg.lower()):
            count += 1
            self.workflow.item('Help',
                               'Need a hand? This is the right place to get it',
                               item_customizer('help.png', autocomplete='> help'))

        if 'version'.startswith(arg.lower()):
            count += 1
            self.workflow.item('Version',
                               'What version of the workflow are you running',
                               item_customizer('info.png', autocomplete='> version'))

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

    def version(self):
        if self.workflow.version:
            self.workflow.item('{0}'.format(str(self.workflow.version)),
                               'Workflow {0}'.format(self.workflow.name),
                               item_customizer('info.png'))
        else:
            self.workflow.item('Not available',
                               'Workflow {0}'.format(self.workflow.name),
                               item_customizer('sad.png'))

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
                pass
            elif arg == 'frequency':
                pass
            elif arg == 'include':
                pass

        count = 0
        if 'enable'.startswith(arg):
            count += 1
            self.workflow.item('Auto update is {0}'.format(
                               'enable' if self.workflow.setting('update', 'enabled') else 'disable'),
                               'Select to change this value',
                               item_customizer('update.png', autocomplete='> settings update auto '))

        if 'frequency'.startswith(arg):
            count += 1
            self.workflow.item('Workflow will check for updates every {0} days'.format(
                               self.workflow.setting('update', 'frequency')),
                               'Select to change this value',
                               item_customizer('time.png', autocomplete='> settings update frequency '))

        if 'include'.startswith(arg):
            count += 1
            self.workflow.item('Only releases will be considered when updating the workflow'
                               if not self.workflow.setting('update', 'include-prereleases')
                               else 'Pre-releases will be considered when updating the workflow',
                               'Select to change this value',
                               item_customizer('release.png', autocomplete='> settings update include '))

        if count == 0:
            self.workflow.item('No match for {0}'.format(arg), 'Click to clear your filter',
                               item_customizer('sad.png', autocomplete='> settings update '))

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
