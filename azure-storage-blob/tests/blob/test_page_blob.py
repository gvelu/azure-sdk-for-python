# coding: utf-8

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest

import pytest
import os
import unittest
from datetime import datetime, timedelta
from azure.common import AzureHttpError
from azure.core.exceptions import HttpResponseError

from azure.storage.blob.common import (
    BlobType,
    PremiumPageBlobTier,
    SequenceNumberAction)
from azure.storage.blob.models import BlobProperties, BlobPermissions
from azure.storage.blob import (
    SharedKeyCredentials,
    BlobServiceClient,
    ContainerClient,
    BlobClient)

from tests.testcase import (
    StorageTestCase,
    TestMode,
    record,
)
from azure.common import (
    AzureException,
)

#------------------------------------------------------------------------------
TEST_BLOB_PREFIX = 'blob'
FILE_PATH = 'blob_input.temp.dat'
LARGE_BLOB_SIZE = 64 * 1024 + 512
EIGHT_TB = 8 * 1024 * 1024 * 1024 * 1024
#------------------------------------------------------------------------------s

class StoragePageBlobTest(StorageTestCase):

    def setUp(self):
        super(StoragePageBlobTest, self).setUp()

        url = self._get_account_url()
        self.config = BlobServiceClient.create_configuration()

        # test chunking functionality by reducing the size of each chunk,
        # otherwise the tests would take too long to execute
        self.config.connection.data_block_size = 4 * 1024
        self.config.blob_settings.max_page_size = 4 * 1024
        credentials = SharedKeyCredentials(*self._get_shared_key_credentials())

        self.bs = BlobServiceClient(url, credentials=credentials, configuration=self.config)
        self.container_name = self.get_resource_name('utcontainer')

        if not self.is_playback():
            container = self.bs.get_container_client(self.container_name)
            container.create_container()

    def tearDown(self):
        if not self.is_playback():
            try:
                container = self.bs.get_container_client(self.container_name)
                container.delete_container()
            except:
                pass

        if os.path.isfile(FILE_PATH):
            try:
                os.remove(FILE_PATH)
            except:
                pass

        return super(StoragePageBlobTest, self).tearDown()

    #--Helpers-----------------------------------------------------------------

    def _get_blob_reference(self):
        return self.bs.get_blob_client(
            self.container_name,
            self.get_resource_name(TEST_BLOB_PREFIX),
            blob_type=BlobType.PageBlob)

    def _create_blob(self, length=512):
        blob = self._get_blob_reference()
        blob.create_blob(content_length=length)
        return blob

    def assertBlobEqual(self, container_name, blob_name, expected_data):
        blob = self.bs.get_blob_client(container_name, blob_name, blob_type=BlobType.PageBlob)
        actual_data = blob.download_blob()
        self.assertEqual(b"".join(list(actual_data)), expected_data)

    def assertRangeEqual(self, container_name, blob_name, expected_data, start_range, end_range):
        blob = self.bs.get_blob_client(container_name, blob_name, blob_type=BlobType.PageBlob)
        actual_data = blob.download_blob(offset=start_range, length=end_range)
        self.assertEqual(b"".join(list(actual_data)), expected_data)

    class NonSeekableFile(object):
        def __init__(self, wrapped_file):
            self.wrapped_file = wrapped_file

        def write(self, data):
            self.wrapped_file.write(data)

        def read(self, count):
            return self.wrapped_file.read(count)

    #--Test cases for page blobs --------------------------------------------
    @record
    def test_create_blob(self):
        # Arrange
        blob = self._get_blob_reference()

        # Act
        resp = blob.create_blob(1024)

        # Assert
        self.assertIsNotNone(resp.get('ETag'))
        self.assertIsNotNone(resp.get('Last-Modified'))
        self.assertTrue(blob.get_blob_properties())

    @record
    def test_create_blob_with_metadata(self):
        # Arrange
        blob = self._get_blob_reference()
        metadata = {'hello': 'world', 'number': '42'}
        
        # Act
        resp = blob.create_blob(512, metadata=metadata)

        # Assert
        md = blob.get_blob_properties()
        self.assertDictEqual(md.metadata, metadata)

    @record
    def test_put_page_with_lease_id(self):
        # Arrange
        blob = self._create_blob()
        lease = blob.acquire_lease()

        # Act        
        data = self.get_random_bytes(512)
        blob.upload_page(data, 0, 511, lease=lease)

        # Assert
        content = blob.download_blob(lease=lease)
        self.assertEqual(b"".join(list(content)), data)

    @record
    def test_update_page(self):
        # Arrange
        blob = self._create_blob()

        # Act
        data = self.get_random_bytes(512)
        resp = blob.upload_page(data, 0, 511)

        # Assert
        self.assertIsNotNone(resp.get('ETag'))
        self.assertIsNotNone(resp.get('Last-Modified'))
        self.assertIsNotNone(resp.get('x-ms-blob-sequence-number'))
        self.assertBlobEqual(self.container_name, blob.name, data)

    @record
    def test_create_8tb_blob(self):
        # Arrange
        blob = self._get_blob_reference()

        # Act
        resp = blob.create_blob(EIGHT_TB)
        props = blob.get_blob_properties()
        page_ranges, cleared = blob.get_page_ranges()

        # Assert
        self.assertIsNotNone(resp.get('ETag'))
        self.assertIsNotNone(resp.get('Last-Modified'))
        self.assertIsInstance(props, BlobProperties)
        self.assertEqual(props.content_length, EIGHT_TB)
        self.assertEqual(0, len(page_ranges))

    @record
    def test_create_larger_than_8tb_blob_fail(self):
        # Arrange
        blob = self._get_blob_reference()

        # Act
        with self.assertRaises(HttpResponseError):
            blob.create_blob(EIGHT_TB + 1)

    @record
    def test_update_8tb_blob_page(self):
        # Arrange
        blob = self._get_blob_reference()
        blob.create_blob(EIGHT_TB)

        # Act
        data = self.get_random_bytes(512)
        start_range = EIGHT_TB - 512
        end_range = EIGHT_TB - 1
        resp = blob.upload_page(data, start_range, end_range)
        props = blob.get_blob_properties()
        page_ranges, cleared = blob.get_page_ranges()
        
        # Assert
        self.assertIsNotNone(resp.get('ETag'))
        self.assertIsNotNone(resp.get('Last-Modified'))
        self.assertIsNotNone(resp.get('x-ms-blob-sequence-number'))
        self.assertRangeEqual(self.container_name, blob.name, data, start_range, end_range)
        self.assertEqual(props.content_length, EIGHT_TB)
        self.assertEqual(1, len(page_ranges))
        self.assertEqual(page_ranges[0]['start'], start_range)
        self.assertEqual(page_ranges[0]['end'], end_range)

    @record
    def test_update_page_with_md5(self):
        # Arrange
        blob = self._create_blob()

        # Act
        data = self.get_random_bytes(512)
        resp = blob.upload_page(data, 0, 511, validate_content=True)

        # Assert

    @record
    def test_clear_page(self):
        # Arrange
        blob = self._create_blob()

        # Act
        resp = blob.clear_page(0, 511)

        # Assert
        self.assertIsNotNone(resp.get('ETag'))
        self.assertIsNotNone(resp.get('Last-Modified'))
        self.assertIsNotNone(resp.get('x-ms-blob-sequence-number'))
        self.assertBlobEqual(self.container_name, blob.name, b'\x00' * 512)

    @record
    def test_put_page_if_sequence_number_lt_success(self):
        # Arrange     
        blob = self._get_blob_reference() 
        data = self.get_random_bytes(512)

        start_sequence = 10
        blob.create_blob(512, sequence_number=start_sequence)

        # Act
        blob.upload_page(data, 0, 511, if_sequence_number_lt=start_sequence + 1)

        # Assert
        self.assertBlobEqual(self.container_name, blob.name, data)

    @record
    def test_update_page_if_sequence_number_lt_failure(self):
        # Arrange
        blob = self._get_blob_reference() 
        data = self.get_random_bytes(512)
        start_sequence = 10
        blob.create_blob(512, sequence_number=start_sequence)

        # Act
        with self.assertRaises(HttpResponseError):
            blob.upload_page(data, 0, 511, if_sequence_number_lt=start_sequence)

        # Assert

    @record
    def test_update_page_if_sequence_number_lte_success(self):
        # Arrange
        blob = self._get_blob_reference() 
        data = self.get_random_bytes(512)
        start_sequence = 10
        blob.create_blob(512, sequence_number=start_sequence)

        # Act
        blob.upload_page(data, 0, 511, if_sequence_number_lte=start_sequence)

        # Assert
        self.assertBlobEqual(self.container_name, blob.name, data)

    @record
    def test_update_page_if_sequence_number_lte_failure(self):
        # Arrange
        blob = self._get_blob_reference() 
        data = self.get_random_bytes(512)
        start_sequence = 10
        blob.create_blob(512, sequence_number=start_sequence)

        # Act
        with self.assertRaises(HttpResponseError):
            blob.upload_page(data, 0, 511, if_sequence_number_lte=start_sequence - 1)

        # Assert

    @record
    def test_update_page_if_sequence_number_eq_success(self):
        # Arrange
        blob = self._get_blob_reference() 
        data = self.get_random_bytes(512)
        start_sequence = 10
        blob.create_blob(512, sequence_number=start_sequence)

        # Act
        blob.upload_page(data, 0, 511, if_sequence_number_eq=start_sequence)

        # Assert
        self.assertBlobEqual(self.container_name, blob.name, data)

    @record
    def test_update_page_if_sequence_number_eq_failure(self):
        # Arrange
        blob = self._get_blob_reference() 
        data = self.get_random_bytes(512)
        start_sequence = 10
        blob.create_blob(512, sequence_number=start_sequence)

        # Act
        with self.assertRaises(HttpResponseError):
            blob.upload_page(data, 0, 511, if_sequence_number_eq=start_sequence - 1)

        # Assert

    @record
    def test_update_page_unicode(self):
        # Arrange
        blob = self._create_blob()

        # Act
        data = u'abcdefghijklmnop' * 32
        resp = blob.upload_page(data, 0, 511)

        # Assert
        self.assertIsNotNone(resp.get('ETag'))
        self.assertIsNotNone(resp.get('Last-Modified'))

    @record
    def test_get_page_ranges_no_pages(self):
        # Arrange
        blob = self._create_blob()

        # Act
        ranges, cleared = blob.get_page_ranges()

        # Assert
        self.assertIsNotNone(ranges)
        self.assertIsInstance(ranges, list)
        self.assertEqual(len(ranges), 0)

    @record
    def test_get_page_ranges_2_pages(self):
        # Arrange
        blob = self._create_blob(2048)
        data = self.get_random_bytes(512)
        resp1 = blob.upload_page(data, 0, 511)
        resp2 = blob.upload_page(data, 1024, 1535)

        # Act
        ranges, cleared = blob.get_page_ranges()

        # Assert
        self.assertIsNotNone(ranges)
        self.assertIsInstance(ranges, list)
        self.assertEqual(len(ranges), 2)
        self.assertEqual(ranges[0]['start'], 0)
        self.assertEqual(ranges[0]['end'], 511)
        self.assertEqual(ranges[1]['start'], 1024)
        self.assertEqual(ranges[1]['end'], 1535)


    @record
    def test_get_page_ranges_diff(self):
        # Arrange
        blob = self._create_blob(2048)
        data = self.get_random_bytes(1536)
        snapshot1 = blob.create_snapshot()
        blob.upload_page(data, 0, 1535)
        snapshot2 = blob.create_snapshot()
        blob.clear_page(512, 1023)

        # Act
        ranges1, cleared1 = blob.get_page_ranges(previous_snapshot_diff=snapshot1)
        ranges2, cleared2 = blob.get_page_ranges(previous_snapshot_diff=snapshot2.snapshot)

        # Assert
        self.assertIsNotNone(ranges1)
        self.assertIsInstance(ranges1, list)
        self.assertEqual(len(ranges1), 2)
        self.assertIsInstance(cleared1, list)
        self.assertEqual(len(cleared1), 1)
        self.assertEqual(ranges1[0]['start'], 0)
        self.assertEqual(ranges1[0]['end'], 511)
        self.assertEqual(cleared1[0]['start'], 512)
        self.assertEqual(cleared1[0]['end'], 1023)
        self.assertEqual(ranges1[1]['start'], 1024)
        self.assertEqual(ranges1[1]['end'], 1535)

        self.assertIsNotNone(ranges2)
        self.assertIsInstance(ranges2, list)
        self.assertEqual(len(ranges2), 0)
        self.assertIsInstance(cleared2, list)
        self.assertEqual(len(cleared2), 1)
        self.assertEqual(cleared2[0]['start'], 512)
        self.assertEqual(cleared2[0]['end'], 1023)

    @record    
    def test_update_page_fail(self):
        # Arrange
        blob = self._create_blob(2048)
        data = self.get_random_bytes(512)
        resp1 = blob.upload_page(data, 0, 511)

        # Act
        try:
            blob.upload_page(data, 1024, 1536)
        except ValueError as e:
            self.assertEqual(str(e), 'end_range must be an integer that aligns with 512 page size')
            return

        # Assert
        raise Exception('Page range validation failed to throw on failure case')


    @record
    def test_resize_blob(self):
        # Arrange
        blob = self._create_blob(1024)
        
        # Act
        resp = blob.resize_blob(512)

        # Assert
        self.assertIsNotNone(resp.get('ETag'))
        self.assertIsNotNone(resp.get('Last-Modified'))
        self.assertIsNotNone(resp.get('x-ms-blob-sequence-number'))
        props = blob.get_blob_properties()
        self.assertIsInstance(props, BlobProperties)
        self.assertEqual(props.content_length, 512)

    @record
    def test_set_sequence_number_blob(self):
        # Arrange
        blob = self._create_blob()
        
        # Act
        resp = blob.set_sequence_number(SequenceNumberAction.Update, 6)     

        #Assert
        self.assertIsNotNone(resp.get('ETag'))
        self.assertIsNotNone(resp.get('Last-Modified'))
        self.assertIsNotNone(resp.get('x-ms-blob-sequence-number'))
        props = blob.get_blob_properties()
        self.assertIsInstance(props, BlobProperties)
        self.assertEqual(props.page_blob_sequence_number, 6)

    def test_create_blob_from_bytes(self):
        # parallel tests introduce random order of requests, can only run live
        if TestMode.need_recording_file(self.test_mode):
            return

        # Arrange
        blob = self._get_blob_reference()
        data = self.get_random_bytes(LARGE_BLOB_SIZE)

        # Act
        create_resp = blob.upload_blob(data)
        props = blob.get_blob_properties()

        # Assert
        self.assertBlobEqual(self.container_name, blob.name, data)
        self.assertEqual(props.etag, create_resp.get('ETag'))
        self.assertEqual(props.last_modified, create_resp.get('Last-Modified'))

    def test_create_blob_from_0_bytes(self):
        # parallel tests introduce random order of requests, can only run live
        if TestMode.need_recording_file(self.test_mode):
            return

        # Arrange
        blob = self._get_blob_reference()
        data = self.get_random_bytes(0)

        # Act
        create_resp = blob.upload_blob(data)
        props = blob.get_blob_properties()

        # Assert
        self.assertBlobEqual(self.container_name, blob.name, data)
        self.assertEqual(props.etag, create_resp.get('ETag'))
        self.assertEqual(props.last_modified, create_resp.get('Last-Modified'))

    def test_create_blob_from_bytes_with_progress(self):
        # parallel tests introduce random order of requests, can only run live
        if TestMode.need_recording_file(self.test_mode):
            return

        # Arrange
        blob = self._get_blob_reference()
        data = self.get_random_bytes(LARGE_BLOB_SIZE)

        # Act
        progress = []

        # TODO
        #def callback(current, total):
        #    progress.append((current, total))

        create_resp = blob.upload_blob(data)
        props = blob.get_blob_properties()

        # Assert
        self.assertBlobEqual(self.container_name, blob.name, data)
        self.assertEqual(props.etag, create_resp.get('ETag'))
        self.assertEqual(props.last_modified, create_resp.get('Last-Modified'))

    def test_create_blob_from_bytes_with_index(self):
        # parallel tests introduce random order of requests, can only run live
        if TestMode.need_recording_file(self.test_mode):
            return

        # Arrange
        blob = self._get_blob_reference()
        data = self.get_random_bytes(LARGE_BLOB_SIZE)
        index = 1024

        # Act
        blob.upload_blob(data[index:])

        # Assert
        self.assertBlobEqual(self.container_name, blob.name, data[1024:])

    @record
    def test_create_blob_from_bytes_with_index_and_count(self):
        # Arrange
        blob = self._get_blob_reference()
        data = self.get_random_bytes(LARGE_BLOB_SIZE)
        index = 512
        count = 1024

        # Act
        create_resp = blob.upload_blob(data[index:], length=count)
        props = blob.get_blob_properties()

        # Assert
        self.assertBlobEqual(self.container_name, blob.name, data[index:index + count])
        self.assertEqual(props.etag, create_resp.get('ETag'))
        self.assertEqual(props.last_modified, create_resp.get('Last-Modified'))

    def test_create_blob_from_path(self):
        # parallel tests introduce random order of requests, can only run live
        if TestMode.need_recording_file(self.test_mode):
            return

        # Arrange        
        blob = self._get_blob_reference()
        data = self.get_random_bytes(LARGE_BLOB_SIZE)
        FILE_PATH = 'blob_input.temp.dat'
        with open(FILE_PATH, 'wb') as stream:
            stream.write(data)

        # Act
        with open(FILE_PATH, 'rb') as stream:
            create_resp = blob.upload_blob(stream)
        props = blob.get_blob_properties()

        # Assert
        self.assertBlobEqual(self.container_name, blob.name, data)
        self.assertEqual(props.etag, create_resp.get('ETag'))
        self.assertEqual(props.last_modified, create_resp.get('Last-Modified'))

    def test_create_blob_from_path_with_progress(self):
        # parallel tests introduce random order of requests, can only run live
        if TestMode.need_recording_file(self.test_mode):
            return

        # Arrange        
        blob = self._get_blob_reference()
        data = self.get_random_bytes(LARGE_BLOB_SIZE)
        with open(FILE_PATH, 'wb') as stream:
            stream.write(data)

        # Act
        progress = []  # TODO Upload progress

        def callback(current, total):
            progress.append((current, total))

        with open(FILE_PATH, 'rb') as stream:
            blob.upload_blob(stream)

        # Assert
        self.assertBlobEqual(self.container_name, blob.name, data)
        #self.assert_upload_progress(len(data), self.config.blob_settings.max_page_size, progress)

    def test_create_blob_from_stream(self):
        # parallel tests introduce random order of requests, can only run live
        if TestMode.need_recording_file(self.test_mode):
            return

        # Arrange        
        blob = self._get_blob_reference()
        data = self.get_random_bytes(LARGE_BLOB_SIZE)
        with open(FILE_PATH, 'wb') as stream:
            stream.write(data)

        # Act
        blob_size = len(data)
        with open(FILE_PATH, 'rb') as stream:
            create_resp = blob.upload_blob(stream, length=blob_size)
        props = blob.get_blob_properties()

        # Assert
        self.assertBlobEqual(self.container_name, blob.name, data[:blob_size])
        self.assertEqual(props.etag, create_resp.get('ETag'))
        self.assertEqual(props.last_modified, create_resp.get('Last-Modified'))

    def test_create_blob_from_stream_with_empty_pages(self):
        # parallel tests introduce random order of requests, can only run live
        if TestMode.need_recording_file(self.test_mode):
            return

        # Arrange
        # data is almost all empty (0s) except two ranges
        blob = self._get_blob_reference()
        data = bytearray(LARGE_BLOB_SIZE)
        data[512: 1024] = self.get_random_bytes(512)
        data[8192: 8196] = self.get_random_bytes(4)
        with open(FILE_PATH, 'wb') as stream:
            stream.write(data)

        # Act
        blob_size = len(data)
        with open(FILE_PATH, 'rb') as stream:
            create_resp = blob.upload_blob(stream, length=blob_size)
        props = blob.get_blob_properties()

        # Assert
        # the uploader should have skipped the empty ranges
        self.assertBlobEqual(self.container_name, blob.name, data[:blob_size])
        page_ranges, cleared = list(blob.get_page_ranges())
        self.assertEqual(len(page_ranges), 2)
        self.assertEqual(page_ranges[0]['start'], 0)
        self.assertEqual(page_ranges[0]['end'], 4095)
        self.assertEqual(page_ranges[1]['start'], 8192)
        self.assertEqual(page_ranges[1]['end'], 12287)
        self.assertEqual(props.etag, create_resp.get('ETag'))
        self.assertEqual(props.last_modified, create_resp.get('Last-Modified'))

    def test_create_blob_from_stream_non_seekable(self):
        # parallel tests introduce random order of requests, can only run live
        if TestMode.need_recording_file(self.test_mode):
            return

        # Arrange      
        blob = self._get_blob_reference()
        data = self.get_random_bytes(LARGE_BLOB_SIZE)
        with open(FILE_PATH, 'wb') as stream:
            stream.write(data)

        # Act
        blob_size = len(data)
        with open(FILE_PATH, 'rb') as stream:
            non_seekable_file = StoragePageBlobTest.NonSeekableFile(stream)
            blob.upload_blob(non_seekable_file, length=blob_size, max_connections=1)

        # Assert
        self.assertBlobEqual(self.container_name, blob.name, data[:blob_size])

    def test_create_blob_from_stream_with_progress(self):
        # parallel tests introduce random order of requests, can only run live
        if TestMode.need_recording_file(self.test_mode):
            return

        # Arrange      
        blob = self._get_blob_reference()
        data = self.get_random_bytes(LARGE_BLOB_SIZE)
        with open(FILE_PATH, 'wb') as stream:
            stream.write(data)

        # Act
        progress = []  # TODO upload progress

        def callback(current, total):
            progress.append((current, total))

        blob_size = len(data)
        with open(FILE_PATH, 'rb') as stream:
            blob.upload_blob(stream, length=blob_size)

        # Assert
        self.assertBlobEqual(self.container_name, blob.name, data[:blob_size])
        #self.assert_upload_progress(len(data), self.config.blob_settings.max_page_size, progress)

    def test_create_blob_from_stream_truncated(self):
        # parallel tests introduce random order of requests, can only run live
        if TestMode.need_recording_file(self.test_mode):
            return

        # Arrange       
        blob = self._get_blob_reference()
        data = self.get_random_bytes(LARGE_BLOB_SIZE)
        with open(FILE_PATH, 'wb') as stream:
            stream.write(data)

        # Act
        blob_size = len(data) - 512
        with open(FILE_PATH, 'rb') as stream:
            blob.upload_blob(stream, blob_size)

        # Assert
        self.assertBlobEqual(self.container_name, blob.name, data[:blob_size])

    def test_create_blob_from_stream_with_progress_truncated(self):
        # parallel tests introduce random order of requests, can only run live
        if TestMode.need_recording_file(self.test_mode):
            return

        # Arrange       
        blob = self._get_blob_reference()
        data = self.get_random_bytes(LARGE_BLOB_SIZE)
        with open(FILE_PATH, 'wb') as stream:
            stream.write(data)

        # Act
        progress = []  # TODO support upload progress

        def callback(current, total):
            progress.append((current, total))

        blob_size = len(data) - 512
        with open(FILE_PATH, 'rb') as stream:
            blob.upload_blob(stream, blob_size)  #, progress_callback=callback)

        # Assert
        self.assertBlobEqual(self.container_name, blob.name, data[:blob_size])
        #self.assert_upload_progress(blob_size, self.config.blob_settings.max_page_size, progress)

    @record
    def test_create_blob_with_md5_small(self):
        # Arrange
        blob = self._get_blob_reference()
        data = self.get_random_bytes(512)

        # Act
        blob.upload_blob(data, validate_content=True)

        # Assert

    def test_create_blob_with_md5_large(self):
        # parallel tests introduce random order of requests, can only run live
        if TestMode.need_recording_file(self.test_mode):
            return

        # Arrange
        blob = self._get_blob_reference()
        data = self.get_random_bytes(LARGE_BLOB_SIZE)

        # Act
        blob.upload_blob(data, validate_content=True)

        # Assert

    def test_incremental_copy_blob(self):
        # parallel tests introduce random order of requests, can only run live
        if TestMode.need_recording_file(self.test_mode):
            return

        # Arrange
        source_blob = self._create_blob(2048)
        data = self.get_random_bytes(512)
        resp1 = source_blob.upload_page(data, 0, 511)
        resp2 = source_blob.upload_page(data, 1024, 1535)
        source_snapshot_blob = source_blob.create_snapshot()

        snapshot_blob = self.bs.get_blob_client(self.container_name, source_snapshot_blob)
        sas_token = snapshot_blob.generate_shared_access_signature(
            permission=BlobPermissions.READ,
            expiry=datetime.utcnow() + timedelta(hours=1),
        )
        print("SAS token: ", sas_token)


        # Act
        snapshot_blob_url = snapshot_blob.make_url(sas_token=sas_token)
        print("Snapshot URL: ", snapshot_blob_url)

        dest_blob = self.bs.get_blob_client(self.container_name, 'dest_blob')
        copy = dest_blob.copy_blob_from_url(snapshot_blob_url, incremental_copy=True)

        # Assert
        self.assertIsNotNone(copy)
        self.assertIsNotNone(copy.copy_id())
        self.assertEqual(copy.status(), 'pending')
        copy.wait()

        copy_blob = dest_blob.get_blob_properties()
        self.assertEqual(copy_blob.copy.status, 'success')
        self.assertIsNotNone(copy_blob.copy.destination_snapshot)

        # strip off protocol
        self.assertTrue(copy_blob.copy.source.endswith(snapshot_blob_url[5:]))

    @record
    def test_blob_tier_on_create(self):
        url = self._get_premium_account_url()
        credentials = SharedKeyCredentials(*self._get_premium_shared_key_credentials())
        pbs = BlobServiceClient(url, credentials=credentials)

        try:
            container_name = self.get_resource_name('utpremiumcontainer')
            container = pbs.get_container_client(container_name)
            if not self.is_playback():
                container.create_container()

            # test create_blob API
            blob = self._get_blob_reference()
            pblob = pbs.get_blob_client(container_name, blob.name, blob_type=BlobType.PageBlob)
            pblob.create_blob(1024, premium_page_blob_tier=PremiumPageBlobTier.P4)

            props = pblob.get_blob_properties()
            self.assertEqual(props.blob_tier, PremiumPageBlobTier.P4)
            self.assertFalse(props.blob_tier_inferred)

            # test create_blob_from_bytes API
            blob2 = self._get_blob_reference()
            pblob2 = pbs.get_blob_client(container_name, blob2.name, blob_type=BlobType.PageBlob)
            byte_data = self.get_random_bytes(1024)
            pblob2.upload_blob(byte_data, premium_page_blob_tier=PremiumPageBlobTier.P6)

            props2 = pblob2.get_blob_properties()
            self.assertEqual(props2.blob_tier, PremiumPageBlobTier.P6)
            self.assertFalse(props2.blob_tier_inferred)

            # test create_blob_from_path API
            blob3 = self._get_blob_reference()
            pblob3 = pbs.get_blob_client(container_name, blob3.name, blob_type=BlobType.PageBlob)
            with open(FILE_PATH, 'wb') as stream:
                stream.write(byte_data)
            with open(FILE_PATH, 'rb') as stream:
                pblob3.upload_blob(stream, premium_page_blob_tier=PremiumPageBlobTier.P10)

            props3 = pblob3.get_blob_properties()
            self.assertEqual(props3.blob_tier, PremiumPageBlobTier.P10)
            self.assertFalse(props3.blob_tier_inferred)

        finally:
            container.delete_container()

    @record
    def test_blob_tier_set_tier_api(self):
        url = self._get_premium_account_url()
        credentials = SharedKeyCredentials(*self._get_premium_shared_key_credentials())
        pbs = BlobServiceClient(url, credentials=credentials)

        try:
            container_name = self.get_resource_name('utpremiumcontainer')
            container = pbs.get_container_client(container_name)

            if not self.is_playback():
                try:
                    container.create_container()
                except HttpResponseError as error:
                    if error.error_code == 'ContainerAlreadyExists':
                        pass
                    else:
                        raise

            blob = self._get_blob_reference()
            pblob = pbs.get_blob_client(container_name, blob.name, blob_type=BlobType.PageBlob)
            pblob.create_blob(1024)
            blob_ref = pblob.get_blob_properties()
            self.assertEqual(PremiumPageBlobTier.P10, blob_ref.blob_tier)
            self.assertIsNotNone(blob_ref.blob_tier)
            self.assertTrue(blob_ref.blob_tier_inferred)

            pcontainer = pbs.get_container_client(container_name)
            blobs = list(pcontainer.list_blob_properties())

            # Assert
            self.assertIsNotNone(blobs)
            self.assertGreaterEqual(len(blobs), 1)
            self.assertIsNotNone(blobs[0])
            self.assertNamedItemInContainer(blobs, blob.name)

            pblob.set_premium_page_blob_tier(PremiumPageBlobTier.P50)

            blob_ref2 = pblob.get_blob_properties()
            self.assertEqual(PremiumPageBlobTier.P50, blob_ref2.blob_tier)
            self.assertFalse(blob_ref2.blob_tier_inferred)

            blobs = list(pcontainer.list_blob_properties())

            # Assert
            self.assertIsNotNone(blobs)
            self.assertGreaterEqual(len(blobs), 1)
            self.assertIsNotNone(blobs[0])
            self.assertNamedItemInContainer(blobs, blob.name)
            self.assertEqual(blobs[0].blob_tier, PremiumPageBlobTier.P50)
            self.assertFalse(blobs[0].blob_tier_inferred)
        finally:
            container.delete_container()

    @record
    def test_blob_tier_copy_blob(self):
        url = self._get_premium_account_url()
        credentials = SharedKeyCredentials(*self._get_premium_shared_key_credentials())
        pbs = BlobServiceClient(url, credentials=credentials)

        try:
            container_name = self.get_resource_name('utpremiumcontainer')
            container = pbs.get_container_client(container_name)

            if not self.is_playback():
                try:
                    container.create_container()
                except HttpResponseError as error:
                    if error.error_code == 'ContainerAlreadyExists':
                        pass
                    else:
                        raise

            # Arrange
            source_blob = pbs.get_blob_client(
                container_name,
                self.get_resource_name(TEST_BLOB_PREFIX),
                blob_type=BlobType.PageBlob)
            source_blob.create_blob(1024, premium_page_blob_tier=PremiumPageBlobTier.P10)

            # Act
            source_blob_url = '/{0}/{1}/{2}'.format(self.settings.PREMIUM_STORAGE_ACCOUNT_NAME,
                                               container_name,
                                               source_blob.name)

            copy_blob = pbs.get_blob_client(container_name, 'blob1copy')
            copy = copy_blob.copy_blob_from_url(source_blob_url, premium_page_blob_tier=PremiumPageBlobTier.P30)

            # Assert
            self.assertIsNotNone(copy)
            self.assertEqual(copy.status(), 'success')
            self.assertIsNotNone(copy.copy_id())

            copy_ref = copy_blob.get_blob_properties()
            self.assertEqual(copy_ref.blob_tier, PremiumPageBlobTier.P30)

            source_blob2 = pbs.get_blob_client(
               container_name,
               self.get_resource_name(TEST_BLOB_PREFIX),
               blob_type=BlobType.PageBlob)

            source_blob2.create_blob(1024)
            source_blob2_url = '/{0}/{1}/{2}'.format(
                self.settings.PREMIUM_STORAGE_ACCOUNT_NAME, source_blob2.container, source_blob2.name)

            copy_blob2 = pbs.get_blob_client(container_name, 'blob2copy', blob_type=BlobType.PageBlob)
            copy2 = copy_blob2.copy_blob_from_url(source_blob2_url, premium_page_blob_tier=PremiumPageBlobTier.P60)
            self.assertIsNotNone(copy2)
            self.assertEqual(copy2.status(), 'success')
            self.assertIsNotNone(copy2.copy_id())

            copy_ref2 = copy_blob2.get_blob_properties()
            self.assertEqual(copy_ref2.blob_tier, PremiumPageBlobTier.P60)
            self.assertFalse(copy_ref2.blob_tier_inferred)

            copy_blob3 = pbs.get_blob_client(container_name, 'blob3copy', blob_type=BlobType.PageBlob)
            copy3 = copy_blob3.copy_blob_from_url(source_blob2_url)
            self.assertIsNotNone(copy3)
            self.assertEqual(copy3.status(), 'success')
            self.assertIsNotNone(copy3.copy_id())

            copy_ref3 = copy_blob3.get_blob_properties()
            self.assertEqual(copy_ref3.blob_tier, PremiumPageBlobTier.P10)
            self.assertTrue(copy_ref3.blob_tier_inferred)
        finally:
            container.delete_container()

#------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()
