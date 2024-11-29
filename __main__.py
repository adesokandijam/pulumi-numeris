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
config = pulumi.Config("numeris-book")

# Configuration values (some required, some optional with defaults)
vpc_cidr = config.require("vpcCidr")  # Required value for the VPC CIDR block
db_name = config.get("dbName", "mydatabase")  # Default value for DB name
db_username = config.get("dbUsername", "admin")  # Default value for DB username
backup_retention = config.get_int("backupRetention", 7)  # Default value for backup retention
stack_name = pulumi.get_stack()

# Create the VPC
vpc = VPC(
    name=f"my-app-vpc-{stack_name}",
    cidr_block=vpc_cidr,  # Use the CIDR block from config
)

alb_sg = SecurityGroup(
    f"alb-sg-{stack_name}",  # Name of the Security Group with stack name
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
    f"ecs-sg-{stack_name}",  # Name of the Security Group with stack name
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
    f"rds-sg-{stack_name}",  # Name of the Security Group with stack name
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

# Create the RDS database
rds_instance = RDS(
    name=f"my-app-rds-{stack_name}",
    vpc_id=vpc.vpc.id,  # Ensure vpc_id resolves properly
    private_subnet_ids=pulumi.Output.all(*[subnet.id for subnet in vpc.private_subnets]),
    db_name=db_name,  # Use db_name from config
    username=db_username,  # Use db_username from config
    backup_retention=backup_retention,  # Use backup_retention from config
    security_group_id=rds_sg.security_group.id
)

with open('./iam-policy/ecs-task-execution-policy.json') as f:
    ecs_task_execution_policy = json.load(f)

task_execution_policy = IAMPolicy(
    name=f"ecs-task-execution-policy-{stack_name}",
    policy_document=ecs_task_execution_policy
)

with open('./assume-role-policy/ecs-task-execution-role.json') as f:
    ecs_task_execution_assume_role_policy = json.load(f)

execution_role = IAMRole(
    name=f"ecs-execution-role-{stack_name}",
    assume_role_policy=ecs_task_execution_assume_role_policy,  # Assume role policy
    policy_arn=task_execution_policy.policy.arn  # Pass the ARN of the existing policy
)

with open('./iam-policy/ecs-task-policy.json') as f:
    ecs_task_policy = json.load(f)

task_policy = IAMPolicy(
    name=f"ecs-task-policy-{stack_name}",
    policy_document=ecs_task_policy
)

task_role = IAMRole(
    name=f"ecs-task-role-{stack_name}",
    assume_role_policy=ecs_task_execution_assume_role_policy,  # Assume role policy
    policy_arn=task_policy.policy.arn  # Pass the ARN of the existing policy
)

ecs_cluster = ECSCluster(name=f"test-cluster-{stack_name}")

# With www subdomain
ssl_cert_with_www = SSLCertificate(f"my-app-{stack_name}", "dijam.online", include_www=True)

# Create ALB
alb = ApplicationLoadBalancer(
    name=f"my-app-alb-{stack_name}",
    vpc_id=vpc.vpc.id,
    subnets=pulumi.Output.all(*[subnet.id for subnet in vpc.public_subnets]),
    certificate_arn=ssl_cert_with_www.certificate.arn,
    alb_security_group_id=alb_sg.security_group.id
)

host_tg_1 = HostBasedALBTargetGroup(
    f"nginx-{stack_name}",
    listener_arn=alb.https_listener.arn,
    vpc_id=vpc.vpc.id,
    host_condition="dijam.online",
    subnets=pulumi.Output.all(*[subnet.id for subnet in vpc.public_subnets]),
    container_port=80
)

nginx_service = ECSService(
    name=f"nginx-{stack_name}",
    cluster_arn=ecs_cluster.cluster.arn,
    task_execution_role_arn=execution_role.role.arn,
    target_group_arn=host_tg_1.target_group.arn,
    container_name="nginx",
    container_image="nginx:latest",  # Ensure the image supports ARM
    container_port=80,
    desired_count=1,
    subnets=pulumi.Output.all(*[subnet.id for subnet in vpc.private_subnets]),
    runtime_architecture="ARM64",  # Specify ARM architecture
    security_group_id=alb_sg.security_group.id,
    vpc_id=vpc.vpc.id
)

kibana_logstash_sg = SecurityGroup(
    f"kibana-logstash-sg-{stack_name}",
    vpc_id=vpc.vpc.id,
    ingress=[
        # Allow Elasticsearch access from another SG (e.g., Kibana SG)
        {"protocol": "tcp", "from_port": 5601, "to_port": 5601, "cidr_block": "0.0.0.0/0"},  # Elasticsearch
    ],
    egress=[
        {"protocol": "-1", "from_port": 0, "to_port": 0, "cidr_blocks": ["0.0.0.0/0"]},  # Allow all outbound
    ]
)

# Define Security Group for Elasticsearch, which allows inbound from either another SG or VPC CIDR
elasticsearch_sg = SecurityGroup(
    f"elasticsearch-sg-{stack_name}",
    vpc_id=vpc.vpc.id,
    ingress=[
        # Allow Elasticsearch access from another SG (e.g., Kibana SG)
        {"protocol": "tcp", "from_port": 9200, "to_port": 9200, "security_group_id": kibana_logstash_sg.security_group.id},  # Elasticsearch
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
    f"elasticsearch-instance-{stack_name}",
    ami="ami-0866a3c8686eaeeba",  # Example AMI ID
    instance_type="t2.micro",  # Example instance type
    subnet_id=vpc.private_subnets[0].id,
    security_group_ids=[elasticsearch_sg.security_group.id],
    user_data=elasticsearch_user_data,
    tags={"Owner": "Dijam",
                    "Project": "Numeris",
                    "CostCenter": "1234","Name": f"Elasticsearch-Instance-{stack_name}"}
)

kibana_logstash_user_data = pulumi.Output.all(elasticsearch_instance.instance.private_ip).apply(
    lambda elasticsearch_private_ip: f'''#!/bin/bash
# Update packages
sudo apt-get update -y

# Install default JDK (required by Logstash)
sudo apt install default-jdk default-jre -y

# Install Kibana
sudo apt-get install kibana -y

# Configure Kibana to connect to Elasticsearch
sudo bash -c 'echo "server.host: 0.0.0.0" >> /etc/kibana/kibana.yml'
sudo bash -c 'echo "elasticsearch.hosts: [\"http://{elasticsearch_private_ip}:9200\"]" >> /etc/kibana/kibana.yml'

# Start Kibana
sudo systemctl start kibana
sudo systemctl enable kibana

# Install Logstash
sudo apt-get install logstash -y

# Configure Logstash to send logs to Elasticsearch
echo "input {{
    file {{
        path => \"/var/log/*.log\"
        start_position => \"beginning\"
    }}
}}

output {{
    elasticsearch {{
        hosts => [\"http://{elasticsearch_private_ip}:9200\"]
        index => \"logstash-%{{+YYYY.MM.dd}}\"
    }}
}}" | sudo tee /etc/logstash/conf.d/logstash.conf

# Start Logstash
sudo systemctl start logstash
sudo systemctl enable logstash

# Test Logstash
curl -XGET 'http://localhost:9200/_cat/indices?v'
'''
)

kibana_logstash_instance = EC2Instance(
    f"kibana-logstash-instance-{stack_name}",
    ami="ami-0866a3c8686eaeeba",  # Example AMI ID
    instance_type="t2.micro",  # Example instance type
    subnet_id=vpc.public_subnets[0].id,
    security_group_ids=[kibana_logstash_sg.security_group.id],
    user_data=kibana_logstash_user_data,
    tags={"Owner": "Dijam",
                    "Project": "Numeris",
                    "CostCenter": "1234","Name": f"Kibana-Logstash-Instance-{stack_name}"}
)