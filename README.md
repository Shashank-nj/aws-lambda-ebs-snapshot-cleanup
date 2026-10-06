# AWS Lambda EBS Snapshot Cleanup

## 📌 Project Overview

This project uses AWS Lambda and Python boto3 to automatically identify
and clean up unnecessary EBS snapshots.

The Lambda function checks:

- Running EC2 instances
- EBS volumes
- EBS snapshots
- Volume attachments

Snapshots whose source volume is not attached to a running EC2 instance
can be deleted automatically.

## 🏗️ Architecture

```text
EventBridge
     |
     v
AWS Lambda
     |
     v
Python + boto3
     |
     v
IAM Role
     |
     +----------------+
     |       |        |
     v       v        v
   EC2     EBS      Snapshots
Instances Volumes
     |
     v
Cleanup Decision
     |
     v
Delete Unused Snapshots