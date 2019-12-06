# ugc-rds-macro

This is a aws cloudformation macro that is used to manipulate the template fragment of type `AWS::RDS::DBInstance`



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

Below are a list of steps you should follow to setup the lambda

| Step                              | Action                                                       |
| --------------------------------- | ------------------------------------------------------------ |
| Create the bucket for the lambda. | `aws s3 mb s3://rds-snapshot-id-lambda`                      |
| build zip file                    | `make build`                                                 |
| Upload zip file to bucket.        | `aws s3 cp rdsmacroinstance.zip s3://rds-snapshot-id-lambda` |

##### Development

After making code changes run the following command to create a new zip, upload to s3 and update the lambda.

``upload.sh``

##### Testing

Within the `src` directory type:

`python -m pytest`

##### Lambda Configuration

Below are the list of global environment variables used by the lambda

| Parameter            | Description                                                  | Example                                                      |
| -------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| db_instance          | This is the arn to the database, used to fetch the latest snapshot | arn:aws:rds:eu-west-2:546933502184:db:mv-ugc-postgres        |
| latest_snapshot      | This is used to indicate whether to add the latest snapshot the template. Either True or False | True                                                         |
| properties_to_add    | A command separated list of items to add to the template, each item should be a wellormed json object. | ```{"BackupRetentionPeriod": {"Ref": "BackupRetentionDays"},{"DBName": { "Ref": "DatabaseName"}}`` |
| properties_to_remove | a comma seperated list of items to remove.                   | BackupRetentionPeriod, DBName                                |
| snap_shot_type       | If this value is not set not it will only fetch the manual and  automated snapshots. Refere to this:https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds.html#RDS.Client.describe_db_snapshots | shared                                                       |



### Cloudformation Stack

To generate the cloudformation stack.

| Step                          | Action                               |
| ----------------------------- | ------------------------------------ |
| Generate virtual env          | `make venv`                          |
| Activate virutal env          | `source env/bin/activate`            |
| generate cloudformation stack | `python infrastructure/rds_macro.py` |



