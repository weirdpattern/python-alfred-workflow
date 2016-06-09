"""
.. module:: utils
   :platform: Unix
   :synopsis: A set of utilities for the workflow.

.. moduleauthor:: Patricio Trevino <patricio@weirdpattern.com>

"""

from __future__ import print_function, unicode_literals

import os
import re
import sys
import json
import zlib
import time
import errno
import signal
import pickle
import cPickle
import threading
import unicodedata

from functools import wraps
from contextlib import contextmanager

try:
    from urllib import urlencode
    from urllib2 import Request, URLError, HTTPError, HTTPRedirectHandler, HTTPBasicAuthHandler, \
        HTTPPasswordMgrWithDefaultRealm, build_opener, install_opener, urlparse, urlopen
except ImportError:
    from urllib.error import URLError, HTTPError
    from urllib.parse import urlparse, urlencode
    from urllib.request import Request, HTTPBasicAuthHandler, HTTPRedirectHandler, HTTPPasswordMgrWithDefaultRealm, \
        build_opener, install_opener, urlopen


class AcquisitionError(Exception):
    """A class that represents a lock acquisition error.

    .. note: used by :class:`lock` to indicate a timeout has occurred while trying to get a lock on a file.

    """


class NoRedirectHttpHandler(HTTPRedirectHandler):
    """A class that represents a no HTTP redirection policy.

    .. note: used by :func:`request` to handle no redirect scenarios.

    """

    def redirect_request(self, *args):
        """Handles the redirection, by preventing it.

        :param args: the arguments of the request.
        :type args: ``tuple``.
        :return: ``None``.
        :rtype: ``None``.
        """

        return None


class PickleSerializer(object):
    """A class that represents a pickle serializer.

    .. note: used by :class:`WorkflowCache` and :class:`WorkflowData` to serialize files.

    """

    def __init__(self):
        """Initializes the serializer"""

        self._serializer = cPickle if sys.version_info[0] < 3 else pickle

    @property
    def name(self):
        """The name of the serializer.

        :return: the constant ``pickle``.
        :rtype: ``str``.
        """

        return 'pickle'

    def load(self, handler):
        """Deserializes the file handler.

        :param handler: the file to be deserialized.
        :type handler: :class:`file`.
        :return: the content of the file.
        :rtype: ``str``
        """

        return self._serializer.load(handler)

    def dump(self, obj, handler):
        """Serializes the object in the given file handler.

        :param obj: the data to be serialized.
        :type obj: ``any``.
        :param handler: the file handle to be used.
        :type handler: :class:`file`.
        :return: the pickled representation of the object as a string
        :rtype: ``str``.
        """

        return self._serializer.dump(obj, handler, protocol=-1)


class lock(object):
    """Creates a lock in a file.

    .. note: used by :class:`WorkflowSettings` to atomically update the settings.

    """

    def __init__(self, path, timeout=0, delay=0.05):
        """Initializes the lock.

        :param path: the path to the file to be locked.
        :type path: ``str``.
        :param timeout: the timeout to be used while locking the file.
        :type timeout: ``int``.
        :param delay: the time to wait on exception scenarios.
        :type delay: ``float``
        """

        self.file = path + '.lock'
        self.timeout = timeout
        self.delay = delay

        self.locked = False

    def acquire(self, blocking=True):
        """Tries to acquire a lock on the file.

        :param blocking: a flag that indicates whether the acquire operation should return ``True``
                         or ``False`` when a file is already locked.
        :type blocking: ``boolean``
        :return: ``True`` if the lock was acquired; ``False`` otherwise.
        :rtype: ``boolean``
        """

        start = time.time()
        while True:
            try:
                fd = os.open(self.file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                with os.fdopen(fd, 'w') as fd:
                    fd.write(str('{0}'.format(os.getpid())))
                break
            except OSError as err:
                if err.errno != errno.EEXIST:
                    raise
                if self.timeout and (time.time() - start) >= self.timeout:
                    raise AcquisitionError('Lock acquisition timed out')
                if not blocking:
                    return False
                time.sleep(self.delay)

        self.locked = True
        return True

    def release(self):
        """Releases the lock on the file"""

        self.locked = False
        os.unlink(self.file)

    def __enter__(self):
        """Handles the enter event in a contextmanager.

        :return: the current instance of the lock.
        :rtype: :class:`lock`
        """

        self.acquire()
        return self

    def __exit__(self, type, value, traceback):
        """Handles the exit event in a contextmanager.

        :param type: the exception type.
        :type type: ``str``
        :param value: the exception instance.
        :type value: ``exception``
        :param traceback: the traceback of the exception.
        :type traceback: :class:`traceback`
        """

        self.release()

    def __del__(self):
        """Handles the destroy event in a contextmanager"""

        if self.locked:
            self.release()


def atomic(func):
    """Decorator that postpones SIGTERM until wrapped function is complete.

    :param func: the function to be decorated.
    :type func: ``callable``.
    :return: the handler function to be invoked by the decorator when ``func`` gets called.
    :rtype: ``callable``.
    """

    @wraps(func)
    def handler(*args, **kwargs):
        """The handler function to be invoked by the decorator when ``func`` gets called.

        :param args: the arguments of ``func``, if any.
        :type ``tuple``.
        :param kwargs: the keyed arguments of ``func``, if any.
        :type ``tuple``.
        """

        if is_main_thread():
            caught_signal = []
            old_signal_handler = signal.getsignal(signal.SIGTERM)

            signal.signal(signal.SIGTERM, lambda s, f: caught_signal.__setitem__(0, (s, f)))

            func(*args, **kwargs)

            signal.signal(signal.SIGTERM, old_signal_handler)
            if len(caught_signal) > 0:
                signum, frame = caught_signal[0]
                if callable(old_signal_handler):
                    old_signal_handler(signum, frame)
                elif old_signal_handler == signal.SIG_DFL:
                    sys.exit(0)
        else:
            func(*args, **kwargs)

    return handler


@contextmanager
def atomic_write(path, mode):
    """Makes sure a file gets written correctly by working on a copy, then renaming it to the real file.

    :param path: the path to the file to be handled.
    :type path: ``str``.
    :param mode: the mode in which the file should be opened.
    :type mode: ``str``.
    """

    suffix = '.aw.temp'
    filepath = path + suffix
    with open(filepath, mode) as handler:
        try:
            yield handler
            os.rename(filepath, path)
        finally:
            try:
                os.remove(filepath)
            except (OSError, IOError):
                pass


def decode(text, normalization='NFC'):
    """Decodes strings to unicode.

    :param text: the text to be decoded.
    :type text: ``str``.
    :param normalization: the normalization to be used.
    :type normalization: ``str``.
    :return: the decoded text.
    :rtype: ``str``.
    """

    if text and not isinstance(text, unicode):
        text = text.decode('unicode-escape')
        return unicodedata.normalize(normalization, text)

    return text


def ensure_path(path):
    """Ensures the path exists.

    :param path: the path to validate.
    :type path: ``str``.
    :return: the same path.
    :rtype: ``str``.
    """

    if not os.path.exists(path):
        os.makedirs(path)

    return path


def parse_version(string):
    """Parses the string to get all the parts that comprises a :class:Version

    .. note: this method parses versions in SEMVER.

    :param string: the string to be parsed.
    :type string: ``str``.
    :return: a 5-tuple containing the major, minor, patch, release and build information.
    :rtype: 5-tuple (``int``, ``int``, ``int``, ``str``, ``str``).
    """

    version_matcher = re.compile(r'([0-9\.]+)([-+].+)?').match

    if string.startswith('v'):
        match = version_matcher(string[1:])
    else:
        match = version_matcher(string)

    if not match:
        raise ValueError('Invalid version (format): {0}'.format(string))

    parts = match.group(1).split('.')
    suffix = match.group(2)

    major = int(parts.pop(0))
    minor = int(parts.pop(0)) if len(parts) else 0
    patch = int(parts.pop(0)) if len(parts) else 0

    if not len(parts) == 0:
        raise ValueError('Invalid version (too long): {0}'.format(string))

    build = None
    release = None
    if suffix:
        parts = suffix.split('+')
        release = parts.pop(0)
        if release.startswith('-'):
            release = release[1:]
        else:
            raise ValueError('Invalid type (must start with -): {0}'.format(string))

        if len(parts):
            build = parts.pop(0)

    return major, minor, patch, release, build


def register_path(path):
    """Adds a path to ``sys.path``

    .. note: adding a path to ``sys.path`` allows python to find it without specifying a relative path.

    :param path: the path to be added.
    :type path: ``str``.
    """
    sys.path.insert(0, path)


def send_notification(title, message):
    """Send a new OS X notification.

    .. note: title accepts 48 chars
             message accepts 96 chars

    :param title: the title of the notification.
    :type title: ``str``.
    :param message:  the message to be displayed in the notification.
    :type message: ``str``.
    """

    script = "osascript -e 'display notification \"{1}\" with title \"{0}\"'"
    script = script.format(title.replace('"', r'\"'), message.replace('"', r'\"'))
    os.system(script)


def close_alfred_window():
    """Closes the current Alfred window"""

    script = "osascript -e 'tell application \"System Events\" to key code 53'"
    os.system(script)


def is_main_thread():
    """Determines if the current thread is the actual main thread.

    .. note: used by :func:`atomic` decorator.

    :return: ``True`` if the current thread is the actual main thread; ``False`` otherwise.
    """

    return isinstance(threading.current_thread(), threading._MainThread)


def item_customizer(icon=None, valid=False, arg=None, autocomplete=None):
    """Creates a :class:`WorkflowItem` customizer.

    .. note: used by :class:`Workflow`
    .. warning: this is not meant to be used by others.
                DO NOT USE IT.

    :param icon: the icon to be used.
    :type icon: ``str``.
    :param valid: a flag indicating whether the item should be valid or not.
    :type valid: ``boolean``.
    :param arg: the argument to be used by the item
    :type arg: ``str``.
    :param autocomplete: the autocomplete information of the item.
    :type autocomplete: ``str``.
    :return: the handler function to be invoked when preparing the item.
    :rtype: ``callable``
    """

    icon = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'icons', icon) if icon else None

    def customize(item):
        """Customizes the item.

        :param item: the item to be customized.
        :type item: :class:`WorkflowItem`.
        :return: the same item with the customizations.
        :rtype: :class:`WorkflowItem`.
        """

        item.arg = arg
        item.icon = icon
        item.valid = valid
        item.autocomplete = autocomplete

        return item

    return customize


def format_headers(headers):
    """Formats the headers of a :class:`Request`.

    :param headers: the headers to be formatted.
    :type headers: :class:`dict`.
    :return: the headers in lower case format.
    :rtype: :class:`dict`.
    """

    dictionary = {}

    for k, v in headers.items():
        if isinstance(k, unicode):
            k = k.encode('utf-8')

        if isinstance(v, unicode):
            v = v.encode('utf-8')

        dictionary[k.lower()] = v.lower()

    return dictionary


def request(method, url, content_type, data=None, params=None, headers=None, cookies=None,
            auth=None, redirection=True, timeout=60):
    """Creates a new HTTP request and processes it.

    :param method: the type of request to be created (``GET`` or ``POST``)
    :type method: ``str``.
    :param url: the url of the request.
    :type url: ``str``.
    :param content_type: the content type to be returned (``raw`` or ``json``)
    :type content_type: ``str``.
    :param data: the data to be posted.
    :type data: ``any``.
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
    :rtype: ``str`` or ``json``.
    """

    openers = []
    if not redirection:
        openers.append(NoRedirectHttpHandler())

    if auth:
        manager = HTTPPasswordMgrWithDefaultRealm()
        manager.add_password(None, url, auth['username'], auth['password'])
        openers.append(HTTPBasicAuthHandler(manager))

    opener = build_opener(*openers)
    install_opener(opener)

    headers = headers or {}
    if cookies:
        for cookie in cookies.keys():
            headers['Cookie'] = "{0}={1}".format(cookie, cookies[cookie])

    if 'user-agent' not in headers:
        headers['user-agent'] = 'Alfred-Workflow/1.17'

    encodings = [s.strip() for s in headers.get('accept-encoding', '').split(',')]
    if 'gzip' not in encodings:
        encodings.append('gzip')

    headers['accept-encoding'] = ', '.join(encodings)

    if method == 'POST' and not data:
        data = ''

    if data and isinstance(data, dict):
        data = urlencode(format_headers(data))

    headers = format_headers(headers)

    if isinstance(url, unicode):
        url = url.encode('utf-8')

    if params:
        scheme, netloc, path, query, fragment = urlparse.urlsplit(url)

        if query:
            url_params = urlparse.parse_qs(query)
            url_params.update(params)
            params = url_params

        query = urlencode(format_headers(params), doseq=True)
        url = urlparse.urlunsplit((scheme, netloc, path, query, fragment))

    try:
        response = urlopen(Request(url, data, headers), timeout=timeout)
        response_headers = response.info()

        content = response.read()
        if 'gzip' in response_headers.get('content-encoding', '') \
                or 'gzip' in response_headers.get('transfer-encoding', ''):
            content = unzip(content)

        if content_type.lower() == 'json':
            return json.loads(content, 'utf-8')

        return content
    except (HTTPError, URLError):
        send_notification('Workflow', 'Error while calling {0}'.format(url))
        if content_type.lower() == 'json':
            return {}

        return ''


def unzip(content):
    """Decompresses the content.

    :param content: the content to be decompressed.
    :type content: ``str``.
    :return: the decompressed content.
    :rtype: ``str``.
    """
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    return decoder.decompress(content)


def bind(func):
    """Binds func.

    :param func: the function to be bind.
    :type func: ``callable``.
    :return: the handler to be used to invoke func.
    :rtype: ``callable``.
    """
    def executor(*args):
        return func(*args)

    return executor
