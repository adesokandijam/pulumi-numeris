import pulumi
from pulumi_aws import iam
import json

class IAMRole(pulumi.ComponentResource):
    def __init__(self, name: str, assume_role_policy: dict, policy_arn: str = None, opts=None):
        """
        Create an IAM Role with optional policy attachment.
        
        :param name: Base name for the IAM role
        :param assume_role_policy: Dictionary containing the assume role policy
        :param policy_arn: Optional policy ARN to attach to the role
        :param opts: Pulumi resource options
        """
        # Call the parent constructor
        super().__init__('custom:iam:IAMRole', name, {}, opts)

        try:
            # Validate assume role policy
            self._validate_assume_role_policy(assume_role_policy)

            # Create IAM Role
            self.role = self._create_role(name, assume_role_policy)

            # Attach external policy if provided
            self.policy_attachment = self._attach_policy(name, policy_arn) if policy_arn else None

            # Export Outputs
            self.register_outputs({
                "role_name": self.role.name,
                "role_arn": self.role.arn,
            })

        except Exception as e:
            # Pulumi-specific error handling
            raise Exception(f"Failed to create IAM Role: {str(e)}")
            raise

    def _validate_assume_role_policy(self, assume_role_policy: dict):
        """
        Validate the assume role policy document structure.
        
        :param assume_role_policy: Dictionary to validate
        :raises ValueError: If policy document is invalid
        """
        if not assume_role_policy or not isinstance(assume_role_policy, dict):
            raise ValueError("Assume role policy must be a non-empty dictionary")
        
        try:
            # Attempt to parse as JSON to ensure valid structure
            json.dumps(assume_role_policy)
        except TypeError as e:
            raise ValueError(f"Invalid assume role policy structure: {e}")

    def _create_role(self, name: str, assume_role_policy: dict) -> iam.Role:
        """
        Create IAM Role with consistent tagging and error handling.
        
        :param name: Base name for the role
        :param assume_role_policy: IAM assume role policy document
        :return: Created IAM Role resource
        """
        try:
            return iam.Role(
                f"{name}-role",
                assume_role_policy=json.dumps(assume_role_policy),
                tags={"Owner": "Dijam",
                    "Project": "Numeris",
                    "CostCenter": "1234",
                    "Name": f"{name}-role",
                    "Environment": pulumi.get_stack(),
                    "ManagedBy": "Pulumi"
                }
            )
        except Exception as e:
            raise Exception(f"Failed to create IAM Role: {str(e)}")

    def _attach_policy(self, name: str, policy_arn: str):
        """
        Attach an external policy to the IAM role.
        
        :param name: Base name for the policy attachment
        :param policy_arn: ARN of the policy to attach
        :return: Policy attachment resource
        """
        try:
            return iam.RolePolicyAttachment(
                f"{name}-policy-attachment",
                role=self.role.name,
                policy_arn=policy_arn
            )
        except Exception as e:
            raise Exception(f"Failed to attach policy to role: {str(e)}")