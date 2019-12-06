import pytest
import json
from lambdas.ugc_rds_macro import handler

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
    monkeypatch.setenv("db_instance","")
    
    e = '{"Type": "AWS::RDS::DBInstance", "Properties": {"AllocatedStorage": {"Ref": "AllocatedStorage"}, "BackupRetentionPeriod": {"Ref": "BackupRetentionDays"}, "DBInstanceClass": {"Ref": "InstanceClass"}, "DBInstanceIdentifier": {"Fn::Sub": "${Environment}-ugc-postgres"}, "DBName": {"Ref": "DatabaseName"}, "DBParameterGroupName": {"Ref": "ParameterGroup"}, "DBSubnetGroupName": {"Ref": "SubnetGroup"}, "Engine": "postgres", "EngineVersion": "9.6", "KmsKeyId": {"Fn::GetAtt": ["UgcRdsEncryptionKey", "Arn"]}, "MasterUserPassword": {"Ref": "DatabasePassword"}, "MasterUsername": {"Ref": "DatabaseUser"}, "MultiAZ": {"Ref": "MultiAZ"}, "PubliclyAccessible": "false", "StorageEncrypted": "true", "VPCSecurityGroups": [{"Ref": "VPCSecurityGroup"}]}}'    
    expected = json.loads(e)
    
    i = {'db_instance':'instance_i'}
    d = '{"Type": "AWS::RDS::DBInstance", "Properties": {"AllocatedStorage": {"Ref": "AllocatedStorage"},"DBInstanceClass": {"Ref": "InstanceClass"}, "DBInstanceIdentifier": {"Fn::Sub": "${Environment}-ugc-postgres"}, "DBName": {"Ref": "DatabaseName"}, "DBParameterGroupName": {"Ref": "ParameterGroup"}, "DBSubnetGroupName": {"Ref": "SubnetGroup"}, "Engine": "postgres", "EngineVersion": "9.6", "KmsKeyId": {"Fn::GetAtt": ["UgcRdsEncryptionKey", "Arn"]}, "MasterUserPassword": {"Ref": "DatabasePassword"}, "MasterUsername": {"Ref": "DatabaseUser"}, "MultiAZ": {"Ref": "MultiAZ"}, "PubliclyAccessible": "false", "StorageEncrypted": "true", "VPCSecurityGroups": [{"Ref": "VPCSecurityGroup"}]}}'
    f = {'fragment' : json.loads(d), 'requestId': 'my_request_id', 'params': i}

    res = handler(f,"hey")    
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected