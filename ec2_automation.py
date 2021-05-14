import boto3
import os
from botocore.exceptions import ClientError

user_data = '''
#!/bin/bash
sudo yum -y update
sudo yum -y upgrade
#sudo yum list installed cloud-init
sudo yum install cloud-init

# Format and mount an attached volume
DEVICE=/dev/$(lsblk -rno NAME | awk 'FNR == 3 {print}')
MOUNT_POINT=/data/
mkdir $MOUNT_POINT
yum -y install xfsprogs
mkfs -t xfs $DEVICE
mount $DEVICE $MOUNT_POINT

# get admin privileges
sudo su

#cloud-config
cloud_final_modules:
- [users-groups,always]
users:
  - name: user1
    groups: [ wheel ]
    sudo: [ "ALL=(ALL) NOPASSWD:ALL" ]
    shell: /bin/bash
    ssh-authorized-keys: 
    - ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCjFdaEAbN4w5A8y3/Yj4qZxD5DJTCBJ9QM2TJREhApAVhTW6UC9+BjeCQiZZdW4ZTgGRLNfdBCOQhoJu2/HjoLQ8lpWtn839dxwOTwBQKNTJAOHKvxCezbFwqU9nzoYaVEfiVzew/LPYwh2MUprwgObSULFLraarGiqf/LhDTNCTzRkThIYLdhkTyLwwHzdCKV4AMyDG7T4HMhB1uA4748H7VCikS5JFvYL1XS0L3d1pKF7wekKHQI5zqJzGOoLbH5Q14dmVZp/z0w7cquTM75qsdTZQKyDEx6R/YWGg3SfYdrlrEc59UR+TyCjvW4UM6K9OW6JURAT6nEZ5/2yjcB
  - name: user1
    groups: [ wheel ]
    sudo: [ "ALL=(ALL) NOPASSWD:ALL" ]
    shell: /bin/bash
    ssh-authorized-keys:
    - ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCdDisFVDFbS1w/iBfUpyubBpotPfMo0B63cvKhh6XMSwm0lV03P31CzArRFbfbtQqdTD11+ZUpLsxwVkH+i9xw1U4g1aD7kApkJ15LbtPJC74YCIUJIXUM4oi3VMz+1WuvPLsfmHvsozusbWtX548jR9/iVEOCAPF5HujHhMEzQJLsYKCOjiDWB6HFTwOtORKHEx3pC2NHjsXZiZYk1EhQMWBbWQJExVv50ubN/Hum6XwmlHpWGDoWrRtfA4NK0IOCxod1T/aGnl2TysKsptk43UbiYNpmA8ZXFwDAe6Ic+OYT7I0vaRGnCKHoRzr1dbJ/D025OgRVqnZT6CIJDxt9
'''

def create_new_key_pair():
    ec2 = boto3.resource('ec2')

    # create a file to store the key locally
    outfile = open('ec2-keypair.pem','w')

    # call the boto ec2 function to create a key pair
    key_pair = ec2.create_key_pair(KeyName='ec2-keypair')

    # capture the key and store it in a file
    KeyPairOut = str(key_pair.key_material)
    outfile.write(KeyPairOut)

# change permissions for the generated pem file using the following commands
# chmod 400 ec2-keypair.pem
def find_image_id():
    ec2_client = boto3.client("ec2", region_name="us-west-1")
    images = ec2_client.describe_images()
    image_id = next(image['ImageId'] for image in images if 'centos' in image['Name'])
    print("Found desired image with ID: " + image_id)

def create_security_group():
    ec2 = boto3.client('ec2')

    response = ec2.describe_vpcs()
    vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')

    try:
        response = ec2.create_security_group(GroupName='Instance_automation_SG',
                                            Description='SG for ec2',
                                            VpcId=vpc_id)
        security_group_id = response['GroupId']
        print('Security Group Created %s in vpc %s.' % (security_group_id, vpc_id))

        data = ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ])
    except ClientError as e:
        print(e)

def create_instance():
    ec2_client = boto3.client("ec2", region_name="us-west-1")
    instances = ec2_client.run_instances(
        BlockDeviceMappings=[
        {
            'DeviceName': '/dev/xvda',
            'Ebs': {
                'DeleteOnTermination': True,
                'VolumeSize': 10,
                'VolumeType': 'gp2',
                'Encrypted': True
            }
        
        },
        {
            'DeviceName': '/dev/xvdf',
            'Ebs': {
                'DeleteOnTermination': True,
                'VolumeSize': 12,
                'VolumeType': 'gp2',
                'Encrypted': True
            }
        
        },

    ],
    ImageId="ami-04468e03c37242e1e",
    MinCount=1,
    MaxCount=1,
    InstanceType="t2.micro",
    KeyName="ec2-keypair",
    UserData=user_data,
    SecurityGroups=["Instance_automation_SG"]
    )

def get_public_ip(instance_id):
    ec2_client = boto3.client("ec2", region_name="us-west-1")
    reservations = ec2_client.describe_instances(InstanceIds=[instance_id]).get("Reservations")

    for reservation in reservations:
        for instance in reservation['Instances']:
            print(instance.get("PublicIpAddress"))

def get_running_instances():
    ec2_client = boto3.client("ec2", region_name="us-west-1")
    reservations = ec2_client.describe_instances(Filters=[
        {
            "Name": "instance-state-name",
            "Values": ["running"],
        }
    ]).get("Reservations")

    for reservation in reservations:
        for instance in reservation["Instances"]:
            instance_id = instance["InstanceId"]
            instance_type = instance["InstanceType"]
            public_ip = instance["PublicIpAddress"]
            private_ip = instance["PrivateIpAddress"]
            print(f"{instance_id}, {instance_type}, {public_ip}, {private_ip}")

def stop_instance(instance_id):
    ec2_client = boto3.client("ec2", region_name="us-west-1")
    response = ec2_client.stop_instances(InstanceIds=[instance_id])
    print(response)

def terminate_instance(instance_id):
    ec2_client = boto3.client("ec2", region_name="us-west-1")
    response = ec2_client.terminate_instances(InstanceIds=[instance_id])
    print(response)

def main():
    create_security_group()
    create_instance()

main()

