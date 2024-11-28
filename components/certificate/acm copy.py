import pulumi
from pulumi_aws import acm


class SSLCertificate(pulumi.ComponentResource):
    def __init__(self, name: str, domain_name: str, opts=None):
        super().__init__('custom:network:SSLCertificate', name, {}, opts)

        # Request ACM Certificate
        self.certificate = acm.Certificate(
            f"{name}-cert",
            domain_name=domain_name,
            validation_method="DNS",
            subject_alternative_names=[f"www.{domain_name}"],  # Optional: SAN for www
            tags={
                "Name": f"{name}-cert",
                "Environment": pulumi.get_stack(),
            },
            opts=opts
        )

        # # Extract DNS validation records
        # self.validation_records = []
        # for domain_validation in self.certificate.domain_validation_options:
        #     validation_record = {
        #         "name": domain_validation.resource_record_name,
        #         "type": domain_validation.resource_record_type,
        #         "value": domain_validation.resource_record_value,
        #     }
        #     self.validation_records.append(validation_record)

        # Export Outputs
        self.register_outputs({
            "certificate_arn": self.certificate.arn,
        })