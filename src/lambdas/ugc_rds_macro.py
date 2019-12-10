import boto3
from botocore.exceptions import ClientError
import os
import json
import uuid

from io import StringIO
client = boto3.client('rds')

def update_snapshot(fragment):

    # Fetching latest snapshot
    rds_stack_name = os.environ['rds_stack_name'].rstrip().lower()
    print("rds_stack_name [{0}]".format(rds_stack_name))
    latest_snapshot = os.environ.get('latest_snapshot').rstrip().lower()
    print("type'{0}'".format(type(latest_snapshot)))
    print('latest_snapshot {0}'.format(latest_snapshot))
    print('latest_snapshot_evalutation {0}'.format(latest_snapshot))
    if latest_snapshot == "true":
        snapshot_id = os.environ.get("snapshot_id").rstrip()

        __remove_property(fragment,"DBInstanceIdentifier")
        __remove_property(fragment,"DBName")

        if snapshot_id:
            for key, value in fragment.items():
                if key == 'Properties':
                    db_snapshot_id = {'DBSnapshotIdentifier': snapshot_id} 
                    value.update(db_snapshot_id)

        elif rds_stack_name:
            snapshot_type = os.environ['snapshot_type'].rstrip()
            instances = client.describe_db_instances()
            db_instance = parse_db_identifier(instances, rds_stack_name)
            print("checking resotre: db_instance:{0}".format(db_instance))
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


def add_properties(fragment):
    # Adding properties
    properties_to_add = os.environ['properties_to_add']
    props_to_add = properties_to_add.split(",")
    if properties_to_add.rstrip():
        for prop_to_add in props_to_add:
            print("props to sadd {0}".format(prop_to_add))
            for key, value in fragment.items():
                if key == 'Properties':
                    p = json.loads(prop_to_add.rstrip())
                    value.update(p)

def remove_properties(fragment):
    # Remving properties
    properties_to_remove = os.environ['properties_to_remove']
    print("to remove {0}".format(properties_to_remove))

    props_to_remove = properties_to_remove.split(",")
    if properties_to_remove.rstrip():
        for prop_to_remove in props_to_remove:
            __remove_property(fragment, prop_to_remove)

   
def __remove_property(fragment, prop):
    print("frag = {0} prop = {1}".format(fragment, prop))
    try:
        for key, value in fragment.items():
            if key == 'Properties':
                del value[prop.strip()]
    except KeyError:
        print("key does not exist `{}`".format(prop))

def point_in_time_restore(fragment):
    # Restoring to point in time
    latest_snapshot = os.environ.get('latest_snapshot').rstrip().lower()
    rds_stack_name = os.environ['rds_stack_name'].rstrip()
    restore = os.environ['restore_point_in_time'].rstrip()
    restore_time = os.environ['restore_time'].rstrip()
    target_db_instance = os.environ['target_db_instance'].rstrip()
    print("target_db_instance:{0}".format(target_db_instance))
    resp = None
    print("this is restor[{0}]".format(restore))
    if restore and latest_snapshot != "true":
        instances = client.describe_db_instances()
        db_instance = parse_db_identifier(instances, rds_stack_name)
        
        if db_instance:
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
                """
                if "DBInstanceAlreadyExists" in str(e):
                    dbInstanceIdentifer = {"DBInstanceIdentifier": target_db_instance}
                    print("dbInstanceIdentifier: {0}".format(target_db_instance))
                    for key, value in fragment.items():
                        if key == 'Properties':
                            value.update(dbInstanceIdentifer)
                """
    if resp:
        print("response_from_point_in_time_restore = {0}".format(resp))
        
        restored_snapshot_id = str(uuid.uuid4())
        res = client.create_db_snapshot(
            DBSnapshotIdentifier="a"+restored_snapshot_id,
            DBInstanceIdentifier=str(resp['DBInstance']['DBInstanceIdentifier']))
        __remove_property(fragment,"DBInstanceIdentifier")
        __remove_property(fragment,"DBName")
        db_snapshot_id = {'DBSnapshotIdentifier': "b"+restored_snapshot_id}
        for key, value in fragment.items():
                if key == 'Properties':
                    value.update(db_snapshot_id)

def handler(event, context):
    print('this is the event = {}'.format(event))
    fragment = event["fragment"]
    status = "success"
    print('fragment_before_modification={0}'.format(fragment))

    update_snapshot(fragment)
    remove_properties(fragment)
    add_properties(fragment)
    point_in_time_restore(fragment)        
  
    print("fragment_after_modification={0}".format(fragment))
    return {
        "requestId": event["requestId"],
        "status": status,
        "fragment": fragment,
    }

def parse_db_identifier(response, key):
    found = None
    print("DBInstances {0}".format(str(response)))
    for item in response['DBInstances']:
        for k,v in item.items():
           if str(k) in str('DBInstanceIdentifier'):
              db_inst_id = str(v)
           """
                Example of how to get the url used to connect to the database
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