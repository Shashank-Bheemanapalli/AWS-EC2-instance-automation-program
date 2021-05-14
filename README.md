# AWS-EC2-instance-automation-program
Fetch Rewards Coding Assessment

## The objective is to develop an automation program that takes a YAML configuration file as input and deploys a Linux AWS EC2 instance with two volumes and two users.

Install awscli and boto3:
 - pip install awscli boto3

Create a User and get AWS Access ID and Secret Key.
Enable only 'Programmatic Access' while creating the user.
To set the permissions, choose 'Attach Existing Policies Directly' and in the Policy Filter type 'AmazonEC2FullAccess'.
Save the .csv file.

Use the following command to configure aws:  
- aws configure

Next enter your Access ID and Secret Key along with default aws region and output format.


The EC2_instance_configuration.yml file contains the required configuration to launch the EC2 instances. (You can modify the YAML file according to your specifications)

Finally, execute the ec2_automation.py file.
  - Firstly, the main function will create a key pair. 
  - Use 'chmod 400 <keyname.pem>' to modify the permissions.
  - Secondly, the main function will create a new security group for the EC2 instance.(Here, I have enable access only for port 80 [ http ]  and port 22 [ ssh ].
  - Finally, the main function will create a new EC2 insctance.

In the Create_instance function, we pass on user data which provides initial configuration for the EC2 instance after launching.


- In the end, we will have a running EC2 instance attached with two EBS volumes (1. root volume [ 10 gb ], 2.mounted to /data [ 100 gb ]) along with two new users (here: user1 and user2).
- The .pem file for both the users are provided in the repo, which can be used to ssh into the instance using the command : ssh -i <keyname.pem> <username@instance public ip>


