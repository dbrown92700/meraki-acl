# [START gae_python38_app]
from flask import Flask, request, make_response, render_template, redirect, url_for, session, Markup
import requests
import json

app = Flask(__name__)
app.secret_key = 'any random string'

base_url = 'https://api.meraki.com/api/v1/'

###########################################################################
#  Prompt user to choose an org from a list of orgs attached to the API key
###########################################################################
@app.route('/org/')
def Organization():

    api_key = request.cookies.get('api_key')
    if api_key == None:
        return redirect(url_for('getapikey'))
    url = base_url + "organizations"
    headers = {
      'X-Cisco-Meraki-API-Key': api_key
    }
    try:
        response = requests.request("GET", url, headers=headers)
        response.raise_for_status()
    except:
        return 'ERROR CODE: <br>'+str(response.status_code) + '<br><br>ERROR DETAILS: ' + str(response.text)
    orgs = json.loads(response.text)

    listorgs = ''
    for org in orgs:
        listorgs += '<option value = "{}">{}</option>\n'.format(org['id'] ,org['name'])

    return render_template('listorgs.html', listorgs=Markup(listorgs))


###########################################################################
#  Prompt user to choose an network from a list of networks in this org
###########################################################################
@app.route('/network/')    
def Network():

    api_key = request.cookies.get('api_key')
    if api_key == None:
        return redirect(url_for('getapikey'))
    org = request.args.get('org')
    if org == None:
        org = session['orgid']
    headers = {
      'X-Cisco-Meraki-API-Key': api_key
    }

    url = "{}organizations/{}".format(base_url, org)

    try:
        response = requests.request("GET", url, headers=headers)
        response.raise_for_status()
    except:
        return 'ERROR CODE: <br>'+str(response.status_code) + '<br><br>ERROR DETAILS: ' + str(response.text)
    jorg = json.loads(response.text)
    session['org'] = jorg['name']
    session['orgid'] = org

    url = "{}organizations/{}/networks".format(base_url, org)
    networks = json.loads(requests.request("GET", url, headers=headers).text)

    listnetworks = ''
    for network in networks:
        listnetworks += '<option value = "{}">{}</option>\n'.format(network['id'], network['name'])

    return render_template('listnetworks.html', org = jorg['name'], listnetworks = Markup(listnetworks))

###########################################################################
#  Prompt user to choose an ACL from this network
###########################################################################
@app.route('/acl/')    
def ACL():

    api_key = request.cookies.get('api_key')
    if api_key == None:
        return redirect(url_for('getapikey'))

    network = request.args.get('network')
    if network == None:
        network = session['netid']
    headers = {
      'X-Cisco-Meraki-API-Key': api_key
    }

    url = base_url + "networks/{}".format(network)
    jnetwork = json.loads(requests.request("GET", url, headers=headers).text)
    session['network'] = jnetwork['name']
    session['netid'] = network

    url = base_url + "networks/{}/groupPolicies".format(network)
    policies = json.loads(requests.request("GET", url, headers=headers).text)

    n = 0
    listpolicies = ''
    for policy in policies:
        listpolicies += '<option value = "{}">{}</option>\n'.format(policy['groupPolicyId'], policy['name'])
        n += 1

    url = "{}organizations/{}/networks".format(base_url, session['orgid'])
    networks = json.loads(requests.request("GET", url, headers=headers).text)

    listnetworks = ''
    for network in networks:
        listnetworks += '<option value = "{}">{}</option>\n'.format(network['id'], network['name'])

    session['lastaclaction'] = 'Select an action below:'

    return render_template('listpolicies.html', org = session['org'], network = session['network'],
                            orgid = session['orgid'], listpolicies = Markup(listpolicies),
                            listnetworks = Markup(listnetworks))

###########################################################################
#  Prompt user to choose a Group Policy to duplicate from another network
###########################################################################
@app.route('/copyacl/')    
def copyacl():

    api_key = request.cookies.get('api_key')
    if api_key == None:
        return redirect(url_for('getapikey'))

    sourcenet = request.args.get('sourcenet')
    headers = {
      'X-Cisco-Meraki-API-Key': api_key
    }

    url = base_url + "networks/{}".format(sourcenet)
    jnetwork = json.loads(requests.request("GET", url, headers=headers).text)

    url = base_url + "networks/{}/groupPolicies".format(sourcenet)
    policies = json.loads(requests.request("GET", url, headers=headers).text)

    n = 0
    listpolicies = ''
    for policy in policies:
        listpolicies += '<option value = "{}">{}</option>\n'.format(policy['groupPolicyId'], policy['name'])
        n += 1

    return render_template('copypolicy.html', network = jnetwork['name'],
                            listpolicies = Markup(listpolicies), sourcenet = sourcenet)

###########################################################################
#  Apply copied policy
###########################################################################
@app.route('/applycopy/')
def applycopy():
    api_key = request.cookies.get('api_key')
    if api_key == None:
        api_key = 'not set'

    network = session['netid']
    sourcenet = request.args.get('sourcenet')
    acl = request.args.get('acl')
    aclname = request.args.get('aclname')

    url = base_url + "networks/{}/groupPolicies/{}".format(sourcenet,acl)
    headers = {
      'X-Cisco-Meraki-API-Key': api_key,
      'Content-Type': 'application/json'
    }
    policy = json.loads(requests.request("GET", url, headers=headers).text)

    policy.pop('groupPolicyId')
    if aclname not in ('',None):
        policy['name'] = aclname

    url = base_url + "networks/{}/groupPolicies".format(network)
    try:
        newpolicy = requests.post(url, headers=headers, data = json.dumps(policy))
        newpolicy.raise_for_status()
    except:
        return "POST Error: " + str(newpolicy.status_code) + "<br><br>Error Details: " + str(newpolicy.text) + \
                            "<br><br>Policy pushed: " + str(policy)
    session['acl'] = json.loads(newpolicy.text)['groupPolicyId']

    resp = make_response(redirect(url_for('ACE')))

    return resp

###########################################################################
#  LIST ACL and Select ACE Action (Delete, Replace, Insert)
###########################################################################
@app.route('/ace/')    
def ACE():

    api_key = request.cookies.get('api_key')
    if api_key == None:
        return redirect(url_for('getapikey'))
    acl = request.args.get('acl')
    if acl == None:
        acl = str(session['acl'])
    else:
        session['acl'] = acl

    network = session['netid']

    url = base_url + "networks/{}/groupPolicies/{}".format(network,acl)
    headers = {
      'X-Cisco-Meraki-API-Key': api_key
    }

    policy = json.loads(requests.request("GET", url, headers=headers).text)
    session['policyname'] = policy['name']

    acltable = ''
    n = 0
    for ace in policy['firewallAndTrafficShaping']['l3FirewallRules']:
        acltable += '<td><input type="radio" name="ace" value = "{}"></td><th>{}</th>'.format(n,n+1)
        for var in ace.values():
            acltable += '<td>{}</td>'.format(var)
        acltable += '</tr>\n'
        n += 1

    return render_template('listacl.html', acl=policy['name'] , lastaclaction = Markup(session['lastaclaction']),
                             acltable=Markup(acltable), org = session['org'], network = session['network'])

###########################################################################
#  Edit (Delete, Replace, Insert) ACL Entry
###########################################################################
@app.route('/editacl/')
def editace():

    api_key = request.cookies.get('api_key')
    if api_key == None:
        return redirect(url_for('getapikey'))

    network = session['netid']
    acl = session['acl']
    ace = request.args.get('ace')
    if ace in ('', None):
        session['lastaclaction'] = '<p style="color:red;">You must select an ACL line</p>'
        resp = make_response(redirect(url_for('ACE')))
        return resp
    aclaction = int(request.args.get('aclaction'))

    url = base_url + "networks/{}/groupPolicies/{}".format(network,acl)

    headers = {
      'X-Cisco-Meraki-API-Key': api_key,
      'Content-Type': 'application/json'
    }
    policy = json.loads(requests.request("GET", url, headers=headers).text)

    if aclaction in (1,2,3):
        comment = request.args.get('comment')
        if comment == None:
            comment = ''
        destPort = request.args.get('port')
        protocol = request.args.get('protocol')
        if destPort in ('any','Any','') or protocol == 'icmp':
            destPort = 'Any'
        else:
            destPort = int(destPort)
        dest = request.args.get('dest')
        if dest == '':
            dest = 'Any'
        aceline = {'comment': comment, 'policy': request.args.get('action'), 'protocol': protocol,
            'destPort': destPort, 'destCidr': dest}

    if aclaction == 0:
        ##### Delete ACE #####
        if ace == 'last':
            session['lastaclaction'] = '<p style="color:red">Cannot delete implicit ALLOW ANY rule</p>'
        else:
            session['lastaclaction'] = 'Deleted line {}: {}'.format(int(ace)+1,policy['firewallAndTrafficShaping']['l3FirewallRules'].pop(int(ace)))

    elif aclaction == 1:
        ##### Replace ACE #####
        if ace == 'last':
            session['lastaclaction'] = '<p style="color:red">Cannot edit implicit ALLOW ANY rule</p>'
        else:
            policy['firewallAndTrafficShaping']['l3FirewallRules'][int(ace)] = aceline
            session['lastaclaction'] = 'Line {} modified: '.format(int(ace)+1) + str(aceline)

    elif aclaction == 2:
        ##### Insert ACE above line #####
        if ace == 'last':
            ace = len(policy['firewallAndTrafficShaping']['l3FirewallRules'])
        policy['firewallAndTrafficShaping']['l3FirewallRules'].insert(int(ace),aceline)
        session['lastaclaction'] = 'Inserted line {}: '.format(int(ace)+1) + str(aceline)

    elif aclaction == 3:
        ##### Insert ACE below line #####
        if ace == 'last':
            session['lastaclaction'] = 'Cannot insert a line below the implicit ALLOW ANY rule'
        else:
            policy['firewallAndTrafficShaping']['l3FirewallRules'].insert(int(ace)+1,aceline)
            session['lastaclaction'] = 'Inserted line {}: '.format(int(ace)+2) + str(aceline)

    policyid = policy.pop('groupPolicyId')
    url = base_url + "networks/{}/groupPolicies/{}".format(network, policyid)
    requests.put(url, headers=headers, data = json.dumps(policy))

    resp = make_response(redirect(url_for('ACE')))

    return resp

###########################################################################
#  Confirm Policy Deletion & Perform Deletion
###########################################################################
@app.route('/deleteconfirm/')    
def deleteconfirm():

    return render_template('deleteconfirm.html', policyname=session['policyname'], network = session['network'])

@app.route('/deleteacl/')    
def deleteacl():

    url = base_url + "networks/{}/groupPolicies/{}".format(session['netid'],session['acl'])
    headers = {
      'X-Cisco-Meraki-API-Key': request.cookies.get('api_key'),
      'Content-Type': 'application/json'
    }
    requests.request("DELETE", url, headers=headers)

    resp = make_response(redirect(url_for('ACL')))

    return resp

###########################################################################
#  Prompt user for Meraki API key
###########################################################################
@app.route('/')
def getapikey():
    api_key = request.cookies.get('api_key')
    if api_key == None:
        api_key = 'not set'
    else:
    	api_key = '**************************' + api_key[-5:]
    return render_template('setapikey.html', api_key = api_key)

###########################################################################
#  Read and set Meraki API Key
###########################################################################
@app.route('/setapikey')
def setapikey():

    resp = make_response(redirect(url_for('Organization')))
    resp.set_cookie('api_key', request.args.get('api_key'))

    return resp

if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
# [END gae_python38_app]
