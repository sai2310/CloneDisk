'''
  Software requirments : Powervc 2.0.0 and above supported, python3.9/python3.7 with Requests module.

  Prequisites:
    Before running the script ensure storage template is set for rootvg disk and also name of lpar passed must exactly match with one managed in powervc. 
    
  Script Usage and parameters accepted :
     Usage: 
        python3.9/python3.7 clonedisk.py --powervc-host  <powervc_name> --username <user_name> --password <password> --disks <rootvg_disks> --lparname <name_of_lpar_in_powervc>

  rootvg_disks: <hdisk0, hdisk1.....>

  Code flow:

   1. User parameters: The user provides all the required parameters for the process.
   2. Authentication: The code initiates the authentication process using the PowerVC API. It authenticates the user and retrieves a token and project ID.
      These credentials will be used for subsequent API calls.
   3. Disk processing loop: The code enters a loop to iterate through the disks provided by the user.
   4. Serial number generation: For each disk, a serial number is generated. This serial number is used to identify the specific disk.
   5. Finding volume ID and LPAR ID: Using the generated serial number, the code makes API calls to PowerVC to find the corresponding volume ID
      and LPAR ID based on the LPAR name.
   6. Clone disk creation: With the volume ID and LPAR name, the code proceeds to create a clone disk using the clone volume API.
      This creates a duplicate of the specified volume.
   7. Attaching disk to LPAR: After creating the clone disk, the code attaches the disk to the LPAR using the attach volume API.
      This makes the cloned disk available to the specified LPAR.
   8. We run "cfgmgr -v" and also clear pv id.  
'''
      
import argparse
import getpass
import requests
import warnings
import requests
import json
import urllib3
import os
import sys
import subprocess
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def authenticate_powervc(powervc_host, username, password): #Authentication to powervc
    url = f'https://{powervc_host}:5000/v3/auth/tokens'

    payload = json.dumps({
      "auth": {
        "scope": {
          "project": {
            "domain": {
              "name": "Default"
            },
           "name": "ibm-default"
          }
       },
       "identity": {
          "password": {
            "user": {
             "domain": {
               "name": "Default"
              },
              "password": password,
              "name": username 
             }
          },
         "methods": [
           "password"
         ]
        }
     }
    })
    headers = {
       'Content-Type': 'application/json',
       'Accept': 'application/json',
       'vary': 'X-Auth-Token'
    }

    response = requests.request("POST", url, headers=headers, data=payload,verify=False)
    # Check for successful authentication
    if response.status_code == 201:
       pid = json.loads(response.text)

       projectid = pid["token"]["project"]["id"]
       token = response.headers['X-Subject-Token']
       return token, projectid
    else:
       print('Authentication failed:', response.text)
       sys.exit(1)
       return None, None

def get_lparid(powervc_host,token, project_id,lparname): #fetching lpar id using name
    url = f'https://{powervc_host}:8774/v2/{project_id}/servers'
    payload = ""
    headers = {
       'Content-Type': 'application/json',
       'Accept': 'application/json',
       'X-Auth-Token': token
    }
    response = requests.request("GET", url,verify=False, headers=headers, data=payload)
    if response.status_code == 200:
       lid = json.loads(response.text)["servers"]
       for i in lid:
          if(lparname == i["name"]):
             return i["id"]
       print("Please enter exact name with which lpar is configured on powervc")
       sys.exit(1)
       return None
    else:
       print('Getting lpar details', response.text)
       sys.exit(1) 
 
def get_lpar_volumeid(powervc_host,token, project_id,lpar_id,diskid): #getting volumeid of lpar
    url = f'https://{powervc_host}:8774/v2/{project_id}/servers/{lpar_id}'
    payload = ""
    headers = {
       'Content-Type': 'application/json',
       'Accept': 'application/json',
       'X-Auth-Token': token 
    }

    response = requests.request("GET", url,verify=False, headers=headers, data=payload)
    flag = 0
    if response.status_code == 200:
       vid = json.loads(response.text)
       for i in vid["server"]["os-extended-volumes:volumes_attached"]:
           volume = get_volumeid(powervc_host,token, project_id,i["id"])
           if(volume == diskid):
              flag = 1
              return i["id"]
       if(flag == 0):
          print("Disk not found,please manage disk using powervc")
          sys.exit(1)
          return None
    else:
       print('Getting disk details for lpar failed:', response.text)
       sys.exit(1)
       return None

def get_volumeid(powervc_host,token, project_id,vol_id): #getting volumeid of disk 
    url = f'https://{powervc_host}:9000/v3/{project_id}/volumes/{vol_id}'
    payload = ""
    headers = {
       'Content-Type': 'application/json',
       'Accept': 'application/json',
       'X-Auth-Token': token 
    }
    response = requests.request("GET", url, verify=False, headers=headers, data=payload)
    if response.status_code == 200:
       vid = json.loads(response.text)
       volumeid = vid["volume"]["metadata"]["volume_wwn"]
       return volumeid
    else:
       print('Getting Volume id failed:', response.text)
       sys.exit(1)
       return None 

def get_clonevolumeid(powervc_host,token, project_id, name): #fetching volumeid of clonedisk
    url = f'https://{powervc_host}:9000/v3/{project_id}/volumes'
    payload = ""
    headers = {
       'Content-Type': 'application/json',
       'Accept': 'application/json',
       'X-Auth-Token': token
    }
    response = requests.request("GET", url, verify=False, headers=headers, data=payload)
    if response.status_code == 200:
       vid = json.loads(response.text)["volumes"]
       volumenames = []
       volumeid = []
       flag =0
       for i in vid:
           if name in i["name"]:
              return i["id"]
       return vid[0]["id"]
    else:
       print('Getting clone Volume id failed:', response.text)
       sys.exit(1)
       return None
def create_clone_disk(powervc_host,token, project_id,volume_id,lpar, num):  #creating clone disk copy
    clone_url = f'https://{powervc_host}:9000/v3/{project_id}/clone-volumes'
    
    headers = {
       'Content-Type': 'application/json',
       'Accept': 'application/json',
       'X-Auth-Token': token
    }

    # Clone request data
    payload = json.dumps({
             "clone-volumes": {
             "display-name": lpar+num ,
             "description": "description",
             "volumes": [volume_id] 
            }
    })
    # Send the clone request
    clone_response = requests.request("POST",clone_url, verify=False, data=payload, headers=headers)

    if clone_response.status_code == 202:
       print('Disk clone request sent successfully.')
    else:
       print('Failed to send disk clone request:', clone_response.text)
       sys.exit(1)

def attachdisktoVm(powervc_host,token, lpar_id,volume_id): #POST request to attach clone disk to vm 
    url = f'https://{powervc_host}:8774/v2/servers/{lpar_id}/os-volume_attachments'
    payload = json.dumps({
        "volumeAttachment": {
            "volumeId": volume_id 
        }
    })
    headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-Auth-token': token 
    }
    response = requests.request("POST", url, verify=False, headers=headers, data=payload)
    if response.status_code == 200:
       print('Clone disk successfully attached to VM.')
    else:
       print('Failed to attach clone disk:', response.text)
       sys.exit(1)

def getdisksinfo(): #fetches list of all the disks using lspv command
    result = subprocess.run(['lspv'], capture_output=True, text=True)
    output = result.stdout.strip()

    disks = []
    lines = output.split('\n')
    for line in lines:  
       disk = line.split()[0]
       disks.append(disk)
    return disks

def gettargetdisk(hdisklist, source):  #gets the target disk information 
    result = subprocess.run(['lspv'], capture_output=True, text=True)
    output = result.stdout.strip()
    ind = hdisklist.index(source)
    disks = []
    lines = output.split('\n')
    for line in lines:
       disk = line.split()[1]
       disks.append(disk)
    sourcediskid = disks[ind]
    for i in range(0,len(disks)):
        if(disks[i] == sourcediskid and ind !=i):
             return hdisklist[i]
 
if __name__ == '__main__':
    # Command-line arguments
    parser = argparse.ArgumentParser(description='Clone rootvg disk between source and target WWNs using PowerVC.')
    parser.add_argument('--powervc-host', required=True, help='PowerVC host name or IP')
    parser.add_argument('--username', required=True, help='PowerVC username')
    parser.add_argument('--password', required=False, help='PowerVC password')
    parser.add_argument('--disks', required=True, help='rootvg disk id')
    parser.add_argument('--lparname', required=True, help='Lpar with exact name configured on powervc')
    args = parser.parse_args()
    # Prompt for PowerVC password if not provided as a command-line argument
    password = args.password or getpass.getpass('Enter PowerVC Password: ')
    # Authenticate with PowerVC
    lpar = args.lparname
    token, project_id  = authenticate_powervc(args.powervc_host, args.username, password)
    disk_list = args.disks.split(",")
    count = 1
    for i in disk_list:
        print("Starting cloning process for disk: ",i)
        result = subprocess.run(['lsmpio', '-q', '-l', i], capture_output=True, text=True)
        command_output = subprocess.run(['chdev', '-l', i, '-a', 'pv=yes'], capture_output=True, text=True) 
        output = result.stdout.strip()
        if(output):
           diskid = output.splitlines()[10].split(" ")[9]
        else:
           print("please enter valid diskname")
           print("Error for disk: ",i)
           sys.exit(1)
        lpar_id = get_lparid(args.powervc_host,token, project_id,lpar)
        volume_id = get_lpar_volumeid(args.powervc_host,token, project_id,lpar_id,diskid)
        num = str(count)
        create_clone_disk(args.powervc_host,token,project_id,volume_id,lpar,num)
        time.sleep(5)
        name = "clone-" + lpar + num
        volume_id = get_clonevolumeid(args.powervc_host,token, project_id, name)
        attachdisktoVm(args.powervc_host,token, lpar_id,volume_id)
        time.sleep(20)
        output = subprocess.run(['cfgmgr', '-v'],capture_output=True, text=True)
        time.sleep(5)
        hdisklist = getdisksinfo()
        if len(hdisklist) > 10:
           time.sleep(5)
        targetdisk = gettargetdisk(hdisklist,i)
        command_output = subprocess.run(['chdev', '-l', targetdisk, '-a', 'pv=clear'], capture_output=True, text=True)
        print(i," cloned with disk ",targetdisk) 
        count = count + 1 
