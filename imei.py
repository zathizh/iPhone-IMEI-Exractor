from __future__ import print_function
import httplib2
import subprocess
import tempfile
import requests
import sys
import re
import os
import ast

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
	import argparse
	flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
	flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'IMEI'

headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'}
key='G0V-R9M-A4A-TAT-7G3-9G8-A25-STZ'
url = "http://sickw.com/api.php?key=" + key +"&service=0&imei="

discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
spreadsheetId = '1jUZLn29FXy9wBNpCy0SLhvIxu0mjc1ahbjpmJptMXJI'

fp = tempfile.TemporaryFile()

def get_credentials():
	"""Gets valid user credentials from storage.
	If nothing has been stored, or if the stored credentials are invalid,
	the OAuth2 flow is completed to obtain the new credentials.
	Returns:
		Credentials, the obtained credential.
	"""
	home_dir = os.path.expanduser('~')
	credential_dir = os.path.join(home_dir, '.credentials')
	if not os.path.exists(credential_dir):
		os.makedirs(credential_dir)
	credential_path = os.path.join(credential_dir,'sheets.googleapis.com-python-quickstart.json')

	store = Storage(credential_path)
	credentials = store.get()
	if not credentials or credentials.invalid:
		flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
		flow.user_agent = APPLICATION_NAME
		if flags:
			credentials = tools.run_flow(flow, store, flags)
		else: # Needed only for compatibility with Python 2.6
			credentials = tools.run(flow, store)
		print('Storing credentials to ' + credential_path)
	return credentials

def get_imei_list_from_gsheet():
	print("[+] Collecting IMEI from DataBase")

	credentials = get_credentials()
        http = credentials.authorize(httplib2.Http())
        
        service = discovery.build('sheets', 'v4', http=http,discoveryServiceUrl=discoveryUrl)

        rangeName = 'IMEI!B2:B'
        result = service.spreadsheets().values().get(spreadsheetId=spreadsheetId, range=rangeName).execute()
        values = result.get('values', [])

        stored_imei = []
        if not values:
                return stored_imei
        else:
                for raw in values:
                        stored_imei.append(str(raw[0]))

        return stored_imei

def update_gsheet(body):
        credentials = get_credentials()
        http = credentials.authorize(httplib2.Http())
        discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
        service = discovery.build('sheets', 'v4', http=http,discoveryServiceUrl=discoveryUrl)

        rangeName = 'IMEI!A1:K1'
        result = service.spreadsheets().values().append(spreadsheetId=spreadsheetId,range=rangeName, valueInputOption='RAW', body=body).execute()


def get_backedup_imei():
	print("[+] Collecting IMEI Numbers")
	p1 = subprocess.Popen(["defaults", "read", "com.apple.iPod"], stdout=subprocess.PIPE)
	p2 = subprocess.Popen(["grep", "IMEI"], stdin=p1.stdout, stdout=subprocess.PIPE)
	p1.stdout.close()
	p3 = subprocess.Popen(["tr", "-s", "' '"], stdin=p2.stdout, stdout=subprocess.PIPE)
	p2.stdout.close()
	p4 = subprocess.Popen(["cut", "-d", " ", "-f4"], stdin=p3.stdout, stdout=subprocess.PIPE)
	p3.stdout.close()
	p5 = subprocess.Popen(["cut", "-d", ";", "-f1"], stdin=p4.stdout, stdout=subprocess.PIPE)
	p4.stdout.close()
	imei_list = p5.communicate()[0]
	p5.stdout.close()
	imei_list = imei_list.strip().split()

	return imei_list

def main():
	print("[+] Starting IMEI EXTRACTOR")
	imei_list = get_backedup_imei()

	if not imei_list:
		print("[-] Nothing to Update")
		print("[-] Exiting from the IMEI EXTRACTOR")
		sys.exit()

	stored_imei = get_imei_list_from_gsheet()
	
	update_imei  = [x for x in imei_list + stored_imei if (x not in imei_list) or (x not in stored_imei)]

	if not update_imei:
		print("[-] Nothing to Update")
		print("[-] Exiting")
		sys.exit()

        for imei in update_imei:
                query= url + imei
                print("[+] Request Details for IMEI : " + imei)
                data =  requests.get(query, headers=headers)
                if data.status_code != 200:
                        print("Invalid IMEI Number")
                        sys.exit()
                data = data.content
                data = re.sub('<\W*font\s*\w*\W*\s*\w*\"*>', '', data)
                data = data[5:-6].split("<br />")
                #data.remove('')
                details = {}
                for s in data:
                        s = s.split(": ")
			if len(s)>1:
				details[s[0]] = s[1]
                try:        
			fp.write("{'values': [["),
			fp.write("'"),
			fp.write(details["Model"]),
			fp.write("','"),
			fp.write(details["IMEI Number"]),
			fp.write("','"),
			fp.write(details["Serial Number"]),
			fp.write("','"),
			fp.write(details["Find My iPhone"]),
			fp.write("','"),
			fp.write(details["Warranty Status"]),
			fp.write("','"),
			fp.write(details["Estimated Purchase Date"]),
			fp.write("','"),
			fp.write(details["Registered Purchase Date"]),
			fp.write("','"),
			fp.write(details["Product Sold by"]),
			fp.write("','"),
			fp.write(details["Initial Carrier"]),
			fp.write("','"),
			fp.write(details["Purchased In"]),
#	                fp.write("','"),
#	                fp.write(details["Sim-lock Status"]),
			fp.write("'"),
			fp.write("]]}")
		except:
			print("[-] Exiting")
			sys.exit()
#                break

        fp.seek(0)
        print("[+] Update DataBase")
        for line in fp:
                update_gsheet(ast.literal_eval(line))
                
        print("[+] Complete Updating DataBase")
        fp.close()
        print("[-] Removing Temporary Files")
        print("[-] Exiting")
        
        sys.exit()

if __name__ == '__main__':
	main()

