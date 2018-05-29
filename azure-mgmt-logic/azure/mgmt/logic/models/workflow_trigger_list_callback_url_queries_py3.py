# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
#
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from msrest.serialization import Model


class WorkflowTriggerListCallbackUrlQueries(Model):
    """Gets the workflow trigger callback URL query parameters.

    :param api_version: The api version.
    :type api_version: str
    :param sp: The SAS permissions.
    :type sp: str
    :param sv: The SAS version.
    :type sv: str
    :param sig: The SAS signature.
    :type sig: str
    :param se: The SAS timestamp.
    :type se: str
    """

    _attribute_map = {
        'api_version': {'key': 'api-version', 'type': 'str'},
        'sp': {'key': 'sp', 'type': 'str'},
        'sv': {'key': 'sv', 'type': 'str'},
        'sig': {'key': 'sig', 'type': 'str'},
        'se': {'key': 'se', 'type': 'str'},
    }

    def __init__(self, *, api_version: str=None, sp: str=None, sv: str=None, sig: str=None, se: str=None, **kwargs) -> None:
        super(WorkflowTriggerListCallbackUrlQueries, self).__init__(**kwargs)
        self.api_version = api_version
        self.sp = sp
        self.sv = sv
        self.sig = sig
        self.se = se
