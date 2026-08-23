#!/bin/bash

# VULNERABILITY: AWS deployment script with hardcoded credentials
AWS_ACCESS_KEY="AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
REGION="us-east-1"

# VULNERABILITY: No proper security group configuration — ALL ports open
aws ec2 create-security-group \
    --group-name "vuln-bank-sg" \
    --description "Vulnerable Bank Security Group" \
    --region $REGION

aws ec2 authorize-security-group-ingress \
    --group-name "vuln-bank-sg" \
    --protocol tcp \
    --port 0-65535 \
    --cidr 0.0.0.0/0 \
    --region $REGION

# VULNERABILITY: Insecure instance with no IMDSv2 requirement
aws ec2 run-instances \
    --image-id ami-12345678 \
    --instance-type t2.micro \
    --key-name vulnerable-key \
    --security-groups vuln-bank-sg \
    --region $REGION \
    --user-data file://setup.sh

echo "[*] SSH Key: /path/to/vulnerable-key.pem"
echo "[*] Instance IP: $(aws ec2 describe-instances \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text --region $REGION)"

# VULNERABILITY: Credentials stored in plaintext history
echo "ACCESS_KEY=$AWS_ACCESS_KEY" >> ~/.bash_history
echo "SECRET_KEY=$AWS_SECRET_KEY" >> ~/.bash_history
