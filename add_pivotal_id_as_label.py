import argparse
import configparser
import json
import os
import requests
import sys
import urllib
from jira import JIRA

jira_user = '' 
jira_password = '' 
ini_file = ''

parser = argparse.ArgumentParser()
parser.add_argument('--user_name', required=True, help='Enter JIRA user name')
parser.add_argument('--password', required=True, help='Enter JIRA password')
parser.add_argument('--ini_file', required=True, help='Enter script configuration/ini file name with extension. Provide full path if file is not in the same directory as this script. Example: config.ini or /Users/user/Desktop/config.ini')
args = parser.parse_args()

jira_user = args.user_name
jira_password = args.password
ini_file = args.ini_file

config = configparser.ConfigParser()
config.read(ini_file)

jira_url = config['JIRA']['url']
jira_project = config['JIRA']['project']
jira_pivotalid_field = config['JIRA']['pivotalid_field']
jira_pivotalid_hiden_field = config['JIRA']['pivotalid_hiden_field']
log_dir = config['DEFAULT']['log_dir']

jira_api_url = jira_url + '/rest/api/latest'
application_json = {'Content-Type': 'application/json',}

jira = JIRA(jira_url, basic_auth=(jira_user, jira_password))

project_jira_issues = jira.search_issues('project='+jira_project, 
                   startAt=0, 
                   maxResults=0, 
                   json_result=True)

project_jira_issues_count = project_jira_issues["total"]

starting_point = 0

all_cases_with_no_piv_id = []

log_file = open(log_dir + jira_project + '_cases_with_no_pivotal_ids.txt', 'w')

while project_jira_issues_count > 0:
	#----------------------------
	# Pagination control settings
	#----------------------------
	pagination = (
		('startAt', starting_point),
		('maxResults', 1000),
	)

	project_jira_issues_count = project_jira_issues_count - 1000
	starting_point = starting_point + 1000

	#----------------------------------------------------------------
	# Get all issues in project include hiden Pivotal ID custom field 
	#   (JSON formated chunks based on pagination max restriction)
	#----------------------------------------------------------------
	all_issues_obj = requests.get(jira_api_url + '/search?jql=project=%22' + jira_project + '%22&fields=' + jira_pivotalid_hiden_field, headers=application_json, params=pagination, auth=(jira_user, jira_password))

	all_issues = json.loads(all_issues_obj.content)

	issue_index = len(all_issues["issues"]) - 1	

	a = -1

	pivotal_jira_issue_ids = []

	#------------------------------------------------------
	# Create list of Pivotal to Jira ID collection mappings
	#------------------------------------------------------
	while issue_index > a:
		issue_map = {}
		issue_map['piv_id'] = all_issues["issues"][issue_index]["fields"][jira_pivotalid_hiden_field]
		issue_map['jira_id'] = all_issues["issues"][issue_index]["key"]
		pivotal_jira_issue_ids.append(issue_map)
		issue_index =issue_index - 1

	cases_with_no_piv_id = []

	#---------------------------------------------------
	# Add Pivotal issue id in "Pivotal ID" field in JIRA 
	#---------------------------------------------------
	for issue_id in pivotal_jira_issue_ids:
		if str(issue_id["piv_id"]) == "None":
			cases_with_no_piv_id.append(issue_id["jira_id"])
		else:
			print(str(issue_id["piv_id"]))
			issue = jira.issue(issue_id["jira_id"])
			issue.update(fields={jira_pivotalid_field: issue_id["piv_id"]})
			# #----------------------------------------
			# # Remove Pivotal ID if its set as a label
			# #----------------------------------------
			# remove_label = '{"update":{"labels":[{"remove":"' + str(issue_id["piv_id"]) + '"}]}}'
			# remove_labels_response = requests.put(jira_api_url + '/issue/'+issue_id["jira_id"], headers=application_json, data=remove_label, auth=(jira_user, jira_password))

#---------------------------------------------------------
# Write all JIRA issue IDs whith no Pivotal ID to log file
#---------------------------------------------------------
for i in all_cases_with_no_piv_id:
	log_file.write("%s%s\n" % (i))
log_file.close
