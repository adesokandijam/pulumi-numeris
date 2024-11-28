import pulumi
from pulumi_aws import ecs, ec2, cloudwatch, appautoscaling


class ECSService(pulumi.ComponentResource):
    def __init__(
        self,
        name: str,
        cluster_arn: str,
        task_execution_role_arn: str,
        target_group_arn: str,
        container_name: str,
        container_image: str,
        container_port: int,
        lb_security_group_id: str,  # Load Balancer Security Group ID
        vpc_id: str,
        desired_count: int = 1,
        min_count: int = 1,
        max_count: int = 5,
        cpu: str = "256",
        memory: str = "512",
        subnets: list = [],
        log_group_name: str = None,
        runtime_architecture: str = "arm64",  # Default to ARM architecture
        opts=None
    ):
        super().__init__('custom:ecs:ECSService', name, {}, opts)

        # Create CloudWatch Log Group if not provided
        log_group = None
        if not log_group_name:
            log_group = cloudwatch.LogGroup(
                f"{name}-log-group",
                name=f"/ecs/{name}",
                retention_in_days=7,  # Adjust log retention as needed
                tags={
                    "Name": f"{name}-log-group",
                    "Environment": pulumi.get_stack(),
                },
                opts=pulumi.ResourceOptions(parent=self)
            )
            log_group_name = log_group.name

        # Create a Security Group for the ECS Service
        self.ecs_security_group = ec2.SecurityGroup(
            f"{name}-ecs-sg",
            description=f"ECS security group for {name}",
            vpc_id=vpc_id,
            ingress=[
                {
                    "protocol": "tcp",
                    "from_port": container_port,
                    "to_port": container_port,
                    "security_groups": [lb_security_group_id],  # Allow traffic from LB Security Group
                }
            ],
            egress=[
                {
                    "protocol": "-1",  # All traffic
                    "from_port": 0,
                    "to_port": 0,
                    "cidr_blocks": ["0.0.0.0/0"],  # Outbound to the internet
                }
            ],
            tags={
                "Name": f"{name}-ecs-sg",
                "Environment": pulumi.get_stack(),
            },
            opts=pulumi.ResourceOptions(parent=self)
        )

        # Define a Task Definition
        self.task_definition = ecs.TaskDefinition(
            f"{name}-task",
            family=f"{name}-task",
            network_mode="awsvpc",
            requires_compatibilities=["FARGATE"],
            cpu=cpu,
            memory=memory,
            execution_role_arn=task_execution_role_arn,
            runtime_platform={
                "cpuArchitecture": runtime_architecture,
                "operatingSystemFamily": "LINUX"
            },
            container_definitions=pulumi.Output.all(container_name, container_image, log_group_name).apply(
                lambda args: pulumi.Output.json_dumps([{
                    "name": args[0],  # container_name
                    "image": args[1],  # container_image
                    "essential": True,
                    "portMappings": [
                        {
                            "containerPort": container_port,
                            "hostPort": container_port,
                            "protocol": "tcp"
                        }
                    ],
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": args[2],  # log_group_name
                            "awslogs-region": "us-east-1",
                            "awslogs-stream-prefix": args[0]  # container_name
                        }
                    }
                }])
            ),
            opts=pulumi.ResourceOptions(parent=self)
        )

        # Create ECS Service
        self.ecs_service = ecs.Service(
            f"{name}-service",
            cluster=cluster_arn,
            desired_count=desired_count,
            launch_type="FARGATE",
            task_definition=self.task_definition.arn,
            network_configuration={
                "assignPublicIp": False,
                "subnets": subnets,
                "securityGroups": [self.ecs_security_group.id],  # Use the created SG
            },
            load_balancers=[{
                "targetGroupArn": target_group_arn,
                "containerName": container_name,
                "containerPort": container_port,
            }],
            tags={
                "Name": f"{name}-service",
                "Environment": pulumi.get_stack(),
            },
            opts=pulumi.ResourceOptions(parent=self)
        )

        # Register ECS Service for Auto Scaling
        self.scalable_target = appautoscaling.Target(
            f"{name}-scalable-target",
            service_namespace="ecs",
            resource_id=pulumi.Output.all(cluster_arn, self.ecs_service.name).apply(
                        lambda args: f"service/{args[0].split('/')[-1]}/{args[1]}"
                    ),
            scalable_dimension="ecs:service:DesiredCount",
            min_capacity=min_count,
            max_capacity=max_count,
            opts=pulumi.ResourceOptions(parent=self)
        )

        # Define Auto Scaling Policies
        self.cpu_scaling_policy = appautoscaling.Policy(
            f"{name}-cpu-scaling-policy",
            policy_type="TargetTrackingScaling",
            resource_id=self.scalable_target.resource_id,
            scalable_dimension="ecs:service:DesiredCount",
            service_namespace="ecs",
            target_tracking_scaling_policy_configuration={
                "targetValue": 50.0,  # Target CPU utilization in percentage
                "predefinedMetricSpecification": {
                    "predefinedMetricType": "ECSServiceAverageCPUUtilization"
                },
                "scaleInCooldown": 60,
                "scaleOutCooldown": 60,
            },
            opts=pulumi.ResourceOptions(parent=self)
        )

        self.memory_scaling_policy = appautoscaling.Policy(
            f"{name}-memory-scaling-policy",
            policy_type="TargetTrackingScaling",
            resource_id=self.scalable_target.resource_id,
            scalable_dimension="ecs:service:DesiredCount",
            service_namespace="ecs",
            target_tracking_scaling_policy_configuration={
                "targetValue": 50.0,  # Target Memory utilization in percentage
                "predefinedMetricSpecification": {
                    "predefinedMetricType": "ECSServiceAverageMemoryUtilization"
                },
                "scaleInCooldown": 60,
                "scaleOutCooldown": 60,
            },
            opts=pulumi.ResourceOptions(parent=self)
        )

        # Export Outputs
        self.register_outputs({
            "task_definition_arn": self.task_definition.arn,
            "service_name": self.ecs_service.name,
            "log_group_name": log_group_name,
            "ecs_security_group_id": self.ecs_security_group.id,
            "scalable_target": self.scalable_target.id,
            "cpu_scaling_policy": self.cpu_scaling_policy.id,
            "memory_scaling_policy": self.memory_scaling_policy.id,
        })