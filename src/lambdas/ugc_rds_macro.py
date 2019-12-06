import boto3
import os
import json




def handler(event, context):
    print('this is the event = {}'.format(event))

    fragment = event["fragment"]
    status = "success"

    expec = str('true')

    print('fragment_before_modification={0}'.format(fragment))

    latest_snaphost = os.environ.get('latest_snapshot')
    print("type'{0}'".format(repr(latest_snaphost)))
    print('latest_snapshot {0}'.format(latest_snaphost.rstrip().strip().lower()))
    print('latest_snapshot_evalutation {0}'.format(latest_snaphost.rstrip().strip().lower() in expec))
    
    if latest_snaphost.strip().lower() in expec:
        
        db_instance = os.environ['db_instance']
        if db_instance.strip():
            client = boto3.client('rds')
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

    property_to_remove = os.environ['property_to_remove']
    print("to remove {0}".format(property_to_remove))

    props_to_remove = property_to_remove.split(",")
    if len(props_to_remove) > 0:
        for prop_to_remove in props_to_remove:
            for key, value in fragment.items():
                if key == 'Properties':
                    del value[prop_to_remove]
    print('fragment_after_removing_property={0}'.format(fragment))

    property_to_add = os.environ['property_to_add']
    print("to addd {0}".format(property_to_add))

    props_to_add = property_to_add.split(',')
    if len(props_to_add) > 0:
        for prop_to_add in props_to_add:
            for key, value in fragment.items():
                if key == 'Properties':
                    p = json.loads(prop_to_add)
                    value.update(p)
            print('fragment_after_adding_property={0}'.format(fragment))
    
    print('fragment_after_modification={0}'.format(fragment))
    return {
        "requestId": event["requestId"],
        "status": status,
        "fragment": fragment,
    }