"""An `Alfred <https://www.alfredapp.com/>`_ workflow helper written in Python

.. moduleauthor:: Patricio Trevino <patricio@weirdpattern.com>

"""

from .workflow import Workflow
from .workflow_item import WorkflowItem, InvalidModifier, InvalidText

__title__ = 'Alfred-Workflow-Utils'
__version__ = '1.2.0'
__author__ = 'WeirdPattern'
__licence__ = 'MIT'
__copyright__ = 'Copyright 2016 WeirdPattern'

__all__ = [
    'Workflow'
    'WorkflowItem'
    'InvalidText'
    'InvalidModifier'
]
