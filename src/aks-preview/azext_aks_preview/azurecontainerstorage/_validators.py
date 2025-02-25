# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azext_aks_preview.azurecontainerstorage._consts import (
    CONST_STORAGE_POOL_OPTION_SSD,
    CONST_STORAGE_POOL_SKU_PREMIUM_LRS,
    CONST_STORAGE_POOL_SKU_PREMIUM_ZRS,
    CONST_STORAGE_POOL_TYPE_AZURE_DISK,
    CONST_STORAGE_POOL_TYPE_EPHEMERAL_DISK,
    CONST_STORAGE_POOL_TYPE_ELASTIC_SAN,
)

from azure.cli.core.azclierror import (
    ArgumentUsageError,
    InvalidArgumentValueError,
    MutuallyExclusiveArgumentError,
)

from knack.log import get_logger
import re

elastic_san_supported_skus = [
    CONST_STORAGE_POOL_SKU_PREMIUM_LRS,
    CONST_STORAGE_POOL_SKU_PREMIUM_ZRS,
]

logger = get_logger(__name__)


def validate_azure_container_storage_params(
    enable_azure_container_storage,
    disable_azure_container_storage,
    storage_pool_name,
    storage_pool_type,
    storage_pool_sku,
    storage_pool_option,
    storage_pool_size,
    nodepool_list,
    agentpool_names,
    is_extension_installed,
):
    if enable_azure_container_storage and disable_azure_container_storage:
        raise MutuallyExclusiveArgumentError(
            'Conflicting flags. Cannot set --enable-azure-container-storage '
            'and --disable-azure-container-storage together.'
        )

    if disable_azure_container_storage:
        _validate_disable_azure_container_storage_params(
            storage_pool_name,
            storage_pool_sku,
            storage_pool_option,
            storage_pool_size,
            nodepool_list,
            is_extension_installed,
        )

    elif enable_azure_container_storage:
        _validate_enable_azure_container_storage_params(
            storage_pool_name,
            storage_pool_type,
            storage_pool_sku,
            storage_pool_option,
            storage_pool_size,
            is_extension_installed
        )

        _validate_nodepool_names(nodepool_list, agentpool_names)


def _validate_disable_azure_container_storage_params(
    storage_pool_name,
    storage_pool_sku,
    storage_pool_option,
    storage_pool_size,
    nodepool_list,
    is_extension_installed,
):
    if not is_extension_installed:
        raise InvalidArgumentValueError(
            'Invalid usage of --disable-azure-container-storage. '
            'Azure Container Storage is not enabled on the cluster. '
            'Aborting disabling of Azure Container Storage.'
        )

    if storage_pool_name is not None:
        raise MutuallyExclusiveArgumentError(
            'Conflicting flags. Cannot define --storage-pool-name value '
            'when --disable-azure-container-storage is set.'
        )

    if storage_pool_sku is not None:
        raise MutuallyExclusiveArgumentError(
            'Conflicting flags. Cannot define --storage-pool-sku value '
            'when --disable-azure-container-storage is set.'
        )

    if storage_pool_size is not None:
        raise MutuallyExclusiveArgumentError(
            'Conflicting flags. Cannot define --storage-pool-size value '
            'when --disable-azure-container-storage is set.'
        )

    if storage_pool_option is not None:
        raise MutuallyExclusiveArgumentError(
            'Conflicting flags. Cannot define --storage-pool-option value '
            'when --disable-azure-container-storage is set.'
        )

    if nodepool_list is not None:
        raise MutuallyExclusiveArgumentError(
            'Conflicting flags. Cannot define --azure-container-storage-nodepools value '
            'when --disable-azure-container-storage is set.'
        )


def _validate_enable_azure_container_storage_params(
    storage_pool_name,
    storage_pool_type,
    storage_pool_sku,
    storage_pool_option,
    storage_pool_size,
    is_extension_installed,
):
    if is_extension_installed:
        raise InvalidArgumentValueError(
            'Invalid usage of --enable-azure-container-storage. '
            'Azure Container Storage is already enabled on the cluster. '
            'Aborting installation of Azure Container Storage.'
        )

    if storage_pool_name is not None:
        pattern = r'[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*'
        is_pool_name_valid = re.fullmatch(pattern, storage_pool_name)
        if not is_pool_name_valid:
            raise InvalidArgumentValueError(
                "Invalid --storage-pool-name value. "
                "Accepted values are lowercase alphanumeric characters, "
                "'-' or '.', and must start and end with an alphanumeric character.")

    if storage_pool_sku is not None:
        if storage_pool_type == CONST_STORAGE_POOL_TYPE_EPHEMERAL_DISK:
            raise ArgumentUsageError('Cannot set --storage-pool-sku when --enable-azure-container-storage is ephemeralDisk.')
        elif storage_pool_type == CONST_STORAGE_POOL_TYPE_ELASTIC_SAN and \
                storage_pool_sku not in elastic_san_supported_skus:
            supported_skus_str = ", ".join(elastic_san_supported_skus)
            raise ArgumentUsageError(
                'Invalid --storage-pool-sku value. '
                'Supported value for --storage-pool-sku are {0} '
                'when --enable-azure-container-storage is set to elasticSan.'
                .format(supported_skus_str)
            )

    if storage_pool_type != CONST_STORAGE_POOL_TYPE_EPHEMERAL_DISK and \
       storage_pool_option is not None:
        raise ArgumentUsageError('Cannot set --storage-pool-option when --enable-azure-container-storage is not ephemeralDisk.')

    if storage_pool_type == CONST_STORAGE_POOL_TYPE_EPHEMERAL_DISK and \
       storage_pool_option == CONST_STORAGE_POOL_OPTION_SSD:
        raise ArgumentUsageError(
            '--storage-pool-option Temp storage (SSD) currently not supported.'
        )

    if storage_pool_size is not None:
        pattern = r'^\d+(\.\d+)?[GT]i$'
        match = re.match(pattern, storage_pool_size)
        if match is None:
            raise ArgumentUsageError(
                'Value for --storage-pool-size should be defined '
                'with size followed by Gi or Ti e.g. 512Gi or 2Ti.'
            )

        else:
            if storage_pool_type == CONST_STORAGE_POOL_TYPE_ELASTIC_SAN:
                pool_size_qty = float(storage_pool_size[:-2])
                pool_size_unit = storage_pool_size[-2:]

                if (
                    (pool_size_unit == "Gi" and pool_size_qty < 1024) or
                    (pool_size_unit == "Ti" and pool_size_qty < 1)
                ):
                    raise ArgumentUsageError(
                        'Value for --storage-pool-size must be at least 1Ti when '
                        '--enable-azure-container-storage is elasticSan.')

            elif storage_pool_type == CONST_STORAGE_POOL_TYPE_EPHEMERAL_DISK:
                logger.warning(
                    'Storage pools using Ephemeral disk use all capacity available on the local device. '
                    ' --storage-pool-size will be ignored.'
                )


def _validate_nodepool_names(nodepool_names, agentpool_details):
    # Validate that nodepool_list is a comma separated string
    # consisting of valid nodepool names i.e. lower alphanumeric
    # characters and the first character should be lowercase letter.
    pattern = r'^[a-z][a-z0-9]*(?:,[a-z][a-z0-9]*)*$'
    if re.fullmatch(pattern, nodepool_names) is None:
        raise InvalidArgumentValueError(
            "Invalid --azure-container-storage-nodepools value. "
            "Accepted value is a comma separated string of valid nodepool "
            "names without any spaces.\nA valid nodepool name may only contain lowercase "
            "alphanumeric characters and must begin with a lowercase letter."
        )

    nodepool_list = nodepool_names.split(',')
    for nodepool in nodepool_list:
        if nodepool not in agentpool_details:
            if len(agentpool_details) > 1:
                raise InvalidArgumentValueError(
                    'Nodepool: {0} not found. '
                    'Please provide a comma separated string of existing nodepool names '
                    'in --azure-container-storage-nodepools.'
                    '\nNodepools available in the cluster are: {1}.'
                    '\nAborting installation of Azure Container Storage.'
                    .format(nodepool, ', '.join(agentpool_details))
                )
            else:
                raise InvalidArgumentValueError(
                    'Nodepool: {0} not found. '
                    'Please provide a comma separated string of existing nodepool names '
                    'in --azure-container-storage-nodepools.'
                    '\nNodepool available in the cluster is: {1}.'
                    '\nAborting installation of Azure Container Storage.'
                    .format(nodepool, agentpool_details[0])
                )
