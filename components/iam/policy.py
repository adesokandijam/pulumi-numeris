import pulumi
from pulumi_aws import iam
import json

class IAMPolicy(pulumi.ComponentResource):
    def __init__(self, name: str, policy_document: dict, opts=None):
        """
        Create an IAM Policy with comprehensive error handling and tagging.
        
        :param name: Base name for the IAM policy
        :param policy_document: Dictionary containing the IAM policy document
        :param opts: Pulumi resource options
        """
        # Call the parent constructor
        super().__init__('custom:iam:IAMPolicy', name, {}, opts)

        try:
            # Validate policy document
            self._validate_policy_document(policy_document)

            # Create IAM Policy
            self.policy = self._create_policy(name, policy_document)

            # Export Outputs
            self.register_outputs({
                "policy_name": self.policy.name,
                "policy_arn": self.policy.arn,
            })

        except Exception as e:
            # Pulumi-specific error handling
            raise Exception(f"Failed to create IAM Policy: {str(e)}")
            raise

    def _validate_policy_document(self, policy_document: dict):
        """
        Validate the IAM policy document structure.
        
        :param policy_document: Dictionary to validate
        :raises ValueError: If policy document is invalid
        """
        if not policy_document or not isinstance(policy_document, dict):
            raise ValueError("Policy document must be a non-empty dictionary")
        
        try:
            # Attempt to parse as JSON to ensure valid structure
            json.dumps(policy_document)
        except TypeError as e:
            raise ValueError(f"Invalid policy document structure: {e}")

    def _create_policy(self, name: str, policy_document: dict) -> iam.Policy:
        """
        Create IAM Policy with consistent tagging and error handling.
        
        :param name: Base name for the policy
        :param policy_document: IAM policy document
        :return: Created IAM Policy resource
        """
        try:
            return iam.Policy(
                f"{name}-policy",
                policy=json.dumps(policy_document),
                tags={
                    "Name": f"{name}-policy",
                    "Environment": pulumi.get_stack(),
                    "ManagedBy": "Pulumi"
                }
            )
        except Exception as e:
            raise Exception(f"Failed to create IAM Policy: {str(e)}")