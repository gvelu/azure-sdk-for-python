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

from .operation_status_extended_info_py3 import OperationStatusExtendedInfo


class OperationStatusProvisionILRExtendedInfo(OperationStatusExtendedInfo):
    """Operation status extended info for ILR provision action.

    All required parameters must be populated in order to send to Azure.

    :param object_type: Required. Constant filled by server.
    :type object_type: str
    :param recovery_target: Target details for file / folder restore.
    :type recovery_target:
     ~azure.mgmt.recoveryservicesbackup.models.InstantItemRecoveryTarget
    """

    _validation = {
        'object_type': {'required': True},
    }

    _attribute_map = {
        'object_type': {'key': 'objectType', 'type': 'str'},
        'recovery_target': {'key': 'recoveryTarget', 'type': 'InstantItemRecoveryTarget'},
    }

    def __init__(self, *, recovery_target=None, **kwargs) -> None:
        super(OperationStatusProvisionILRExtendedInfo, self).__init__(**kwargs)
        self.recovery_target = recovery_target
        self.object_type = 'OperationStatusProvisionILRExtendedInfo'
