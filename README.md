# meraki-acl

This repository has been cloned to https://github.com/CiscoSE/meraki-acl

This web app can view and edit L3 ACL's in a Meraki Network group policy.  The primary use case for this solution is to allow security teams to modify named ACL's called through RADIUS in an 802.1x deployment without having full access to the Meraki Dashboard.  The following features are implemented:
- Select Organization, Network and Group Policy
- View ACL
- Delete, modify or insert ACE
- Delete entire Group Policy
- Create new Group Policy
- Duplicate Group Policy from another network

Written in Python 3.7 using Flask templates.  Make sure you have the necessary libraries noted in requirements.txt.  Execute using "python3 main.py"
Also tested and works as a cloud native app on Google Cloud Platform.

<img src='https://github.com/dbrown92700/meraki-acl/blob/main/Screen%20Shot%202020-11-19.png?raw=true'>
