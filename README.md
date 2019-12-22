# Contents

 - [UGC rds macro](#ugc-rds-macro)
  - [Referencing the macro](#usage)
  - [Lambda](#lambda)
      - [Setup](#setup)
      - [Lambda State](#lambda--state)
      - [Lambda Configuration](#lambda-configuration)
  - [Development](#development)
  - [Running unit Tests](#runing--tests)
  - [Cloudformation Stack](#cloudformation--stack)
  - [Connect to Database](#connect--to--database)
  - [Point In Time Restore](#point--in--time--restore)

# ugc-rds-macro

AWS cloudformation macro that is used to manipulate template fragment of type `AWS::RDS::DBInstance`

When using macros, stack updates should be done via creating a changeset otherwise the lambda will be invoked multiple times. https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-changesets-execute.html



Creating snapshots and Point in time restore do not usually happen instantaneously. Therefore the following process should be followed for performing stack updates.

1. Initiate the operation.
2. Wait for the creation operation to complete.
3. Initiate the operation again.



# Usage

Due to  validation constraints imposed by troposphere it makes it slightly arduos to specify the transform, when using this macro in your template. The following is provided by troposhere to support fn intinsic functions https://github.com/cloudtools/troposphere/blob/master/troposphere/__init__.py#L391.

But found the process to be slightly obtuse. So used the following approach instead.

```
y = json.loads(t.to_json())
for key, value in y.items():
    if key == "Resources":
        for k, v in value.items():
            if  k == "UGCDatabase":
                f = {'Ref' : 'AWS::StackName'}
                s = {'stackname' : f}
                d = {'Name':'UgcRdsMacro', 'Parameters' : s} 
                k = {'Fn::Transform': d}
                v.update(k)
```

This file [Usage.md](Usage.md) contains examples of how to configure the lambda to perform the different operations.

[Backup]

# Lambda

## Setup

Below are a list of steps you should follow to setup the lambda. After completing these steps you should then create the cloudformation stack: Refer to the section: `Cloudformation Stack`

| Step                              | Action                                                       |
| --------------------------------- | ------------------------------------------------------------ |
| Create the bucket for the lambda. | `aws s3 mb s3://rds-snapshot-id-lambda`                      |
| build zip file                    | `make build`                                                 |
| Upload zip file to bucket.        | `aws s3 cp rdsmacroinstance.zip s3://rds-snapshot-id-lambda` |


## Lamba State

Create operations do not happen instantaneously, the following lambda tags are used to maintain the state. The table below describes the meaning of these tags.



| Global Tag                            | Meaning                                                   |
| ------------------------------------- | --------------------------------------------------------- |
| ugc:point-in-time:dbinstance          | waiting for point in time restore to complete             |
| ugc:point-in-time:snapshot:dbinstance | waiting for snapshot of point in time restore to complete |



## Lambda Configuration

Below are the list of global environment variables used by the lambda

| Parameter               | Description                                                  | Example                                                      |
| ----------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| log_level               | The verbosity of the logging displayed in cloudwatch:possible values [INFO, DEBUG, CRITICAL, WARNING, NOTSET] | INFO                                                         |
| rds_snapshot_stack_name | The stack of the database you want to take the snapshot of   | test-ugc-rds-stack                                           |
| replace_snapshot        | Used to indicate if db instance should be replaced with a snapshot. Accepted Values = =[True == replace db instance with snapshot, False == dont replace instance with snapshot ] | True                                                         |
| snapshot_id             | DBSnapshotIdentifier or DBSnapshotArn. If **blank** The latest snapshot of the database defined in the stack [rds_snapshot_stack_name] will be used | arn:aws:rds:eu-west-2:546933502184:snapshot:rds:test-ugc-postgres-2019-12-03-02-13 |
| restore_point_in_time   | Used to indicate whether to perform a point in time restore.Accepted Values = =[True == perform restore, False == do not perform restore] | True                                                         |
| restore_time            | The time to restore to. If empty restores to the latest restorable time. | 2009-09-07T23:45:00Z                                         |
| properties_to_add       | A command separated list of items to add to the template, each item should be a wellormed json object. | ```{"BackupRetentionPeriod": {"Ref": "BackupRetentionDays"}},{"DBName": { "Ref": "DatabaseName"}}`` |
| properties_to_remove    | a comma seperated list of items to remove.                   | BackupRetentionPeriod, DBName                                |
| snap_shot_type          | For accepatable values refer to this:https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds.html#RDS.Client.describe_db_snapshots | shared                                                       |


# Development

After making code changes run the following command to create a new zip, upload to s3 and update the lambda.

``upload.sh``

# Runing Tests

Within *src* directory type the following:

`python -m pytest`

`NOTE`: All tests that invoke operations that use `get_template` cloudformation api have been skipped because of an issue with the stubber provided by boto3. The following issue as been raised: https://github.com/boto/botocore/issues/1911


# Cloudformation Stack

Below are the instructions to  generate the cloudformation template which contains the macro and its associated lambda.

| Step                          | Action                                                |
| ----------------------------- | ----------------------------------------------------- |
| Generate virtual env          | `make venv`                                           |
| Activate virutal env          | `source env/bin/activate`                             |
| generate cloudformation stack | `python infrastructure/rds_macro.py > rds_macro.json` |

The generated template can then be used to create the cloudformation stack.

# Connect to Database

The python script  `scripts\test_db_tunnel.py` can be used to create a tunnnel to the newly created database.

Below are usage instructions. 

```

Usage:
  test_db_tunnel.py <env> <component> <port> <db>
  test_db_tunnel.py (-h | --help)


Commands:
   env               The environment
   component         The compoent eg. ugc-web-receier
   port              The postgress localhost port
   db                The address of the db to create the tunnel to.
```



The script [startup.sh](startup.sh) creates python virtual env and executes the tunnel script.

**NOTE**: You will need to change the address of the db instance.

# Point In Time Restore:

<u>Add Lambda role to database kms encryption key</u>

In order to perform a point in time restore the lambda role needs to be given permission to use the database kms encryption key. This is achieved by adding the lambda role to the key policy of the encryption key.

The aliases for database encryption keys use the following naming convention: 

**{environment}-ugc-rds-encryption-key** where the *environment* is the parameter that is specified within the database stack.

Within the folder **scripts** the following files can be used to add the lambda role to the key policy.

| File                                           | Description                                                  | Usage                     |
| ---------------------------------------------- | ------------------------------------------------------------ | ------------------------- |
| [key_policy.json](scripts/key_policy.json)     | The contains the kms key policy to give the lambda.          |                           |
| [add_key_policy.sh](scripts/add_key_policy.sh) | script used to add the policy to the database encryption key.  **./add_key_policy.sh {environment}**. NOTE: This will replace the key policy with the contents of the items specified in [key_policy.json](scripts/key_policy.json)| *./add_key_policy.sh int* |



