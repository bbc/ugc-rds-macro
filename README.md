# ugc-rds-macro

This is a aws cloudformation macro that is used to manipulate the template fragment of type `AWS::RDS::DBInstance`

NOTE:  The macro does not modify the existing template but applies changes to new template which contains the construct used to invoke the macro `Fn::Transfom`. It then replaces the existing template with newly generated template but with the following construct `Fn::Transform` removed.

### Usage

Due to  validation constraints imposed by troposphere it makes it slightly arduos to specify the transform, when using this macro in your template. The following is provided by troposhere to support fn intinsic functions https://github.com/cloudtools/troposphere/blob/master/troposphere/__init__.py#L391.

But found the process to be slightly obtuse. So used the following approach instead.

```y = json.loads(t.to_json())
y = json.loads(t.to_json())
for key, value in y.items():
    if key == "Resources":
        for k, v in value.items():
            if  k == "RdsPostGresDatabase":
                d = {'Name':'UgcRdsMacro'} 
                k = {'Fn::Transform': d}
                v.update(k)
```

### Lambda

##### Setup

Below are a list of steps you should follow to setup the lambda. After completing these steps you should then create the cloudformation stack: Refer to the section: `Cloudformation Stack`

| Step                              | Action                                                       |
| --------------------------------- | ------------------------------------------------------------ |
| Create the bucket for the lambda. | `aws s3 mb s3://rds-snapshot-id-lambda`                      |
| build zip file                    | `make build`                                                 |
| Upload zip file to bucket.        | `aws s3 cp rdsmacroinstance.zip s3://rds-snapshot-id-lambda` |



##### Development

After making code changes run the following command to create a new zip, upload to s3 and update the lambda.

``upload.sh``

##### Testing

`NOTE`: All tests that invoke operations that use `get_template` cloudformation api have been skipped because of an issue with the stubber provided by boto3. The following issue as been raised: https://github.com/boto/botocore/issues/1911

`python -m pytest`

##### Lambda Configuration

Below are the list of global environment variables used by the lambda

| Parameter               | Description                                                  | Example                                                      |
| ----------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| log_level               | The verbosity of the logging displayed in cloudwatch:possible values [INFO, DEBUG, CRITICAL, WARNING, NOTSET] | INFO                                                         |
| rds_snapshot_stack_name | The stack of the database you want to take the snapshot of   | test-ugc-rds-stack                                           |
| replace_snapshot        | Used to indicate if db instance should be replaced with a snapshot. Accepted Values = =[True == replace db instance with snapshot, False == dont replace instance with snapshot ] | True                                                         |
| snapshot_id             | AWS ARN of the the snapshot. If **blank** The latest snapshot of the database defined in the stack supplied by this variable [rds_snapshot_stack_name] will be used | arn:aws:rds:eu-west-2:546933502184:snapshot:rds:test-ugc-postgres-2019-12-03-02-13 |
| restore_point_in_time   | Used to perform a point in time restore.                     | True                                                         |
| restore_time            | The time to restore from. If empty restores from the latest restorable time. | 2009-09-07T23:45:00Z                                         |
| properties_to_add       | A command separated list of items to add to the template, each item should be a wellormed json object. | ```{"BackupRetentionPeriod": {"Ref": "BackupRetentionDays"}},{"DBName": { "Ref": "DatabaseName"}}`` |
| properties_to_remove    | a comma seperated list of items to remove.                   | BackupRetentionPeriod, DBName                                |
| snap_shot_type          | If this value is not set not it will only fetch the manual and  automated snapshots. Refere to this:https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds.html#RDS.Client.describe_db_snapshots | shared                                                       |

### Cloudformation Stack

Below are the instructions to  generate the cloudformation template which contains the macro and its associated lambda.

| Step                          | Action                                                |
| ----------------------------- | ----------------------------------------------------- |
| Generate virtual env          | `make venv`                                           |
| Activate virutal env          | `source env/bin/activate`                             |
| generate cloudformation stack | `python infrastructure/rds_macro.py > rds_macro.json` |

The generated template can then be used to create the cloudformation stack.

#### Connect to Database

The python script  `scripts\test_db_tunnel.py` can be used to create a tunnnel to the newly created database.

Below are usag instructions. 

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



The script `startup.sh` creates python virtual env and executes the tunnel script.

**NOTE**: You will need to change the address of the db instance.

##### Point In Time Restore:

In order to be able to use this functionality the lambda role needs to be given permission to access the `kms` key used to encrypt and decrypt the database:

Below is an example policy:

```
 {
            "Sid": "Allow Use of Key",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::546933502184:role/ugc-rds-db-macro-FunctionRole-10ZH7C360U4QY"
            },
            "Action": [
                "kms:Create*",
                "kms:Describe*",
                "kms:Enable*",
                "kms:List*",
                "kms:Put*",
                "kms:Update*",
                "kms:Revoke*",
                "kms:Disable*",
                "kms:Get*",
                "kms:Delete*",
                "kms:ScheduleKeyDeletion",
                "kms:CancelKeyDeletion"
            ],
            "Resource": "*"
        }
```

In order to use this new instance you will need to take a snapshot of the instance and then update the stack with this new snaphost id. 

