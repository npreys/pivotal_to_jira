import argparse
import configparser
import json
import os
import requests
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

pivotal_url = config['PIVOTAL']['url']
pivotal_project = config['PIVOTAL']['project']
pivotal_xtracker_token = config['PIVOTAL']['xtracker_token']
jira_url = config['JIRA']['url']
jira_project = config['JIRA']['project']
jira_bearer_token= config['JIRA']['bearer_token']
jira_pivotalid_field = config['JIRA']['pivotalid_field']
jira_pivotalid_hiden_field = config['JIRA']['pivotalid_hiden_field']
log_dir = config['DEFAULT']['log_dir']
global_dir = config['DEFAULT']['global_dir']

pivotal_api_url = pivotal_url + '/services/v5/projects/' + pivotal_project + '/stories/'
jira_api_url = jira_url + '/rest/api/latest'
pivotal_attachments = (('fields', 'comments(attachments)'),)
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
	all_issues_obj = requests.get(jira_api_url + '/search?jql=project=%22' + jira_project + '%22&fields=attachment&fields=' + jira_pivotalid_hiden_field, headers=application_json, params=pagination, auth=(jira_user, jira_password))

	all_issues = json.loads(all_issues_obj.content)

	issue_index = len(all_issues["issues"]) - 1

	a = -1

	pivotal_jira_issue_ids = []

	#------------------------------------------------------
	# Create list of Pivotal to Jira ID collection mappings
	#------------------------------------------------------
	while issue_index > a:
		issue_map = {}
		if all_issues["issues"][issue_index]["fields"]["attachment"]:
			attachments_dir = global_dir + all_issues["issues"][issue_index]["fields"][jira_pivotalid_hiden_field]
			issue_map['piv_id'] = all_issues["issues"][issue_index]["fields"][jira_pivotalid_hiden_field]
			issue_map['jira_id'] = all_issues["issues"][issue_index]["key"]
			pivotal_jira_issue_ids.append(issue_map)
			
			if not os.path.exists(attachments_dir):
				os.makedirs(attachments_dir)

		length =length - 1

	cases_with_no_piv_id = []

	#-----------------------------------------------
	# Upload attachments from Pivotal to Jira issues
	# (delete attachment links created by importer) 
	#-----------------------------------------------
	for issue_id in pivotal_jira_issue_ids:
		attachments_dir = global_dir + issue_id['piv_id']
		pivotal_issue_info = json.loads(requests.get(pivotal_api_url + issue_id['piv_id'], headers=pivotal_xtracker_token, params=pivotal_attachments).content)
		jira_issue_info = requests.get(jira_api_url + '/issue/' + issue_id['jira_id'], headers=application_json, auth=(jira_user, jira_password))
		jira_issue_json = json.loads(jira_issue_info.content)
		jira_attachments_info = jira_issue_json["fields"]["attachment"]

		for pivotal_comment in pivotal_issue_info["comments"]:
			if pivotal_comment["attachments"]:
				count = 0
				for pivotal_attachment in pivotal_comment["attachments"]:
					for attempt in range(3):
						try:
							download_response = requests.get(pivotal_url + pivotal_attachment["download_url"], headers=pivotal_xtracker_token, allow_redirects=True, timeout=10)
						except:
							download_response = requests.get(pivotal_url + pivotal_attachment["download_url"], headers=pivotal_xtracker_token, allow_redirects=True, timeout=10)
						else:
							break
					attachment_url = r.url
					with open(attachments_dir+'/'+pivotal_attachment["filename"], 'wb') as attachment_file:
						attachment_file.write(download_response.content)

					#-------------------------------------------
					# Delete incorrect attachment link if exists  
					#-------------------------------------------
					for jira_attachment in jira_attachments_info:
						if jira_attachment["filename"] == pivotal_attachment["filename"]:
							to_be_deleted = jira_attachment["self"]
							print("DELETING")
							print(to_be_deleted)
							delete_old_attachment = requests.delete(to_be_deleted, headers=jira_bearer_token)

					count = count+1
					print(count)
					print("ADDING")
					print(d["filename"])
					
					jira.add_attachment(issue=jira_issue_json["key"], attachment=attachments_dir+'/'+pivotal_attachment["filename"])

#---------------------------------------------------------
# Write all JIRA issue IDs whith no Pivotal ID to log file
#---------------------------------------------------------
for i in all_cases_with_no_piv_id:
	log_file.write("%s%s\n" % (i))
log_file.close
