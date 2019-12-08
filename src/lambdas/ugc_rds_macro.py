import boto3
from botocore.exceptions import ClientError
import os
import json

from io import StringIO
client = boto3.client('rds')

def handler(event, context):
    print('this is the event = {}'.format(event))
    rd_stack_name = os.environ['rds_stack_name'].rstrip()
    fragment = event["fragment"]
    status = "success"

    # Fetching latest snapshot
    expec = str('true')
    print('fragment_before_modification={0}'.format(fragment))
    latest_snaphost = os.environ.get('latest_snapshot')
    print("type'{0}'".format(repr(latest_snaphost)))
    print('latest_snapshot {0}'.format(latest_snaphost.rstrip().strip().lower()))
    print('latest_snapshot_evalutation {0}'.format(latest_snaphost.rstrip().strip().lower() in expec))
    if latest_snaphost.strip().lower() in expec:
        
        if rd_stack_name:
            snapshot_type = os.environ['snapshot_type'].rstrip()
            instances = client.describe_db_instances()
            db_instance = parse_db_identifier(instances, rd_stack_name)
            print("checking resotre: db_instance{0}".format(db_instance))
            if db_instance:
                if snapshot_type:
                    snapshots = client.describe_db_snapshots(
                        DBInstanceIdentifier=db_instance,
                        SnapshotType=snapshot_type
                    )
                else:
                    snapshots = client.describe_db_snapshots(
                        DBInstanceIdentifier=db_instance
                    )

                print('snapshots_id={0}'.format(snapshots))

                all_snap_shots = snapshots['DBSnapshots']
                if len(all_snap_shots) > 0:
                    snap_shot_id = all_snap_shots[0]['DBSnapshotArn']
    
                    for key, value in fragment.items():
                        if key == 'Properties':
                            db_snapshot_id = {'DBSnapshotIdentifier': snap_shot_id} 
                            value.update(db_snapshot_id)
                else:
                    for key, value in fragment.items():
                        if key == 'Properties':
                            del value['DBSnapshotIdentifier']

    # Remving properties
    properties_to_remove = os.environ['properties_to_remove']
    print("to remove {0}".format(properties_to_remove))

    props_to_remove = properties_to_remove.split(",")
    if properties_to_remove.rstrip():
        for prop_to_remove in props_to_remove:
            for key, value in fragment.items():
                if key == 'Properties':
                    del value[prop_to_remove.strip()]
    print('fragment_after_removing_property={0}'.format(fragment))

    # Adding properties
    properties_to_add = os.environ['properties_to_add']
    props_to_add = properties_to_add.split(",")
    if properties_to_add.rstrip():
        for prop_to_add in props_to_add:
            for key, value in fragment.items():
                if key == 'Properties':
                    p = json.loads(prop_to_add.rstrip())
                    value.update(p)
            


    # Restoring to point in time
    restore = os.environ['restore_point_in_time'].rstrip()
    restore_time = os.environ['restore_time'].rstrip()
    target_db_instance = os.environ['target_db_instance'].rstrip()
    print("target_db_instance:{0}".format(target_db_instance))
    resp = None
    print("this is restor{0}".format(restore))
    if restore and latest_snaphost.lower() != "true":
        instances = client.describe_db_instances()
        print("instances {0}".format(instances))
        db_instance = parse_db_identifier(instances, rd_stack_name)
        
        if db_instance:
            print("checking restoring: db_instance:{0}".format(db_instance))
            try:
                if restore.lower() == "true" and restore_time:
                    resp = client.restore_db_instance_to_point_in_time(
                        SourceDBInstanceIdentifier=db_instance,
                        TargetDBInstanceIdentifier=target_db_instance,
                        RestoreTime=restore_time)
                elif restore.lower() == "true":
                    resp = client.restore_db_instance_to_point_in_time(
                        SourceDBInstanceIdentifier=db_instance,
                        TargetDBInstanceIdentifier=target_db_instance,
                        UseLatestRestorableTime=True)
            except ClientError as e:
                print("problems restoring = [%s]" % e)
            
    if resp:
        print("response_from_point_in_time_restore = {0}".format(resp))
        dbInstanceIdentifer = {"DBInstanceIdentifier": str(resp['DBInstance']['DBInstanceIdentifier'])}
        print("dbInstanceIdentifier: {0}".format(dbInstanceIdentifer))
        for key, value in fragment.items():
                if key == 'Properties':
                    value.update(dbInstanceIdentifer)
      
    print("fragment_after_modification={0}".format(fragment))
    return {
        "requestId": event["requestId"],
        "status": status,
        "fragment": fragment,
    }

def parse_db_identifier(response, key):
    found = None
    for item in response['DBInstances']:
       for k,v in item.items():
           if str(k) in str('DBInstanceIdentifier'):
              db_inst_id = str(v)
                
          
           """
                if str(k) in str('Endpoint'):
               address = v['Address']
           """

           if str(k) in str('DBSubnetGroup'):
                if str(v['DBSubnetGroupName']).startswith(key):
                    db_instance_id = db_inst_id
                    db_subnet_group = v['DBSubnetGroupName']
                    found = True

    if found:
        return db_instance_id

    return None