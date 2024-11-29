import pulumi
from pulumi_aws import acm
import re

class SSLCertificate(pulumi.ComponentResource):
    def __init__(self, name: str, domain_name: str, include_www: bool = False, opts=None):
        """
        Create an SSL Certificate with optional www subdomain.
        
        :param name: Base name for resources
        :param domain_name: Primary domain for the certificate
        :param include_www: Whether to include www subdomain
        :param opts: Pulumi resource options
        """
        # Validate inputs
        self._validate_inputs(name, domain_name)
        
        # Call the parent constructor
        super().__init__('custom:network:SSLCertificate', name, {}, opts)

        try:
            # Request ACM Certificate
            self.certificate = self._create_certificate(name, domain_name, include_www, opts)

            # Export Outputs
            self.register_outputs({
                "certificate_arn": self.certificate.arn,
                "certificate_id": self.certificate.id,
                "domain_name": domain_name
            })

        except Exception as e:
            # Pulumi-specific error handling
            raise Exception(f"Failed to create SSL Certificate: {str(e)}")
            raise

    def _validate_inputs(self, name: str, domain_name: str):
        """
        Validate input parameters before certificate creation.
        
        :param name: Resource name
        :param domain_name: Domain name to validate
        :raises ValueError: If inputs are invalid
        """
        # Validate name
        if not name or not isinstance(name, str):
            raise ValueError("Name must be a non-empty string")

        # Validate domain name
        if not domain_name or not isinstance(domain_name, str):
            raise ValueError("Domain name must be a non-empty string")

        # Basic domain name validation using regex
        domain_pattern = r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$'
        if not re.match(domain_pattern, domain_name, re.IGNORECASE):
            raise ValueError(f"Invalid domain name format: {domain_name}")

    def _create_certificate(self, name: str, domain_name: str, include_www: bool, opts=None):
        """
        Create ACM Certificate with optional www subdomain.
        
        :param name: Base name for the certificate
        :param domain_name: Primary domain for the certificate
        :param include_www: Whether to include www subdomain
        :param opts: Pulumi resource options
        :return: Created ACM Certificate resource
        """
        try:
            # Prepare subject alternative names
            subject_alternative_names = [domain_name]
            if include_www:
                subject_alternative_names.append(f"www.{domain_name}")

            return acm.Certificate(
                f"{name}-cert",
                domain_name=domain_name,
                validation_method="DNS",
                subject_alternative_names=subject_alternative_names,
                tags={"Owner": "Dijam",
                    "Project": "Numeris",
                    "CostCenter": "1234",
                    "Name": f"{name}-cert",
                    "Environment": pulumi.get_stack(),
                    "ManagedBy": "Pulumi",
                    "Domain": domain_name
                },
                opts=opts
            )
        except Exception as e:
            raise Exception(f"Failed to create SSL Certificate: {str(e)}")