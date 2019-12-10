NOTE: It takes approximately 20 minutes to create a new database using cloudformation.


### 1: Create inital database:

The following configuration will cause the cloudformation macro to pass the template without any modification. i.e Replicate live.

Lambda Configuration:

| Property              | Value            |
| -------------------   | ----------------:|
| rds_stack_name        | test-ugc-rds-stack|
| latest_snaphot        | false             |
| properties_to_add     |                   |
| properties_to_remove  |                   |
| restore_point_in_time | false             |
| restore_time          |                   |
| snapshot_type         |                   |
| target_db_instancei   | not_yet           |


##### Outcome

Creates an empty database called ugc with not tables etc:

To login you will need the database username and password you used to intially create it.

It creates a new url for connecting to the database: ie.

`mv-ugc-postgres.c66kz9sr8urn.eu-west-2.rds.amazonaws.com`

### 2: Restore to latest snapshot:

The following table shows the lambda configuration which will cause the macro to modify the stack template so that the database is restored to the latest snapshot.

Following poperies are removed:

`DBInstanceIdentifier`and `DBName`

And the following property  is added

`DBSnapshotIdentifier`



| Property              | Value                       |      |
| --------------------- | --------------------------- | ---- |
| rds_stack_name        | test-ugc-rds-stack          |      |
| latest_snaphot        | true                        |      |
| properties_to_add     |                             |      |
| properties_to_remove  | DBInstanceIdentifier,DBName |      |
| restore_point_in_time | false                       |      |
| restore_time          |                             |      |
| snapshot_type         |                             |      |
| target_db_instancei   | not_yet                     |      |

##### Outcome:

Creates a new database that points the snapshot taken from test-ugc-database.

You will need to login in using the credentials for the test-ugc-database.

It creates a new url that will be used to connect to the database

It creates a random identifier for the database.

It inherits the kms key used by the snapshot. If you restore from a diferent environment, it will use the kms key for that environment.

### 3: Restore to Latest Restorable Point:

The following table shows the lambda configuration which will cause the macro to restore the database to  the latest point in time. But makes no changes to the cloudformation template.

| Property              | Value                       |      |
| --------------------- | --------------------------- | ---- |
| rds_stack_name        | mv-rds-db-stack             |      |
| latest_snaphot        | false                       |      |
| properties_to_add     |                             |      |
| properties_to_remove  | DBInstanceIdentifier,DBName |      |
| restore_point_in_time | true                        |      |
| restore_time          |                             |      |
| snapshot_type         |                             |      |
| target_db_instancei   | my_target_instance          |      |

### 4: Restore to a specific point in time:

The following table shows the lambda configuration which will cause the macro to restore the database to  the latest point in time. But makes no changes to the cloudformation template.

| Property              | Value                       |      |
| --------------------- | --------------------------- | ---- |
| rds_stack_name        | mv-rds-db-stack             |      |
| latest_snaphot        | false                       |      |
| properties_to_add     |                             |      |
| properties_to_remove  | DBInstanceIdentifier,DBName |      |
| restore_point_in_time | true                        |      |
| restore_time          | 2018-07-30T23:45:00.000Z    |      |
| snapshot_type         |                             |      |
| target_db_instancei   | my_target_instance          |      |

### 5: Validate point in time restore:

Below are the tests which will be performed in order to validate the database restoration procedure.

##### Outline of Test steps:

1. Restore to point in time on original database

   1. Create db instance
   2. Import dump database
   3. modify data ... wait for ten minutes .. modify data.
   4. Restore back to the first modification

   

2. Restore to point in time from a snapshot.

   1. Create db instance
   2. swith to using snapshot
   3. modify data.. wait for 10 minutes.. modify data
   4. restore back to first modification.

