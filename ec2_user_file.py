import boto3
import os, sys
from subprocess import PIPE, Popen
import argparse
from string import Template
import logging
from datetime import datetime
from time import time
import logging


import yaml
import sys

from dateutil import parser

region = sys.argv[1]
SubnetId_yours=sys.argv[2]

security_group="sg-xxxxxxxxx"

def sprint(message):
    print ("{0} {1}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'),str(message))) 

# to run any shell commands
def shell_command(query,IsShell=None):
      logging.info ("< ------ Running Command   ------ >" )
      logging.info (query)
      sprint (query)
      if IsShell:
         run_process = Popen(query, stdout=PIPE, stderr=PIPE, shell=True)
         run_output, run_error = run_process.communicate()
         return run_process.returncode, run_output, run_error

#status, output, error = shell_command(s3_to_s3_copy, True)
ssh_add=""

#Create user and pem key and extract the public key
def user_keypair_creation(user,ssh_keyname):

        build_string=""

        iam = boto3.client('iam')

        # create a user
        iam.create_user( UserName=user)

        # attach a policy
        iam.attach_user_policy(
        UserName = user,
        PolicyArn='arn:aws:iam::aws:policy/AmazonEC2FullAccess'

        )
    

        
        ec2 = boto3.client('ec2','us-west-2')
        response = ec2.create_key_pair(KeyName=ssh_keyname)

        with open('./'+ssh_keyname+'.pem', 'w') as file:
             file.write(response['KeyMaterial'])
             print(response)

        get_pub_key = 'ssh-keygen -y -f ./'+ssh_keyname+'.pem'
        status, output, error = shell_command(get_pub_key, True)
        
        if status==0:
            print(output)
        return output    

#get the values from yaml
try:
    with open(r'config_a.yaml') as configfile:
          configfile = yaml.safe_load(configfile)
          print(configfile)
          volumes_data=configfile["server"]["volumes"]
          volumes_data=configfile["server"]["volumes"]
          #for i in range volumes_data:
          volume_image1=volumes_data[0]["device"]
          volume_size_gb1=volumes_data[0]["size_gb"]
          volume_type1=volumes_data[0]["type"]
          volume_mount1=volumes_data[0]["mount"]
          volume_image2=volumes_data[1]["device"]
          volume_size_gb2=volumes_data[1]["size_gb"]
          volume_type2=volumes_data[1]["type"]
          volume_mount2=volumes_data[1]["mount"]
           

          print(volumes_data)
          print(volume_image1)
          users = configfile["server"]["users"]
          print(users)
          print(configfile["server"]["instance_type"])
          amitype=configfile["server"]["ami_type"]
          if amitype=="amzn2":
             amitype="Amazon Linux AMI*"
          architecturetype=  configfile["server"]["architecture"] 
          rootdevicetype =  configfile["server"]["root_device_type"]
          virtualizationtype = configfile["server"]["virtualization_type"]
          instancetype = configfile["server"]["instance_type"]

          print(architecturetype+"/"+rootdevicetype+"/"+virtualizationtype+"/"+instancetype+"/"+amitype)
          #for i in users:
             #print(i)
             #user=i["login"]
             #ssh_keyname=i["ssh_key"]
             #output=user_keypair_creation(user,ssh_keyname)
             
except yaml.YAMLError as exc:
    print(exc)

#Know we should not repeat but to get user data as shell commands we are getting formatting issue
user=users[0]["login"]
ssh_keyname=users[0]["ssh_key"]

output=user_keypair_creation(user,ssh_keyname)

ssh_add +="""
mkdir -p  /home/%s/.ssh/
useradd %s
echo "%s ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/90-cloud-init-users
cat <<EOD >> /home/%s/.ssh/authorized_keys
%s
EOD
"""%(user,user,user,user,output)

user=users[1]["login"]
ssh_keyname=users[1]["ssh_key"]

output=user_keypair_creation(user,ssh_keyname)

ssh_add +="""
mkdir -p /home/%s/.ssh/
useradd %s
echo "%s ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/90-cloud-init-users
cat <<EOD >> /home/%s/.ssh/authorized_keys
%s
EOD
"""%(user,user,user,user,output)

#looks some issues with root volume if we format temporarily commented
#myCode = """#!/bin/bash
#sudo mkfs.%s %s
#sudo mkdir %s
#echo "%s %s auto noatime 0 0" | sudo tee -a /etc/fstab
#sudo mkfs.%s %s
#sudo mkdir %s
#echo "%s %s auto noatime 0 0" | sudo tee -a /etc/fstab
#%s"""%(volume_type1,volume_image1,volume_mount1,volume_mount1,volume_type1,volume_type2,volume_image2,volume_mount2,volume_mount2,volume_type2,ssh_add)

myCode = """#!/bin/bash

sudo mkfs.%s %s
sudo mkdir %s
echo "%s %s auto noatime 0 0" | sudo tee -a /etc/fstab
%s"""%(volume_type2,volume_image2,volume_mount2,volume_mount2,volume_type2,ssh_add)


print(myCode)



#get newest image
def newest_image(list_of_images):
    latest = None

    for image in list_of_images:
        if not latest:
            latest = image
            continue

        if parser.parse(image['CreationDate']) > parser.parse(latest['CreationDate']):
            latest = image

    return latest

client = boto3.client('ec2', region_name=region)

virtualizationtype = 'hvm'

filters = [ {
        'Name': 'name',
        'Values': ['amzn-ami-hvm-*']
    },{
        'Name': 'description',
        'Values': [amitype]
    },{
        'Name': 'architecture',
        'Values': [architecturetype]
    },{
        'Name': 'owner-alias',
        'Values': ['amazon']
    },{
        'Name': 'state',
        'Values': ['available']
    },{
        'Name': 'root-device-type',
        'Values': [rootdevicetype]
    },{
        'Name': 'virtualization-type',
        'Values': [virtualizationtype]
    },{
        'Name': 'hypervisor',
        'Values': ['xen']
    },{
        'Name': 'image-type',
        'Values': ['machine']
    } ]

response = client.describe_images(Owners=['amazon'], Filters=filters)

source_image = newest_image(response['Images'])
print(source_image['ImageId'])
image_id_final=source_image['ImageId']

client = boto3.client('ec2', region_name='us-west-2')

response = client.run_instances(
    BlockDeviceMappings=[
        {
            'DeviceName': volume_image1,
            'Ebs': {

                'DeleteOnTermination': True,
                'VolumeSize': volume_size_gb1,
                'VolumeType': "gp2"
            },
        },
        {
            'DeviceName': volume_image2,
            'Ebs': {

                'DeleteOnTermination': True,
                'VolumeSize': volume_size_gb2,
                'VolumeType': "gp2"
            },
        },        
    ],
    SecurityGroupIds=[
        security_group
    ],
    ImageId=image_id_final,
    InstanceType=instancetype,
    UserData=myCode,
    SubnetId=SubnetId_yours,
    MaxCount=1,
    MinCount=1,
    Monitoring={
        'Enabled': False
    },
)
