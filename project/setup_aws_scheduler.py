"""
setup_aws_scheduler.py — One-time setup script for AWS EventBridge + Lambda.
Creates a scheduled rule to auto-start the EC2 instance Mon-Fri at 2:50 PM IST.

Prerequisites:
  pip install boto3
  aws configure (with your AWS credentials)

Usage:
  python setup_aws_scheduler.py --instance-id i-0xxxxx --region ap-south-1
"""
import argparse
import json
import boto3
import time


def create_lambda_role(iam_client, role_name="TradingBotEC2StartRole"):
    """Create an IAM role for the Lambda function."""
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }

    try:
        role = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Role for Lambda to start/stop EC2 for trading bot"
        )
        role_arn = role['Role']['Arn']
        print(f"Created IAM Role: {role_arn}")
    except iam_client.exceptions.EntityAlreadyExistsException:
        role = iam_client.get_role(RoleName=role_name)
        role_arn = role['Role']['Arn']
        print(f"IAM Role already exists: {role_arn}")

    # Attach EC2 start/stop permissions
    ec2_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": ["ec2:StartInstances", "ec2:StopInstances", "ec2:DescribeInstances"],
            "Resource": "*"
        }]
    }

    try:
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName="EC2StartStopPolicy",
            PolicyDocument=json.dumps(ec2_policy)
        )
    except Exception:
        pass

    # Attach basic Lambda execution role
    try:
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        )
    except Exception:
        pass

    time.sleep(10)  # Wait for role propagation
    return role_arn


def create_lambda_function(lambda_client, role_arn, instance_id, region, func_name="TradingBotStartEC2"):
    """Create the Lambda function that starts the EC2 instance."""
    code = f"""
import boto3

def lambda_handler(event, context):
    ec2 = boto3.client('ec2', region_name='{region}')
    ec2.start_instances(InstanceIds=['{instance_id}'])
    print(f'Started instance: {instance_id}')
    return {{'statusCode': 200, 'body': 'Instance started'}}
"""

    import zipfile
    import io
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        zf.writestr('lambda_function.py', code)
    zip_buffer.seek(0)

    try:
        response = lambda_client.create_function(
            FunctionName=func_name,
            Runtime='python3.12',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_buffer.read()},
            Timeout=30,
            MemorySize=128
        )
        func_arn = response['FunctionArn']
        print(f"Created Lambda: {func_arn}")
    except lambda_client.exceptions.ResourceConflictException:
        response = lambda_client.get_function(FunctionName=func_name)
        func_arn = response['Configuration']['FunctionArn']
        print(f"Lambda already exists: {func_arn}")

    return func_arn


def create_eventbridge_rule(events_client, lambda_client, func_arn, rule_name="TradingBotSchedule"):
    """Create an EventBridge rule that fires Mon-Fri at 2:50 PM IST (9:20 AM UTC)."""
    # 2:50 PM IST = 9:20 AM UTC
    response = events_client.put_rule(
        Name=rule_name,
        ScheduleExpression="cron(20 9 ? * MON-FRI *)",
        State="ENABLED",
        Description="Start EC2 for live trading bot at 2:50 PM IST, Mon-Fri"
    )
    rule_arn = response['RuleArn']
    print(f"Created EventBridge Rule: {rule_arn}")

    # Add Lambda as target
    events_client.put_targets(
        Rule=rule_name,
        Targets=[{
            'Id': 'TradingBotTarget',
            'Arn': func_arn
        }]
    )

    # Allow EventBridge to invoke Lambda
    try:
        lambda_client.add_permission(
            FunctionName=func_arn.split(":")[-1],
            StatementId='EventBridgeInvoke',
            Action='lambda:InvokeFunction',
            Principal='events.amazonaws.com',
            SourceArn=rule_arn
        )
    except Exception:
        pass  # Permission may already exist

    print("EventBridge → Lambda → EC2 pipeline configured!")
    print("Schedule: Mon-Fri at 2:50 PM IST (9:20 AM UTC)")


def main():
    parser = argparse.ArgumentParser(description="Setup AWS scheduler for trading bot")
    parser.add_argument("--instance-id", required=True, help="EC2 Instance ID (e.g., i-0abc123)")
    parser.add_argument("--region", default="ap-south-1", help="AWS region (default: ap-south-1)")
    args = parser.parse_args()

    print(f"Setting up scheduler for EC2: {args.instance_id} in {args.region}")
    print("=" * 60)

    iam = boto3.client('iam', region_name=args.region)
    lam = boto3.client('lambda', region_name=args.region)
    events = boto3.client('events', region_name=args.region)

    role_arn = create_lambda_role(iam)
    func_arn = create_lambda_function(lam, role_arn, args.instance_id, args.region)
    create_eventbridge_rule(events, lam, func_arn)

    print("\n✅ Setup complete! Your EC2 will auto-start at 2:50 PM IST every weekday.")
    print("The bot will auto-shutdown after execution (~3:25 PM).")
    print(f"Estimated monthly cost: ~₹20 (EC2 runs ~30 min/day)")


if __name__ == "__main__":
    main()
