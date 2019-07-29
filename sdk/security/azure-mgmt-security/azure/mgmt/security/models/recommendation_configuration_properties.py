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


class RecommendationConfigurationProperties(Model):
    """Recommendation configuration.

    Variables are only populated by the server, and will be ignored when
    sending a request.

    All required parameters must be populated in order to send to Azure.

    :param recommendation_type: Required. The recommendation type. Possible
     values include: 'IoT_ACRAuthentication',
     'IoT_AgentSendsUnutilizedMessages', 'IoT_Baseline',
     'IoT_EdgeHubMemOptimize', 'IoT_EdgeLoggingOptions',
     'IoT_InconsistentModuleSettings', 'IoT_InstallAgent',
     'IoT_IPFilter_DenyAll', 'IoT_IPFilter_PermissiveRule', 'IoT_OpenPorts',
     'IoT_PermissiveFirewallPolicy', 'IoT_PermissiveInputFirewallRules',
     'IoT_PermissiveOutputFirewallRules', 'IoT_PrivilegedDockerOptions',
     'IoT_SharedCredentials', 'IoT_VulnerableTLSCipherSuite'
    :type recommendation_type: str or
     ~azure.mgmt.security.models.RecommendationType
    :ivar name:
    :vartype name: str
    :param status: Required. Recommendation status. The recommendation is not
     generated when the status is disabled. Possible values include:
     'Disabled', 'Enabled'. Default value: "Enabled" .
    :type status: str or
     ~azure.mgmt.security.models.RecommendationConfigStatus
    """

    _validation = {
        'recommendation_type': {'required': True},
        'name': {'readonly': True},
        'status': {'required': True},
    }

    _attribute_map = {
        'recommendation_type': {'key': 'recommendationType', 'type': 'str'},
        'name': {'key': 'name', 'type': 'str'},
        'status': {'key': 'status', 'type': 'str'},
    }

    def __init__(self, **kwargs):
        super(RecommendationConfigurationProperties, self).__init__(**kwargs)
        self.recommendation_type = kwargs.get('recommendation_type', None)
        self.name = None
        self.status = kwargs.get('status', "Enabled")
