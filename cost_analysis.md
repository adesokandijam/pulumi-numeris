# AWS Cost Estimate

## Monthly Service Breakdown

| Service | Region | Monthly Cost | Configuration | Notes |
|---------|--------|--------------|---------------|-------|
| Amazon VPC | US East (N. Virginia) | $38.75 | - 1 NAT Gateway<br>- 1 Public IPv4 Address | Optimize network configuration |
| AWS Fargate | US East (N. Virginia) | $7.21 | - Linux OS<br>- ARM Architecture<br>- 1 Task/Day | Leverage ARM for efficiency and consider reserved instances for up to 70% cost savings |
| Elastic Load Balancing | US East (N. Virginia) | $16.90 | - 1 Application Load Balancer | Ensure efficient traffic distribution |
| Amazon RDS PostgreSQL | US East (N. Virginia) | $3.87 | - 20 GB Storage<br>- db.t4g.micro<br>- 10% Utilization | Consider reserved instances for up to 70% cost savings |
| Amazon EC2 | US East (N. Virginia) | $16.94 | - 2 t2.micro Instances<br>- Linux OS | Consider reserved instances for up to 70% cost savings |

## Cost Summary

- **Upfront Cost:** $0.00 USD
- **Monthly Cost:** $83.67 USD
- **Annual Cost:** $1,004.04 USD

## Key Cost Optimization Strategies

1. Utilize Reserved Instances and Compute Saving Plans for up to 60% cost savings in compute
2. Standardize on ARM architecture
3. Continuously monitor and right-size resources

**Disclaimer:** Pricing is estimated and may vary based on actual usage.