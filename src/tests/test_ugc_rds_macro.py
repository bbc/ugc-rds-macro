import datetime
import fnmatch
import json
import os
import time
import uuid
from io import StringIO

import py
import pytest
from botocore.stub import Stubber
from pytest_mock import mocker

from datetime import datetime, timedelta, timezone

import lambdas.ugc_rds_macro
from lambdas.ugc_rds_macro import (_add_snapshot_identifier, _remove_property,
                                   add_tag,
                                   check_if_point_in_time_date_is_valid,
                                   get_instance_state, get_snapshot_identifier,
                                   get_tagged_db_instance,
                                   get_ugc_database_template, handler,
                                   get_back_retention_period,
                                   parse_db_identifier, remove_tag)

_dir = os.path.dirname(os.path.realpath(__file__))
FIXTURE_DIR = py.path.local(_dir) / 'test_files'


class TestContext:
    invoked_function_arn = "arn:aws:lambda:eu-west-2:546933502184:function:int-ugc-rds-macro"


test_context = TestContext()

# Disable test for get_template:
# issue has been raise on git: https://github.com/boto/botocore/issues/1911
lambdas.ugc_rds_macro.do_not_ignore_get_template = False

lambdas.ugc_rds_macro.point_in_time_db_instance_tag


def _read_test_data(datafiles, expected_file, orig_template):
    for testFile in datafiles.listdir():
        if fnmatch.fnmatch(testFile, "*"+expected_file):
            expected = json.loads(testFile.read_text(encoding="'utf-8'"))

        if fnmatch.fnmatch(testFile, "*"+orig_template):
            db_instance_template = json.loads(
                testFile.read_text(encoding="'utf-8'"))

    return (expected, db_instance_template)


def _add_list_tag_response(lambda_stub):
    list_tag_response = {
        "Tags": {
            "aws:cloudformation:logical-id": "RdsSnapShotLambdaFunction",
            "aws:cloudformation:stack-id": "arn:aws:cloudformation:eu-west-2:546933502184:stack/ugc-rds-db-macro/ef020480-19c5-11ea-9f4f-0617023ccf6e",
        }
    }

    lambda_stub.add_response(
        "list_tags",
        expected_params={'Resource': lambdas.ugc_rds_macro.lambda_arn},
        service_response=list_tag_response
    )


def _add_describe_db_instance_response(rds_stub, datafiles, id, state):
    for testFile in datafiles.listdir():
        if fnmatch.fnmatch(testFile, "*db_describe_instance_response.json"):
            desc_db_inst_response = json.loads(
                testFile.read_text(encoding="'utf-8'"))

    if id:
        for val in desc_db_inst_response['DBInstances']:
            if str(val['DBInstanceIdentifier']) in "dv-ugc-postgres":
                db = {'DBInstanceIdentifier': id}
                val.update(db)
                state = {'DBInstanceStatus': state}
                val.update(state)

    rds_stub.add_response(
        'describe_db_instances',
        service_response=desc_db_inst_response
    )


def _add_tag_resource_response(lambda_stub, id):
    response = {'ResponseMetadata':
                {'RequestId': 'c48d99c2-704b-4d51-adc1-93d64eb60f2c',
                 'HTTPStatusCode': 204,
                 'HTTPHeaders': {'date': 'Sat, 14 Dec 2019 18:14:20 GMT',
                                 'content-type': 'application/json',
                                 'connection': 'keep-alive',
                                 'x-amzn-requestid': 'c48d99c2-704b-4d51-adc1-93d64eb60f2c'},
                 'RetryAttempts': 0
                 }
                }

    lambda_stub.add_response(
        "tag_resource",
        expected_params={'Resource': lambdas.ugc_rds_macro.lambda_arn,
                         'Tags': {lambdas.ugc_rds_macro.point_in_time_db_instance_tag: id}},
        service_response=response
    )


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_instance_template_with_backup_retention_property_removed.json',
)
def test_handler_remove_property(monkeypatch, datafiles):

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template_with_backup_retention_property_removed.json",
                                                       "db_instance_template.json")

    monkeypatch.setenv("replace_snapshot", "False")
    monkeypatch.setenv("snapshot_id", "")
    monkeypatch.setenv("properties_to_remove", "BackupRetentionPeriod")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv(" rds_snapshot_stack_name", "")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "")

    i = {'stackname': 'one-rds-db-stack'}
    f = {'fragment': db_instance_template,
         'requestId': 'my_request_id', 'params': i}

    res = handler(f, test_context)

    assert res['requestId'] == 'my_request_id'
    assert res['fragment'] == expected


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_instance_template_with_multiple_props_removed.json',
)
def test_handler_remove_multiple_properties(monkeypatch, datafiles):

    monkeypatch.setenv("replace_snapshot", "False")
    monkeypatch.setenv("snapshot_id", "")
    monkeypatch.setenv("properties_to_remove", "DBInstanceIdentifier, DBName")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv(" rds_snapshot_stack_name", "")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "")

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template_with_multiple_props_removed.json",
                                                       "db_instance_template.json")

    i = {'stackname': 'one-rds-db-stack'}
    f = {'fragment': db_instance_template,
         'requestId': 'my_request_id', 'params': i}

    res = handler(f, test_context)

    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_instance_template_with_property_added.json',
)
def test_handler_add_property(monkeypatch, datafiles):
    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("replace_snapshot", "False")
    monkeypatch.setenv("snapshot_id", "")
    monkeypatch.setenv(
        "properties_to_add", '{"BackupRetentionPeriod": {"Ref": "BackupRetentionDays"}}')
    monkeypatch.setenv(" rds_snapshot_stack_name", "")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "")

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template_with_property_added.json",
                                                       "db_instance_template.json")

    i = {'stackname': 'one-rds-db-stack'}
    f = {'fragment': db_instance_template,
         'requestId': 'my_request_id', 'params': i}

    res = handler(f, test_context)
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template_props_removed.json',
    FIXTURE_DIR / 'db_instance_template_with_multiple_props_added.json',
)
def test_handler_add_multiple_properties(monkeypatch, datafiles):
    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("replace_snapshot", "false")
    monkeypatch.setenv("snapshot_id", "")
    monkeypatch.setenv(
        "properties_to_add", '{"BackupRetentionPeriod": {"Ref": "BackupRetentionDays"}},{"DBName": { "Ref": "DatabaseName"}}')
    monkeypatch.setenv(" rds_snapshot_stack_name", "arn")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "")

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template_with_multiple_props_added.json",
                                                       "db_instance_template_props_removed.json")

    i = {'stackname': 'one-rds-db-stack'}
    f = {'fragment': db_instance_template,
         'requestId': 'my_request_id', 'params': i}

    res = handler(f, test_context)
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_instance_template_with_snapshot_specified.json',
    FIXTURE_DIR / 'db_describe_instance_response.json'
)
def test_snapshot_identifer(rds_stub, monkeypatch, datafiles):

    monkeypatch.setenv("properties_to_remove", "BackupRetentionPeriod")
    monkeypatch.setenv("replace_snapshot", "true")
    monkeypatch.setenv("snapshot_id", "")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv(" rds_snapshot_stack_name", "mv-rds-db-stack")
    monkeypatch.setenv("snapshot_type", " ")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "")

    _add_describe_db_instance_response(rds_stub,  datafiles, None, None)

    response = {'DBSnapshots': [{'DBSnapshotIdentifier': 'rds:mv-ugc-postgres-2019-12-06-11-10', 'DBInstanceIdentifier': 'mv-ugc-postgres', 'SnapshotCreateTime': datetime(2019, 12, 6, 11, 10, 33, 790000), 'Engine': 'postgres', 'AllocatedStorage': 20, 'Status': 'available', 'Port': 5432, 'AvailabilityZone': 'eu-west-2b', 'VpcId': 'vpc-19483f70', 'InstanceCreateTime': datetime(2019, 12, 6, 11, 9, 28, 424000), 'MasterUsername': 'ugc', 'EngineVersion': '9.6.15', 'LicenseModel': 'postgresql-license', 'SnapshotType': 'automated', 'OptionGroupName': 'default:postgres-9-6', 'PercentProgress': 100, 'StorageType': 'standard',
                                 'Encrypted': True, 'KmsKeyId': 'arn:aws:kms:eu-west-2:546933502184:key/83f283d1-7b58-4827-854c-db776149795f', 'DBSnapshotArn': 'arn:aws:rds:eu-west-2:546933502184:snapshot:rds:mv-ugc-postgres-2019-12-06-11-10', 'IAMDatabaseAuthenticationEnabled': False, 'ProcessorFeatures': [], 'DbiResourceId': 'db-CQ76MXOJJIFBOQ7WT63Y6AXUKA'}], 'ResponseMetadata': {'RequestId': '8290e734-5717-4c94-9ed5-1eaf0aa20ec6', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': '8290e734-5717-4c94-9ed5-1eaf0aa20ec6', 'content-type': 'text/xml', 'content-length': '1687', 'date': 'Fri, 06 Dec 2019 15:02:09 GMT'}, 'RetryAttempts': 0}}
    rds_stub.add_response(
        'describe_db_snapshots',
        expected_params={'DBInstanceIdentifier': 'mr1qf4ez7ls7xfn'},
        service_response=response
    )

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template_with_snapshot_specified.json",
                                                       "db_instance_template.json")
    i = {'stackname': 'one-rds-db-stack'}
    f = {'fragment': db_instance_template,
         'requestId': 'my_request_id', 'params': i}

    res = handler(f, test_context)
    assert res['requestId'] == "my_request_id"
    print("frag={0}".format(res['fragment']))
    assert res['fragment'] == expected


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_instance_template_with_snapshot_specified.json',
    FIXTURE_DIR / 'db_describe_instance_response.json'
)
def test_snapshot_identifer_with_snapshot_type(rds_stub, monkeypatch, datafiles):

    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("replace_snapshot", "true")
    monkeypatch.setenv("snapshot_id", "")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv(" rds_snapshot_stack_name", "mv-rds-db-stack")
    monkeypatch.setenv("snapshot_type", "shared")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "")

    _add_describe_db_instance_response(rds_stub,  datafiles, None, None)

    response = {'DBSnapshots': [{'DBSnapshotIdentifier': 'rds:mv-ugc-postgres-2019-12-06-11-10', 'DBInstanceIdentifier': 'mv-ugc-postgres', 'SnapshotCreateTime': datetime(2019, 12, 6, 11, 10, 33, 790000), 'Engine': 'postgres', 'AllocatedStorage': 20, 'Status': 'available', 'Port': 5432, 'AvailabilityZone': 'eu-west-2b', 'VpcId': 'vpc-19483f70', 'InstanceCreateTime': datetime(2019, 12, 6, 11, 9, 28, 424000), 'MasterUsername': 'ugc', 'EngineVersion': '9.6.15', 'LicenseModel': 'postgresql-license', 'SnapshotType': 'automated', 'OptionGroupName': 'default:postgres-9-6', 'PercentProgress': 100, 'StorageType': 'standard',
                                 'Encrypted': True, 'KmsKeyId': 'arn:aws:kms:eu-west-2:546933502184:key/83f283d1-7b58-4827-854c-db776149795f', 'DBSnapshotArn': 'arn:aws:rds:eu-west-2:546933502184:snapshot:rds:mv-ugc-postgres-2019-12-06-11-10', 'IAMDatabaseAuthenticationEnabled': False, 'ProcessorFeatures': [], 'DbiResourceId': 'db-CQ76MXOJJIFBOQ7WT63Y6AXUKA'}], 'ResponseMetadata': {'RequestId': '8290e734-5717-4c94-9ed5-1eaf0aa20ec6', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': '8290e734-5717-4c94-9ed5-1eaf0aa20ec6', 'content-type': 'text/xml', 'content-length': '1687', 'date': 'Fri, 06 Dec 2019 15:02:09 GMT'}, 'RetryAttempts': 0}}
    rds_stub.add_response(
        'describe_db_snapshots',
        expected_params={'DBInstanceIdentifier': 'mr1qf4ez7ls7xfn',
                         'SnapshotType': 'shared'},
        service_response=response
    )

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template_with_snapshot_specified.json",
                                                       "db_instance_template.json")

    i = {'stackname': 'one-rds-db-stack'}
    f = {'fragment': expected, 'requestId': 'my_request_id', 'params': i}

    res = handler(f, test_context)
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected

@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_describe_instance_response.json'
)
def test_snapshot_identifer_with_invalid_snapshot_type(rds_stub, monkeypatch, datafiles):

    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("replace_snapshot", "true")
    monkeypatch.setenv("snapshot_id", "")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv(" rds_snapshot_stack_name", "mv-rds-db-stack")
    monkeypatch.setenv("snapshot_type", "invalid_snapshot_type")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "")

    _add_describe_db_instance_response(rds_stub,  datafiles, None, None)

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template.json",
                                                       "db_instance_template.json")

    i = {'stackname': 'one-rds-db-stack'}
    f = {'fragment': expected, 'requestId': 'my_request_id', 'params': i}

    res = handler(f, test_context)
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected

@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_instance_template_with_supplied_snapshot_identifier.json',
    FIXTURE_DIR / 'db_describe_instance_response.json'
)
def test_snapshot_with_supplied_identifier(rds_stub, monkeypatch, datafiles):

    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("replace_snapshot", "true")
    monkeypatch.setenv("snapshot_id", "snaphost_id")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv(" rds_snapshot_stack_name", "mv-rds-db-stack")
    monkeypatch.setenv("snapshot_type", "shared")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "")

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template_with_supplied_snapshot_identifier.json",
                                                       "db_instance_template.json")

    i = {'stackname': 'one-rds-db-stack'}
    f = {'fragment': expected, 'requestId': 'my_request_id', 'params': i}

    res = handler(f, test_context)
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_restore_to_point_in_time.json',
    FIXTURE_DIR / 'db_describe_instance_response.json'
)
def test_point_in_time_create_snap_shot(mocker, monkeypatch, lambda_stub, rds_stub, datafiles):
    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("replace_snapshot", "false")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv(" rds_snapshot_stack_name", "mv-rds-db-stack")
    monkeypatch.setenv("snapshot_type", "shared")
    monkeypatch.setenv("restore_time", "2018-07-30T23:45:00.000Z")
    monkeypatch.setenv("restore_point_in_time", "true")

    test_snapshot_id = uuid.uuid4()
    target_db_instance_id = "tdi{0}".format(str(test_snapshot_id))
    mocker.patch.object(uuid, 'uuid4', return_value=test_snapshot_id)
    _add_describe_db_instance_response(
        rds_stub,  datafiles, target_db_instance_id, "Available")
    create_db_response = {
        "DBSnapshot": {
            "DBSnapshotIdentifier": target_db_instance_id,
            "DBInstanceIdentifier": "five-ugc-postgres",
            "Engine": "postgres",
            "AllocatedStorage": 20,
            "Status": "creating",
            "Port": 5432,
            "AvailabilityZone": "eu-west-2a",
            "VpcId": "vpc-19483f70",
            "InstanceCreateTime": "2019-12-09T14:31:25.541Z",
            "MasterUsername": "ugc",
            "EngineVersion": "9.6.15",
            "LicenseModel": "postgresql-license",
            "SnapshotType": "manual",
            "OptionGroupName": "default:postgres-9-6",
            "PercentProgress": 0,
            "StorageType": "standard",
            "Encrypted": True,
            "KmsKeyId": "arn:aws:kms:eu-west-2:546933502184:key/729df303-6521-4f52-8e09-b8156fc1265b",
            "DBSnapshotArn": "arn:aws:rds:eu-west-2:546933502184:snapshot:my-snapshot-1",
            "IAMDatabaseAuthenticationEnabled": False,
            "ProcessorFeatures": [],
            "DbiResourceId": "db-PSC7UU72SDEX7TDNFIKJNUCOVA"
        }
    }


    rds_stub.add_response(
        'create_db_snapshot',
          expected_params={'DBSnapshotIdentifier': "rsi{0}".format(str(test_snapshot_id)),
               'DBInstanceIdentifier': target_db_instance_id},
        service_response=create_db_response
    )
    list_tag_response = {
        "Tags": {
            "aws:cloudformation:logical-id": "RdsSnapShotLambdaFunction",
            "aws:cloudformation:stack-id": "arn:aws:cloudformation:eu-west-2:546933502184:stack/ugc-rds-db-macro/ef020480-19c5-11ea-9f4f-0617023ccf6e",
            lambdas.ugc_rds_macro.point_in_time_db_instance_tag: target_db_instance_id
        }
    }
    lambda_stub.add_response(
        "list_tags",
        expected_params={'Resource': lambdas.ugc_rds_macro.lambda_arn},
        service_response=list_tag_response
    )

    lambda_stub.add_response(
        "untag_resource",
        expected_params={'Resource': lambdas.ugc_rds_macro.lambda_arn, 'TagKeys': [
            'ugc:point-in-time:dbinstance']},
        service_response={}
    )

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_restore_to_point_in_time.json",
                                                       "db_instance_template.json")
    _remove_property(expected, "DBInstanceIdentifier")
    _remove_property(expected, "DBName")
    _add_snapshot_identifier(expected, "rsi{0}".format(str(test_snapshot_id)))

    i = {'stackname': 'dv-rds-database-stack'}
    f = {'fragment': db_instance_template,
         'requestId': 'my_request_id', 'params': i}

    res = handler(f, test_context)
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_restore_to_point_in_time.json',
    FIXTURE_DIR / 'db_describe_instance_response.json'
)
def test_point_in_time_restore_to_a_specific_time(rds_stub, lambda_stub, monkeypatch, datafiles, mocker):
    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("replace_snapshot", "false")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv(" rds_snapshot_stack_name", "mv-rds-db-stack")
    monkeypatch.setenv("snapshot_type", "shared")
    today = datetime.now(timezone.utc)
    restore_time = today - timedelta(days=1)
    monkeypatch.setenv("restore_time", str(restore_time))
    monkeypatch.setenv("restore_point_in_time", "true")

    test_snapshot_id = uuid.uuid4()
    mocker.patch.object(uuid, 'uuid4', return_value=test_snapshot_id)
    _add_list_tag_response(lambda_stub)
    _add_describe_db_instance_response(rds_stub,  datafiles, None, None)
    target_db_instance_id = "tdi{0}".format(str(test_snapshot_id))
    _add_tag_resource_response(lambda_stub, target_db_instance_id)

    response = {
        "DBInstance": {
            "AllocatedStorage": 20,
            "DBInstanceArn": "arn:aws:rds:us-east-1:123456789012:db:restored-test-instance",
            "DBInstanceStatus": "creating",
            "DBInstanceIdentifier": "restored-test-instance"
        }
    }
    rds_stub.add_response(
        'restore_db_instance_to_point_in_time',
        expected_params={'SourceDBInstanceIdentifier': 'dv-ugc-postgres',
                         'RestoreTime': str(restore_time),
                         'TargetDBInstanceIdentifier': target_db_instance_id},
        service_response=response
    )

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template.json",
                                                       "db_instance_template.json")

    i = {'stackname': 'dv-rds-database-stack'}
    f = {'fragment': db_instance_template,
         'requestId': 'my_request_id', 'params': i}

    res = handler(f, test_context)
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_describe_instance_response.json'
)
def test_point_in_time_restore_using_invalid_time(rds_stub, lambda_stub, monkeypatch, datafiles, mocker):
    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("replace_snapshot", "false")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv(" rds_snapshot_stack_name", "mv-rds-db-stack")
    monkeypatch.setenv("snapshot_type", "shared")
    monkeypatch.setenv("restore_time", "INVALID_DATE")
    monkeypatch.setenv("restore_point_in_time", "true")

    test_snapshot_id = uuid.uuid4()
    mocker.patch.object(uuid, 'uuid4', return_value=test_snapshot_id)
    _add_list_tag_response(lambda_stub)
    _add_describe_db_instance_response(rds_stub,  datafiles, None, None)

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template.json",
                                                       "db_instance_template.json")

    i = {'stackname': 'dv-rds-database-stack'}
    f = {'fragment': db_instance_template,
         'requestId': 'my_request_id', 'params': i}

    res = handler(f, test_context)
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_restore_to_point_in_time.json',
    FIXTURE_DIR / 'db_describe_instance_response.json'
)
def test_point_in_time_restore_latest_restorable_time(rds_stub, lambda_stub, cloudformation_stub, monkeypatch, datafiles, mocker):
    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("replace_snapshot", "false")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv(" rds_snapshot_stack_name", "mv-rds-db-stack")
    monkeypatch.setenv("snapshot_type", "shared")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "true")

    test_snapshot_id = uuid.uuid4()
    target_db_instance_id = "tdi{0}".format(str(test_snapshot_id))
    """
        Monkey patch gives the following error: TypeError: 'UUID' object is not callable
        monkeypatch.setattr(uuid, "uuid4", test_snapshot_id)
    """
    mocker.patch.object(uuid, 'uuid4', return_value=test_snapshot_id)
    _add_list_tag_response(lambda_stub)
    _add_describe_db_instance_response(rds_stub,  datafiles, None, None)
    _add_tag_resource_response(lambda_stub, target_db_instance_id)

    response = {
        "DBInstance": {
            "AllocatedStorage": 20,
            "DBInstanceArn": "arn:aws:rds:us-east-1:123456789012:db:restored-test-instance",
            "DBInstanceStatus": "creating",
            "DBInstanceIdentifier": "restored-test-instance"
        }
    }
    rds_stub.add_response(
        'restore_db_instance_to_point_in_time',
        expected_params={'SourceDBInstanceIdentifier': 'dv-ugc-postgres',
                         'TargetDBInstanceIdentifier': target_db_instance_id,
                         'UseLatestRestorableTime': True},
        service_response=response
    )

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template.json",
                                                       "db_instance_template.json")
    i = {'stackname': 'dv-rds-database-stack'}
    f = {'fragment': db_instance_template,
         'requestId': 'my_request_id', 'params': i}

    res = handler(f, test_context)
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_describe_instance_response.json'
)
def test_point_in_time_restore_when_instance_is_being_created(rds_stub, lambda_stub, cloudformation_stub, monkeypatch, datafiles, mocker):
    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("replace_snapshot", "false")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv(" rds_snapshot_stack_name", "mv-rds-db-stack")
    monkeypatch.setenv("snapshot_type", "shared")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "true")

    test_snapshot_id = uuid.uuid4()
    target_db_instance_id = "tdi{0}".format(str(test_snapshot_id))
    mocker.patch.object(uuid, 'uuid4', return_value=test_snapshot_id)
    _add_describe_db_instance_response(
        rds_stub,  datafiles, target_db_instance_id, "Creating")

    list_tag_response = {
        "Tags": {
            "aws:cloudformation:logical-id": "RdsSnapShotLambdaFunction",
            "aws:cloudformation:stack-id": "arn:aws:cloudformation:eu-west-2:546933502184:stack/ugc-rds-db-macro/ef020480-19c5-11ea-9f4f-0617023ccf6e",
            lambdas.ugc_rds_macro.point_in_time_db_instance_tag: target_db_instance_id
        }
    }
    lambda_stub.add_response(
        "list_tags",
        expected_params={'Resource': lambdas.ugc_rds_macro.lambda_arn},
        service_response=list_tag_response
    )

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template.json",
                                                       "db_instance_template.json")

    i = {'stackname': 'dv-rds-database-stack'}
    f = {'fragment': db_instance_template,
         'requestId': 'my_request_id', 'params': i}

    res = handler(f, test_context)
    print("exepect={0}".format(expected))
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_describe_instance_response.json'
)
def test_point_in_time_restore_when_instance_is_being_modified(rds_stub, lambda_stub, cloudformation_stub, monkeypatch, datafiles, mocker):
    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("replace_snapshot", "false")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv(" rds_snapshot_stack_name", "mv-rds-db-stack")
    monkeypatch.setenv("snapshot_type", "shared")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "true")

    test_snapshot_id = uuid.uuid4()
    target_db_instance_id = "tdi{0}".format(str(test_snapshot_id))
    mocker.patch.object(uuid, 'uuid4', return_value=test_snapshot_id)
    _add_describe_db_instance_response(
        rds_stub,  datafiles, target_db_instance_id, "Modifying")

    list_tag_response = {
        "Tags": {
            "aws:cloudformation:logical-id": "RdsSnapShotLambdaFunction",
            "aws:cloudformation:stack-id": "arn:aws:cloudformation:eu-west-2:546933502184:stack/ugc-rds-db-macro/ef020480-19c5-11ea-9f4f-0617023ccf6e",
            lambdas.ugc_rds_macro.point_in_time_db_instance_tag: target_db_instance_id
        }
    }
    lambda_stub.add_response(
        "list_tags",
        expected_params={'Resource': lambdas.ugc_rds_macro.lambda_arn},
        service_response=list_tag_response
    )

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template.json",
                                                       "db_instance_template.json")

    i = {'stackname': 'dv-rds-database-stack'}
    f = {'fragment': db_instance_template,
         'requestId': 'my_request_id', 'params': i}

    res = handler(f, test_context)
    print("exepect={0}".format(expected))
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_describe_instance_response.json',
)
def test_find_db_indentifier_using_stack_name(datafiles):

    for testFile in datafiles.listdir():
        if fnmatch.fnmatch(testFile, "*db_describe_instance_response.json"):
            response = json.loads(testFile.read_text(encoding="utf-8"))

    db_instance_id = parse_db_identifier(response, 'mv-rds-db-stack')
    assert db_instance_id == "mr1qf4ez7ls7xfn"


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
)
def test_get_snapshot_identier_when_it_does_not_exist(datafiles):
    for testFile in datafiles.listdir():
        if fnmatch.fnmatch(testFile, "*db_instance_template.json"):
            response = json.loads(testFile.read_text(encoding="utf-8"))

    res = get_snapshot_identifier(response)
    assert res == None


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template_with_snapshot_specified.json',
)
def test_get_snapshot_identier(datafiles):
    for testFile in datafiles.listdir():
        if fnmatch.fnmatch(testFile, "*db_instance_template_with_snapshot_specified.json"):
            response = json.loads(testFile.read_text(encoding="utf-8"))

    res = get_snapshot_identifier(response)
    assert res == "arn:aws:rds:eu-west-2:546933502184:snapshot:rds:mv-ugc-postgres-2019-12-06-11-10"


@pytest.mark.skip(reason="skiping because of issue with the boto3 stubber for get_template")
@pytest.mark.datafiles(
    FIXTURE_DIR / 'cloudformation_get_template_response.json',
    FIXTURE_DIR / 'ugc_database_stack_template.json'
)
def test_get_ugc_database_template(monkeypatch, cloudformation_stub, datafiles):

    monkeypatch.setenv(" rds_snapshot_stack_name", "mv-rds-db-stack")
    (response, db_instance_template) = _read_test_data(datafiles,
                                                       "cloudformation_get_template_response.json",
                                                       "ugc_database_stack_template.json")

    cloudformation_stub.add_response(
        'get_template',
        service_response=response
    )

    template = get_ugc_database_template()

    assert db_instance_template == template


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_describe_single_instance.json'
)
def test_get_instance_state(datafiles):
    instance_id = 'wingse'
    for testFile in datafiles.listdir():
        if fnmatch.fnmatch(testFile, "*db_describe_single_instance.json"):
            instances = json.loads(testFile.read_text(encoding="utf-8"))
    state = get_instance_state(instance_id, instances)
    assert state == 'available'


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_describe_single_instance.json'
)
def test_get_instance_state_when_instance_not_found(datafiles):
    instance_id = 'instance_id'
    for testFile in datafiles.listdir():
        if fnmatch.fnmatch(testFile, "*db_describe_single_instance.json"):
            instances = json.loads(testFile.read_text(encoding="utf-8"))

    state = get_instance_state(instance_id, instances)
    assert state == None

@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json'
)
def test_invalid_log_level(monkeypatch, datafiles):
    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("replace_snapshot", "false")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv(" rds_snapshot_stack_name", "mv-rds-db-stack")
    monkeypatch.setenv("snapshot_type", "shared")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "true")
    monkeypatch.setenv("log_level", "not_valid")

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template.json",
                                                       "db_instance_template.json")

    i = {'stackname': 'dv-rds-database-stack'}
    f = {'fragment': db_instance_template,
         'requestId': 'my_request_id', 'params': i}

    res = handler(f, test_context)
    print("exepect={0}".format(expected))
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected


def test_remove_tag(lambda_stub):
    lambda_stub.add_response(
        "untag_resource",
        expected_params={'Resource': lambdas.ugc_rds_macro.lambda_arn, 'TagKeys': [
            'ugc:point-in-time:dbinstance']},
        service_response={}
    )
    remove_tag()


def test_add_tag(lambda_stub):
    tag = 'tag'
    value = 'value'
    lambda_stub.add_response(
        "tag_resource",
        expected_params={
            'Resource': lambdas.ugc_rds_macro.lambda_arn, 'Tags': {tag: value}},
        service_response={}
    )

    add_tag(tag, value)


def test_get_tagged_db_instance(lambda_stub):
    response = {
        "Tags": {
            "aws:cloudformation:logical-id": "RdsSnapShotLambdaFunction",
            "aws:cloudformation:stack-id": "arn:aws:cloudformation:eu-west-2:546933502184:stack/ugc-rds-db-macro/ef020480-19c5-11ea-9f4f-0617023ccf6e",
            "aws:cloudformation:stack-name": "ugc-rds-db-macro",
            "ugc:point-in-time:dbinstance": "mr15xh2mg99mr07"
        }
    }
    lambda_stub.add_response(
        "list_tags",
        expected_params={'Resource': lambdas.ugc_rds_macro.lambda_arn},
        service_response=response
    )

    instance = get_tagged_db_instance()
    assert instance == "mr15xh2mg99mr07"


def test_get_tagged_db_instance_when_no_instance(lambda_stub):
    response = {
        "Tags": {
            "aws:cloudformation:logical-id": "RdsSnapShotLambdaFunction",
            "aws:cloudformation:stack-id": "arn:aws:cloudformation:eu-west-2:546933502184:stack/ugc-rds-db-macro/ef020480-19c5-11ea-9f4f-0617023ccf6e",
            "aws:cloudformation:stack-name": "ugc-rds-db-macro"
        }
    }
    lambda_stub.add_response(
        "list_tags",
        expected_params={'Resource': lambdas.ugc_rds_macro.lambda_arn},
        service_response=response
    )

    instance = get_tagged_db_instance()
    assert instance == None


def test_when_stack_name_is_not_supplied():

    i = {'nostackname': 'one-rds-db-stack'}
    f = {'fragment': 'test data',
         'requestId': 'my_request_id', 'params': i}

    with pytest.raises(Exception) as e:
        handler(f, test_context)
    assert str(e.value) == "stackname parameter was not defined in the macro"


def test_check_if_point_in_time_date_is_not_valid():
    today = datetime.now(timezone.utc)
    assert check_if_point_in_time_date_is_valid(str(today), 100) == False


def test_check_if_point_in_time_date_is_valid():
    today = datetime.now(timezone.utc)
    valid = today - timedelta(minutes=6)

    assert check_if_point_in_time_date_is_valid(str(valid), 100) == True


def test_check_if_point_in_time_date_is_valid_parse_error():
    assert check_if_point_in_time_date_is_valid(
        "20019-12-13T23:45:00Z", 10) == False


def test_check_if_point_in_time_date_is_valid_fails_for_days_less_than_retention_period():
    today = datetime.now(timezone.utc)
    valid = today - timedelta(days=31)
    assert check_if_point_in_time_date_is_valid(str(valid), 30) == False


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_describe_instance_response.json'
)
def test_get_back_retention_period(datafiles):

    for testFile in datafiles.listdir():
        if fnmatch.fnmatch(testFile, "*db_describe_instance_response.json"):
            response = json.loads(testFile.read_text(encoding="utf-8"))

    assert 100 == get_back_retention_period(response, "dv-ugc-postgres")

