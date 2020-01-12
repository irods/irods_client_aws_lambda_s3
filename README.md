# irods_client_aws_lambda_s3

This AWS Lambda function updates an iRODS Catalog with events that occur in an S3 bucket.

Files created, renamed, or deleted in S3 appear quickly in iRODS.                

### Lambda Function

The lambda function: `irods_client_aws_lambda_s3.py`

Runtime: `Python 3.7`

Environment Variables:

    `IRODS_COLLECTION_PREFIX` : `/tempZone/home/rods/lambda`
    `IRODS_ENVIRONMENT_SSM_PARAMETER_NAME` :  irods_default_environment`

### Triggers

You must configure your lambda to trigger on all `ObjectCreated` and `ObjectRemoved` events for a connected S3 bucket.

### iRODS Connection Environment

The connection information is stored in the `AWS Systems Manager > Parameter Store` as a JSON object string.

  https://console.aws.amazon.com/systems-manager/parameters

Create a parameter with:

1 - Name (of your choice):
```
irods_default_environment
```

2 - Description:
```
For use with iRODS Client AWS Lambda S3
```

3 - Type:
```
SecureString
```

4 - Value:
```
{
    "irods_default_resource": "s3Resc",
    "irods_host": "irods.example.org",
    "irods_password": "rods",
    "irods_port": 1247,
    "irods_user_name": "rods",
    "irods_zone_name": "tempZone"
}
```

