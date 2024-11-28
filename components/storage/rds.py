import pulumi
from pulumi_aws import rds

class RDS(pulumi.ComponentResource):
    def __init__(
        self,
        name: str,
        vpc_id: str,
        private_subnet_ids: list,
        security_group_id: pulumi.Output,  # Accept security group as input
        db_name: str = "mydatabase",
        username: str = "admin",
        manage_master_user_password: bool = True,  # Use Pulumi config for secrets
        backup_retention: int = 7,
        engine: str = "postgres",  # Default to PostgreSQL
        engine_version: str = "14.12",  # Default PostgreSQL version
        instance_class: str = "db.t4g.micro",  # Default instance class
        allocated_storage: int = 20,  # Default allocated storage
        opts=None,
    ):
        """
        Create an RDS PostgreSQL instance with comprehensive configuration.
        
        :param name: Base name for resources
        :param vpc_id: VPC ID
        :param private_subnet_ids: Private subnet IDs
        :param security_group_id: Pre-created Security Group for the RDS instance
        :param db_name: Database name
        :param username: Database username
        :param backup_retention: Backup retention period
        :param engine: Database engine type
        :param engine_version: Version of the database engine
        :param instance_class: Instance class for the RDS instance
        :param allocated_storage: Allocated storage size for the RDS instance
        :param opts: Pulumi resource options
        """
        super().__init__('custom:storage:RDS', name, {}, opts)

        try:
            # Validate inputs
            self._validate_inputs(
                name, vpc_id, 
                private_subnet_ids, db_name, username
            )

            # Create Subnet Group
            self.subnet_group = self._create_subnet_group(name, private_subnet_ids)

            # Create RDS Instance
            self.db_instance = self._create_db_instance(
                name, db_name, username, manage_master_user_password, 
                backup_retention, self.subnet_group, security_group_id, 
                engine, engine_version, instance_class, allocated_storage
            )

            # Export Outputs
            self.register_outputs({
                "db_endpoint": self.db_instance.endpoint,
                "db_name": db_name,
                "db_port": self.db_instance.port,
            })

        except ValueError as ve:
            # Raise the validation error
            raise
        except Exception as e:
            # Use Pulumi's built-in error mechanism
            raise Exception(f"Failed to create RDS resources: {str(e)}")

    def _validate_inputs(
        self, name: str, vpc_id: str,
        private_subnet_ids: list, db_name: str, username: str
    ):
        """
        Validate input parameters before resource creation.
        
        :raises ValueError: If inputs are invalid
        """
        if isinstance(vpc_id, pulumi.Output):
            # Defer validation for Outputs
            return
        # Comprehensive input validation
        if not name or not isinstance(name, str):
            raise ValueError("Name must be a non-empty string")
        
        if not vpc_id or not isinstance(vpc_id, str):
            raise ValueError("VPC ID must be a non-empty string")
        
        if not private_subnet_ids or not isinstance(private_subnet_ids, list) or len(private_subnet_ids) == 0:
            raise ValueError("Private subnet IDs must be a non-empty list")
        
        if not db_name or not isinstance(db_name, str):
            raise ValueError("Database name must be a non-empty string")
        
        if not username or not isinstance(username, str):
            raise ValueError("Username must be a non-empty string")

    def _create_subnet_group(self, name: str, private_subnet_ids: list) -> rds.SubnetGroup:
        """
        Create an RDS Subnet Group for private subnets.
        
        :param name: Base name for the subnet group
        :param private_subnet_ids: List of private subnet IDs
        :return: Created Subnet Group
        """
        return rds.SubnetGroup(
            f"{name}-rds-subnet-group",
            subnet_ids=private_subnet_ids,
            tags={"Owner": "Dijam",
    "Project": "Numeris",
    "CostCenter": "1234",
                "Name": f"{name}-rds-subnet-group",
                "Environment": pulumi.get_stack(),
            }
        )

    def _create_db_instance(
        self, name: str, db_name: str, username: str, manage_master_user_password,
        backup_retention: int, subnet_group, security_group_id,
        engine: str, engine_version: str, instance_class: str, allocated_storage: int
    ) -> rds.Instance:
        """
        Create the RDS instance.
        
        :param name: Base name for the RDS instance
        :param db_name: Database name
        :param username: Database username
        :param password: Database password
        :param backup_retention: Backup retention period
        :param subnet_group: The subnet group
        :param security_group_id: The security group
        :param engine: The database engine
        :param engine_version: The version of the database engine
        :param instance_class: Instance class for the database
        :param allocated_storage: Storage size for the database
        :return: Created RDS Instance
        """
        return rds.Instance(
            f"{name}-rds-instance",
            engine=engine,
            engine_version=engine_version,
            instance_class=instance_class,
            allocated_storage=allocated_storage,
            db_name=db_name,
            username=username,
            manage_master_user_password=True,
            backup_retention_period=backup_retention,
            multi_az=False,
            publicly_accessible=False,
            vpc_security_group_ids=[security_group_id],
            db_subnet_group_name=subnet_group.name,
            tags={"Owner": "Dijam",
    "Project": "Numeris",
    "CostCenter": "1234",
                "Name": f"{name}-rds-instance",
                "Environment": pulumi.get_stack(),
                "ManagedBy": "Pulumi",
            },
            skip_final_snapshot=True,  # Set to False if you want final snapshot before deletion
        )