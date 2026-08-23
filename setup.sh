#!/bin/bash
# setup.sh - AWS EC2 User Data Payload for AdvancedVulnBank
# This script automatically installs dependencies when the EC2 instance boots.

# 1. Update packages
apt-get update -y
apt-get upgrade -y

# 2. Install dependencies for Docker
apt-get install -y apt-transport-https ca-certificates curl software-properties-common

# 3. Install Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
apt-get update -y
apt-get install -y docker-ce docker-compose

# 4. Enable Docker to start on boot
systemctl enable docker
systemctl start docker

# Add ubuntu user to docker group (if using default Ubuntu AMI)
usermod -aG docker ubuntu

# Note: Since the application source code is not in a public repository, 
# you will need to SCP or Git Clone the code into /opt/vulnbank 
# and then run `docker-compose up -d` manually.

mkdir -p /opt/vulnbank
chown ubuntu:ubuntu /opt/vulnbank

echo "Docker installation complete. Awaiting application code sync." > /var/log/vulnbank_setup.log
