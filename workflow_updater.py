import os
import tempfile
import subprocess

from workflow_version import Version


def check_update(workflow, forced='never', auto_install=False):
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
