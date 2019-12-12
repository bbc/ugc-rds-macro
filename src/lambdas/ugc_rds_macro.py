import json
import os
import sys
import time
import uuid
import traceback
from io import StringIO

import boto3
from botocore.exceptions import ClientError

client = boto3.client('rds')
cf_client = boto3.client('cloudformation')
lambda_client = boto3.client('lambda')
lambda_arn = None
# This is support the issue with boto3 stubber not working for get_template
do_not_ignore_get_template = True
def __add_snapshot_identifier(fragment, snapshot_id):
    for key, value in fragment.items():
        if key == 'Properties':
            db_snapshot_id = {'DBSnapshotIdentifier': snapshot_id} 
            value.update(db_snapshot_id)

def check_if_snapshot_identifier_needs_be_added(fragment):
    snapshot_id = get_snapshot_identifier(get_ugc_database_template())

    if snapshot_id != None and get_snapshot_identifier(fragment) == None:
        __remove_property(fragment,"DBInstanceIdentifier")
        __remove_property(fragment,"DBName")
        __add_snapshot_identifier(fragment, snapshot_id)

def get_ugc_database_template():

    if do_not_ignore_get_template:
        rds_stack_name = os.environ['rds_stack_name'].rstrip()
        print("this stack name {0}".format(rds_stack_name))
        try:
            response = cf_client.get_template(StackName = rds_stack_name, TemplateStage='Processed')
            print("response from get_ugc_database_template [{0}]".format(json.dumps(response)))
            print("ugc_database {0}".format(json.dumps(response['TemplateBody']['Resources']['UGCDatabase'])))
            return json.dumps(response['TemplateBody']['Resources']['UGCDatabase'])
        except ClientError as e:
            print("error getting template [{0}]".format(str(e)))

        
    return None


def get_snapshot_identifier(dbinstance_template):

    db = dbinstance_template
    if type(dbinstance_template) is str:
        db  = json.loads(dbinstance_template)
    
    try:
        snapshot_id = db["Properties"]["DBSnapshotIdentifier"]
    except KeyError:
        return None

    return snapshot_id

def update_snapshot(fragment):

    # Fetching latest snapshot
    rds_stack_name = os.environ['rds_stack_name'].rstrip().lower()
    print("rds_stack_name [{0}]".format(rds_stack_name))
    latest_snapshot = os.environ.get('latest_snapshot').rstrip().lower()
    print('latest_snapshot {0}'.format(latest_snapshot))
    if latest_snapshot == "true":
        snapshot_id = os.environ.get("snapshot_id").rstrip()

        __remove_property(fragment,"DBInstanceIdentifier")
        __remove_property(fragment,"DBName")

        if snapshot_id:
            __add_snapshot_identifier(fragment, snapshot_id)

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
                    __add_snapshot_identifier(fragment, snap_shot_id)

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
            for key, value in fragment.items():
                if key == 'Properties':
                    p = json.loads(prop_to_add.rstrip())
                    value.update(p)

def remove_properties(fragment):
    # Remving properties
    properties_to_remove = os.environ['properties_to_remove']
   
    props_to_remove = properties_to_remove.split(",")
    if properties_to_remove.rstrip():
        for prop_to_remove in props_to_remove:
            __remove_property(fragment, prop_to_remove)
   
def __remove_property(fragment, prop):
    try:
        for key, value in fragment.items():
            if key == 'Properties':
                del value[prop.strip()]
    except KeyError:
        print("key does not exist `{}`".format(prop))

def get_instance_state(instance_id):

    try:
        instances = client.describe_db_instances(DBInstanceIdentifier = instance_id)
        return instances['DBInstances'][0]['DBInstanceStatus']
    except ClientError as e:
        print("error calling describe_db_instances for {0}={1}]".format(instance_id, str(e)))
        return None
        
def check_for_tag(tag):
    tags = lambda_client.list_tags(Resource=lambda_arn)
    for k,v in tags['Tags'].items():
        if k == "ugc:point-in-time:dbinstance:"+tag:
            return v
    
    return None

def add_tag(key, value):
    lambda_client.tag_resource(Resource=lambda_arn, Tags={"ugc:point-in-time:dbinstance:"+tag: value})

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
        
        state = get_instance_state(target_db_instance)

        if db_instance and state == None:
            try:
                if restore.lower() == "true" and restore_time:
                    resp = client.restore_db_instance_to_point_in_time(
                        SourceDBInstanceIdentifier = db_instance,
                        TargetDBInstanceIdentifier = target_db_instance,
                        RestoreTime=restore_time)
                elif restore.lower() == "true":
                    resp = client.restore_db_instance_to_point_in_time(
                        SourceDBInstanceIdentifier = db_instance,
                        TargetDBInstanceIdentifier = target_db_instance,
                        UseLatestRestorableTime = True)
                                    

            except ClientError as e:
                print("problems creating point in time restore = [%s]" % e)
            
            if resp:
                    print("response_from_point_in_time_restore = {0}".format(resp))
            
            deployed_db_template = get_ugc_database_template()
            print("deployed template{0}".format(deployed_db_template))
            return json.loads(deployed_db_template)
            """
                if "DBInstanceAlreadyExists" in str(e):
                    dbInstanceIdentifer = {"DBInstanceIdentifier": target_db_instance}
                    print("dbInstanceIdentifier: {0}".format(target_db_instance))
                    for key, value in fragment.items():
                        if key == 'Properties':
                            value.update(dbInstanceIdentifer)
            """
                
        elif db_instance and state is 'creating':
            print("point in time restore has not finnished creating yet:{0}".format(target_db_instance))
            t = get_ugc_database_template()
            print("deployed template{0}".format(t))
            return json.loads(t)

        elif db_instance and state is 'available':
            restored_snapshot_id = "a"+str(uuid.uuid4())
            res = client.create_db_snapshot(
                    DBSnapshotIdentifier = restored_snapshot_id,
                    DBInstanceIdentifier = target_db_instance)
            print("resp from create_snapshot_of_point_in_time={0}".format(str(res)))
            __remove_property(fragment, "DBInstanceIdentifier")
            __remove_property(fragment, "DBName")
            __add_snapshot_identifier(fragment, restored_snapshot_id)

    return fragment
        

def handler(event, context):
    lambda_arn = context.invoked_function_arn
    print("lambda_arn{0}".format(lambda_arn))
    print('this is the event = {}'.format(event))
    fragment = event["fragment"]
    status = "success"
    print('fragment_before_modification={0}'.format(fragment))

    try:
        get_ugc_database_template()
        update_snapshot(fragment)
        remove_properties(fragment)
        add_properties(fragment)
        fragment = point_in_time_restore(fragment)   
        check_if_snapshot_identifier_needs_be_added(fragment)     
    except:
        traceback.format_exc()
        e = sys.exc_info()[0]
        print("something went wrong:{0}".format(str(e)))
        deployed_template = get_ugc_database_template()
        if deployed_template:
            fragment = json.loads()
        
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
                
           if str(k) == str('DBSubnetGroup'):
                if str(v['DBSubnetGroupName']).startswith(key):
                    db_instance_id = db_inst_id
                    db_subnet_group = v['DBSubnetGroupName']
                    found = True

    if found:
        return db_instance_id

    return found
