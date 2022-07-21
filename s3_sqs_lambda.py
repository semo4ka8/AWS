import boto3
import requests
import re

aws_services = ["ssm", "s3", "sqs"]
aws_clients = {}
for service in aws_services:
    aws_clients[service] = boto3.client(service)
ssm_param_name = '/s3_sqs_lambda/data_source_url'
s3_bucket_name = 'aminayeva-dowloaded-data'
queue_name = 'tasks'


def setup_ssm():
    try:
        response = aws_clients['ssm'].put_parameter(
            Name=ssm_param_name,
            Value='https://data.wa.gov/api/views/e6ip-wkqq/rows.csv?accessType=DOWNLOAD',
            Type='String'
        )
    except aws_clients['ssm'].exceptions.ParameterAlreadyExists as e:
        print(f'Error creating parameter: {ssm_param_name}. Error: {e}')
        return False
    if response.get('Version', False):
        print('SSM param created')
        return True
    else:
        print('SSM param not created')
        return False


def ssm_get_value(aws_client, ssm_param):
    try:
        response = aws_client['ssm'].get_parameter(
            Name=ssm_param
        )
        return response['Parameter']['Value']
    except aws_client['ssm'].exceptions.ParameterNotFound as e:
        print(f'Error getting parameter: {ssm_param}. Error: {e}')
        return False


def create_s3():
    try:
        response = aws_clients['s3'].create_bucket(
            Bucket=s3_bucket_name,
            CreateBucketConfiguration={
                'LocationConstraint': 'us-west-2'
            }
        )
    except aws_clients['s3'].exceptions.BucketAlreadyExists as e:
        print(f'Error creating bucket: {s3_bucket_name}. Error: {e}')
        return False
    except aws_clients['s3'].exceptions.BucketAlreadyOwnedByYou as e:
        print(f'Error creating bucket: {s3_bucket_name}. Error: {e}')
        return False
    if response.get('Location', False):
        print(f'S3 bucket {s3_bucket_name} created')
        return True
    else:
        print('S3 bucket not created')
        return False


def download_data_to_s3():
    data_url = ssm_get_value(aws_clients, ssm_param_name)
    r = requests.get(data_url)
    response = aws_clients['s3'].put_object(
        Body=r.text,
        Bucket=s3_bucket_name,
        Key=re.findall('/(\w+.csv)', data_url)[0]
    )
    print(response)


def create_queue():
    try:
        response = aws_clients['sqs'].create_queue(
            QueueName=queue_name)
        return response['QueueUrl']
    except aws_clients['sqs'].exceptions.QueueNameExists as e:
        print(f'Error creating queue {queue_name}. Error: {e}')
        return False
    # if response.get('QueueUrl', False):
    #     print('Queue created')
    #     return True
    # else:
    #     print('Queue not created')
    #     return False


def send_message_to_sqs():
    queue_url = create_queue()
    try:
        response = aws_clients['sqs'].send_message(
            QueueUrl=queue_url,
            MessageBody=f'Process data from the {s3_bucket_name}'
        )
    except aws_clients['sqs'].exceptions.InvalidMessageContents as e:
        print(f'Error sending message to queue {queue_name}. Error: {e}')
        return False
    except aws_clients['sqs'].exceptions.UnsupportedOperation as e:
        print(f'Error sending message to queue {queue_name}. Error: {e}')
        return False
    if response.get('MessageId', False):
        print(f'Message sent to queue {queue_name}')
        return True
    else:
        print(f'Message not send to queue {queue_name}')
        return False

if __name__ == "__main__":
    setup_ssm()
    create_s3()
    #download_data_to_s3()
    create_queue()
    send_message_to_sqs()
