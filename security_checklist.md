# Security Audit Checklist

## Overview
This document lists key security checks to ensure AWS environment compliance with best practices.

## Identity and Access Management (IAM)
- [ ] Use MFA for all IAM users.
- [ ] Restrict root account access.
- [ ] Rotate IAM keys regularly.

## Networking
- [ ] Use VPCs with restricted CIDR ranges.
- [ ] Ensure security groups follow the principle of least privilege.
- [ ] Enable VPC Flow Logs for monitoring.

## Data Protection
- [ ] Enable encryption at rest (e.g., RDS, S3).
- [ ] Enforce encryption in transit using TLS.

## Monitoring and Logging
- [ ] Enable CloudTrail for all regions.
- [ ] Monitor logs using CloudWatch.
- [ ] Set up alerts for suspicious activity.

## Application Security
- [ ] Perform static and dynamic code analysis.
- [ ] Validate input to prevent injection attacks.

## Disaster Recovery
- [ ] Test backup restoration processes regularly.
- [ ] Ensure failover mechanisms work as intended.