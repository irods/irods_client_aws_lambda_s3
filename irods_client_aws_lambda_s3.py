import boto3
import json
import irods.keywords as kw
from irods.session import iRODSSession
import os
import time
import urllib.parse
import tempfile
import ssl

s3 = boto3.client('s3')
ssm = boto3.client('ssm')

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
                ssl_context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile=None, capath=None, cadata=None)
                if irods_env['irods_ssl_ca_certificate_string']:
                    ssl_context.load_verify_locations(cadata=irods_env['irods_ssl_ca_certificate_string'])
                ssl_settings = {'ssl_context': ssl_context}
                try:
                    for x in [  'irods_client_server_negotiation',
                                'irods_client_server_policy',
                                'irods_encryption_algorithm',
                                'irods_encryption_key_size',
                                'irods_encryption_num_hash_rounds',
                                'irods_encryption_salt_size',
                                'irods_ssl_verify_server',
                                ]:
                        if irods_env[x]:
                            ssl_settings.update({x: irods_env[x]})
                except KeyError as e:
                    print('irods_environment is missing a required key')
                    raise e
                with iRODSSession(  host=irods_env['irods_host'],
                                    port=irods_env['irods_port'],
                                    user=irods_env['irods_user_name'],
                                    password=irods_env['irods_password'],
                                    zone=irods_env['irods_zone_name'],
                                    **ssl_settings) as session:

                    # create collection
                    s3_prefix = os.path.dirname(s3_key)
                    s3_filename = os.path.basename(s3_key)
                    physical_path_to_register_in_catalog = os.path.join('/', s3_bucket, s3_prefix, s3_filename)
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
                print('Error registering [{}]'.format(physical_path_to_register_in_catalog))
                raise e

        elif event['Records'][0]['eventName'] in ['ObjectRemoved:Delete']:
            print("S3 - ",event['Records'][0]['eventName'])
            try:
                ssl_context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile=None, capath=None, cadata=None)
                if irods_env['irods_ssl_ca_certificate_string']:
                    ssl_context.load_verify_locations(cadata=irods_env['irods_ssl_ca_certificate_string'])
                ssl_settings = {'ssl_context': ssl_context}
                try:
                    for x in [  'irods_client_server_negotiation',
                                'irods_client_server_policy',
                                'irods_encryption_algorithm',
                                'irods_encryption_key_size',
                                'irods_encryption_num_hash_rounds',
                                'irods_encryption_salt_size',
                                'irods_ssl_verify_server',
                                ]:
                        if irods_env[x]:
                            ssl_settings.update({x: irods_env[x]})
                except KeyError as e:
                    print('irods_environment is missing a required key')
                    raise e
                with iRODSSession(  host=irods_env['irods_host'],
                                    port=irods_env['irods_port'],
                                    user=irods_env['irods_user_name'],
                                    password=irods_env['irods_password'],
                                    zone=irods_env['irods_zone_name'],
                                    **ssl_settings) as session:
                    s3_prefix = os.path.dirname(s3_key)
                    s3_filename = os.path.basename(s3_key)
                    irods_collection_name = os.path.join(irods_collection_prefix, s3_bucket, s3_prefix)
                    irods_dataobj_logical_fullpath = os.path.join(irods_collection_name,s3_filename)
                    obj = session.data_objects.get(irods_dataobj_logical_fullpath)
                    if len(obj.replicas) > 1:
                    # if one of multiple replicas -> unregister s3 replica only
                        for replica in obj.replicas:
                            if replica.resource_name == irods_env['irods_default_resource']:
                                options = {kw.REPL_NUM_KW: replica.number}
                                obj.unregister(**options)
                    else:
                    # if only replica -> unregister (lose any associated metadata)
                        obj.unregister()
                    print('Unregistered [{}][{}]'.format(irods_env['irods_user_name'], irods_dataobj_logical_fullpath))

            except Exception as e:
                print(e)
                print('Error unregistering [{}][{}]'.format(irods_env['irods_user_name'], irods_dataobj_logical_fullpath))
                raise e
        else:
            print("S3 - Unknown Event")

    except Exception as e:
        print(e)
        raise e

