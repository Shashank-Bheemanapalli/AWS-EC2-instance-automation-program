import yaml
import boto3
import os
from botocore.exceptions import ClientError

#amazon linux 2 image id
image_id = "ami-04468e03c37242e1e"

#user data used to pre-configure the ec2 instance
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

# to add two new users
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

# reading the given yaml configuration 
with open("EC2_instance_configuration.yml") as f:
        data = yaml.load(f, Loader=yaml.FullLoader)

        instance_type = data['server']['instance_type']
        ami_type = data['server']['ami_type']
        architecture = data['server']['architecture']
        root_device_type = data['server']['root_device_type']
        virtualization_type  = data['server']['virtualization_type']
        min_count = data['server']['min_count']
        max_count = data['server']['max_count']

        volume_1 = data['server']['volumes'][0]
        volume_2 = data['server']['volumes'][1]
        user_1 = data['server']['users'][0]
        user_2 = data['server']['users'][1]

        volume_1_device = volume_1['device']
        volume_1_size_gb = volume_1['size_gb']
        volume_1_type = volume_1['type']
        volume_1_mount = volume_1['mount']

        volume_2_device = volume_2['device']
        volume_2_size_gb = volume_2['size_gb']
        volume_2_type = volume_2['type']
        volume_2_mount = volume_2['mount']

        user_1_login = user_1['login']
        user_1_ssh_key = user_1['ssh_key']

        user_2_login = user_2['login']
        user_2_ssh_key = user_2['ssh_key']

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


# to find any image id on aws
def find_image_id():
    ec2_client = boto3.client("ec2", region_name="us-west-1")
    images = ec2_client.describe_images()
    image_id = next(image['ImageId'] for image in images if 'centos' in image['Name'])
    print("Found desired image with ID: " + image_id)

# to create security group
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

# to create new instance
def create_instance():
    ec2_client = boto3.client("ec2", region_name="us-west-1")
    instances = ec2_client.run_instances(
        BlockDeviceMappings=[
        {
            'DeviceName': volume_1_device,
            'Ebs': {
                'DeleteOnTermination': True,
                'VolumeSize': volume_1_size_gb,
                'VolumeType': 'gp2',
                'Encrypted': True
            }
        
        },
        {
            'DeviceName': volume_2_device,
            'Ebs': {
                'DeleteOnTermination': True,
                'VolumeSize': volume_2_size_gb,
                'VolumeType': 'gp2',
                'Encrypted': True
            }
        
        },

    ],
    ImageId= image_id,
    MinCount=min_count,
    MaxCount=max_count,
    InstanceType=instance_type,
    KeyName="ec2-keypair",
    UserData=user_data,
    SecurityGroups=["Instance_automation_SG"]
    )

# to get the public ip of the launched instance
def get_public_ip(instance_id):
    ec2_client = boto3.client("ec2", region_name="us-west-1")
    reservations = ec2_client.describe_instances(InstanceIds=[instance_id]).get("Reservations")

    for reservation in reservations:
        for instance in reservation['Instances']:
            print(instance.get("PublicIpAddress"))

# to list out all the running instances
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

# to stop the running instances
def stop_instance(instance_id):
    ec2_client = boto3.client("ec2", region_name="us-west-1")
    response = ec2_client.stop_instances(InstanceIds=[instance_id])
    print(response)

# to terminate the instances
def terminate_instance(instance_id):
    ec2_client = boto3.client("ec2", region_name="us-west-1")
    response = ec2_client.terminate_instances(InstanceIds=[instance_id])
    print(response)

# the main function for ec2 automation
def main():
    #create_new_key_pair()
    #create_security_group()
    create_instance()

main()

