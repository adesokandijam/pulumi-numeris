import pulumi
from pulumi_aws import ec2
import ipaddress

class VPC(pulumi.ComponentResource):
    def __init__(self, name: str, cidr_block: str = "10.0.0.0/16", opts=None):
        """
        Create a VPC with public and private subnets across two availability zones.
        
        :param name: Base name for resources
        :param cidr_block: CIDR block for the VPC
        :param opts: Pulumi resource options
        """
        # Validate inputs
        self._validate_inputs(name, cidr_block)
        
        # Call the parent constructor
        super().__init__('custom:network:VPC', name, {}, opts)

        try:
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
            self._associate_route_tables(name)

            # Export Outputs
            self.register_outputs({
                "vpc_id": self.vpc.id,
                "public_subnet_ids": [subnet.id for subnet in self.public_subnets],
                "private_subnet_ids": [subnet.id for subnet in self.private_subnets],
                "internet_gateway_id": self.igw.id
            })

        except Exception as e:
            # Pulumi-specific error handling
            raise Exception(f"Failed to create VPC resources: {str(e)}", self)

    def _validate_inputs(self, name: str, cidr_block: str):
        """
        Validate input parameters before resource creation.
        
        :param name: Resource name
        :param cidr_block: CIDR block to validate
        :raises ValueError: If inputs are invalid
        """
        # Validate name
        if not name or not isinstance(name, str):
            raise ValueError("Name must be a non-empty string")

        # Validate CIDR block
        try:
            ip_network = ipaddress.ip_network(cidr_block)
            if ip_network.prefixlen < 16 or ip_network.prefixlen > 24:
                raise ValueError("CIDR block must be between /16 and /24")
        except ValueError as e:
            raise ValueError(f"Invalid CIDR block: {e}")

    def _create_vpc(self, name: str, cidr_block: str) -> ec2.Vpc:
        """
        Create VPC with error handling and consistent tagging.
        
        :param name: Base name for the VPC
        :param cidr_block: CIDR block for the VPC
        :return: Created VPC resource
        """
        try:
            return ec2.Vpc(
                f"{name}-vpc",
                cidr_block=cidr_block,
                enable_dns_hostnames=True,
                enable_dns_support=True,
                tags={"Owner": "Dijam",
    "Project": "Numeris",
    "CostCenter": "1234",
                    "Name": f"{name}-vpc",
                    "Environment": pulumi.get_stack(),
                    "ManagedBy": "Pulumi"
                }
            )
        except Exception as e:
            raise pulumi.ResourceError(f"Failed to create VPC: {str(e)}")

    def _create_subnets(self, name: str, aws_region: str):
        """
        Create public and private subnets in two availability zones.
        
        :param name: Base name for subnets
        :param aws_region: AWS region
        :return: Tuple of public and private subnets
        """
        try:
            public_subnets = [
                ec2.Subnet(
                    f"{name}-public-subnet-az{i+1}",
                    vpc_id=self.vpc.id,
                    cidr_block=f"10.0.{i+1}.0/24",
                    map_public_ip_on_launch=True,
                    availability_zone=f"{aws_region}{['a', 'b'][i]}",
                    tags={"Owner": "Dijam",
    "Project": "Numeris",
    "CostCenter": "1234",
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
                    tags={"Owner": "Dijam",
    "Project": "Numeris",
    "CostCenter": "1234",
                        "Name": f"{name}-private-subnet-az{i+1}",
                        "Environment": pulumi.get_stack(),
                        "Type": "Private"
                    }
                ) for i in range(2)
            ]

            return public_subnets, private_subnets
        except Exception as e:
            raise pulumi.ResourceError(f"Failed to create subnets: {str(e)}")

    def _create_internet_gateway(self, name: str) -> ec2.InternetGateway:
        """
        Create Internet Gateway for the VPC.
        
        :param name: Base name for the Internet Gateway
        :return: Created Internet Gateway resource
        """
        try:
            return ec2.InternetGateway(
                f"{name}-igw",
                vpc_id=self.vpc.id,
                tags={"Owner": "Dijam",
    "Project": "Numeris",
    "CostCenter": "1234",
                    "Name": f"{name}-igw",
                    "Environment": pulumi.get_stack(),
                    "ManagedBy": "Pulumi"
                }
            )
        except Exception as e:
            raise pulumi.ResourceError(f"Failed to create Internet Gateway: {str(e)}")

    def _create_nat_gateway(self, name: str):
        """
        Create NAT Gateway in the first public subnet.
        
        :param name: Base name for NAT Gateway resources
        :return: Tuple of NAT Gateway and Elastic IP
        """
        try:
            nat_eip = ec2.Eip(f"{name}-nat-eip", opts=pulumi.ResourceOptions(depends_on=[self.igw]))
            nat_gw = ec2.NatGateway(
                f"{name}-nat-gw",
                allocation_id=nat_eip.id,
                subnet_id=self.public_subnets[0].id,
                tags={"Owner": "Dijam",
    "Project": "Numeris",
    "CostCenter": "1234",
                    "Name": f"{name}-nat-gw",
                    "Environment": pulumi.get_stack(),
                    "ManagedBy": "Pulumi"
                }
            )
            return nat_gw, nat_eip
        except Exception as e:
            raise pulumi.ResourceError(f"Failed to create NAT Gateway: {str(e)}")

    def _create_route_tables(self, name: str):
        """
        Create public and private route tables.
        
        :param name: Base name for route tables
        :return: Tuple of public and private route tables
        """
        try:
            public_route_table = ec2.RouteTable(
                f"{name}-public-rt",
                vpc_id=self.vpc.id,
                routes=[{
                    "cidr_block": "0.0.0.0/0",
                    "gateway_id": self.igw.id,
                }],
                tags={"Owner": "Dijam",
    "Project": "Numeris",
    "CostCenter": "1234",
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
                tags={"Owner": "Dijam",
    "Project": "Numeris",
    "CostCenter": "1234",
                    "Name": f"{name}-private-rt",
                    "Environment": pulumi.get_stack(),
                    "Type": "Private"
                }
            )

            return public_route_table, private_route_table
        except Exception as e:
            raise pulumi.ResourceError(f"Failed to create Route Tables: {str(e)}")

    def _associate_route_tables(self, name: str):
        """
        Associate subnets with their respective route tables.
        
        :param name: Base name for route table associations
        """
        try:
            # Public subnet associations
            for i, subnet in enumerate(self.public_subnets):
                ec2.RouteTableAssociation(
                    f"{name}-public-rta-az{i+1}",
                    subnet_id=subnet.id,
                    route_table_id=self.public_route_table.id
                )

            # Private subnet associations
            for i, subnet in enumerate(self.private_subnets):
                ec2.RouteTableAssociation(
                    f"{name}-private-rta-az{i+1}",
                    subnet_id=subnet.id,
                    route_table_id=self.private_route_table.id
                )
        except Exception as e:
            raise pulumi.ResourceError(f"Failed to associate Route Tables: {str(e)}")