
# Deployment Guide

This guide provides step-by-step instructions for deploying the Pulumi project.

## Prerequisites
1. Install **Pulumi CLI** and authenticate using your cloud provider credentials.
2. Install **AWS CLI** and configure it with your credentials.
3. Set up a Python virtual environment and install the required dependencies.

## Deployment Steps

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd pulumi-numeris
```

### Step 2: Install Dependencies
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Configure Pulumi Stack
- Create a new Pulumi stack for the environment:
  ```bash
  pulumi stack init dev
  ```
- Set configuration values:
  ```bash
  pulumi config set myproject:vpcCidr 10.0.0.0/16
  pulumi config set myproject:dbPassword --secret <your-password>
  ```

### Step 4: Preview Deployment
- Review planned infrastructure changes:
  ```bash
  pulumi preview
  ```

### Step 5: Deploy Infrastructure
- Deploy the resources:
  ```bash
  pulumi up
  ```

## Post-Deployment Steps

### Verify the Infrastructure
1. **Application Load Balancer (ALB)**:
   - Verify that the ALB is running and serving traffic on HTTPS.
2. **ECS Service**:
   - Access the ECS service via the ALB domain.
3. **RDS Database**:
   - Retrieve RDS connection details from Pulumi outputs and test connectivity.
4. **Elasticsearch**:
   - SSH into the Elasticsearch EC2 instance and confirm the service is running.

## Rollback Instructions
If deployment issues occur, you can roll back the infrastructure by destroying it:
```bash
pulumi destroy
pulumi stack rm dev
```

## Deployment Diagram
Include an architecture diagram here to provide a visual representation of the deployed infrastructure.
