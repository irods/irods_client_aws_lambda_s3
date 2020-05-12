# irods_client_aws_lambda_s3

This AWS Lambda function updates an iRODS Catalog with events that occur in one or more S3 buckets.

Files created, renamed, or deleted in S3 appear quickly in iRODS.

The following AWS configurations are supported at this time:
- S3 -> Lambda -> iRODS
- S3 -> SNS -> Lambda -> iRODS
- S3 -> SQS -> Lambda -> iRODS

iRODS is assumed to have its associated S3 Storage Resource(s) configured with `HOST_MODE=cacheless_attached`.

If SQS is involved, it is assumed to be configured with `batch_size = 1`.

## Configuration

### Function

Handler: `irods_client_aws_lambda_s3.lambda_handler`

Runtime: `Python 3.7`

Environment Variables:

`IRODS_COLLECTION_PREFIX` : `/tempZone/home/rods/lambda`

`IRODS_ENVIRONMENT_SSM_PARAMETER_NAME` :  `irods_default_environment`

`IRODS_MULTIBUCKET_SUFFIX` : `_s3`

### Triggers

You must configure your lambda to trigger on all `ObjectCreated` and `ObjectRemoved` events for a connected S3 bucket.

### iRODS Connection Environment

The connection information is stored in the `AWS Systems Manager > Parameter Store` as a JSON object string.

  https://console.aws.amazon.com/systems-manager/parameters

Create a parameter with:

Name (must match `IRODS_ENVIRONMENT_SSM_PARAMETER_NAME` above):
```
irods_default_environment
```

Type:
```
SecureString
```

Value:
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

## Configuration Options

### SSL Support

If the Lambda needs to be configured to connect with an SSL-enabled iRODS Zone, the following additional keys need to be included in the environment in the Parameter Store:
```
    "irods_client_server_negotiation": "request_server_negotiation",
    "irods_client_server_policy": "CS_NEG_REQUIRE",
    "irods_encryption_algorithm": "AES-256-CBC",
    "irods_encryption_key_size": 32,
    "irods_encryption_num_hash_rounds": 16,
    "irods_encryption_salt_size": 8,
    "irods_ssl_verify_server": "cert",
    "irods_ssl_ca_certificate_file": "irods.crt"
```

Note `irods_ssl_ca_certificate_file` is a relative path to a certificate file (or [certificate chain file](https://docs.python.org/3/library/ssl.html#ssl-certificates)) within the Lambda package.

### Multi-Bucket Support

This Lambda function can be configured to receive events from multiple sources at the same time.

If the `irods_default_resource` is *NOT* defined in the environment in the Parameter Store, then the Lambda function will derive the name of a target iRODS Resource.

By default, the Lambda function will append `_s3` to the incoming bucket name.

For example, if the incoming event comes from bucket `example_bucket`, then the iRODS resource that would be targeted would be `example_bucket_s3`.

However, if `IRODS_MULTIBUCKET_SUFFIX` is defined as `-S3Resc`, the the iRODS resource that would be targeted would be `example_bucket-S3Resc`.
