import pulumi
import pulumi_aws as aws
import re

class EC2Instance(pulumi.ComponentResource):
    def __init__(self, name: str, ami: str, instance_type: str, 
                 subnet_id: str, security_group_ids: list, 
                 user_data: str = None, tags: dict = None, opts=None):
        """
        Create a configurable EC2 instance with input validation.
        
        :param name: Base name for the EC2 instance
        :param ami: AMI ID to launch
        :param instance_type: EC2 instance type
        :param subnet_id: Subnet ID where the instance will be created
        :param security_group_ids: List of security group IDs
        :param user_data: Optional user data script
        :param tags: Optional tags for the instance
        :param opts: Pulumi resource options
        """
        # Validate inputs
        self._validate_inputs(name, ami, instance_type, subnet_id, security_group_ids)
        
        # Call the parent constructor
        super().__init__('custom:resource:EC2Instance', name, {}, opts)
        
        try:
            # Create EC2 Instance
            self.instance = self._create_instance(
                name, ami, instance_type, subnet_id, 
                security_group_ids, user_data, tags
            )
            
            # Register outputs
            self.register_outputs({
                "instance_id": self.instance.id,
                "public_ip": self.instance.public_ip,
                "private_ip": self.instance.private_ip,
            })
        except Exception as e:
            # Pulumi-specific error handling
            raise Exception(f"Failed to create EC2 Instance: {str(e)}")
            raise
    
    def _validate_inputs(self, name: str, ami: str, instance_type: str, 
                          subnet_id: str, security_group_ids: list):
        """
        Validate input parameters before instance creation.
        
        :raises ValueError: If inputs are invalid
        """
        if isinstance(subnet_id, pulumi.Output):
            # Defer validation for Outputs
            return
        # Validate name
        if not name or not isinstance(name, str):
            raise ValueError("Name must be a non-empty string")
        if not re.match(r'^[a-zA-Z0-9-]+$', name):
            raise ValueError("Name can only contain alphanumeric characters and hyphens")
        
        # Validate AMI
        if not ami or not isinstance(ami, str):
            raise ValueError("AMI must be a non-empty string")
        
        # Validate instance type
        if not instance_type or not isinstance(instance_type, str):
            raise ValueError("Instance type must be a non-empty string")
        
        # Validate subnet ID
        if not subnet_id or not isinstance(subnet_id, str):
            raise ValueError("Subnet ID must be a non-empty string")
        
        # Validate security group IDs
        if not security_group_ids or not isinstance(security_group_ids, list):
            raise ValueError("Security group IDs must be a non-empty list")
        
    def _create_instance(self, name: str, ami: str, instance_type: str, 
                          subnet_id: str, security_group_ids: list, 
                          user_data: str = None, tags: dict = None):
        """
        Create EC2 Instance with comprehensive configuration.
        
        :return: Created EC2 Instance resource
        """
        try:
            return aws.ec2.Instance(
                resource_name=f"{name}-ec2-instance",
                ami=ami,
                instance_type=instance_type,
                subnet_id=subnet_id,
                vpc_security_group_ids=security_group_ids,
                user_data=user_data,
                tags={
                    "Name": f"{name}-instance",
                    "Environment": pulumi.get_stack(),
                    "ManagedBy": "Pulumi",
                    **(tags or {})
                }
            )
        except Exception as e:
            raise Exception(f"Failed to create EC2 Instance: {str(e)}")