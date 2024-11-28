import pulumi
from pulumi_aws import secretsmanager

class DBSecret(pulumi.ComponentResource):
    def __init__(
        self,
        name: str,
        username: str,
        password: str,
        opts: pulumi.ResourceOptions = None,
    ):
        """
        Create a secret in AWS Secrets Manager for database credentials.
        
        :param name: Name of the secret
        :param username: Database username
        :param password: Database password
        :param opts: Pulumi resource options
        """
        super().__init__('custom:secrets:DBSecret', name, {}, opts)

        # Create the secret in AWS Secrets Manager
        self.secret = secretsmanager.Secret(
            f"{name}-db-credentials",
            description="Database credentials for RDS",
            secret_string=pulumi.Output.all(username, password).apply(
                lambda args: f'{{"username": "{args[0]}", "password": "{args[1]}"}}'
            ),
            tags={
                "Name": f"{name}-db-credentials",
                "Environment": pulumi.get_stack(),
            }
        )

        # Export the secret ARN and ID
        self.register_outputs({
            "secret_arn": self.secret.arn,
            "secret_name": self.secret.name,
        })