#!/bin/bash
set -euxo pipefail

dnf update -y
dnf install -y docker git
systemctl enable --now docker
usermod -aG docker ec2-user

if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

cd /home/ec2-user
if [ ! -d dil-olympics ]; then
  git clone https://github.com/dil-kmoghe/dil-olympics.git dil-olympics
fi
mkdir -p /home/ec2-user/dil-olympics/seed /home/ec2-user/dil-olympics-data
chown -R ec2-user:ec2-user /home/ec2-user/dil-olympics /home/ec2-user/dil-olympics-data
