import pulumi
from pulumi_aws import lb, ec2

class HostBasedALBTargetGroup(pulumi.ComponentResource):
    _priority_counter = 1  # Class-level variable to track the priority

    def __init__(
        self,
        name: str,
        listener_arn: str,
        vpc_id: str,
        host_condition: str,
        subnets: list,
        container_port: int,
        opts=None
    ):
        """
        Create a host-based ALB Target Group with listener rule.
        
        :param name: Base name for resources
        :param listener_arn: ARN of the listener
        :param vpc_id: VPC ID
        :param host_condition: Host header for routing
        :param subnets: List of subnets
        :param container_port: Port for the container
        :param opts: Pulumi resource options
        """
        super().__init__('custom:network:HostBasedALBTargetGroup', name, {}, opts)

        try:
            # Validate inputs
            self._validate_inputs(listener_arn, vpc_id, host_condition, subnets, container_port)

            # Create Target Group
            self.target_group = self._create_target_group(name, vpc_id, container_port)

            # Create Listener Rule
            self.listener_rule = self._create_listener_rule(name, listener_arn, host_condition)

            # Export Outputs
            self.register_outputs({
                "target_group_arn": self.target_group.arn,
                "listener_rule_arn": self.listener_rule.arn,
            })

        except Exception as e:
            raise Exception(f"Failed to create Host-Based ALB Target Group: {str(e)}")
            raise

    def _validate_inputs(self, listener_arn: str, vpc_id: str, host_condition: str, subnets: list, container_port: int):
        """
        Validate input parameters before resource creation.
        
        :raises ValueError: If inputs are invalid
        """
        if isinstance(vpc_id, pulumi.Output):
            # Defer validation for Outputs
            return
        if not listener_arn or not isinstance(listener_arn, str):
            raise ValueError("Listener ARN must be a non-empty string")
        
        if not vpc_id or not isinstance(vpc_id, str):
            raise ValueError("VPC ID must be a non-empty string")
        
        if not host_condition or not isinstance(host_condition, str):
            raise ValueError("Host condition must be a non-empty string")
        
        if not subnets or not isinstance(subnets, list):
            raise ValueError("Subnets must be a non-empty list")
        
        if not isinstance(container_port, int) or container_port <= 0 or container_port > 65535:
            raise ValueError("Container port must be a valid port number")


    def _create_target_group(self, name: str, vpc_id: str, container_port: int) -> lb.TargetGroup:
        """
        Create Target Group for the ALB.
        
        :param name: Base name for the target group
        :param vpc_id: VPC ID
        :param container_port: Port for the container
        :return: Created target group
        """
        try:
            return lb.TargetGroup(
                f"{name}-tg",
                port=container_port,
                protocol="HTTP",
                vpc_id=vpc_id,
                target_type="ip",
                health_check={
                    "path": "/",
                    "interval": 30,
                    "timeout": 5,
                    "healthy_threshold": 3,
                    "unhealthy_threshold": 3,
                },
                tags={"Owner": "Dijam",
    "Project": "Numeris",
    "CostCenter": "1234",
                    "Name": f"{name}-tg",
                    "Environment": pulumi.get_stack(),
                    "ManagedBy": "Pulumi"
                }
            )
        except Exception as e:
            raise Exception(f"Failed to create target group: {str(e)}")

    def _create_listener_rule(self, name: str, listener_arn: str, host_condition: str) -> lb.ListenerRule:
        """
        Create Listener Rule for host-based routing.
        
        :param name: Base name for the listener rule
        :param listener_arn: ARN of the listener
        :param host_condition: Host header for routing
        :return: Created listener rule
        """
        try:
            # Assign and increment the priority
            priority = HostBasedALBTargetGroup._priority_counter
            HostBasedALBTargetGroup._priority_counter += 1

            return lb.ListenerRule(
                f"{name}-listener-rule",
                listener_arn=listener_arn,
                priority=priority,  # Automatically assigned priority
                conditions=[
                    {
                        "host_header": {
                            "values": [host_condition],
                        },
                    },
                ],
                actions=[{
                    "type": "forward",
                    "target_group_arn": self.target_group.arn
                }],
                opts=pulumi.ResourceOptions(parent=self)
            )
        except Exception as e:
            raise Exception(f"Failed to create listener rule: {str(e)}")