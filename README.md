  # Software requirments : Powervc 2.0.0 and above supported, python3.9/python3.7 with Requests module.

  # Prequisites:
    Before running the script ensure storage template is set for rootvg disk and also name of lpar passed must exactly match with one managed in powervc. 
    
  # Script Usage and parameters accepted :
     Usage: 
        python3.9/python3.7 clonedisk.py --powervc-host  <powervc_name> --username <user_name> --password <password> --disks <rootvg_disks> --lparname <name_of_lpar_in_powervc>

  rootvg_disks: <hdisk0, hdisk1.....>

  # Code flow:

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
