import os
import datetime
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

class AWSService:
    def __init__(self):
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        try:
            self.ec2 = boto3.client('ec2', region_name=self.region, 
                                    aws_access_key_id=self.access_key, 
                                    aws_secret_access_key=self.secret_key)
            self.s3 = boto3.client('s3', region_name=self.region, 
                                   aws_access_key_id=self.access_key, 
                                   aws_secret_access_key=self.secret_key)
            self.rds = boto3.client('rds', region_name=self.region, 
                                    aws_access_key_id=self.access_key, 
                                    aws_secret_access_key=self.secret_key)
            self.cloudwatch = boto3.client('cloudwatch', region_name=self.region, 
                                           aws_access_key_id=self.access_key, 
                                           aws_secret_access_key=self.secret_key)
            self.ce = boto3.client('ce', region_name=self.region, 
                                   aws_access_key_id=self.access_key, 
                                   aws_secret_access_key=self.secret_key)
            self.iam = boto3.client('iam', region_name=self.region,
                                    aws_access_key_id=self.access_key,
                                    aws_secret_access_key=self.secret_key)
        except Exception as e:
            print(f"AWS init error: {e}.")
            self.ec2 = self.s3 = self.rds = self.cloudwatch = self.ce = self.iam = None

    def get_resources(self):
        resources = []
        if not self.ec2:
            return resources
            
        try:
            # EC2
            instances = self.ec2.describe_instances()
            for reservation in instances.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    name = "Unnamed EC2"
                    for tag in instance.get('Tags', []):
                        if tag['Key'] == 'Name':
                            name = tag['Value']
                            break
                    state = "Running" if instance['State']['Name'] == 'running' else "Stopped"
                    
                    # Fetch real CPU if running
                    cpu_usage = 0
                    if state == "Running":
                        try:
                            # Try to get CPU from CloudWatch (last 5 mins)
                            end_time = datetime.datetime.utcnow()
                            start_time = end_time - datetime.timedelta(minutes=10)
                            stats = self.cloudwatch.get_metric_statistics(
                                Namespace='AWS/EC2',
                                MetricName='CPUUtilization',
                                Dimensions=[{'Name': 'InstanceId', 'Value': instance['InstanceId']}],
                                StartTime=start_time,
                                EndTime=end_time,
                                Period=300,
                                Statistics=['Average']
                            )
                            if stats['Datapoints']:
                                cpu_usage = round(stats['Datapoints'][0]['Average'], 1)
                        except Exception:
                            pass
                            
                    # Calculate Uptime
                    uptime_str = "0h"
                    if state == "Running" and 'LaunchTime' in instance:
                        launch_time = instance['LaunchTime'].replace(tzinfo=None)
                        delta = datetime.datetime.utcnow() - launch_time
                        days = delta.days
                        hours = delta.seconds // 3600
                        uptime_str = f"{days}d {hours}h" if days > 0 else f"{hours}h"
                        
                    ip = instance.get('PublicIpAddress', instance.get('PrivateIpAddress', 'None'))
                    size = instance.get('InstanceType', 'Unknown')
                    os_type = instance.get('PlatformDetails', 'Linux/UNIX')

                    resources.append({
                        "id": instance['InstanceId'],
                        "name": name,
                        "type": "EC2 Instance",
                        "status": state,
                        "region": self.region,
                        "cpu": cpu_usage,
                        "mem": 0, # Requires agent
                        "cost": 0, # Cannot dynamically compute per instance cost here easily without detailed billing analysis

                        "ip": ip,
                        "size": size,
                        "os": os_type,
                        "uptime": uptime_str
                    })

            # S3
            buckets = self.s3.list_buckets()
            for bucket in buckets.get('Buckets', []):
                resources.append({
                    "name": bucket['Name'],
                    "type": "S3 Bucket",
                    "status": "Running",
                    "region": "Global",
                    "cpu": 0,
                    "mem": 0,
                    "cost": 0,
                    "ip": "N/A",
                    "size": "Standard",
                    "os": "N/A",
                    "uptime": "N/A"
                })

            # RDS
            db_instances = self.rds.describe_db_instances()
            for db in db_instances.get('DBInstances', []):
                state = "Running" if db['DBInstanceStatus'] == 'available' else "Stopped"
                resources.append({
                    "name": db['DBInstanceIdentifier'],
                    "type": "RDS Database",
                    "status": state,
                    "region": self.region,
                    "cpu": 0,
                    "mem": 0,
                    "cost": 0,
                    "ip": db.get('Endpoint', {}).get('Address', 'None') if 'Endpoint' in db else 'None',
                    "size": db.get('DBInstanceClass', 'Unknown'),
                    "os": db.get('Engine', 'Unknown'),
                    "uptime": "N/A"
                })

            # VPC
            vpcs = self.ec2.describe_vpcs()
            for vpc in vpcs.get('Vpcs', []):
                name = "Unnamed VPC"
                for tag in vpc.get('Tags', []):
                    if tag['Key'] == 'Name':
                        name = tag['Value']
                        break
                state = "Running" if vpc.get('State') == 'available' else "Stopped"
                resources.append({
                    "id": vpc['VpcId'],
                    "name": name,
                    "type": "VPC",
                    "status": state,
                    "region": self.region,
                    "cpu": 0,
                    "mem": 0,
                    "cost": 0,
                    "ip": vpc.get('CidrBlock', 'Unknown'),
                    "size": "N/A",
                    "os": "N/A",
                    "uptime": "N/A"
                })

            # Subnets
            subnets = self.ec2.describe_subnets()
            for subnet in subnets.get('Subnets', []):
                name = "Unnamed Subnet"
                for tag in subnet.get('Tags', []):
                    if tag['Key'] == 'Name':
                        name = tag['Value']
                        break
                state = "Running" if subnet.get('State') == 'available' else "Stopped"
                avail_ips = subnet.get('AvailableIpAddressCount', 0)
                resources.append({
                    "id": subnet['SubnetId'],
                    "name": name,
                    "type": "Subnet",
                    "status": state,
                    "region": self.region,
                    "cpu": 0,
                    "mem": 0,
                    "cost": 0,
                    "ip": subnet.get('CidrBlock', 'Unknown'),
                    "size": f"{avail_ips} IPs",
                    "os": subnet.get('AvailabilityZone', 'Unknown'),
                    "uptime": "N/A"
                })

            # Security Groups
            sgs = self.ec2.describe_security_groups()
            for sg in sgs.get('SecurityGroups', []):
                resources.append({
                    "id": sg['GroupId'],
                    "name": sg.get('GroupName', 'Unnamed SG'),
                    "type": "Security Group",
                    "status": "Running",
                    "region": self.region,
                    "cpu": 0,
                    "mem": 0,
                    "cost": 0,
                    "ip": sg.get('VpcId', 'N/A'),
                    "size": f"{len(sg.get('IpPermissions', []))} rules",
                    "os": "N/A",
                    "uptime": "N/A"
                })

            # IAM Roles
            roles = self.iam.list_roles(MaxItems=100) # limit to 100 to avoid huge UI overload
            for role in roles.get('Roles', []):
                create_date = role['CreateDate'].replace(tzinfo=None)
                delta = datetime.datetime.utcnow() - create_date
                resources.append({
                    "id": role['RoleId'],
                    "name": role['RoleName'],
                    "type": "IAM Role",
                    "status": "Running",
                    "region": "Global",
                    "cpu": 0,
                    "mem": 0,
                    "cost": 0,
                    "ip": "N/A",
                    "size": "N/A",
                    "os": "N/A",
                    "uptime": f"{delta.days}d"
                })

        except (NoCredentialsError, ClientError) as e:
            print(f"Error fetching AWS resources: {e}")
            
        return resources

    def start_resource(self, resource_id, resource_type="EC2 Instance"):
        if not self.ec2:
            return {"status": "error", "message": "AWS client not initialized"}
            
        if resource_type == "EC2 Instance":
            try:
                self.ec2.start_instances(InstanceIds=[resource_id])
                return {"status": "success", "message": f"Started {resource_id}"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Unsupported resource type"}

    def stop_resource(self, resource_id, resource_type="EC2 Instance"):
        if not self.ec2:
            return {"status": "error", "message": "AWS client not initialized"}
            
        if resource_type == "EC2 Instance":
            try:
                self.ec2.stop_instances(InstanceIds=[resource_id])
                return {"status": "success", "message": f"Stopped {resource_id}"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Unsupported resource type"}
        
    def get_costs(self):
        empty_data = {
            "cost_months": [],
            "cost_values": [],
            "cost_by_service": {
                "labels": [],
                "values": [],
                "colors": [],
            }
        }
        
        if not self.ce:
            return empty_data
            
        try:
            # Real cost calculation
            end = datetime.date.today().replace(day=1)
            start = (end - datetime.timedelta(days=180)).replace(day=1)
            
            response = self.ce.get_cost_and_usage(
                TimePeriod={'Start': start.strftime('%Y-%m-%d'), 'End': end.strftime('%Y-%m-%d')},
                Granularity='MONTHLY',
                Metrics=['UnblendedCost']
            )
            
            months = []
            values = []
            for res in response.get('ResultsByTime', []):
                dt = datetime.datetime.strptime(res['TimePeriod']['Start'], '%Y-%m-%d')
                months.append(dt.strftime('%b'))
                val = float(res['Total']['UnblendedCost']['Amount'])
                values.append(round(val, 2))
                
            return {
                "cost_months": months,
                "cost_values": values,
                "cost_by_service": empty_data["cost_by_service"]
            }
        except Exception as e:
            print(f"Error fetching AWS costs: {e}")
            return empty_data

    def get_performance(self):
        labels = [(datetime.date.today() - datetime.timedelta(days=i)).strftime('%a') for i in range(6, -1, -1)]
        empty_data = {
            "labels": labels,
            "cpu_data": [],
            "mem_data": []
        }

        if not self.ec2:
            return empty_data

        try:
            # We need an InstanceId to query CW for EC2 CPU. Get first running instance.
            instances = self.ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
            instance_id = None
            for r in instances.get('Reservations', []):
                if r.get('Instances'):
                    instance_id = r['Instances'][0]['InstanceId']
                    break
            
            if not instance_id:
                return empty_data

            end_time = datetime.datetime.utcnow()
            start_time = end_time - datetime.timedelta(days=7)
            
            stats = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400, # 1 day
                Statistics=['Average']
            )

            if not stats['Datapoints']:
                return empty_data
                
            # Sort datapoints by timestamp
            datapoints = sorted(stats['Datapoints'], key=lambda x: x['Timestamp'])
            
            # Map datapoints to our 7-day labels. If some days are missing, fill with 0 or mock values
            cpu_data = []
            for i in range(7):
                target_date = (datetime.datetime.utcnow() - datetime.timedelta(days=6-i)).date()
                val = 0
                for dp in datapoints:
                    if dp['Timestamp'].date() == target_date:
                        val = round(dp['Average'], 1)
                        break
                # if instance is new and has no data for that day, append 0
                cpu_data.append(val)
                
            return {
                "labels": labels,
                "cpu_data": cpu_data,
                "mem_data": [] 
            }
            
        except Exception as e:
            print(f"Error fetching performance: {e}")
            return empty_data
