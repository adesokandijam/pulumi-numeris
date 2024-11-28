import pulumi
import json
from components.network import VPC
from components.storage import RDS
from components.ecs import ECSCluster, ECSService
from components.iam import IAMPolicy, IAMRole
from components.lb import ApplicationLoadBalancer, HostBasedALBTargetGroup
from components.certificate import SSLCertificate
from components.ec2 import EC2Instance, SecurityGroup
import pulumi_aws as aws
from pulumi import Output


# # Create the VPC
# Create the VPC
config = pulumi.Config("numeris-book")

# Configuration values (some required, some optional with defaults)
vpc_cidr = config.require("vpcCidr")  # Required value for the VPC CIDR block
db_name = config.get("dbName", "mydatabase")  # Default value for DB name
db_username = config.get("dbUsername", "admin")  # Default value for DB username
backup_retention = config.get_int("backupRetention", 7)  # Default value for backup retention
vpc = VPC(
    name="my-app-vpc",
    cidr_block=vpc_cidr,  # Use the CIDR block from config

)

alb_sg = SecurityGroup(
    "alb-sg",  # Name of the Security Group
    vpc_id=vpc.vpc.id,  # VPC ID where the security group will be created
    ingress=[
        {
            "protocol": "tcp",
            "from_port": 80,
            "to_port": 80,
            "cidr_block": "0.0.0.0/0",  # Allow HTTP traffic from anywhere
        },
        {
            "protocol": "tcp",
            "from_port": 443,
            "to_port": 443,
            "cidr_block": "0.0.0.0/0",  # Allow HTTPS traffic from anywhere
        },
    ],
    egress=[
        {
            "protocol": "-1",  # Allow all outbound traffic
            "from_port": 0,
            "to_port": 0,
            "cidr_blocks": ["0.0.0.0/0"],  # Allow outbound traffic to anywhere
        },
    ],
)

ecs_sg = SecurityGroup(
    "ecs-sg",  # Name of the Security Group
    vpc_id=vpc.vpc.id,  # VPC ID where the security group will be created
    ingress=[{
        "protocol": "tcp",
        "from_port": 80,
        "to_port": 80,
        "security_group_id": alb_sg.security_group.id,  # Allow traffic only from the ALB's security group
    }],
    egress=[{
        "protocol": "-1",  # Allow all outbound traffic
        "from_port": 0,
        "to_port": 0,
        "cidr_blocks": ["0.0.0.0/0"],  # Allow all outbound traffic
    }],
)

rds_sg = SecurityGroup(
    "rds-sg",
    vpc_id=vpc.vpc.id,  # Replace with your VPC ID
    ingress=[{
        "protocol": "tcp",
        "from_port": 5432,
        "to_port": 5432,
        "security_group_id": ecs_sg.security_group.id,  # Allow traffic only from ECS security group
    }],
    egress=[{
        "protocol": "-1",
        "from_port": 0,
        "to_port": 0,
        "cidr_blocks": ["0.0.0.0/0"],  # Allow all outbound traffic
    }],
)



# Create the VPC



# Create the RDS database
rds_instance = RDS(
    name="my-app-rds",
    vpc_id=vpc.vpc.id,  # Ensure vpc_id resolves properly
    private_subnet_ids=pulumi.Output.all(*[subnet.id for subnet in vpc.private_subnets]),
    db_name=db_name,  # Use db_name from config
    username=db_username,  # Use db_username from config
    backup_retention=backup_retention,  # Use backup_retention from config
    # opts=pulumi.ResourceOptions(parent=vpc)
    security_group_id=rds_sg.security_group.id
)
with open('./iam-policy/ecs-task-execution-policy.json') as f:
    ecs_task_execution_policy = json.load(f)

task_ececution_policy = IAMPolicy(
    name="ecs-task-execution-policy",
    policy_document=ecs_task_execution_policy)


with open('./assume-role-policy/ecs-task-execution-role.json') as f:
    ecs_task_execution_assume_role_policy = json.load(f)

execution_role = IAMRole(
    name="ecs-execution-role",
    assume_role_policy=ecs_task_execution_assume_role_policy,  # Assume role policy
    policy_arn=task_ececution_policy.policy.arn  # Pass the ARN of the existing policy
)

with open('./iam-policy/ecs-task-policy.json') as f:
    ecs_task_policy = json.load(f)


task_policy = IAMPolicy(
    name="ecs-task-policy",
    policy_document=ecs_task_policy)


task_role = IAMRole(
    name="ecs-task-role",
    assume_role_policy=ecs_task_execution_assume_role_policy,  # Assume role policy
    policy_arn=task_policy.policy.arn  # Pass the ARN of the existing policy
)

ecs_cluster = ECSCluster(name="test-cluster")


# With www subdomain
ssl_cert_with_www = SSLCertificate("my-app", "dijam.online", include_www=True)



# Create ALB
alb = ApplicationLoadBalancer(
    name="my-app-alb",
    vpc_id=vpc.vpc.id,
    subnets=pulumi.Output.all(*[subnet.id for subnet in vpc.public_subnets]),
    certificate_arn=ssl_cert_with_www.certificate.arn,
    alb_security_group_id=alb_sg.security_group.id
)

host_tg_1 = HostBasedALBTargetGroup(
    name="nginx",
    listener_arn=alb.https_listener.arn,
    vpc_id=vpc.vpc.id,
    host_condition="dijam.online",
    subnets=pulumi.Output.all(*[subnet.id for subnet in vpc.public_subnets]),
    container_port=80
)

# Define the ECS Security Group using the custom SecurityGroup class


nginx_service = ECSService(
    name="nginx",
    cluster_arn=ecs_cluster.cluster.arn,
    task_execution_role_arn=execution_role.role.arn,
    target_group_arn=host_tg_1.target_group.arn,
    container_name="nginx",
    container_image="nginx:latest",  # Ensure the image supports ARM
    container_port=80,
    desired_count=1,
    subnets=pulumi.Output.all(*[subnet.id for subnet in vpc.private_subnets]),
    runtime_architecture="ARM64",  # Specify ARM architecture
    security_group_id = alb_sg.security_group.id,
    vpc_id = vpc.vpc.id
)

# Define Security Group for Elasticsearch, which allows inbound from either another SG or VPC CIDR
elasticsearch_sg = SecurityGroup(
    name="elasticsearch-sg",
    vpc_id=vpc.vpc.id,
    ingress=[
        # Allow SSH from anywhere
        {"protocol": "tcp", "from_port": 22, "to_port": 22, "cidr_block": "0.0.0.0/0"},  # SSH
        # Allow Elasticsearch access from another SG (e.g., Kibana SG)
        {"protocol": "tcp", "from_port": 9200, "to_port": 9200, "cidr_block": "0.0.0.0/0"},  # Elasticsearch
    ],
    egress=[
        {"protocol": "-1", "from_port": 0, "to_port": 0, "cidr_blocks": ["0.0.0.0/0"]},  # Allow all outbound
    ]
)

elasticsearch_user_data = '''#!/bin/bash
# Update packages
sudo apt-get update -y

# Install default JDK
sudo apt install default-jdk default-jre -y

# Add Elasticsearch's GPG key and repository
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
sudo apt-get install apt-transport-https

# Add the Elasticsearch APT repository
echo "deb https://artifacts.elastic.co/packages/7.x/apt stable main" | sudo tee –a /etc/apt/sources.list.d/elastic-7.x.list

# Update again
sudo apt-get update -y

# Install Elasticsearch
sudo apt-get install elasticsearch -y

# Configure Elasticsearch
sudo bash -c 'echo "network.host: 0.0.0.0" >> /etc/elasticsearch/elasticsearch.yml'

# Start Elasticsearch
sudo systemctl start elasticsearch
sudo systemctl enable elasticsearch

# Test Elasticsearch
curl http://localhost:9200
'''

# Elasticsearch Instance
elasticsearch_instance = EC2Instance(
    name="elasticsearch-instance",
    ami="ami-0866a3c8686eaeeba",  # Example AMI ID
    instance_type="t2.micro",  # Example instance type
    subnet_id=vpc.public_subnets[0].id,
    security_group_ids=[elasticsearch_sg.security_group.id],
    user_data=elasticsearch_user_data,
    tags={"Name": "Elasticsearch-Instance", "Environment": "Development"}
)

# elasticsearch_instance_1 = EC2Instance(
#     name="elasticsearch-instance-1",
#     ami="ami-0866a3c8686eaeeba",  # Example AMI ID
#     instance_type="t2.micro",  # Example instance type
#     subnet_id=vpc.public_subnets[0].id,
#     security_group_ids=[elasticsearch_sg.security_group.id],
#     user_data=elasticsearch_user_data,
#     tags={"Name": "Elasticsearch-Instance-1", "Environment": "Development"}
# )