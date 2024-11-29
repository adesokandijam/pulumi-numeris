import pulumi
import pulumi_aws as aws
import re

class SecurityGroup(pulumi.ComponentResource):
    def __init__(self, name: str, vpc_id: str, ingress: list, egress: list, tags: dict = None, opts=None):
        """
        Create a configurable Security Group with input validation.
        
        :param name: Base name for the Security Group
        :param vpc_id: VPC ID where the security group will be created
        :param ingress: List of ingress rules (can reference another security group or a VPC CIDR)
        :param egress: List of egress rules
        :param tags: Optional tags for the security group
        :param opts: Pulumi resource options
        """
        # Validate inputs
        self._validate_inputs(name, vpc_id, ingress, egress)
        
        # Call the parent constructor
        super().__init__('custom:resource:SecurityGroup', name, {}, opts)
        
        try:
            # Create Security Group
            self.security_group = self._create_security_group(
                name, vpc_id, ingress, egress, tags
            )
            
            # Register outputs
            self.register_outputs({
                "security_group_id": self.security_group.id,
                "security_group_name": self.security_group.name,
            })
        except Exception as e:
            # Pulumi-specific error handling
            raise Exception(f"Failed to create Security Group: {str(e)}")
    
    def _validate_inputs(self, name: str, vpc_id: str, ingress: list, egress: list):
        """
        Validate input parameters before security group creation.
        
        :raises ValueError: If inputs are invalid
        """
        # Validate name
        if isinstance(vpc_id, pulumi.Output):
            # Defer validation for Outputs
            return
        if not name or not isinstance(name, str):
            raise ValueError("Name must be a non-empty string")
        if not re.match(r'^[a-zA-Z0-9-]+$', name):
            raise ValueError("Name can only contain alphanumeric characters and hyphens")
        
        # Validate VPC ID
        if not vpc_id or not isinstance(vpc_id, str):
            raise ValueError("VPC ID must be a non-empty string")
        
        # Validate ingress rules
        if not ingress or not isinstance(ingress, list):
            raise ValueError("Ingress rules must be a non-empty list")
        
        # Validate egress rules
        if not egress or not isinstance(egress, list):
            raise ValueError("Egress rules must be a non-empty list")
    
    def _create_security_group(self, name: str, vpc_id: str, ingress: list, egress: list, tags: dict = None):
        """
        Create the Security Group with given ingress and egress rules.
        
        :return: Created Security Group resource
        """
        try:
            formatted_ingress = self._format_ingress_rules(ingress)
            return aws.ec2.SecurityGroup(
                resource_name=f"{name}-sg",
                vpc_id=vpc_id,
                ingress=formatted_ingress,
                egress=egress,
                tags={"Owner": "Dijam",
                    "Project": "Numeris",
                    "CostCenter": "1234",
                    "Name": f"{name}-sg",
                    "Environment": pulumi.get_stack(),
                    "ManagedBy": "Pulumi",
                    **(tags or {})
                }
            )
        except Exception as e:
            raise Exception(f"Failed to create Security Group: {str(e)}")

    def _format_ingress_rules(self, ingress):
        """
        Format the ingress rules based on the input.
        
        :param ingress: List of ingress rules, which can contain security group IDs or CIDR blocks
        :return: A list of formatted ingress rules
        """
        formatted_ingress = []
        
        for rule in ingress:
            # If the rule is a dictionary with "security_group_id" or "cidr_block"
            if isinstance(rule, dict):
                if "security_group_id" in rule:
                    formatted_ingress.append({
                        "protocol": rule.get("protocol", "tcp"),
                        "from_port": rule.get("from_port"),
                        "to_port": rule.get("to_port"),
                        "security_groups": [rule["security_group_id"]],
                    })
                elif "cidr_block" in rule:
                    formatted_ingress.append({
                        "protocol": rule.get("protocol", "tcp"),
                        "from_port": rule.get("from_port"),
                        "to_port": rule.get("to_port"),
                        "cidr_blocks": [rule["cidr_block"]],
                    })
            else:
                raise ValueError("Ingress rule must be a dictionary containing 'security_group_id' or 'cidr_block'")
        
        return formatted_ingress