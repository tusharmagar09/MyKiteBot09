import boto3
def lambda_handler(event, context):
    ec2 = boto3.client('ec2', region_name='ap-south-1')
    ec2.start_instances(InstanceIds=['i-0514e13e73544d3ee'])
    print(f'Started FINAL production instance: i-0514e13e73544d3ee')
    return {'statusCode': 200, 'body': 'Final production instance started'}
