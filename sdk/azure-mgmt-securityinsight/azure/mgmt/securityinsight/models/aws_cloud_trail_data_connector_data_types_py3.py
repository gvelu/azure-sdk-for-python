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


class AwsCloudTrailDataConnectorDataTypes(Model):
    """The available data types for Amazon Web Services CloudTrail data connector.

    :param logs: Logs data type.
    :type logs:
     ~azure.mgmt.securityinsight.models.AwsCloudTrailDataConnectorDataTypesLogs
    """

    _attribute_map = {
        'logs': {'key': 'logs', 'type': 'AwsCloudTrailDataConnectorDataTypesLogs'},
    }

    def __init__(self, *, logs=None, **kwargs) -> None:
        super(AwsCloudTrailDataConnectorDataTypes, self).__init__(**kwargs)
        self.logs = logs
