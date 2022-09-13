import oci
import logging
import time
import sys
import requests
import pathlib
import json

from pickle import TRUE
from pathlib import Path
from getpass import getpass

#########################################      Log Settings        #####################################################

LOG_FORMAT = '[%(levelname)s] %(asctime)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler("oci.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

#####################################      SCRIPT SETTINGS       #######################################################
# Script Setting, change this (Each VM.Standard.A1.Flex ocpus = 6 GB memroy)
# instance_type = "VM.Standard.A1.Flex"
# OCI API_KEY and other parametter: https://github.com/hitrov/oci-arm-host-capacity (intercept request from web console)

ocpus = 4 #Configurable
memory_in_gbs = ocpus*6 #Configurable
wait_s_for_retry = 30 #Configurable

instance_size = f"{ocpus} ocpus and {memory_in_gbs} GB of memory"
path = Path.cwd() #current dir

#################################    CONFIG GENERATION AND VARIABLE HANDLER     ########################################

config_loop = True
while config_loop:
    finstance_display_name = 'displayName'
    fcompartment_id = 'compartmentId'
    fdomain = "availabilityDomain"
    fimage_id = "imageId"
    fsubnet_id = 'subnetId'
    fssh_key = 'ssh_authorized_keys'

    post_data = input(f"To generate config paste POST data output here:(to intercept request from web console: Submit instance request in OCI -> Settings -> Tools -> Network -> Find 500 error -> Copy -> POST data)' \n")
    script_settings = json.loads(post_data)
    print("\nParsing Request data and generating instance configuration")
    time.sleep(3)
    if finstance_display_name in script_settings:
        instance_display_name = script_settings[finstance_display_name]
        print(f"Display Name: {instance_display_name}")
        time.sleep(1)
    if fdomain in script_settings:
        domain = script_settings[fdomain]
        print(f"Domain: {domain}")
        time.sleep(1)
    if fcompartment_id in script_settings:
        compartment_id = script_settings[fcompartment_id]
        print(f"Compartment ID: {compartment_id}")
        time.sleep(1)
    if fimage_id in script_settings['sourceDetails']:
        print(f"Image ID: ", script_settings['sourceDetails'][fimage_id])
        image_id = script_settings['sourceDetails'][fimage_id]
        time.sleep(1)
    if fsubnet_id in script_settings['createVnicDetails']:
        print(f"Subnet ID: ", script_settings['createVnicDetails'][fsubnet_id])
        subnet_id = script_settings['createVnicDetails'][fsubnet_id]
        time.sleep(1)
    if fssh_key in script_settings['metadata']:
        ssh_key = script_settings['metadata'][fssh_key]
        print(f"SSH key is ****** {ssh_key[-18:]}")

    cont = input(f"Would you like to continue with this configuration Y|N? \n").lower()
    if "no" in cont or "n" in cont:
        print("Existing configuration will be deleted and you will be returned to generate a new configuration file")
        continue
    else:        
        print(f"Continuing with instance configuration for {instance_display_name}")
        time.sleep(2)
        break

######################################## Telegram setting ############################################################
# https://medium.com/@ManHay_Hong/how-to-create-a-telegram-bot-and-send-messages-with-python-4cf314d9fa3e
# Create bot with BotFather, get the API key
# Start the bot via conversation/chat with command /start
# Get chat_id: https://api.telegram.org/bot<yourtoken>/getUpdates   if not get chat_id, chat some thing to the bot and retry
# Start a chat with your bot, add [@get_id_bot](https://telegram.me/get_id_bot), and issue the `/my_id` command
session = requests.Session()
bot_api = '*******'
chat_id = '*******'
######################################################################################################################

def telegram_notify(session, bot_api, chat_id, message):
    '''Notify via telegram'''
    try:
        session.get(
            f'https://api.telegram.org/bot{bot_api}/sendMessage?chat_id={chat_id}&text={message}')
    except:
        logging.info("Message fail to sent via telegram")

#######################################################################################################################

#####################################      IFTTT SETTINGS         ######################################################
# Create new action from Webhook "Recieve WebRequest"
# From Webhook documentation copy the example URL
# Use variables from Script settings in web request

url = "" # maker.ifttt.com/trigger/recipe_name/with/key/your_key
value1 = instance_display_name
value2 = domain
value3 = instance_size

logging.info("#####################################################")
logging.info("Script to spawn VM.Standard.A1.Flex instance")


message = f'Start spawning instance VM.Standard.A1.Flex - {ocpus} ocpus - {memory_in_gbs} GB'
logging.info(message)
telegram_notify(session, bot_api, chat_id, message)

# Loading config file
logging.info("Loading OCI config")
config = oci.config.from_file(file_location = f"{Path.cwd()}\\config")

# Initialize service client
logging.info("Initialize service client with default config file")
to_launch_instance = oci.core.ComputeClient(config)


message = f"Instance to create: VM.Standard.A1.Flex - {ocpus} ocpus - {memory_in_gbs} GB"
logging.info(message)
telegram_notify(session, bot_api, chat_id, message)

###########################       Check current existing instance(s) in account         ##############################
logging.info("Check current instances in account")
logging.info(
    "Note: Free upto 4xVM.Standard.A1.Flex instance, total of 4 ocpus and 24 GB of memory")
current_instance = to_launch_instance.list_instances(
    compartment_id=compartment_id)
response = current_instance.data
# oci.core.models.InstanceShapeConfig
# print(type(response[0]))
total_ocpus = total_memory = _A1_Flex = 0
instance_names = []
if response:
    logging.info(f"{len(response)} instance(s) found!")
    for instance in response:
        logging.info(f"{instance.display_name} - {instance.shape} - {int(instance.shape_config.ocpus)} ocpu(s) - {instance.shape_config.memory_in_gbs} GB(s) | State: {instance.lifecycle_state}")
        instance_names.append(instance.display_name)
        if instance.shape == "VM.Standard.A1.Flex" and instance.lifecycle_state not in ("TERMINATING", "TERMINATED"):
            _A1_Flex += 1
            total_ocpus += int(instance.shape_config.ocpus)
            total_memory += int(instance.shape_config.memory_in_gbs)

    message = f"Current: {_A1_Flex} active VM.Standard.A1.Flex instance(s) (including RUNNING OR STOPPED)"
    logging.info(message)
else:
    logging.info(f"No instance(s) found!")


message = f"Total ocpus: {total_ocpus} - Total memory: {total_memory} (GB) || Free {4-total_ocpus} ocpus - Free memory: {24-total_memory} (GB)"
logging.info(message)
telegram_notify(session, bot_api, chat_id, message)


# Pre-check to verify total resource of current VM.Standard.A1.Flex (max 4 ocpus/24GB ram)
if total_ocpus + ocpus > 4 or total_memory + memory_in_gbs > 24:
    message = "Total maximum resource exceed free tier limit (Over 4 ocpus/24GB total). **SCRIPT STOPPED**"
    logging.critical(message)
    sys.exit()

# Check for duplicate display name
if instance_display_name in instance_names:
    message = f"Duplicate display name: >>>{instance_display_name}<<< Change this! **SCRIPT STOPPED**"
    logging.critical(message)
    sys.exit()

message = f"Precheck pass! Create new instance VM.Standard.A1.Flex: {ocpus} ocpus - {memory_in_gbs} GB"
logging.info(message)
telegram_notify(session, bot_api, chat_id, message)
######################################################################################################################

# Instance-detail
instance_detail = oci.core.models.LaunchInstanceDetails(
    metadata={
        "ssh_authorized_keys": ssh_key
    },
    availability_domain=domain,
    shape='VM.Standard.A1.Flex',
    compartment_id=compartment_id,
    display_name=instance_display_name,
    source_details=oci.core.models.InstanceSourceViaImageDetails(
        source_type="image", image_id=image_id),
    create_vnic_details=oci.core.models.CreateVnicDetails(
        assign_public_ip=False, subnet_id=subnet_id, assign_private_dns_record=True),
    agent_config=oci.core.models.LaunchInstanceAgentConfigDetails(
        is_monitoring_disabled=False,
        is_management_disabled=False,
        plugins_config=[oci.core.models.InstanceAgentPluginConfigDetails(
            name='Vulnerability Scanning', desired_state='DISABLED'), oci.core.models.InstanceAgentPluginConfigDetails(name='Compute Instance Monitoring', desired_state='ENABLED'), oci.core.models.InstanceAgentPluginConfigDetails(name='Bastion', desired_state='DISABLED')]
    ),
    defined_tags={},
    freeform_tags={},
    instance_options=oci.core.models.InstanceOptions(
        are_legacy_imds_endpoints_disabled=False),
    availability_config=oci.core.models.LaunchInstanceAvailabilityConfigDetails(
        recovery_action="RESTORE_INSTANCE"),
    shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
        ocpus=ocpus, memory_in_gbs=memory_in_gbs)
)

#######################################      Main loop - program        ####################################################
# Script try to send request each $wait_s_for_retry seconds until success
to_try = True
while to_try:
    try:
        to_launch_instance.launch_instance(instance_detail)
        to_try = False
        message = 'Success! Edit vnic to get public ip address'
        logging.info(message)
        telegram_notify(session, bot_api, chat_id, message)
        # post to IFTTT
        requests.post(f"{url}?value1={value1}&value2={value2}&value3={value3}")
        # print(to_launch_instance.data)
        session.close()
    except oci.exceptions.ServiceError as e:
        if e.status == 500:
            # Out of host capacity.
            message = f"{e.message} Retry in {wait_s_for_retry}s"
        elif e.status == 429:
            # TooManyRequests
            message = f"target_service: compute, status: 429, code: TooManyRequests Retry in {wait_s_for_retry}s"
            telegram_notify(session, bot_api, chat_id, message)
        else:
            message = f"{e} Retry in {wait_s_for_retry}s"
            telegram_notify(session, bot_api, chat_id, message)
        logging.info(message)
        time.sleep(wait_s_for_retry)
    except Exception as e:
        message = f"{e} Retry in {wait_s_for_retry}s"
        logging.info(message)
        telegram_notify(session, bot_api, chat_id, message)
        time.sleep(wait_s_for_retry)
    except KeyboardInterrupt:
        session.close()
        sys.exit()