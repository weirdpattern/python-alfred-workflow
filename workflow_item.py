"""
.. module:: workflow_item
   :platform: Unix
   :synopsis: Main class of the project.

.. moduleauthor:: Patricio Trevino <patricio@weirdpattern.com>

"""

import sys


class InvalidModifier(Exception):
    """Invalid modifier error"""


class InvalidText(Exception):
    """Invalid text error"""


class WorkflowItem(object):
    """A class that represents an item of the workflow"""

    def __init__(self, title, subtitle):
        """Initializes the :class:`WorkflowItem`.

        :param title: the title of the workflow item.
        :type title: ``str``.
        :param subtitle: the subtitle of the workflow item.
        :type subtitle: ``str``.
        """

        self.title = title
        self.subtitle = subtitle

        self.type = None
        self.icon = None
        self.icontype = None

        self.modifiers = {'cmd': None, 'ctrl': None, 'shift': None, 'alt': None, 'fn': None}

        self.uid = None
        self.arg = None
        self.valid = True
        self.autocomplete = None

        self.texts = {'large': None, 'copy': None}

    def modifier(self, mod, subtitle):
        """Adds a new subtitle modifier.

        :param mod: the modifier key to be used.
        :type mod: ``str``.
        :param subtitle: the subtitle to be used.
        :type subtitle: ``str``.
        """

        if mod not in self.modifiers:
            raise InvalidModifier('Modifier {0} not support'.format(mod))

        self.modifiers[mod] = subtitle

    def text(self, ttype, text):
        """Adds a new text modifier.

        :param ttype: the text type to be used.
        :type ttype: ``str``.
        :param text: the text to be used.
        :type text: ``str``.
        """
        if ttype not in self.texts:
            raise InvalidText('Text type {0} not support'.format(ttype))

        self.texts[ttype] = text

    def feedback(self, flush=False):
        """Outputs the workflow item feedback

        :param flush: a flag indicating whether we want to flush ``sys.stdout`` or not.
                      This is usually done by :class:`Workflow`.
        :type flush: ``boolean``.
        """
        item = '\t<item {0}>\n'

        options = []
        if self.uid:
            options.append('uid="{0}"'.format(self.uid))

        if self.valid:
            options.append('valid="Yes"')
        else:
            options.append('valid="No"')

        if self.autocomplete:
            options.append('autocomplete="{0}"'.format(self.autocomplete))

        item = item.format(' '.join(str(x) for x in options))
        item += '\t\t<title>{0}</title>\n'.format(self.title)

        if self.subtitle:
            item += '\t\t<subtitle>{0}</subtitle>\n'.format(self.subtitle)

        if self.icon and self.icontype:
            item += '\t\t<icon type="{1}">{0}</icon>\n'.format(self.icon, self.icontype)
        elif self.icon:
            item += '\t\t<icon>{0}</icon>\n'.format(self.icon)

        if self.arg:
            item += '\t\t<arg>{0}</arg>\n'.format(self.arg)

        for mod in self.modifiers.keys():
            if self.modifiers[mod]:
                item += '\t\t<subtitle mod="{1}">{0}</subtitle>\n'.format(self.modifiers[mod], mod)

        for texttype in self.texts.keys():
            if self.texts[texttype]:
                item += '\t\t<text type="{1}">{0}</text>\n'.format(self.texts[texttype], texttype)

        item += '\t</item>\n'

        sys.stdout.write(item)
        if flush:
            sys.stdout.flush()
