import pulumi
from pulumi_aws import ec2, lb

class ApplicationLoadBalancer(pulumi.ComponentResource):
    def __init__(self, name: str, vpc_id: str, subnets: list, certificate_arn: str, alb_security_group_id: str, opts=None):
        """
        Create an Application Load Balancer with HTTPS and HTTP listeners, and use an externally created Security Group.
        
        :param name: Base name for resources
        :param vpc_id: VPC ID where resources will be created
        :param subnets: List of subnet IDs for the load balancer
        :param certificate_arn: ARN of the SSL certificate
        :param alb_security_group_id: Security Group ID to use for the ALB
        :param opts: Pulumi resource options
        """
        super().__init__('custom:network:ApplicationLoadBalancer', name, {}, opts)

        try:
            # Validate inputs
            self._validate_inputs(vpc_id, subnets, certificate_arn, alb_security_group_id)

            # Use the provided Security Group ID
            self.alb_security_group_id = alb_security_group_id

            # Create Load Balancer
            self.alb = self._create_load_balancer(name, subnets)

            # Create HTTPS Listener
            self.https_listener = self._create_https_listener(name, certificate_arn)

            # Create HTTP Listener
            self.http_listener = self._create_http_listener(name)

            # Export Outputs
            self.register_outputs({
                "alb_arn": self.alb.arn,
                "alb_dns_name": self.alb.dns_name,
                "https_listener_arn": self.https_listener.arn,
                "http_listener_arn": self.http_listener.arn,
            })

        except Exception as e:
            raise Exception(f"Failed to create Application Load Balancer: {str(e)}")

    def _validate_inputs(self, vpc_id: str, subnets: list, certificate_arn: str, alb_security_group_id: str):
        """
        Validate input parameters before resource creation.
        
        :raises ValueError: If inputs are invalid
        """
        if isinstance(vpc_id, pulumi.Output):
            # Defer validation for Outputs
            return
        if not vpc_id or not isinstance(vpc_id, str):
            raise ValueError("VPC ID must be a non-empty string")
        
        if not subnets or not isinstance(subnets, list) or len(subnets) < 2:
            raise ValueError("At least two subnets are required")
        
        if not certificate_arn or not isinstance(certificate_arn, str):
            raise ValueError("Certificate ARN must be a non-empty string")
        
        if not alb_security_group_id or not isinstance(alb_security_group_id, str):
            raise ValueError("Security Group ID must be a non-empty string")

    def _create_load_balancer(self, name: str, subnets: list) -> lb.LoadBalancer:
        """
        Create Application Load Balancer.
        
        :param name: Base name for the load balancer
        :param subnets: List of subnet IDs
        :return: Created load balancer
        """
        try:
            return lb.LoadBalancer(
                f"{name}-alb",
                internal=False,
                load_balancer_type="application",
                security_groups=[self.alb_security_group_id],
                subnets=subnets,
                enable_deletion_protection=False,
                tags={
                    "Name": f"{name}-alb",
                    "Environment": pulumi.get_stack(),
                    "ManagedBy": "Pulumi"
                }
            )
        except Exception as e:
            raise Exception(f"Failed to create load balancer: {str(e)}")

    def _create_https_listener(self, name: str, certificate_arn: str) -> lb.Listener:
        """
        Create HTTPS listener with fixed response.
        
        :param name: Base name for the listener
        :param certificate_arn: ARN of SSL certificate
        :return: Created HTTPS listener
        """
        try:
            return lb.Listener(
                f"{name}-https-listener",
                load_balancer_arn=self.alb.arn,
                port=443,
                protocol="HTTPS",
                ssl_policy="ELBSecurityPolicy-TLS13-1-2-2021-06",
                certificate_arn=certificate_arn,
                default_actions=[{
                    "type": "fixed-response",
                    "fixed_response": {
                        "content_type": "text/plain",
                        "message_body": "Hello from here. Happy to be serving you",
                        "status_code": "200",
                    },
                }]
            )
        except Exception as e:
            raise Exception(f"Failed to create HTTPS listener: {str(e)}")

    def _create_http_listener(self, name: str) -> lb.Listener:
        """
        Create HTTP listener with redirect to HTTPS.
        
        :param name: Base name for the listener
        :return: Created HTTP listener
        """
        try:
            return lb.Listener(
                f"{name}-http-listener",
                load_balancer_arn=self.alb.arn,
                port=80,
                protocol="HTTP",
                default_actions=[{
                    "type": "redirect",
                    "redirect": {
                        "port": "443",
                        "protocol": "HTTPS",
                        "status_code": "HTTP_301",
                    },
                }]
            )
        except Exception as e:
            raise Exception(f"Failed to create HTTP listener: {str(e)}")