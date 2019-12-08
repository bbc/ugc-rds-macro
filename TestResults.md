The following table shows the results of updating individual elements within the database template.

### 1: Create inital database:

The following configuration will cause the cloudformation macro to pass the template without any modification. i.e Replicate live.

Lambda Configuration:

| Property              | Value              |      |
| --------------------- | ------------------ | ---- |
| rds_stack_name        | test-ugc-rds-stack |      |
| latest_snaphot        | false              |      |
| properties_to_add     |                    |      |
| properties_to_remove  |                    |      |
| restore_point_in_time | false              |      |
| restore_time          |                    |      |
| snapshot_type         |                    |      |
| target_db_instancei   | not_yet            |      |

##### Outcome

Creates an empty database called ugc with not tables etc:

To login you will need the database username and password you used to intially create it.

It creates a new url for connecting to the database: ie.

`mv-ugc-postgres.c66kz9sr8urn.eu-west-2.rds.amazonaws.cOUTLINE1: Create inital database:Outcome**2: Restore to latest snapshot:** om`

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

 

| Operation                                               | Outcome                                                    | Instance identifier                                      | Lamba  Configuration |
| ------------------------------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------- | -------------------- |
| Recreate initial database using the same stack as live  | creates an empty database called`ugc` with no tables.etc.. | mv-ugc-postgres.c66kz9sr8urn.eu-west-2.rds.amazonaws.com |                      |
| Recreate database from test. databases latest snaphost. | creates a new database from the snapshot.                  |                                                          |                      |
|                                                         |                                                            |                                                          |                      |
|                                                         |                                                            |                                                          |                      |
|                                                         |                                                            |                                                          |                      |

