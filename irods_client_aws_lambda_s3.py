import boto3
import json
import irods.keywords as kw
from irods.session import iRODSSession
import os
import time
import urllib.parse

s3 = boto3.client('s3')
ssm = boto3.client('ssm')

# TODO - handle SSL if available
# TODO - check bad/missing environment variables

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=4))

    # get variables from environment
    irods_environment_ssm_parameter_name = os.environ['IRODS_ENVIRONMENT_SSM_PARAMETER_NAME']
    irods_collection_prefix = os.environ['IRODS_COLLECTION_PREFIX']

    # get variables from event
    s3_bucket = event['Records'][0]['s3']['bucket']['name']
    s3_key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')

    try:
        # get iRODS client environment from AWS Systems Manager > Parameter Store
        parameter = ssm.get_parameter(Name=irods_environment_ssm_parameter_name, WithDecryption=True)
        irods_env = json.loads(parameter['Parameter']['Value'])

        if event['Records'][0]['eventName'] in ['ObjectCreated:Put','ObjectCreated:Copy']:
            print("S3 - ",event['Records'][0]['eventName'])
            s3_size = event['Records'][0]['s3']['object']['size']
            try:
                # register the new s3 object into iRODS
                with iRODSSession(  host=irods_env['irods_host'],
                                    port=irods_env['irods_port'],
                                    user=irods_env['irods_user_name'],
                                    password=irods_env['irods_password'],
                                    zone=irods_env['irods_zone_name']) as session:

                    # create collection
                    s3_prefix = os.path.dirname(s3_key)
                    s3_filename = os.path.basename(s3_key)
                    physical_path_to_register_in_catalog = os.path.join('/', s3_prefix, s3_filename)
                    irods_collection_name = os.path.join(irods_collection_prefix, s3_bucket, s3_prefix)
                    print(irods_collection_name)
                    session.collections.create(irods_collection_name, recurse=True)

                    # register the data object
                    irods_dataobj_logical_fullpath = os.path.join(irods_collection_name,s3_filename)
                    options = {}
                    options[kw.DATA_SIZE_KW] = str(s3_size)
                    options[kw.DATA_MODIFY_KW] = str(int(time.time()))
                    options[kw.DEST_RESC_NAME_KW] = irods_env['irods_default_resource']
                    session.data_objects.register(  physical_path_to_register_in_catalog,
                                                    irods_dataobj_logical_fullpath,
                                                    **options)
                    print('Registered [{}] as [{}][{}]'.format(physical_path_to_register_in_catalog, irods_env['irods_user_name'], irods_dataobj_logical_fullpath))
            except Exception as e:
                print(e)
                print('Error registering [{}] as [{}][{}]'.format(physical_path_to_register_in_catalog, irods_env['irods_user_name'], irods_dataobj_logical_fullpath))
                raise e

        elif event['Records'][0]['eventName'] in ['ObjectRemoved:Delete']:
            print("S3 - ",event['Records'][0]['eventName'])
            try:
                with iRODSSession(  host=irods_env['irods_host'],
                                    port=irods_env['irods_port'],
                                    user=irods_env['irods_user_name'],
                                    password=irods_env['irods_password'],
                                    zone=irods_env['irods_zone_name']) as session:
                    s3_prefix = os.path.dirname(s3_key)
                    s3_filename = os.path.basename(s3_key)
                    irods_collection_name = os.path.join(irods_collection_prefix, s3_bucket, s3_prefix)
                    irods_dataobj_logical_fullpath = os.path.join(irods_collection_name,s3_filename)
                    obj = session.data_objects.get(irods_dataobj_logical_fullpath)
                    if len(obj.replicas) > 1:
                    # if one of multiple replicas -> trim s3 replica
                        for replica in obj.replicas:
                            if replica.resource_name == irods_env['irods_default_resource']:
                                obj.unlink(replNum=replica.number, force=True) # does not go to trash
                    else:
                    # if only replica -> delete (loss of metadata)
                        obj.unlink(force=True) # does not go to trash
                    print('Deleting [{}][{}]'.format(irods_env['irods_user_name'], irods_dataobj_logical_fullpath))

            except Exception as e:
                print(e)
                print('Error deleting [{}][{}]'.format(irods_env['irods_user_name'], irods_dataobj_logical_fullpath))
                raise e
        else:
            print("S3 - Unknown Event")

    except Exception as e:
        print(e)
        raise e

