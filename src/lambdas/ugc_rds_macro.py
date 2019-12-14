import json
import logging
import os
import sys
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from io import StringIO

import boto3
from botocore.exceptions import ClientError
from dateutil.parser import parse

logger = logging.getLogger(__name__)

snap_shot_types = set(['automated', 'manual', 'shared', 'public', 'awsbackup'])


client = boto3.client('rds')
cf_client = boto3.client('cloudformation')
lambda_client = boto3.client('lambda')
lambda_arn = "arn:aws:lambda:eu-west-2:546933502184:function:int-ugc-rds-macro"

do_not_ignore_get_template = True
point_in_time_db_instance_tag = 'ugc:point-in-time:dbinstance'


def _add_snapshot_identifier(fragment, snapshot_id):
    for key, value in fragment.items():
        if key == 'Properties':
            db_snapshot_id = {'DBSnapshotIdentifier': snapshot_id}
            value.update(db_snapshot_id)


def check_if_snapshot_identifier_needs_be_added(fragment, stack_of_interest):
    func_name = traceback.extract_stack(None, 2)[0][2]

    fragment_snapshot_id = get_snapshot_identifier(fragment)
    snapshot_id = get_snapshot_identifier(
        get_ugc_database_template(stack_of_interest))
    logger.info(":{0}:snapshot id of [fragment = {1} deployed = {2} ".format(
        func_name,  fragment_snapshot_id, snapshot_id))
    if snapshot_id != None and fragment_snapshot_id == None:
        logger.debug(":{0}:add snapshot id to template {1}".format(
            func_name, snapshot_id))
        _remove_property(fragment, "DBInstanceIdentifier")
        _remove_property(fragment, "DBName")
        _add_snapshot_identifier(fragment, snapshot_id)

    return get_snapshot_identifier(fragment)


def get_ugc_database_template(stack_of_interest):
    func_name = traceback.extract_stack(None, 2)[0][2]
    if do_not_ignore_get_template:
        try:
            response = cf_client.get_template(
                StackName=stack_of_interest, TemplateStage='Processed')

            logger.debug(":{0}:deployed_template:{1}".format(
                func_name, str(json.dumps(response,  default=str))))
            db_inst_temp = json.dumps(
                response['TemplateBody']['Resources']['UGCDatabase'],  default=str)
            logger.debug(":{0}:deployed_db_instance_template:{1}".format(
                func_name, str(db_inst_temp)))
            return db_inst_temp
        except (ClientError, KeyError) as e:
            logger.error(":{0}:problems getting deployed template".format(
                func_name), exc_info=True)

    return None


def get_snapshot_identifier(dbinstance_template):
    func_name = traceback.extract_stack(None, 2)[0][2]

    if dbinstance_template:
        db = dbinstance_template
        if type(dbinstance_template) is str:
            db = json.loads(dbinstance_template)

        v = json.dumps(db)
        logger.info(":{0}:{1}".format(func_name, str(v)))
        try:
            snapshot_id = db["Properties"]["DBSnapshotIdentifier"]
        except KeyError:
            logger.error(":{0}:no snapshot identifier".format(
                func_name), exc_info=True)
            return None

        return snapshot_id

    return None


def update_snapshot(fragment, stack_of_interest):
    func_name = traceback.extract_stack(None, 2)[0][2]
    # Fetching latest snapshot
    rds_snapshot_stack_name = os.environ[' rds_snapshot_stack_name'].rstrip().lower()
    replace_with_snapshot = os.environ.get('replace_with_snapshot').rstrip().lower()
    if replace_with_snapshot == "true":
        snapshot_id = os.environ.get("snapshot_id").rstrip()

        _remove_property(fragment, "DBInstanceIdentifier")
        _remove_property(fragment, "DBName")

        if snapshot_id:
            _add_snapshot_identifier(fragment, snapshot_id)
            logger.info(":{0}:adding snapshot {1}".format(
                func_name, snapshot_id))
        elif  rds_snapshot_stack_name:
            _create_snapshot_using_stack_name( rds_snapshot_stack_name, fragment)
        else:
            _create_snapshot_using_stack_name(stack_of_interest, fragment)


def _create_snapshot_using_stack_name(stackname, fragment):
    func_name = traceback.extract_stack(None, 2)[0][2]
    snapshot_type = os.environ['snapshot_type'].rstrip()
    instances = client.describe_db_instances()
    db_instance = parse_db_identifier(instances, stackname)
    logger.info(":{0}:creating snapshot for db_instance [{1}]".format(
        func_name, db_instance))
    if db_instance:
        if snapshot_type:

            if not snapshot_type in snap_shot_types:
                raise Exception("SUPPLIED SNAP SHOT TYPE NOT VALID")

            snapshots = client.describe_db_snapshots(
                    DBInstanceIdentifier=db_instance, SnapshotType=snapshot_type)
        else:
            snapshots = client.describe_db_snapshots(
                DBInstanceIdentifier=db_instance)

        logger.debug(':{0}:available snapshots: {1}'.format(
            func_name, snapshots))

        all_snap_shots = snapshots['DBSnapshots']
        if len(all_snap_shots) > 0:
            snap_shot_id = all_snap_shots[0]['DBSnapshotArn']
            logger.debug(":{0}:adding snapshot {1}".format(
                func_name, snap_shot_id))
            _add_snapshot_identifier(fragment, snap_shot_id)


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
            _remove_property(fragment, prop_to_remove)


def _remove_property(fragment, prop):
    try:
        for key, value in fragment.items():
            if key == 'Properties':
                del value[prop.strip()]
    except KeyError:
        logger.error("unable to remove property", exc_info=True)


def get_instance_state(instance_id, instances):
    func_name = traceback.extract_stack(None, 2)[0][2]
    for val in instances['DBInstances']:
        if str(val['DBInstanceIdentifier']) in instance_id:
            return val['DBInstanceStatus']

    return None


def remove_tag():
    func_name = traceback.extract_stack(None, 2)[0][2]
    response = lambda_client.untag_resource(
        Resource=lambda_arn,
        TagKeys=[point_in_time_db_instance_tag])
    logger.debug(":{0}: response = [{1}]".format(func_name, str(response)))


def add_tag(key, value):
    func_name = traceback.extract_stack(None, 2)[0][2]
    tags = {key: value}
    logger.debug(":{0}: lambda_arn[{1}]".format(func_name, lambda_arn))
    res = lambda_client.tag_resource(
        Resource=lambda_arn, Tags=tags)
    logger.debug(":{0}:response from add tag {1}".format(func_name, res))


def get_tagged_db_instance():
    func_name = traceback.extract_stack(None, 2)[0][2]
    tags = lambda_client.list_tags(Resource=lambda_arn)
    logger.debug(":{0}: list_of_tags = {1}".format(func_name, str(tags)))
    for k, v in tags['Tags'].items():
        if k in point_in_time_db_instance_tag:
            return v
    return None


def point_in_time_restore(fragment, stack_of_interest):
    # Restoring to point in time
    func_name = traceback.extract_stack(None, 2)[0][2]
    replace_with_snapshot = os.environ.get('replace_with_snapshot').rstrip().lower()
    restore = os.environ['restore_point_in_time'].rstrip()
    restore_time = os.environ['restore_time'].rstrip()
    resp = None

    if restore and replace_with_snapshot != "true":
        instances = client.describe_db_instances()
        db_instance = parse_db_identifier(instances, stack_of_interest)
        target_db_instance = get_tagged_db_instance()
        state = None
        if target_db_instance:
            state = get_instance_state(target_db_instance, instances)

        if db_instance and state == None:
            target_db_instance = "tdi"+str(uuid.uuid4())
            logger.info(":{0}:PERFORMING POINT IN TIME RESTORE:curent_db_instance = {1} taget_db_instance = {2} state = {3}".format(
                func_name, db_instance, target_db_instance, state))
            try:
                if restore.lower() == "true" and restore_time:
                    backup_retention_period = get_back_retention_period(
                        instances, db_instance)
                    if not check_if_point_in_time_date_is_valid(restore_time, backup_retention_period):
                        raise Exception("Supplied date is not valid")

                    resp = client.restore_db_instance_to_point_in_time(
                        SourceDBInstanceIdentifier=db_instance,
                        TargetDBInstanceIdentifier=target_db_instance,
                        RestoreTime=restore_time)
                elif restore.lower() == "true":
                    resp = client.restore_db_instance_to_point_in_time(
                        SourceDBInstanceIdentifier=db_instance,
                        TargetDBInstanceIdentifier=target_db_instance,
                        UseLatestRestorableTime=True)

                add_tag(point_in_time_db_instance_tag, target_db_instance)

            except ClientError as e:
                logger.error(":{0}:POINT_IN_TIME_RESTORE:problems creating point in time restore".format(
                    func_name), exc_info=True)

            if resp:
                logger.info(
                    ":{0}:POINT_IN_TIME_RESTORE:response from point in time restore = {1}".format(func_name, resp))

        elif db_instance and state.lower() in 'creating':
            logger.debug(":{0}:POINT_IN_TIME_RESTORE_CREATING:point in time restore has not finnished creating yet:{1}".format(
                func_name, target_db_instance))
            t = get_ugc_database_template(stack_of_interest)
            logger.debug(":{0}:deployed template{1}".format(func_name, t))
            if t:
                return json.loads(t)

        elif db_instance and state.lower() in 'modifying':
            logger.debug(":{0}:POINT_IN_TIME_RESTORE_MOIFYING:point in time restore has not finnished modifying:{1}".format(
                func_name, target_db_instance))
            t = get_ugc_database_template(stack_of_interest)
            logger.debug(":{0}:deployed template{1}".format(func_name, t))
            if t:
                return json.loads(t)

        elif db_instance and state.lower() in 'available':
            restored_snapshot_id = "rsi"+str(uuid.uuid4())
            logger.debug(":{0}:POINT_IN_TIME_RESTORE_CREATING_SNAPSHOT: snapshotid = [{1}]".format(
                func_name, restored_snapshot_id))
            res = client.create_db_snapshot(
                DBSnapshotIdentifier=restored_snapshot_id,
                DBInstanceIdentifier=target_db_instance)
            logger.debug(":{0}:response from create_snapshot_of_point_in_time={1}".format(
                func_name, str(res)))
            _remove_property(fragment, "DBInstanceIdentifier")
            _remove_property(fragment, "DBName")
            _add_snapshot_identifier(fragment, restored_snapshot_id)
            remove_tag()
        else:
            logger.error("should not be here if doing point in time restore")

    return fragment


def handler(event, context):
    level = logging.getLevelName(os.environ['log_level'].rstrip().upper())
    do_not_skip_processing = True
    try:
        logger.setLevel(level)
    except ValueError as ve:
        print("Logger level is not  valid {0}".format(str(ve)))
        do_not_skip_processing = False
        
    #lambda_arn = context.invoked_function_arn
    func_name = traceback.extract_stack(None, 2)[0][2]
    logger.debug(':{0}:this is the event = {1}'.format(func_name, event))
    fragment = event["fragment"]
    params = event['params']
    try:
        stack_of_interest = params['stackname']
    except:
        raise Exception('stackname parameter was not defined in the macro')

    status = "success"
    logger.info(':{0}:fragment_before_modification={1}'.format(
        func_name, fragment))

    try:

        if do_not_skip_processing:
            update_snapshot(fragment, stack_of_interest)
            remove_properties(fragment)
            add_properties(fragment)
            fragment = point_in_time_restore(fragment, stack_of_interest)
        
        snapshot_id = check_if_snapshot_identifier_needs_be_added(
            fragment, stack_of_interest)
    except:
        logger.error(":{0}:something went wrong".format(
            func_name), exc_info=True)
        deployed_template = get_ugc_database_template(stack_of_interest)
        if deployed_template:
            fragment = json.loads(deployed_template)

    logger.info(":{0}:fragment_after_modification={1}".format(
        func_name, fragment))
    return {
        "requestId": event["requestId"],
        "status": status,
        "fragment": fragment,
    }


def parse_db_identifier(response, key):
    found = None
    for item in response['DBInstances']:
        for k, v in item.items():
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


def check_if_point_in_time_date_is_valid(pnt_in_time, backup_retention_period):
    func_name = traceback.extract_stack(None, 2)[0][2]
    try:
        datetime = parse(pnt_in_time)
    except ValueError as e:
        print(str(e))
        logger.error("{0}:POINT_IN_TIME_DATE_IS_NOT_VALUE: point_in_time = {1}".format(
            func_name, pnt_in_time))
        return False

    today = datetime.now(timezone.utc)
    minus5 = today - timedelta(minutes=5)
    last_backup_date = today - timedelta(days=backup_retention_period)
    return last_backup_date < datetime < minus5


def get_back_retention_period(instances, instance_id):
    for v in instances['DBInstances']:
        if str(v['DBInstanceIdentifier']) in instance_id:
            return int(v['BackupRetentionPeriod'])
