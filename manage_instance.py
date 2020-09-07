#!/usr/bin/env python

# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Example of using the Compute Engine API to create and delete instances.
Creates a new compute engine instance and uses it to apply a caption to
an image.
    https://cloud.google.com/compute/docs/tutorials/python-guide
For more information, see the README.md under /compute.
"""

import argparse
import os
import time
import json

import googleapiclient.discovery
from six.moves import input


# [START list_instances]
def list_instances(compute, project, zone, filter_str ='NONE'):
    if filter_str == 'NONE' :
        result = compute.instances().list(project=project, zone=zone).execute()
    else :
        result = compute.instances().list(project=project, zone=zone, filter=filter_str).execute()
    return result['items'] if 'items' in result else None
# [END list_instances]


# [START create_instance]
def create_instance(compute, project, zone, name, bucket,machine_type,image_project,image_family,network,subnetwork):
    image_response = compute.images().getFromFamily(
        project=image_project, family=image_family).execute()
    source_disk_image = image_response['selfLink']

    # Configure the machine
    machine_type = "zones/%s/machineTypes/%s" % ( zone ,  machine_type)
    machine_zone = "projects/%s/zones/%s" % ( project, zone)
    machine_diskType = "%s/diskTypes/pd-standard" % machine_zone
    machine_os_disk= "%s-os-disk" % name 
    machine_data_disk= "%s-data-disk" % name 
    
    if network == 'default':
        instance_network = "global/networks/default"
        instance_subnetwork = "projects/%s/regions/us-east1/subnetworks/%s" % ( project , subnetwork)
    else : 
        instance_network = "projects/%s/global/networks/%s" % ( project ,  network)
        instance_subnetwork = "projects/%s/regions/us-east1/subnetworks/%s" % ( project , subnetwork)
    startup_script = open(
        os.path.join(
            os.path.dirname(__file__), 'startup-script.sh'), 'r').read()
    image_url = "http://storage.googleapis.com/gce-demo-input/photo.jpg"
    image_caption = "Ready for dessert?"

    config = {
        'kind': "compute#instance",    
        'name': name,
        "zone": machine_zone,
        'machineType': machine_type,
        "tags": {
                "items": [
                  "http-server",
                  "https-server"
                 ]
                },
        # Specify the boot disk and the image to use as a source.
        'disks': [
            {
                'kind': 'compute#attachedDisk',
                'type': 'PERSISTENT',
                'boot': True,
                'autoDelete': False,
                'mode': 'READ_WRITE',
                'deviceName': machine_os_disk,
                'initializeParams': {
                    'sourceImage': source_disk_image,
                    'diskType': machine_diskType,
                    'diskName': machine_os_disk,  
                    'diskSizeGb': '20'
                },
                'diskEncryptionKey': {}
            },
            {
              'kind': 'compute#attachedDisk',
              'mode': 'READ_WRITE',
              'autoDelete': True,
              'type': 'PERSISTENT',
              'deviceName': machine_data_disk,
              'initializeParams': {
                'diskName': machine_data_disk,  
                'diskType': machine_diskType,
                'diskSizeGb': '500'
                } 
             }
        ],

        # Specify a network interface with NAT to access the public
        # internet.
        'networkInterfaces': [{
            'network': instance_network,
            'subnetwork': instance_subnetwork,
            'accessConfigs': [
                {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
            ]
        }],

        # Allow the instance to access cloud storage and logging.
        'serviceAccounts': [{
            'email': 'default',
            'scopes': [
                     "https://www.googleapis.com/auth/devstorage.read_only",
                     "https://www.googleapis.com/auth/logging.write",
                     "https://www.googleapis.com/auth/monitoring.write",
                     "https://www.googleapis.com/auth/servicecontrol",
                     "https://www.googleapis.com/auth/service.management.readonly",
                     "https://www.googleapis.com/auth/trace.append",
                     "https://www.googleapis.com/auth/cloud-platform"
                ]
        }],

        # Metadata is readable from the instance and allows you to
        # pass configuration from deployment scripts to instances.
        'metadata': {
            'items': [{
                # Startup script is automatically executed by the
                # instance upon startup.
                'key': 'startup-script',
                'value': startup_script
            }, {
                'key': 'url',
                'value': image_url
            }, {
                'key': 'text',
                'value': image_caption
            }, {
                'key': 'bucket',
                'value': bucket
            }]
        }
    }

    return compute.instances().insert(
        project=project,
        zone=zone,
        body=config).execute()
# [END create_instance]


# [START delete_instance]
def delete_instance(compute, project, zone, name):
    return compute.instances().delete(
        project=project,
        zone=zone,
        instance=name).execute()
# [END delete_instance]


# [START wait_for_operation]
def wait_for_operation(compute, project, zone, operation):
    print('Waiting for operation to finish...')
    while True:
        result = compute.zoneOperations().get(
            project=project,
            zone=zone,
            operation=operation).execute()

        if result['status'] == 'DONE':
            print("done.")
            if 'error' in result:
                raise Exception(result['error'])
            return result

        time.sleep(1)
# [END wait_for_operation]


# [START run]
def main( project, bucket, zone, instance_name, machine_type, image_project, image_family, network, subnetwork, foperation, wait=True):
            compute = googleapiclient.discovery.build('compute', 'v1')
            if foperation == "add" :        
                print('Creating instance.')
                operation = create_instance(compute, project, zone, instance_name, bucket,machine_type,image_project,image_family,network,subnetwork)
                wait_for_operation(compute, project, zone, operation['name'])
                print("""
                      Instance created.
                      It will take a minute or two for the instance to complete work.
                      Check this URL: http://storage.googleapis.com/{}/output.png
                      Once the image is uploaded press enter to delete the instance.
                      """.format(bucket))

                if wait:
                   input()
            if foperation  == "list" :
                if  instance_name == "demo-instance" :
                    instances = list_instances(compute, project, zone)
                else:
                    filter_str="name = %s" %instance_name
                    instances = list_instances(compute, project, zone, filter_str)

                print('\nInstances in project %s and zone %s:\n=======================================================================' 
                        % (project, zone))
                for instance in instances:
                         print( '%s - %s - %s' % ( instance['name'],
                             instance['networkInterfaces'][0]['networkIP'],instance['networkInterfaces'][0]['accessConfigs'][0]['natIP']))
                if wait:
                        input()
            if foperation  == "delete" :
                print('Deleting instance.')

                operation = delete_instance(compute, project, zone, instance_name)
                wait_for_operation(compute, project, zone, operation['name'])
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('project_id', help='Your Google Cloud project ID.')
    parser.add_argument(
        'bucket_name', help='Your Google Cloud Storage bucket name.')
    parser.add_argument(
        '--zone',
        default='us-central1-f',
        help='Compute Engine zone to deploy to.Get valid zones from https://cloud.google.com/compute/docs/regions-zones/')
    parser.add_argument(
        '--name', default='demo-instance', help='New instance name.')
    parser.add_argument(
        '--machine_type', default='n1-standard-1', help='Please get machine type from https://cloud.google.com/compute/docs/machine-types')
    parser.add_argument(
        '--image_project', default='debian-cloud', help='Please mention OS Project https://cloud.google.com/compute/docs/images')
    parser.add_argument(
        '--image_family', default='debian-9', help='Please mention OS Family https://cloud.google.com/compute/docs/images')
    parser.add_argument(
        '--network', default='default', help='Please mention the network name')
    parser.add_argument(
        '--subnetwork', default='default', help='Please mention the subnetwork name')
    parser.add_argument(
        '--operation', help='add (Add an instance)/ list ( list an instance)/ delete (Delete an instance)')
    args = parser.parse_args()
    main(args.project_id, args.bucket_name, args.zone, args.name, args.machine_type, args.image_project, args.image_family, args.network, args.subnetwork, args.operation)
# [END run]
#python create_instance.py --name [INSTANCE_NAME] --zone [ZONE] --machine_type [MACHINE_TYPE] --image_project [IMAGE_PROJECT] --image_family [IMAGE_FAMILY] --network [NETWORK NAME] --subnetwork [SUBNETWORK NAME] --operation [add/loistall/delete] [PROJECT_ID] [CLOUD_STORAGE_BUCKET]
