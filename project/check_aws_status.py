import boto3
import json

def check_status():
    region = "ap-south-1"
    events = boto3.client('events', region_name=region)
    lam = boto3.client('lambda', region_name=region)
    
    print("--- AWS EventBridge Rules ---")
    try:
        rules = events.list_rules()
        for rule in rules.get('Rules', []):
            print(f"Name: {rule['Name']}, State: {rule['State']}, Schedule: {rule.get('ScheduleExpression')}")
    except Exception as e:
        print(f"Error listing rules: {e}")

    print("\n--- AWS Lambda Functions ---")
    try:
        funcs = lam.list_functions()
        for f in funcs.get('Functions', []):
            print(f"Name: {f['FunctionName']}, LastModified: {f['LastModified']}")
    except Exception as e:
        print(f"Error listing functions: {e}")

if __name__ == "__main__":
    check_status()
