"""
.. module:: workflow_updater
   :platform: Unix
   :synopsis: Controls the workflow update operations.

.. moduleauthor:: Patricio Trevino <patricio@weirdpattern.com>

"""

import os
import tempfile
import subprocess

from workflow_version import Version


def check_update(workflow, forced='never', auto_install=False):
    """Check for updates.

    .. note: this method uses the ``update.repository.github`` configuration to call home.

    :param workflow: the :class:`Workflow` instance we want to update.
    :type workflow: :class:`workflow.Workflow`
    :param forced: a flag indicating whether we are forcing the check (through the ``> workflow check`` action).
    :type forced: ``boolean``.
    :param auto_install: a flag indicating whether we want to install without confirmation if a new version
                         is available (through the ``> workflow force-update`` action).
    :type auto_install: ``boolean``.
    :return: ``True``.
    :rtype: ``boolean``.
    """

    if not workflow.updatable():
        return False

    prereleases = workflow.setting('update', 'include-prereleases') or False
    github = workflow.setting('update', 'repository', 'github')
    if not github:
        workflow.notification('Workflow updater', 'No repository configuration has been detected')
        return False

    def fill():
        url = 'https://api.github.com/repos/{0}/{1}/releases'.format(github['username'], github['repository'])

        data = workflow.getJSON(url, headers={'User-Agent': 'Alfred-Workflow/1.17'})
        if data:
            urls = []
            for asset in data[0].get('assets', []):
                url = asset.get('browser_download_url')
                if not url or not url.endswith('.alfredworkflow'):
                    continue
                urls.append(url)

            return {
                'url': url,
                'version': data[0]['tag_name'],
                'prerelease': data[0]['prerelease']
            }

        return {}

    available = False
    message = 'You are running the latest version of "{0}"'.format(workflow.name)
    release = workflow.cache.read('.workflow_updater', fill, 3600)
    if release:
        if not release['prerelease'] or (release['prerelease'] and prereleases):
            latest = Version(release['version'])
            if latest > workflow.version:
                message = 'Version {0} of workflow {1} is available'.format(latest, workflow.name)
                available = True

    if forced == 'always' or (available and forced == 'only_when_available'):
        if available and auto_install:
            install_update(workflow, release['url'])
        else:
            workflow.notification('Workflow updater', message)

    return True


def install_update(workflow, url):
    """Installs an update.

    .. note: this method is the second part of the :func:`check_update` method.

    :param workflow: the :class:`workflow.Workflow` instance we want to update.
    :type workflow: :class:`workflow.Workflow`
    :param url: the url where to download the latest version.
    :type url: ``str``.
    """

    workflow.notification(workflow.name, 'Installation will commence shortly')

    filename = url.split('/')[-1]
    if not filename.endswith('.alfredworkflow'):
        workflow.notification('Workflow updater', 'The provided url is not an actual workflow')

    installer = os.path.join(tempfile.gettempdir(), filename)
    content = workflow.getRaw(url)
    with open(installer, 'wb') as output:
        output.write(content)

    workflow.cache.save('.workflow_updater', {})
    subprocess.call(['open', installer])
