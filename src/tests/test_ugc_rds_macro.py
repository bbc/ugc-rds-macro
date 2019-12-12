import pytest
from pytest_mock import mocker
from botocore.stub import Stubber
import json
import datetime
from lambdas.ugc_rds_macro import handler, parse_db_identifier, get_ugc_database_template, get_snapshot_identifier
import os
import py
import fnmatch
import uuid
import time
from io import StringIO

_dir = os.path.dirname(os.path.realpath(__file__))
FIXTURE_DIR = py.path.local(_dir) / 'test_files'


template_response = {
  "TemplateBody": {
      "Outputs": {
          "RDSEncryptionKeyArn": {
              "Description": "The arn of the database encryption key",
              "Export": {
                  "Name": {
                      "Fn::Sub": "${Environment}-RDSEncryptionKeyArn"
                  }
              },
              "Value": {
                  "Fn::GetAtt": [
                      "UgcRdsEncryptionKey",
                      "Arn"
                  ]
              }
          }
      },
      "AWSTemplateFormatVersion": "2010-09-09",
      "Description": "Create UGC RDS instances",
      "Parameters": {
          "AllocatedStorage": {
              "ConstraintDescription": "Should be between 5 and 1024GB.",
              "Default": "20",
              "Description": "Allocated storage for the database (GB).",
              "MaxValue": "1024",
              "MinValue": "5",
              "Type": "Number"
          },
          "BackupRetentionDays": {
              "Default": 30,
              "Description": "Number of days to retain automated backups for",
              "Type": "Number"
          },
          "DatabaseName": {
              "AllowedPattern": "[a-zA-Z][a-zA-Z0-9]*",
              "ConstraintDescription": "Should begin with a letter and contain only alphanumeric characters.",
              "Default": "ugc",
              "Description": "The name of the database to create.",
              "MaxLength": "64",
              "MinLength": "1",
              "Type": "String"
          },
          "DatabasePassword": {
              "AllowedPattern": "[a-zA-Z0-9]*",
              "ConstraintDescription": "Should contain only alphanumeric characters.",
              "Default": "letmeinplease",
              "Description": "The database admin account password.",
              "MaxLength": "41",
              "MinLength": "1",
              "NoEcho": True,
              "Type": "String"
          },
          "DatabaseUser": {
              "AllowedPattern": "[a-zA-Z][a-zA-Z0-9]*",
              "ConstraintDescription": "Should begin with a letter and contain only alphanumeric characters.",
              "Default": "ugc",
              "Description": "The database admin account username.",
              "MaxLength": "16",
              "MinLength": "1",
              "Type": "String"
          },
          "DomainNameBase": {
              "Default": "c7dff5ab13c48206.xhst.bbci.co.uk.",
              "Description": "Base domain under which to create DNS records",
              "Type": "String"
          },
          "Environment": {
              "AllowedValues": [
                  "int",
                  "test",
                  "live",
                  "one",
                  "two",
                  "three",
                  "four",
                  "five",
                  "six"
              ],
              "Description": "The name of the environment.",
              "Type": "String"
          },
          "InstanceClass": {
              "AllowedValues": [
                  "db.t2.small",
                  "db.t2.medium",
                  "db.t2.large"
              ],
              "ConstraintDescription": "The database instance type to use.",
              "Default": "db.t2.small",
              "Description": "Database instance class.",
              "Type": "String"
          },
          "MultiAZ": {
              "AllowedValues": [
                  "true",
                  "false"
              ],
              "Default": "false",
              "Description": "Replicate across multiple AZs?",
              "Type": "String"
          }
      },
      "Resources": {
          "UGCDNSRecord": {
              "Properties": {
                  "HostedZoneName": {
                      "Ref": "DomainNameBase"
                  },
                  "Name": {
                      "Fn::Sub": "ugc-postgres.${Environment}.${DomainNameBase}"
                  },
                  "ResourceRecords": [
                      {
                          "Fn::GetAtt": [
                              "UGCDatabase",
                              "Endpoint.Address"
                          ]
                      }
                  ],
                  "TTL": "300",
                  "Type": "CNAME"
              },
              "Type": "AWS::Route53::RecordSet"
          },
          "UGCDatabase": {
              "Type": "AWS::RDS::DBInstance",
              "Properties": {
                  "AllocatedStorage": {
                      "Ref": "AllocatedStorage"
                  },
                  "BackupRetentionPeriod": {
                      "Ref": "BackupRetentionDays"
                  },
                  "DBInstanceClass": {
                      "Ref": "InstanceClass"
                  },
                  "DBParameterGroupName": {
                      "Ref": "ParameterGroup"
                  },
                  "DBSubnetGroupName": {
                      "Ref": "SubnetGroup"
                  },
                  "Engine": "postgres",
                  "EngineVersion": "9.6",
                  "KmsKeyId": {
                      "Fn::GetAtt": [
                          "UgcRdsEncryptionKey",
                          "Arn"
                      ]
                  },
                  "MasterUserPassword": {
                      "Ref": "DatabasePassword"
                  },
                  "MasterUsername": {
                      "Ref": "DatabaseUser"
                  },
                  "MultiAZ": {
                      "Ref": "MultiAZ"
                  },
                  "PubliclyAccessible": "false",
                  "StorageEncrypted": "true",
                  "VPCSecurityGroups": [
                      {
                          "Ref": "VPCSecurityGroup"
                      }
                  ],
                  "DBSnapshotIdentifier": "arn:aws:rds:eu-west-2:546933502184:snapshot:rds:test-ugc-postgres-2019-12-03-02-13"
              }
          },
          "VPCSecurityGroup": {
              "Properties": {
                  "GroupDescription": "Security group for RDS DB instance.",
                  "SecurityGroupIngress": [
                      {
                          "FromPort": 5432,
                          "IpProtocol": "tcp",
                          "SourceSecurityGroupId": {
                              "Fn::ImportValue": {
                                  "Fn::Sub": "int-ManagerSecurityGroup"
                              }
                          },
                          "ToPort": 5432
                      },
                      {
                          "FromPort": 5432,
                          "IpProtocol": "tcp",
                          "SourceSecurityGroupId": {
                              "Fn::ImportValue": {
                                  "Fn::Sub": "int-InputHandlerSecurityGroup"
                              }
                          },
                          "ToPort": 5432
                      },
                      {
                          "FromPort": 5432,
                          "IpProtocol": "tcp",
                          "SourceSecurityGroupId": {
                              "Fn::ImportValue": {
                                  "Fn::Sub": "int-CleanerSecurityGroup"
                              }
                          },
                          "ToPort": 5432
                      }
                  ],
                  "VpcId": {
                      "Fn::ImportValue": "core-infrastructure-VpcId"
                  }
              },
              "Type": "AWS::EC2::SecurityGroup"
          },
          "ParameterGroup": {
              "Properties": {
                  "Description": "Parameters for the RDS DB",
                  "Family": "postgres9.6",
                  "Parameters": {
                      "rds.force_ssl": "1"
                  }
              },
              "Type": "AWS::RDS::DBParameterGroup"
          },
          "UgcRdsEncryptionKey": {
              "Properties": {
                  "Description": "Ugc Rds Encryption Key",
                  "EnableKeyRotation": "true",
                  "Enabled": "true",
                  "KeyPolicy": {
                      "Id": "ugc-rds-encryption-key-policy",
                      "Statement": [
                          {
                              "Action": [
                                  "kms:*"
                              ],
                              "Effect": "Allow",
                              "Principal": {
                                  "AWS": {
                                      "Ref": "AWS::AccountId"
                                  }
                              },
                              "Resource": [
                                  "*"
                              ],
                              "Sid": "Administer key via root"
                          }
                      ],
                      "Version": "2012-10-17"
                  }
              },
              "Type": "AWS::KMS::Key"
          },
          "UgcPostgresPasswordsKey": {
              "Properties": {
                  "Description": "Ugc Postgres Passwords Key",
                  "EnableKeyRotation": "true",
                  "Enabled": "true",
                  "KeyPolicy": {
                      "Id": "ugc-postgres-passwords-key-policy",
                      "Statement": [
                          {
                              "Action": [
                                  "kms:*"
                              ],
                              "Effect": "Allow",
                              "Principal": {
                                  "AWS": {
                                      "Ref": "AWS::AccountId"
                                  }
                              },
                              "Resource": [
                                  "*"
                              ],
                              "Sid": "Administer key via root"
                          },
                          {
                              "Action": [
                                  "kms:Decrypt"
                              ],
                              "Condition": {
                                  "StringEquals": {
                                      "kms:ViaService": "ssm.eu-west-2.amazonaws.com"
                                  }
                              },
                              "Effect": "Allow",
                              "Principal": {
                                  "AWS": [
                                      {
                                          "Fn::ImportValue": {
                                              "Fn::Sub": "int-InputHandlerRole"
                                          }
                                      },
                                      {
                                          "Fn::ImportValue": {
                                              "Fn::Sub": "int-ManagerComponentRole"
                                          }
                                      },
                                      {
                                          "Fn::ImportValue": {
                                              "Fn::Sub": "int-CleanerComponentRole"
                                          }
                                      }
                                  ]
                              },
                              "Resource": [
                                  "*"
                              ],
                              "Sid": "Allow decryption"
                          }
                      ],
                      "Version": "2012-10-17"
                  }
              },
              "Type": "AWS::KMS::Key"
          },
          "UgcRdsEncryptionKeyAlias": {
              "Properties": {
                  "AliasName": {
                      "Fn::Join": [
                          "",
                          [
                              "alias/",
                              {
                                  "Ref": "Environment"
                              },
                              "-ugc-rds-encryption-key"
                          ]
                      ]
                  },
                  "TargetKeyId": {
                      "Ref": "UgcRdsEncryptionKey"
                  }
              },
              "Type": "AWS::KMS::Alias"
          },
          "SubnetGroup": {
              "Properties": {
                  "DBSubnetGroupDescription": "Subnets available for the RDS DB instance",
                  "SubnetIds": [
                      {
                          "Fn::ImportValue": "core-infrastructure-PrivateSubnet0"
                      },
                      {
                          "Fn::ImportValue": "core-infrastructure-PrivateSubnet1"
                      }
                  ]
              },
              "Type": "AWS::RDS::DBSubnetGroup"
          },
          "UgcPostgresPasswordsKeyAlias": {
              "Properties": {
                  "AliasName": {
                      "Fn::Join": [
                          "",
                          [
                              "alias/",
                              {
                                  "Ref": "Environment"
                              },
                              "-ugc-postgres-passwords-key"
                          ]
                      ]
                  },
                  "TargetKeyId": {
                      "Ref": "UgcPostgresPasswordsKey"
                  }
              },
              "Type": "AWS::KMS::Alias"
          }
      }
  },
  "StagesAvailable": [
      "Original",
      "Processed"
  ]
}

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
    monkeypatch.setenv("snapshot_id","")
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
    monkeypatch.setenv("snapshot_id","")
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
    monkeypatch.setenv("snapshot_id","")
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
    FIXTURE_DIR / 'db_instance_template_props_removed.json',
    FIXTURE_DIR / 'db_instance_template_with_multiple_props_added.json',
)
def test_handler_add_multiple_properties(monkeypatch, datafiles):
    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("latest_snapshot", "false")
    monkeypatch.setenv("snapshot_id","")
    monkeypatch.setenv(
        "properties_to_add", '{"BackupRetentionPeriod": {"Ref": "BackupRetentionDays"}},{"DBName": { "Ref": "DatabaseName"}}')
    monkeypatch.setenv("rds_stack_name", "arn")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "")
    monkeypatch.setenv('target_db_instance', "target_instance")


    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template_with_multiple_props_added.json",
                                                       "db_instance_template_props_removed.json")

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
def test_snapshot_identifer(rds_stub, monkeypatch, datafiles):
    
    monkeypatch.setenv("properties_to_remove", "BackupRetentionPeriod")
    monkeypatch.setenv("latest_snapshot", "true")
    monkeypatch.setenv("snapshot_id","")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv("rds_stack_name", "mv-rds-db-stack")
    monkeypatch.setenv("snapshot_type", " ")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "")
    monkeypatch.setenv('target_db_instance', "target_instance")

    for testFile in datafiles.listdir():
            if fnmatch.fnmatch(testFile, "*db_describe_instance_response.json"):
                desc_db_inst_response = json.loads(testFile.read_text(encoding="'utf-8'"))
        
    rds_stub.add_response(
            'describe_db_instances',
            service_response=desc_db_inst_response
    )
    
    response = {'DBSnapshots': [{'DBSnapshotIdentifier': 'rds:mv-ugc-postgres-2019-12-06-11-10', 'DBInstanceIdentifier': 'mv-ugc-postgres', 'SnapshotCreateTime': datetime.datetime(2019, 12, 6, 11, 10, 33, 790000), 'Engine': 'postgres', 'AllocatedStorage': 20, 'Status': 'available', 'Port': 5432, 'AvailabilityZone': 'eu-west-2b', 'VpcId': 'vpc-19483f70', 'InstanceCreateTime': datetime.datetime(2019, 12, 6, 11, 9, 28, 424000), 'MasterUsername': 'ugc', 'EngineVersion': '9.6.15', 'LicenseModel': 'postgresql-license', 'SnapshotType': 'automated', 'OptionGroupName': 'default:postgres-9-6', 'PercentProgress': 100, 'StorageType': 'standard',
                                 'Encrypted': True, 'KmsKeyId': 'arn:aws:kms:eu-west-2:546933502184:key/83f283d1-7b58-4827-854c-db776149795f', 'DBSnapshotArn': 'arn:aws:rds:eu-west-2:546933502184:snapshot:rds:mv-ugc-postgres-2019-12-06-11-10', 'IAMDatabaseAuthenticationEnabled': False, 'ProcessorFeatures': [], 'DbiResourceId': 'db-CQ76MXOJJIFBOQ7WT63Y6AXUKA'}], 'ResponseMetadata': {'RequestId': '8290e734-5717-4c94-9ed5-1eaf0aa20ec6', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': '8290e734-5717-4c94-9ed5-1eaf0aa20ec6', 'content-type': 'text/xml', 'content-length': '1687', 'date': 'Fri, 06 Dec 2019 15:02:09 GMT'}, 'RetryAttempts': 0}}
    rds_stub.add_response(
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
def test_snapshot_identifer_with_snapshot_type(rds_stub, monkeypatch, datafiles):

    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("latest_snapshot", "true")
    monkeypatch.setenv("snapshot_id","")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv("rds_stack_name", "mv-rds-db-stack")
    monkeypatch.setenv("snapshot_type", "shared")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "")
    monkeypatch.setenv('target_db_instance', "target_instance")

    for testFile in datafiles.listdir():
            if fnmatch.fnmatch(testFile, "*db_describe_instance_response.json"):
                desc_db_inst_response = json.loads(testFile.read_text(encoding="'utf-8'"))
        
    rds_stub.add_response(
            'describe_db_instances',
            service_response=desc_db_inst_response
    )

    response = {'DBSnapshots': [{'DBSnapshotIdentifier': 'rds:mv-ugc-postgres-2019-12-06-11-10', 'DBInstanceIdentifier': 'mv-ugc-postgres', 'SnapshotCreateTime': datetime.datetime(2019, 12, 6, 11, 10, 33, 790000), 'Engine': 'postgres', 'AllocatedStorage': 20, 'Status': 'available', 'Port': 5432, 'AvailabilityZone': 'eu-west-2b', 'VpcId': 'vpc-19483f70', 'InstanceCreateTime': datetime.datetime(2019, 12, 6, 11, 9, 28, 424000), 'MasterUsername': 'ugc', 'EngineVersion': '9.6.15', 'LicenseModel': 'postgresql-license', 'SnapshotType': 'automated', 'OptionGroupName': 'default:postgres-9-6', 'PercentProgress': 100, 'StorageType': 'standard',
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

    i = {'db_instance': 'instance_i'}
    f = {'fragment': expected, 'requestId': 'my_request_id', 'params': i}

    res = handler(f, "hey")
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected

@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_instance_template_with_supplied_snapshot_identifier.json',
    FIXTURE_DIR / 'db_describe_instance_response.json'
)
def test_snapshot_with_supplied_identifier(rds_stub, monkeypatch, datafiles):
    
    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("latest_snapshot", "true")
    monkeypatch.setenv("snapshot_id","snaphost_id")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv("rds_stack_name", "mv-rds-db-stack")
    monkeypatch.setenv("snapshot_type", "shared")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "")
    monkeypatch.setenv('target_db_instance', "target_instance")

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_instance_template_with_supplied_snapshot_identifier.json",
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
def test_point_in_time_restore_to_a_specific_time(rds_stub, monkeypatch, datafiles, mocker):
    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("latest_snapshot", "false")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv("rds_stack_name", "mv-rds-db-stack")
    monkeypatch.setenv("snapshot_type", "shared")
    monkeypatch.setenv("restore_time", "2018-07-30T23:45:00.000Z")
    monkeypatch.setenv("restore_point_in_time", "true")
    monkeypatch.setenv('target_db_instance', "target_instance")
    test_snapshot_id = uuid.uuid4()
    mocker.patch.object(uuid, 'uuid4', return_value= test_snapshot_id)
    mocker.patch.object(time, 'sleep')

    for testFile in datafiles.listdir():
            if fnmatch.fnmatch(testFile, "*db_describe_instance_response.json"):
                desc_db_inst_response = json.loads(testFile.read_text(encoding="'utf-8'"))
        
    rds_stub.add_response(
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
    rds_stub.add_response(
        'restore_db_instance_to_point_in_time',
        expected_params={'SourceDBInstanceIdentifier':'mr1qf4ez7ls7xfn',
                'RestoreTime': '2018-07-30T23:45:00.000Z',
                'TargetDBInstanceIdentifier':'target_instance'},
        service_response=response
    )
    
    create_db_response = {
        "DBSnapshot": {
            "DBSnapshotIdentifier": "my-snapshot-1",
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
     #   expected_params={'DBSnapshotIdentifier':'*',
     #           'DBInstanceIdentifier':'target_instance'},
        service_response=create_db_response
    )

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_restore_to_point_in_time.json",
                                                       "db_instance_template.json")

    ss = {"DBSnapshotIdentifier": "b"+str(test_snapshot_id)}
    expected['Properties'].update(ss)
    i = {'db_instance': 'instance_i'}
    f = {'fragment': db_instance_template,
         'requestId': 'my_request_id', 'params': i}

    res = handler(f, "hey")
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected

@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_restore_to_point_in_time.json',
    FIXTURE_DIR / 'db_describe_instance_response.json'
)
def test_point_in_time_restore_latest_restorable_time(rds_stub, monkeypatch, datafiles, mocker):
    monkeypatch.setenv("properties_to_remove", "")
    monkeypatch.setenv("latest_snapshot", "false")
    monkeypatch.setenv("properties_to_add", "")
    monkeypatch.setenv("rds_stack_name", "mv-rds-db-stack")
    monkeypatch.setenv("snapshot_type", "shared")
    monkeypatch.setenv("restore_time", "")
    monkeypatch.setenv("restore_point_in_time", "true")
    monkeypatch.setenv('target_db_instance', "target_instance")
    test_snapshot_id = uuid.uuid4()
    """
    Monkey patch gives the following error: TypeError: 'UUID' object is not callable
    monkeypatch.setattr(uuid, "uuid4", test_snapshot_id)
    """
    mocker.patch.object(uuid, 'uuid4', return_value= test_snapshot_id) 
    mocker.patch.object(time, 'sleep')

    for testFile in datafiles.listdir():
            if fnmatch.fnmatch(testFile, "*db_describe_instance_response.json"):
                desc_db_inst_response = json.loads(testFile.read_text(encoding="'utf-8'"))
        
    rds_stub.add_response(
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
    rds_stub.add_response(
        'restore_db_instance_to_point_in_time',
        expected_params={'SourceDBInstanceIdentifier':'mr1qf4ez7ls7xfn',
                'TargetDBInstanceIdentifier':'target_instance',
                'UseLatestRestorableTime':True},
        service_response=response
    )

    create_db_response = {
        "DBSnapshot": {
            "DBSnapshotIdentifier": "my-snapshot-1",
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
     #   expected_params={'DBSnapshotIdentifier':'*',
     #           'DBInstanceIdentifier':'target_instance'},
        service_response=create_db_response
    )

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_restore_to_point_in_time.json",
                                                       "db_instance_template.json")

    
    ss = {"DBSnapshotIdentifier": "b"+str(test_snapshot_id)}
    expected['Properties'].update(ss)
    i = {'db_instance': 'instance_i'}
    f = {'fragment': db_instance_template,
         'requestId': 'my_request_id', 'params': i}

    res = handler(f, "hey")
    assert res['requestId'] == "my_request_id"
    assert res['fragment'] == expected

@pytest.mark.skip(reason="need to fix the implementation")
@pytest.mark.datafiles(
    FIXTURE_DIR / 'db_instance_template.json',
    FIXTURE_DIR / 'db_restore_to_point_in_time_db_already_exist.json',
    FIXTURE_DIR / 'db_describe_instance_response.json'
)
def test_point_in_time_restore_fails(rds_stub, monkeypatch, datafiles):
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
        
    rds_stub.add_response(
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
    rds_stub.add_client_error(
        'restore_db_instance_to_point_in_time',
        service_error_code='DBInstanceAlreadyExists',
        expected_params={'SourceDBInstanceIdentifier':'mr1qf4ez7ls7xfn',
                'TargetDBInstanceIdentifier':'target_instance',
                'UseLatestRestorableTime':True}
    )

    (expected, db_instance_template) = _read_test_data(datafiles,
                                                       "db_restore_to_point_in_time_db_already_exist.json",
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
                response = json.loads(testFile.read_text(encoding="utf-8"))
        
        db_instance_id = parse_db_identifier(response,'mv-rds-db-stack')
        assert db_instance_id == "mr1qf4ez7ls7xfn"
""" 
        rds_stub.add_response(
            'describe_db_instances',
            service_response=response
        ) """

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

@pytest.mark.datafiles(
    FIXTURE_DIR / 'ugc_database_stack_template.json'
)
def test_get_ugc_database_template(monkeypatch, cloudformation_stub, datafiles):

    monkeypatch.setenv("rds_stack_name", "mv-rds-db-stack")
    #(response, db_instance_template) = _read_test_data(datafiles,
    #                                                   "cloudformation_get_template_response.json",
    #                                                   "ugc_database_stack_template.json")
    
    io = StringIO()
    json.dump(template_response, io)
    cloudformation_stub.add_response(
        'get_template',
        service_response=template_response
    )

    template = get_ugc_database_template()

    assert db_instance_template == template  

