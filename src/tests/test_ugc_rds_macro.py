import pytest
from botocore.stub import Stubber
import json
import datetime
from lambdas.ugc_rds_macro import handler, client, parse_db_identifier
import os
import py
import fnmatch

_dir = os.path.dirname(os.path.realpath(__file__))
FIXTURE_DIR = py.path.local(_dir) / 'test_files'


def _read_test_data(datafiles, expected_file, orig_template):
    for testFile in datafiles.listdir():
        if fnmatch.fnmatch(testFile, "*"+expected_file):
            expected = json.loads(testFile.read_text(encoding="'utf-8'"))

        if fnmatch.fnmatch(testFile, "*"+orig_template):
            db_instance_template = json.loads(
                testFile.read_text(encoding="'utf-8'"))

    return (expected, db_instance_template)


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_instance_template_with_backup_retention_property_removed.json',
)
def test_handler_remove_property(monkeypatch, datafiles):

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template_with_backup_retention_property_removed.json",
                                                       "db_instance_template.json")


    monkeypatch.setenv("latest_snapshot", "False")
    monkeypatch.setenv("properties_to_remove", "BackupRetentionPeriod")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv("rds_stack_name", "")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "")
    monkeypatch.setenv('target_db_instance', "target_instance")
    
    i = {'db_instance': 'instance_i'}
    f = {'fragment': db_instance_template,
         'requestId': 'my_request_id', 'params': i}

    res = handler(f, "hey")

    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_instance_template_with_multiple_props_removed.json',
)
def test_handler_remove_multiple_properties(monkeypatch, datafiles):

    monkeypatch.setenv("latest_snapshot", "False")
    monkeypatch.setenv("properties_to_remove", "DBInstanceIdentifier, DBName")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv("rds_stack_name", "")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "")
    monkeypatch.setenv('target_db_instance', "target_instance")

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template_with_multiple_props_removed.json",
                                                       "db_instance_template.json")

    i = {'db_instance': 'instance_i'}
    f = {'fragment': db_instance_template,
         'requestId': 'my_request_id', 'params': i}

    res = handler(f, "hey")

    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_instance_template_with_property_added.json',
)
def test_handler_add_property(monkeypatch, datafiles):
    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("latest_snapshot", "False")
    monkeypatch.setenv(
        "properties_to_add", '{"BackupRetentionPeriod": {"Ref": "BackupRetentionDays"}}')
    monkeypatch.setenv("rds_stack_name", "")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "")
    monkeypatch.setenv('target_db_instance', "target_instance")

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template_with_property_added.json",
                                                       "db_instance_template.json")

    i = {'db_instance': 'instance_i'}
    f = {'fragment': db_instance_template,
         'requestId': 'my_request_id', 'params': i}

    res = handler(f, "hey")
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_instance_template_with_multiple_props_added.json',
)
def test_handler_add_multiple_properties(monkeypatch, datafiles):
    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("latest_snapshot", "false")
    monkeypatch.setenv(
        "properties_to_add", '{"BackupRetentionPeriod": {"Ref": "BackupRetentionDays"}},{"DBName": { "Ref": "DatabaseName"}}')
    monkeypatch.setenv("rds_stack_name", "arn")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "")
    monkeypatch.setenv('target_db_instance', "target_instance")


    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template_with_multiple_props_added.json",
                                                       "db_instance_template.json")

    i = {'db_instance': 'instance_i'}
    f = {'fragment': db_instance_template,
         'requestId': 'my_request_id', 'params': i}

    res = handler(f, "hey")
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_instance_template_with_snapshot_specified.json',
    FIXTURE_DIR / 'db_describe_instance_response.json'
)
def test_snapshot_identifer(s3_stub, monkeypatch, datafiles):
    
    monkeypatch.setenv("properties_to_remove", "BackupRetentionPeriod")
    monkeypatch.setenv("latest_snapshot", "true")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv("rds_stack_name", "mv-rds-db-stack")
    monkeypatch.setenv("snapshot_type", " ")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "")
    monkeypatch.setenv('target_db_instance', "target_instance")

    for testFile in datafiles.listdir():
            if fnmatch.fnmatch(testFile, "*db_describe_instance_response.json"):
                desc_db_inst_response = json.loads(testFile.read_text(encoding="'utf-8'"))
        
    s3_stub.add_response(
            'describe_db_instances',
            service_response=desc_db_inst_response
    )
    
    response = {'DBSnapshots': [{'DBSnapshotIdentifier': 'rds:mv-ugc-postgres-2019-12-06-11-10', 'DBInstanceIdentifier': 'mv-ugc-postgres', 'SnapshotCreateTime': datetime.datetime(2019, 12, 6, 11, 10, 33, 790000), 'Engine': 'postgres', 'AllocatedStorage': 20, 'Status': 'available', 'Port': 5432, 'AvailabilityZone': 'eu-west-2b', 'VpcId': 'vpc-19483f70', 'InstanceCreateTime': datetime.datetime(2019, 12, 6, 11, 9, 28, 424000), 'MasterUsername': 'ugc', 'EngineVersion': '9.6.15', 'LicenseModel': 'postgresql-license', 'SnapshotType': 'automated', 'OptionGroupName': 'default:postgres-9-6', 'PercentProgress': 100, 'StorageType': 'standard',
                                 'Encrypted': True, 'KmsKeyId': 'arn:aws:kms:eu-west-2:546933502184:key/83f283d1-7b58-4827-854c-db776149795f', 'DBSnapshotArn': 'arn:aws:rds:eu-west-2:546933502184:snapshot:rds:mv-ugc-postgres-2019-12-06-11-10', 'IAMDatabaseAuthenticationEnabled': False, 'ProcessorFeatures': [], 'DbiResourceId': 'db-CQ76MXOJJIFBOQ7WT63Y6AXUKA'}], 'ResponseMetadata': {'RequestId': '8290e734-5717-4c94-9ed5-1eaf0aa20ec6', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': '8290e734-5717-4c94-9ed5-1eaf0aa20ec6', 'content-type': 'text/xml', 'content-length': '1687', 'date': 'Fri, 06 Dec 2019 15:02:09 GMT'}, 'RetryAttempts': 0}}
    s3_stub.add_response(
        'describe_db_snapshots',
        expected_params={'DBInstanceIdentifier': 'mr1qf4ez7ls7xfn'},
        service_response=response
    )

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template_with_snapshot_specified.json",
                                                       "db_instance_template.json")
    i = {'db_instance': 'instance_i'}
    f = {'fragment': db_instance_template,
         'requestId': 'my_request_id', 'params': i}

    res = handler(f, "hey")
    assert res['requestId'] == "my_request_id"
    print("frag={0}".format(res['fragment']))
    assert res['fragment'] == expected


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_instance_template_with_snapshot_specified.json',
    FIXTURE_DIR / 'db_describe_instance_response.json'
)
def test_snapshot_identifer_with_snapshot_type(s3_stub, monkeypatch, datafiles):

    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("latest_snapshot", "true")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv("rds_stack_name", "mv-rds-db-stack")
    monkeypatch.setenv("snapshot_type", "shared")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "")
    monkeypatch.setenv('target_db_instance', "target_instance")

    for testFile in datafiles.listdir():
            if fnmatch.fnmatch(testFile, "*db_describe_instance_response.json"):
                desc_db_inst_response = json.loads(testFile.read_text(encoding="'utf-8'"))
        
    s3_stub.add_response(
            'describe_db_instances',
            service_response=desc_db_inst_response
    )

    response = {'DBSnapshots': [{'DBSnapshotIdentifier': 'rds:mv-ugc-postgres-2019-12-06-11-10', 'DBInstanceIdentifier': 'mv-ugc-postgres', 'SnapshotCreateTime': datetime.datetime(2019, 12, 6, 11, 10, 33, 790000), 'Engine': 'postgres', 'AllocatedStorage': 20, 'Status': 'available', 'Port': 5432, 'AvailabilityZone': 'eu-west-2b', 'VpcId': 'vpc-19483f70', 'InstanceCreateTime': datetime.datetime(2019, 12, 6, 11, 9, 28, 424000), 'MasterUsername': 'ugc', 'EngineVersion': '9.6.15', 'LicenseModel': 'postgresql-license', 'SnapshotType': 'automated', 'OptionGroupName': 'default:postgres-9-6', 'PercentProgress': 100, 'StorageType': 'standard',
                                 'Encrypted': True, 'KmsKeyId': 'arn:aws:kms:eu-west-2:546933502184:key/83f283d1-7b58-4827-854c-db776149795f', 'DBSnapshotArn': 'arn:aws:rds:eu-west-2:546933502184:snapshot:rds:mv-ugc-postgres-2019-12-06-11-10', 'IAMDatabaseAuthenticationEnabled': False, 'ProcessorFeatures': [], 'DbiResourceId': 'db-CQ76MXOJJIFBOQ7WT63Y6AXUKA'}], 'ResponseMetadata': {'RequestId': '8290e734-5717-4c94-9ed5-1eaf0aa20ec6', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': '8290e734-5717-4c94-9ed5-1eaf0aa20ec6', 'content-type': 'text/xml', 'content-length': '1687', 'date': 'Fri, 06 Dec 2019 15:02:09 GMT'}, 'RetryAttempts': 0}}
    s3_stub.add_response(
        'describe_db_snapshots',
        expected_params={'DBInstanceIdentifier': 'mr1qf4ez7ls7xfn',
                         'SnapshotType': 'shared'},
        service_response=response
    )


    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template_with_snapshot_specified.json",
                                                       "db_instance_template.json")

    i = {'db_instance': 'instance_i'}
    f = {'fragment': expected, 'requestId': 'my_request_id', 'params': i}

    res = handler(f, "hey")
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_restore_to_point_in_time.json',
    FIXTURE_DIR / 'db_describe_instance_response.json'
)
def test_point_in_time_restore_latest_restorable_time(s3_stub, monkeypatch, datafiles):
    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("latest_snapshot", "false")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv("rds_stack_name", "mv-rds-db-stack")
    monkeypatch.setenv("snapshot_type", "shared")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "true")
    monkeypatch.setenv('target_db_instance', "target_instance")

    for testFile in datafiles.listdir():
            if fnmatch.fnmatch(testFile, "*db_describe_instance_response.json"):
                desc_db_inst_response = json.loads(testFile.read_text(encoding="'utf-8'"))
        
    s3_stub.add_response(
            'describe_db_instances',
            service_response=desc_db_inst_response
    )

    response = {
        "DBInstance": {
            "AllocatedStorage": 20,
            "DBInstanceArn": "arn:aws:rds:us-east-1:123456789012:db:restored-test-instance",
            "DBInstanceStatus": "creating",
            "DBInstanceIdentifier": "restored-test-instance"
        }
    }
    s3_stub.add_response(
        'restore_db_instance_to_point_in_time',
        expected_params={'SourceDBInstanceIdentifier':'mr1qf4ez7ls7xfn',
                'TargetDBInstanceIdentifier':'target_instance',
                'UseLatestRestorableTime':True},
        service_response=response
    )

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_restore_to_point_in_time.json",
                                                       "db_instance_template.json")

    i = {'db_instance': 'instance_i'}
    f = {'fragment': db_instance_template,
         'requestId': 'my_request_id', 'params': i}

    res = handler(f, "hey")
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected


@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_describe_instance_response.json',
)
def test_find_db_indentifier_using_stack_name(datafiles):

        for testFile in datafiles.listdir():
            if fnmatch.fnmatch(testFile, "*db_describe_instance_response.json"):
                response = json.loads(testFile.read_text(encoding="'utf-8'"))
        
        db_instance_id = parse_db_identifier(response,'mv-rds-db-stack')
        assert db_instance_id == "mr1qf4ez7ls7xfn"
""" 
        s3_stub.add_response(
            'describe_db_instances',
            service_response=response
        ) """
       