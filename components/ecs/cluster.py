import pulumi
from pulumi_aws import ecs
import re

class ECSCluster(pulumi.ComponentResource):
    def __init__(self, name: str, enable_container_insights: bool = False, opts=None):
        """
        Create an ECS Cluster with optional container insights.
        
        :param name: Base name for the ECS cluster
        :param enable_container_insights: Enable CloudWatch Container Insights
        :param opts: Pulumi resource options
        """
        # Validate inputs
        self._validate_inputs(name)
        
        # Call the parent constructor
        super().__init__('custom:ecs:ECSCluster', name, {}, opts)

        try:
            # Create ECS Cluster
            self.cluster = self._create_cluster(name, enable_container_insights)

            # Export Outputs
            self.register_outputs({
                "cluster_arn": self.cluster.arn,
                "cluster_name": self.cluster.name,
                "container_insights": enable_container_insights
            })

        except Exception as e:
            # Pulumi-specific error handling
            raise Exception(f"Failed to create ECS Cluster: {str(e)}")
            raise

    def _validate_inputs(self, name: str):
        """
        Validate input parameters before cluster creation.
        
        :param name: Resource name
        :raises ValueError: If inputs are invalid
        """
        # Validate name
        if not name or not isinstance(name, str):
            raise ValueError("Name must be a non-empty string")

        # Additional name validation (optional)
        if not re.match(r'^[a-zA-Z0-9-]+$', name):
            raise ValueError("Name can only contain alphanumeric characters and hyphens")

    def _create_cluster(self, name: str, enable_container_insights: bool):
        """
        Create ECS Cluster with comprehensive configuration.
        
        :param name: Base name for the cluster
        :param enable_container_insights: Enable CloudWatch Container Insights
        :return: Created ECS Cluster resource
        """
        try:
            return ecs.Cluster(
                f"{name}-ecs-cluster",
                name=f"{name}-ecs-cluster",
                tags={"Owner": "Dijam",
                    "Project": "Numeris",
                    "CostCenter": "1234",
                    "Name": f"{name}-cluster",
                    "Environment": pulumi.get_stack(),
                    "ManagedBy": "Pulumi",
                    "ContainerInsights": str(enable_container_insights)
                }
            )
        except Exception as e:
            raise Exception(f"Failed to create ECS Cluster: {str(e)}")