import pytest
from botocore.stub import Stubber
import json
import datetime
from lambdas.ugc_rds_macro import handler, client

def test_handler_remove_property(monkeypatch):
    e = '{"Type": "AWS::RDS::DBInstance", "Properties": {"AllocatedStorage": {"Ref": "AllocatedStorage"},"DBInstanceClass": {"Ref": "InstanceClass"}, "DBInstanceIdentifier": {"Fn::Sub": "${Environment}-ugc-postgres"}, "DBName": {"Ref": "DatabaseName"}, "DBParameterGroupName": {"Ref": "ParameterGroup"}, "DBSubnetGroupName": {"Ref": "SubnetGroup"}, "Engine": "postgres", "EngineVersion": "9.6", "KmsKeyId": {"Fn::GetAtt": ["UgcRdsEncryptionKey", "Arn"]}, "MasterUserPassword": {"Ref": "DatabasePassword"}, "MasterUsername": {"Ref": "DatabaseUser"}, "MultiAZ": {"Ref": "MultiAZ"}, "PubliclyAccessible": "false", "StorageEncrypted": "true", "VPCSecurityGroups": [{"Ref": "VPCSecurityGroup"}]}}'
    expected = json.loads(e)
    monkeypatch.setenv("latest_snapshot","False")
    monkeypatch.setenv("properties_to_remove","BackupRetentionPeriod")
    monkeypatch.setenv("properties_to_add","")
    monkeypatch.setenv("db_instance","")
    d = '{"Type": "AWS::RDS::DBInstance", "Properties": {"AllocatedStorage": {"Ref": "AllocatedStorage"}, "BackupRetentionPeriod": {"Ref": "BackupRetentionDays"}, "DBInstanceClass": {"Ref": "InstanceClass"}, "DBInstanceIdentifier": {"Fn::Sub": "${Environment}-ugc-postgres"}, "DBName": {"Ref": "DatabaseName"}, "DBParameterGroupName": {"Ref": "ParameterGroup"}, "DBSubnetGroupName": {"Ref": "SubnetGroup"}, "Engine": "postgres", "EngineVersion": "9.6", "KmsKeyId": {"Fn::GetAtt": ["UgcRdsEncryptionKey", "Arn"]}, "MasterUserPassword": {"Ref": "DatabasePassword"}, "MasterUsername": {"Ref": "DatabaseUser"}, "MultiAZ": {"Ref": "MultiAZ"}, "PubliclyAccessible": "false", "StorageEncrypted": "true", "VPCSecurityGroups": [{"Ref": "VPCSecurityGroup"}]}}'    
    i = {'db_instance':'instance_i'}
    f = {'fragment' : json.loads(d), 'requestId': 'my_request_id', 'params': i}

    res = handler(f,"hey")
  
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected

def test_handler_remove_multiple_properties(monkeypatch):
    e = '{"Type": "AWS::RDS::DBInstance", "Properties": {"AllocatedStorage": {"Ref": "AllocatedStorage"}, "BackupRetentionPeriod": {"Ref": "BackupRetentionDays"}, "DBInstanceClass": {"Ref": "InstanceClass"}, "DBParameterGroupName": {"Ref": "ParameterGroup"}, "DBSubnetGroupName": {"Ref": "SubnetGroup"}, "Engine": "postgres", "EngineVersion": "9.6", "KmsKeyId": {"Fn::GetAtt": ["UgcRdsEncryptionKey", "Arn"]}, "MasterUserPassword": {"Ref": "DatabasePassword"}, "MasterUsername": {"Ref": "DatabaseUser"}, "MultiAZ": {"Ref": "MultiAZ"}, "PubliclyAccessible": "false", "StorageEncrypted": "true", "VPCSecurityGroups": [{"Ref": "VPCSecurityGroup"}]}}'
    expected = json.loads(e)
    monkeypatch.setenv("latest_snapshot","False")
    monkeypatch.setenv("properties_to_remove","DBInstanceIdentifier, DBName")
    monkeypatch.setenv("properties_to_add","")
    monkeypatch.setenv("db_instance","")
    d = '{"Type": "AWS::RDS::DBInstance", "Properties": {"AllocatedStorage": {"Ref": "AllocatedStorage"}, "BackupRetentionPeriod": {"Ref": "BackupRetentionDays"}, "DBInstanceClass": {"Ref": "InstanceClass"}, "DBInstanceIdentifier": {"Fn::Sub": "${Environment}-ugc-postgres"}, "DBName": {"Ref": "DatabaseName"}, "DBParameterGroupName": {"Ref": "ParameterGroup"}, "DBSubnetGroupName": {"Ref": "SubnetGroup"}, "Engine": "postgres", "EngineVersion": "9.6", "KmsKeyId": {"Fn::GetAtt": ["UgcRdsEncryptionKey", "Arn"]}, "MasterUserPassword": {"Ref": "DatabasePassword"}, "MasterUsername": {"Ref": "DatabaseUser"}, "MultiAZ": {"Ref": "MultiAZ"}, "PubliclyAccessible": "false", "StorageEncrypted": "true", "VPCSecurityGroups": [{"Ref": "VPCSecurityGroup"}]}}'    
    i = {'db_instance':'instance_i'}
    f = {'fragment' : json.loads(d), 'requestId': 'my_request_id', 'params': i}

    res = handler(f,"hey")
  
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected

def test_handler_add_property(monkeypatch):
    monkeypatch.setenv("properties_to_remove","")
    monkeypatch.setenv("latest_snapshot","False")
    monkeypatch.setenv("properties_to_add",'{"BackupRetentionPeriod": {"Ref": "BackupRetentionDays"}}')
    monkeypatch.setenv("db_instance","")
    
    e = '{"Type": "AWS::RDS::DBInstance", "Properties": {"AllocatedStorage": {"Ref": "AllocatedStorage"}, "BackupRetentionPeriod": {"Ref": "BackupRetentionDays"}, "DBInstanceClass": {"Ref": "InstanceClass"}, "DBInstanceIdentifier": {"Fn::Sub": "${Environment}-ugc-postgres"}, "DBName": {"Ref": "DatabaseName"}, "DBParameterGroupName": {"Ref": "ParameterGroup"}, "DBSubnetGroupName": {"Ref": "SubnetGroup"}, "Engine": "postgres", "EngineVersion": "9.6", "KmsKeyId": {"Fn::GetAtt": ["UgcRdsEncryptionKey", "Arn"]}, "MasterUserPassword": {"Ref": "DatabasePassword"}, "MasterUsername": {"Ref": "DatabaseUser"}, "MultiAZ": {"Ref": "MultiAZ"}, "PubliclyAccessible": "false", "StorageEncrypted": "true", "VPCSecurityGroups": [{"Ref": "VPCSecurityGroup"}]}}'    
    expected = json.loads(e)
    
    i = {'db_instance':'instance_i'}
    d = '{"Type": "AWS::RDS::DBInstance", "Properties": {"AllocatedStorage": {"Ref": "AllocatedStorage"},"DBInstanceClass": {"Ref": "InstanceClass"}, "DBInstanceIdentifier": {"Fn::Sub": "${Environment}-ugc-postgres"}, "DBName": {"Ref": "DatabaseName"}, "DBParameterGroupName": {"Ref": "ParameterGroup"}, "DBSubnetGroupName": {"Ref": "SubnetGroup"}, "Engine": "postgres", "EngineVersion": "9.6", "KmsKeyId": {"Fn::GetAtt": ["UgcRdsEncryptionKey", "Arn"]}, "MasterUserPassword": {"Ref": "DatabasePassword"}, "MasterUsername": {"Ref": "DatabaseUser"}, "MultiAZ": {"Ref": "MultiAZ"}, "PubliclyAccessible": "false", "StorageEncrypted": "true", "VPCSecurityGroups": [{"Ref": "VPCSecurityGroup"}]}}'
    f = {'fragment' : json.loads(d), 'requestId': 'my_request_id', 'params': i}

    res = handler(f,"hey")    
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected

def test_handler_add_multiple_properties(monkeypatch):
    monkeypatch.setenv("properties_to_remove","")
    monkeypatch.setenv("latest_snapshot","False")
    monkeypatch.setenv("properties_to_add",'{"BackupRetentionPeriod": {"Ref": "BackupRetentionDays"}},{"DBName": { "Ref": "DatabaseName"}}')
    monkeypatch.setenv("db_instance","arn")
    
    e = '{"Type": "AWS::RDS::DBInstance", "Properties": {"AllocatedStorage": {"Ref": "AllocatedStorage"}, "BackupRetentionPeriod": {"Ref": "BackupRetentionDays"}, "DBInstanceClass": {"Ref": "InstanceClass"}, "DBInstanceIdentifier": {"Fn::Sub": "${Environment}-ugc-postgres"}, "DBName": {"Ref": "DatabaseName"}, "DBParameterGroupName": {"Ref": "ParameterGroup"}, "DBSubnetGroupName": {"Ref": "SubnetGroup"}, "Engine": "postgres", "EngineVersion": "9.6", "KmsKeyId": {"Fn::GetAtt": ["UgcRdsEncryptionKey", "Arn"]}, "MasterUserPassword": {"Ref": "DatabasePassword"}, "MasterUsername": {"Ref": "DatabaseUser"}, "MultiAZ": {"Ref": "MultiAZ"}, "PubliclyAccessible": "false", "StorageEncrypted": "true", "VPCSecurityGroups": [{"Ref": "VPCSecurityGroup"}]}}'    
    expected = json.loads(e)
    
    i = {'db_instance':'instance_i'}
    d = '{"Type": "AWS::RDS::DBInstance", "Properties": {"AllocatedStorage": {"Ref": "AllocatedStorage"},"DBInstanceClass": {"Ref": "InstanceClass"}, "DBInstanceIdentifier": {"Fn::Sub": "${Environment}-ugc-postgres"}, "DBName": {"Ref": "DatabaseName"}, "DBParameterGroupName": {"Ref": "ParameterGroup"}, "DBSubnetGroupName": {"Ref": "SubnetGroup"}, "Engine": "postgres", "EngineVersion": "9.6", "KmsKeyId": {"Fn::GetAtt": ["UgcRdsEncryptionKey", "Arn"]}, "MasterUserPassword": {"Ref": "DatabasePassword"}, "MasterUsername": {"Ref": "DatabaseUser"}, "MultiAZ": {"Ref": "MultiAZ"}, "PubliclyAccessible": "false", "StorageEncrypted": "true", "VPCSecurityGroups": [{"Ref": "VPCSecurityGroup"}]}}'
    f = {'fragment' : json.loads(d), 'requestId': 'my_request_id', 'params': i}

    res = handler(f,"hey")    
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected
    

def test_snapshot_identifer(s3_stub, monkeypatch):
    response = {'DBSnapshots': [{'DBSnapshotIdentifier': 'rds:mv-ugc-postgres-2019-12-06-11-10', 'DBInstanceIdentifier': 'mv-ugc-postgres', 'SnapshotCreateTime': datetime.datetime(2019, 12, 6, 11, 10, 33, 790000), 'Engine': 'postgres', 'AllocatedStorage': 20, 'Status': 'available', 'Port': 5432, 'AvailabilityZone': 'eu-west-2b', 'VpcId': 'vpc-19483f70', 'InstanceCreateTime': datetime.datetime(2019, 12, 6, 11, 9, 28, 424000), 'MasterUsername': 'ugc', 'EngineVersion': '9.6.15', 'LicenseModel': 'postgresql-license', 'SnapshotType': 'automated', 'OptionGroupName': 'default:postgres-9-6', 'PercentProgress': 100, 'StorageType': 'standard', 'Encrypted': True, 'KmsKeyId': 'arn:aws:kms:eu-west-2:546933502184:key/83f283d1-7b58-4827-854c-db776149795f', 'DBSnapshotArn': 'arn:aws:rds:eu-west-2:546933502184:snapshot:rds:mv-ugc-postgres-2019-12-06-11-10', 'IAMDatabaseAuthenticationEnabled': False, 'ProcessorFeatures': [], 'DbiResourceId': 'db-CQ76MXOJJIFBOQ7WT63Y6AXUKA'}], 'ResponseMetadata': {'RequestId': '8290e734-5717-4c94-9ed5-1eaf0aa20ec6', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': '8290e734-5717-4c94-9ed5-1eaf0aa20ec6', 'content-type': 'text/xml', 'content-length': '1687', 'date': 'Fri, 06 Dec 2019 15:02:09 GMT'}, 'RetryAttempts': 0}}
    s3_stub.add_response(
        'describe_db_snapshots',
        expected_params={'DBInstanceIdentifier': 'arn'},
        service_response=response
    )

    monkeypatch.setenv("properties_to_remove","")
    monkeypatch.setenv("latest_snapshot","true")
    monkeypatch.setenv("properties_to_add","")
    monkeypatch.setenv("db_instance","arn")
    monkeypatch.setenv("snapshot_type"," ")
    
    e = '{"Type": "AWS::RDS::DBInstance", "Properties": {"AllocatedStorage": {"Ref": "AllocatedStorage"}, "DBInstanceClass": {"Ref": "InstanceClass"}, "DBInstanceIdentifier": {"Fn::Sub": "${Environment}-ugc-postgres"}, "DBName": {"Ref": "DatabaseName"}, "DBParameterGroupName": {"Ref": "ParameterGroup"}, "DBSubnetGroupName": {"Ref": "SubnetGroup"}, "Engine": "postgres", "EngineVersion": "9.6", "KmsKeyId": {"Fn::GetAtt": ["UgcRdsEncryptionKey", "Arn"]}, "MasterUserPassword": {"Ref": "DatabasePassword"}, "MasterUsername": {"Ref": "DatabaseUser"}, "MultiAZ": {"Ref": "MultiAZ"}, "PubliclyAccessible": "false", "StorageEncrypted": "true", "VPCSecurityGroups": [{"Ref": "VPCSecurityGroup"}], "DBSnapshotIdentifier": "arn:aws:rds:eu-west-2:546933502184:snapshot:rds:mv-ugc-postgres-2019-12-06-11-10"}}'    
    expected = json.loads(e)
    
    i = {'db_instance':'instance_i'}
    d = '{"Type": "AWS::RDS::DBInstance", "Properties": {"AllocatedStorage": {"Ref": "AllocatedStorage"},"DBInstanceClass": {"Ref": "InstanceClass"}, "DBInstanceIdentifier": {"Fn::Sub": "${Environment}-ugc-postgres"}, "DBName": {"Ref": "DatabaseName"}, "DBParameterGroupName": {"Ref": "ParameterGroup"}, "DBSubnetGroupName": {"Ref": "SubnetGroup"}, "Engine": "postgres", "EngineVersion": "9.6", "KmsKeyId": {"Fn::GetAtt": ["UgcRdsEncryptionKey", "Arn"]}, "MasterUserPassword": {"Ref": "DatabasePassword"}, "MasterUsername": {"Ref": "DatabaseUser"}, "MultiAZ": {"Ref": "MultiAZ"}, "PubliclyAccessible": "false", "StorageEncrypted": "true", "VPCSecurityGroups": [{"Ref": "VPCSecurityGroup"}]}}'
    f = {'fragment' : json.loads(d), 'requestId': 'my_request_id', 'params': i}

    res = handler(f,"hey")    
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected

def test_snapshot_identifer_with_snapshot_type(s3_stub, monkeypatch):
    response = {'DBSnapshots': [{'DBSnapshotIdentifier': 'rds:mv-ugc-postgres-2019-12-06-11-10', 'DBInstanceIdentifier': 'mv-ugc-postgres', 'SnapshotCreateTime': datetime.datetime(2019, 12, 6, 11, 10, 33, 790000), 'Engine': 'postgres', 'AllocatedStorage': 20, 'Status': 'available', 'Port': 5432, 'AvailabilityZone': 'eu-west-2b', 'VpcId': 'vpc-19483f70', 'InstanceCreateTime': datetime.datetime(2019, 12, 6, 11, 9, 28, 424000), 'MasterUsername': 'ugc', 'EngineVersion': '9.6.15', 'LicenseModel': 'postgresql-license', 'SnapshotType': 'automated', 'OptionGroupName': 'default:postgres-9-6', 'PercentProgress': 100, 'StorageType': 'standard', 'Encrypted': True, 'KmsKeyId': 'arn:aws:kms:eu-west-2:546933502184:key/83f283d1-7b58-4827-854c-db776149795f', 'DBSnapshotArn': 'arn:aws:rds:eu-west-2:546933502184:snapshot:rds:mv-ugc-postgres-2019-12-06-11-10', 'IAMDatabaseAuthenticationEnabled': False, 'ProcessorFeatures': [], 'DbiResourceId': 'db-CQ76MXOJJIFBOQ7WT63Y6AXUKA'}], 'ResponseMetadata': {'RequestId': '8290e734-5717-4c94-9ed5-1eaf0aa20ec6', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': '8290e734-5717-4c94-9ed5-1eaf0aa20ec6', 'content-type': 'text/xml', 'content-length': '1687', 'date': 'Fri, 06 Dec 2019 15:02:09 GMT'}, 'RetryAttempts': 0}}
    s3_stub.add_response(
        'describe_db_snapshots',
        expected_params={'DBInstanceIdentifier': 'arn', 'SnapshotType':'shared'},
        service_response=response
    )

    monkeypatch.setenv("properties_to_remove","")
    monkeypatch.setenv("latest_snapshot","true")
    monkeypatch.setenv("properties_to_add","")
    monkeypatch.setenv("db_instance","arn")
    monkeypatch.setenv("snapshot_type","shared")
    
    e = '{"Type": "AWS::RDS::DBInstance", "Properties": {"AllocatedStorage": {"Ref": "AllocatedStorage"}, "DBInstanceClass": {"Ref": "InstanceClass"}, "DBInstanceIdentifier": {"Fn::Sub": "${Environment}-ugc-postgres"}, "DBName": {"Ref": "DatabaseName"}, "DBParameterGroupName": {"Ref": "ParameterGroup"}, "DBSubnetGroupName": {"Ref": "SubnetGroup"}, "Engine": "postgres", "EngineVersion": "9.6", "KmsKeyId": {"Fn::GetAtt": ["UgcRdsEncryptionKey", "Arn"]}, "MasterUserPassword": {"Ref": "DatabasePassword"}, "MasterUsername": {"Ref": "DatabaseUser"}, "MultiAZ": {"Ref": "MultiAZ"}, "PubliclyAccessible": "false", "StorageEncrypted": "true", "VPCSecurityGroups": [{"Ref": "VPCSecurityGroup"}], "DBSnapshotIdentifier": "arn:aws:rds:eu-west-2:546933502184:snapshot:rds:mv-ugc-postgres-2019-12-06-11-10"}}'    
    expected = json.loads(e)
    
    i = {'db_instance':'instance_i'}
    d = '{"Type": "AWS::RDS::DBInstance", "Properties": {"AllocatedStorage": {"Ref": "AllocatedStorage"},"DBInstanceClass": {"Ref": "InstanceClass"}, "DBInstanceIdentifier": {"Fn::Sub": "${Environment}-ugc-postgres"}, "DBName": {"Ref": "DatabaseName"}, "DBParameterGroupName": {"Ref": "ParameterGroup"}, "DBSubnetGroupName": {"Ref": "SubnetGroup"}, "Engine": "postgres", "EngineVersion": "9.6", "KmsKeyId": {"Fn::GetAtt": ["UgcRdsEncryptionKey", "Arn"]}, "MasterUserPassword": {"Ref": "DatabasePassword"}, "MasterUsername": {"Ref": "DatabaseUser"}, "MultiAZ": {"Ref": "MultiAZ"}, "PubliclyAccessible": "false", "StorageEncrypted": "true", "VPCSecurityGroups": [{"Ref": "VPCSecurityGroup"}]}}'
    f = {'fragment' : json.loads(d), 'requestId': 'my_request_id', 'params': i}

    res = handler(f,"hey")    
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected
