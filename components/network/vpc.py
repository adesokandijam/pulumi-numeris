import pulumi
from pulumi_aws import ec2
import ipaddress

class VPC(pulumi.ComponentResource):
    def __init__(self, name: str, cidr_block: str = "10.0.0.0/16", opts=None):
        """
        Create a VPC with public and private subnets across two availability zones, and a VPC endpoint.

        :param name: Base name for resources
        :param cidr_block: CIDR block for the VPC
        :param opts: Pulumi resource options
        """
        self._validate_inputs(name, cidr_block)
        super().__init__('custom:network:VPC', name, {}, opts)

        # Fetch AWS region from Pulumi config
        aws_region = pulumi.Config("aws").require("region")

        # Create VPC
        self.vpc = self._create_vpc(name, cidr_block)

        # Create Subnets
        self.public_subnets, self.private_subnets = self._create_subnets(name, aws_region)

        # Create Internet Gateway
        self.igw = self._create_internet_gateway(name)

        # Create NAT Gateway
        self.nat_gw, self.nat_eip = self._create_nat_gateway(name)

        # Create Route Tables
        self.public_route_table, self.private_route_table = self._create_route_tables(name)

        # Associate Subnets with Route Tables
        self._associate_route_tables()

        # Create VPC Endpoint (for S3 in this example)
        self.s3_vpc_endpoint = self._create_vpc_endpoint(name)

        # Export Outputs
        self.register_outputs({
            "vpc_id": self.vpc.id,
            "public_subnet_ids": [subnet.id for subnet in self.public_subnets],
            "private_subnet_ids": [subnet.id for subnet in self.private_subnets],
            "internet_gateway_id": self.igw.id,
            "s3_vpc_endpoint_id": self.s3_vpc_endpoint.id
        })

    def _validate_inputs(self, name: str, cidr_block: str):
        if not name or not isinstance(name, str):
            raise ValueError("Name must be a non-empty string")
        try:
            ip_network = ipaddress.ip_network(cidr_block)
            if ip_network.prefixlen < 16 or ip_network.prefixlen > 24:
                raise ValueError("CIDR block must be between /16 and /24")
        except ValueError as e:
            raise ValueError(f"Invalid CIDR block: {e}")

    def _create_vpc(self, name: str, cidr_block: str) -> ec2.Vpc:
        return ec2.Vpc(
            f"{name}-vpc",
            cidr_block=cidr_block,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            tags={
                "Name": f"{name}-vpc",
                "Environment": pulumi.get_stack(),
                "ManagedBy": "Pulumi"
            }
        )

    def _create_subnets(self, name: str, aws_region: str):
        public_subnets = [
            ec2.Subnet(
                f"{name}-public-subnet-az{i+1}",
                vpc_id=self.vpc.id,
                cidr_block=f"10.0.{i+1}.0/24",
                map_public_ip_on_launch=True,
                availability_zone=f"{aws_region}{['a', 'b'][i]}",
                tags={
                    "Name": f"{name}-public-subnet-az{i+1}",
                    "Environment": pulumi.get_stack(),
                    "Type": "Public"
                }
            ) for i in range(2)
        ]

        private_subnets = [
            ec2.Subnet(
                f"{name}-private-subnet-az{i+1}",
                vpc_id=self.vpc.id,
                cidr_block=f"10.0.{i+3}.0/24",
                map_public_ip_on_launch=False,
                availability_zone=f"{aws_region}{['a', 'b'][i]}",
                tags={
                    "Name": f"{name}-private-subnet-az{i+1}",
                    "Environment": pulumi.get_stack(),
                    "Type": "Private"
                }
            ) for i in range(2)
        ]

        return public_subnets, private_subnets

    def _create_internet_gateway(self, name: str) -> ec2.InternetGateway:
        return ec2.InternetGateway(
            f"{name}-igw",
            vpc_id=self.vpc.id,
            tags={
                "Name": f"{name}-igw",
                "Environment": pulumi.get_stack(),
                "ManagedBy": "Pulumi"
            }
        )

    def _create_nat_gateway(self, name: str):
        nat_eip = ec2.Eip(f"{name}-nat-eip")
        nat_gw = ec2.NatGateway(
            f"{name}-nat-gw",
            allocation_id=nat_eip.id,
            subnet_id=self.public_subnets[0].id,
            tags={
                "Name": f"{name}-nat-gw",
                "Environment": pulumi.get_stack(),
                "ManagedBy": "Pulumi"
            }
        )
        return nat_gw, nat_eip

    def _create_route_tables(self, name: str):
        public_route_table = ec2.RouteTable(
            f"{name}-public-rt",
            vpc_id=self.vpc.id,
            routes=[{
                "cidr_block": "0.0.0.0/0",
                "gateway_id": self.igw.id,
            }],
            tags={
                "Name": f"{name}-public-rt",
                "Environment": pulumi.get_stack(),
                "Type": "Public"
            }
        )

        private_route_table = ec2.RouteTable(
            f"{name}-private-rt",
            vpc_id=self.vpc.id,
            routes=[{
                "cidr_block": "0.0.0.0/0",
                "nat_gateway_id": self.nat_gw.id,
            }],
            tags={
                "Name": f"{name}-private-rt",
                "Environment": pulumi.get_stack(),
                "Type": "Private"
            }
        )

        return public_route_table, private_route_table

    def _associate_route_tables(self):
        for i, subnet in enumerate(self.public_subnets):
            ec2.RouteTableAssociation(
                f"public-rta-{i+1}",
                subnet_id=subnet.id,
                route_table_id=self.public_route_table.id
            )

        for i, subnet in enumerate(self.private_subnets):
            ec2.RouteTableAssociation(
                f"private-rta-{i+1}",
                subnet_id=subnet.id,
                route_table_id=self.private_route_table.id
            )

    def _create_vpc_endpoint(self, name: str) -> ec2.VpcEndpoint:
        return ec2.VpcEndpoint(
            f"{name}-s3-vpce",
            vpc_id=self.vpc.id,
            service_name=f"com.amazonaws.{pulumi.Config('aws').require('region')}.s3",
            vpc_endpoint_type="Gateway",
            route_table_ids=[self.public_route_table.id],
            tags={
                "Name": f"{name}-s3-vpce",
                "Environment": pulumi.get_stack(),
                "ManagedBy": "Pulumi"
            }
        )