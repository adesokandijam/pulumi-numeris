import pulumi
from pulumi_aws import ecs, cloudwatch, appautoscaling
import re

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
        security_group_id: str,  # Now accept the security group ID as a parameter
        vpc_id: str,
        desired_count: int = 1,
        min_count: int = 1,
        max_count: int = 5,
        cpu: str = "256",
        memory: str = "512",
        subnets: list = [],
        log_group_name: str = None,
        runtime_architecture: str = "ARM64",
        opts=None
    ):
        """
        Create an ECS Service with comprehensive configuration and error handling.
        
        :param name: Base name for the ECS service resources
        :param cluster_arn: ARN of the ECS cluster
        :param task_execution_role_arn: ARN of the task execution IAM role
        :param target_group_arn: ARN of the target group for load balancing
        :param container_name: Name of the container
        :param container_image: Docker image for the container
        :param container_port: Port exposed by the container
        :param security_group_id: Security group ID to be used for the ECS service
        :param vpc_id: VPC ID for network configuration
        """
        # Validate inputs
        self._validate_inputs(
            name, container_name, container_image, container_port, 
            desired_count, min_count, max_count
        )

        # Call the parent constructor
        super().__init__('custom:ecs:ECSService', name, {}, opts)

        try:
            # Create Log Group
            log_group_name = self._create_log_group(name, log_group_name)

            # Create Task Definition
            task_definition = self._create_task_definition(
                name, task_execution_role_arn, container_name, 
                container_image, container_port, log_group_name, 
                cpu, memory, runtime_architecture
            )

            # Create ECS Service
            ecs_service = self._create_ecs_service(
                name, cluster_arn, task_definition, 
                desired_count, subnets, security_group_id,  # Use the passed security group ID
                target_group_arn, container_name, container_port
            )

            # Configure Auto Scaling
            self._configure_auto_scaling(
                name, cluster_arn, ecs_service, 
                min_count, max_count
            )

            # Export Outputs
            self.register_outputs({
                "task_definition_arn": task_definition.arn,
                "service_name": ecs_service.name,
                "log_group_name": log_group_name,
                "ecs_security_group_id": security_group_id,  # Output the passed security group ID
            })

        except Exception as e:
            raise Exception(f"Failed to create ECS Service: {str(e)}")

    def _validate_inputs(
        self, name, container_name, container_image, 
        container_port, desired_count, min_count, max_count
    ):
        """
        Validate input parameters before resource creation.
        
        :raises ValueError: If inputs are invalid
        """
        # Validate name
        if not re.match(r'^[a-zA-Z0-9-]+$', name):
            raise ValueError("Name can only contain alphanumeric characters and hyphens")

        # Validate container details
        if not container_name or not container_image:
            raise ValueError("Container name and image are required")

        if container_port <= 0 or container_port > 65535:
            raise ValueError("Container port must be between 1 and 65535")

        # Validate scaling parameters
        if min_count < 1 or max_count < min_count or desired_count < min_count or desired_count > max_count:
            raise ValueError("Invalid scaling configuration")

    def _create_log_group(self, name, log_group_name):
        """Create CloudWatch Log Group if not provided"""
        if not log_group_name:
            log_group = cloudwatch.LogGroup(
                f"{name}-log-group",
                name=f"/ecs/{name}",
                retention_in_days=7,
                tags={
                    "Name": f"{name}-log-group",
                    "Environment": pulumi.get_stack(),
                },
                opts=pulumi.ResourceOptions(parent=self)
            )
            return log_group.name
        return log_group_name

    def _create_task_definition(
        self, name, task_execution_role_arn, container_name, 
        container_image, container_port, log_group_name, 
        cpu, memory, runtime_architecture
    ):
        """Create ECS Task Definition"""
        return ecs.TaskDefinition(
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
            container_definitions=pulumi.Output.all(
                container_name, container_image, log_group_name
            ).apply(
                lambda args: pulumi.Output.json_dumps([{
                    "name": args[0],
                    "image": args[1],
                    "essential": True,
                    "portMappings": [{
                        "containerPort": container_port,
                        "hostPort": container_port,
                        "protocol": "tcp"
                    }],
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": args[2],
                            "awslogs-region": "us-east-1",
                            "awslogs-stream-prefix": args[0]
                        }
                    }
                }])
            ),
            opts=pulumi.ResourceOptions(parent=self)
        )

    def _create_ecs_service(
        self, name, cluster_arn, task_definition, 
        desired_count, subnets, security_group_id,  # Use the passed security group ID here
        target_group_arn, container_name, container_port
    ):
        """Create ECS Service"""
        return ecs.Service(
            f"{name}-service",
            cluster=cluster_arn,
            desired_count=desired_count,
            launch_type="FARGATE",
            task_definition=task_definition.arn,
            network_configuration={
                "assignPublicIp": False,
                "subnets": subnets,
                "securityGroups": [security_group_id],  # Use passed security group ID
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

    def _configure_auto_scaling(self, name, cluster_arn, ecs_service, min_count, max_count):
        try:
            # Create scalable target
            scalable_target = appautoscaling.Target(
                f"{name}-scalable-target",
                service_namespace="ecs",
                resource_id=pulumi.Output.all(cluster_arn, ecs_service.name).apply(
                    lambda args: f"service/{args[0].split('/')[-1]}/{args[1]}"
                ),
                scalable_dimension="ecs:service:DesiredCount",
                min_capacity=min_count,
                max_capacity=max_count,
                opts=pulumi.ResourceOptions(parent=self)
            )

            # Create CPU Scaling Policy
            cpu_scaling_policy = appautoscaling.Policy(
                f"{name}-cpu-scaling-policy",
                policy_type="TargetTrackingScaling",
                resource_id=scalable_target.resource_id,
                scalable_dimension="ecs:service:DesiredCount",
                service_namespace="ecs",
                target_tracking_scaling_policy_configuration={
                    "targetValue": 50.0,
                    "predefinedMetricSpecification": {
                        "predefinedMetricType": "ECSServiceAverageCPUUtilization"
                    },
                    "scaleInCooldown": 60,
                    "scaleOutCooldown": 60,
                },
                opts=pulumi.ResourceOptions(parent=self)
            )

            # Create Memory Scaling Policy
            memory_scaling_policy = appautoscaling.Policy(
                f"{name}-memory-scaling-policy",
                policy_type="TargetTrackingScaling",
                resource_id=scalable_target.resource_id,
                scalable_dimension="ecs:service:DesiredCount",
                service_namespace="ecs",
                target_tracking_scaling_policy_configuration={
                    "targetValue": 50.0,
                    "predefinedMetricSpecification": {
                        "predefinedMetricType": "ECSServiceAverageMemoryUtilization"
                    },
                    "scaleInCooldown": 60,
                    "scaleOutCooldown": 60,
                },
                opts=pulumi.ResourceOptions(parent=self)
            )

            # Apply `.apply()` to log scaling policy ids
            cpu_scaling_policy.id.apply(lambda id: pulumi.log.info(f"CPU scaling policy created: {id}"))
            memory_scaling_policy.id.apply(lambda id: pulumi.log.info(f"Memory scaling policy created: {id}"))

        except Exception as e:
            raise Exception(f"Error creating auto scaling policies: {str(e)}")