
# Security Overview

This document outlines the key security mechanisms implemented in the Pulumi project.

## VPC Network Isolation
- **Private and Public Subnets**: The infrastructure uses a combination of private and public subnets to segregate resources based on access requirements.
- **Security Groups**: Security groups are configured to restrict inbound and outbound traffic for specific resources:
  - **ALB Security Group**: Allows traffic only on ports 80 (HTTP) and 443 (HTTPS) from any source.
  - **ECS Security Group**: Restricts access to traffic originating from the ALB.
  - **RDS Security Group**: Permits access only from the ECS security group on port 5432 (PostgreSQL).

## IAM Role and Policy Management
- **Task Execution Role**: An IAM role with the minimal permissions required for ECS tasks to interact with AWS resources.
- **Custom IAM Policies**: Policies are defined explicitly for ECS task execution and specific task requirements.

## Sensitive Data Handling
- **Secrets Management**: Sensitive values like database passwords are stored using Pulumi's `require_secret` function to ensure they are encrypted and not exposed in plain text.

## Secure Traffic and Encryption
- **SSL Certificate**: HTTPS traffic is secured using an SSL certificate provisioned via AWS Certificate Manager.
- **Encryption in Transit**: All communication between the client and ALB, as well as between ECS and RDS, is encrypted.

## Instance Security
- **Elasticsearch EC2 Instance**:
  - SSH access is limited to port 22.
  - Elasticsearch traffic is restricted to port 9200, with configurable CIDR blocks.

## Sensitive Data Handling
- **Secrets Management**: Sensitive values like database passwords are stored using Pulumi's `require_secret` function to ensure they are encrypted and not exposed in plain text. 
- **RDS Database Credentials**: The database password is managed securely using AWS Secrets Manager. This prevents hardcoding of sensitive data in infrastructure code, offering:
  - **Access Control**: Only authorized services (e.g., ECS or Lambda) can retrieve the credentials with IAM roles/policies that grant appropriate access.
  - **Short-lived Credentials**: The credentials provided by Secrets Manager can be accessed for a limited time, further reducing the risk of unauthorized use.
  - **Credential Rotation**: Automatic rotation of the credentials ensures the database credentials are regularly updated without manual intervention, improving security posture.
