NOTE: It takes approximately 20 minutes to create a new database using cloudformation.


### 1: Create inital database:

The following configuration will cause the cloudformation macro to pass the template without any modification. i.e Replicate live.

Lambda Configuration:

| Property              | Value            |
| -------------------   | ----------------:|
| replace_with_snapshot | false             |
| restore_point_in_time | false             |


##### Outcome

Creates an empty database called ugc with not tables etc:

To login you will need the database username and password you used to intially create it.

It creates a new url for connecting to the database: ie.

`mv-ugc-postgres.c66kz9sr8urn.eu-west-2.rds.amazonaws.com`

### 2: Restore to latest snapshot:

The following table shows the lambda configuration which will cause the macro to modify the stack template so that the database is restored to the latest manual snapshot of the instance specified in the stack *test-ugc-rds-stack*. 

Following poperies are removed:

`DBInstanceIdentifier`and `DBName`

And the following property  is added

`DBSnapshotIdentifier`

| Property                | Value              |
| ----------------------- | ------------------ |
| rds_snapshot_stack_name | test-ugc-rds-stack |
| replace_with_snapshot   | true               |
| restore_point_in_time   | false              |
| snapshot_type           | Manual             |

##### Outcome:

Creates a new database using the latest snapshot of the database defined within the stack specifed by the variable *rds_snapshot_stack_name*.

You will need to login in using the credentials for the test-ugc-database.

It inherits the kms key used by the snapshot. If you restore from a diferent environment, it will use the kms key for that environment.

### 3: Restore to Specific snapshot:

The following table shows the lambda configuration which will cause the macro to modify the stack template so that the database is restored to the snapshot specified.

Following poperies are removed:

`DBInstanceIdentifier`and `DBName`

And the following property  is added

`DBSnapshotIdentifier`

| Property                | Value                                                        |
| ----------------------- | ------------------------------------------------------------ |
| rds_snapshot_stack_name | test-ugc-rds-stack                                           |
| replace_with_snapshot   | true                                                         |
| restore_point_in_time   | false                                                        |
| snapshot_id             | arn:aws:rds:eu-west-2:546933502184:snapshot:rds:mv-ugc-postgres-2019-12-06-11-10 |

##### Outcome:

Creates a new database using the snapshot specified.

It inherits the kms key used by the snapshot. If you restore from a diferent environment, it will use the kms key for that environment.

### 4: Add Properties

The following configuration is used to change the *BackupRetentionPeriod* and the *DBName*.

| Property              | Value                                                        |      |
| --------------------- | ------------------------------------------------------------ | ---- |
| replace_with_snapshot | false                                                        |      |
| restore_point_in_time | false                                                        |      |
| properties_to_add     | ```{"BackupRetentionPeriod": "100"},{"DBName": "new_db_name"`` |      |

### 5: Remove Properties

The following configuration is used to remove *BackupRetentionPeriod* and *DBName* properties.

| Property              | Value                             |      |
| --------------------- | --------------------------------- | ---- |
| replace_with_snapshot | false                             |      |
| restore_point_in_time | false                             |      |
| properties_to_remove  | *BackupRetentionPeriod*, *DBName* |      |

### 6: Restore to Latest Restorable Point:

Before performing a point in time restore make sure there are no lambda tags that begin with **ugc:**

The lambda configuration below needs to be invoked three times.

###### 1:First Invocation of the lambda:

​	Create the db instance to the latest restorable time, this process is dependent on the size of the database.

​	Creates a lambda tag **ugc:point-in-time:dbinstance** using the new instance id as the value.

###### 2:Second Invocation of the lambda:

​	Creates a snaphost of the instance specified by the lambda tag: **ugc:point-in-time:dbinstance**

​	If the operation does not happen instantaneously it will create the following lambda tag **ugc:point-in-time:snapshot:dbinstance** using the snapshot id as the value.  

###### 3:Third Invocation of the lambda:

​	Updates the stack with the snapshot id.

| Property              | Value |      |
| --------------------- | ----- | ---- |
| replace_with_snapshot | false |      |
| restore_point_in_time | True  |      |
| restore_time          |       |      |



### 7: Restore to a specific point in time:

Before performing a point in time restore make sure there are no lambda tags that begin with **ugc:**

The lambda configuration below needs to be invoked three times.

###### 1:First Invocation of the lambda:

​	Create the db instance to the time specified, this process is dependent on the size of the database.

​	Creates a lambda tag **ugc:point-in-time:dbinstance** using the new instance id as the value.

###### 2:Second Invocation of the lambda:

​	Creates a snaphost of the instance specified by the lambda tag: **ugc:point-in-time:dbinstance**

​	If the operation does not happen instantaneously it will create the following lambda tag **ugc:point-in-time:snapshot:dbinstance** using the snapshot id as the value.  

###### 3:Third Invocation of the lambda:

​	Updates the stack with the snapshot id.



| Property              | Value                |
| --------------------- | -------------------- |
| replace_with_snapshot | false                |
| restore_point_in_time | true                 |
| restore_time          | 2009-09-07T23:45:00Z |

