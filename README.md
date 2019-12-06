# ugc-database-snapshot-id

This lambda returns the latest database snapshot arn.


Please refer to links for the possible values:

https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds.html#RDS.Client.describe_db_snapshots

SnapShotType:
Currently this value is not set, which results on only manual and  automated snapshots being returned.

