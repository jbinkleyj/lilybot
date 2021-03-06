# -*- coding: utf-8 -*-
#
# Copyright (C) 2013 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Command-line skeleton application for BigQuery API.
Usage:
  $ python sample.py

You can also get help on all the command-line flags the program understands
by running:

  $ python sample.py --help

"""
import json
import redis
import argparse
import httplib2
import os
import sys

from apiclient import discovery
from oauth2client import file
from oauth2client import client
from oauth2client import tools

# Parser for command-line arguments.
parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    parents=[tools.argparser])


# CLIENT_SECRETS is name of a file containing the OAuth 2.0 information for this
# application, including client_id and client_secret. You can see the Client ID
# and Client secret on the APIs page in the Cloud Console:
# <https://cloud.google.com/console#/project/373966326924/apiui>
CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), 'client_secrets.json')

# Set up a Flow object to be used for authentication.
# Add one or more of the following scopes. PLEASE ONLY ADD THE SCOPES YOU
# NEED. For more information on using scopes please see
# <https://developers.google.com/+/best-practices>.
FLOW = client.flow_from_clientsecrets(CLIENT_SECRETS,
  scope=[
      'https://www.googleapis.com/auth/bigquery',
      'https://www.googleapis.com/auth/bigquery.insertdata',
      'https://www.googleapis.com/auth/cloud-platform',
      'https://www.googleapis.com/auth/devstorage.full_control',
      'https://www.googleapis.com/auth/devstorage.read_only',
      'https://www.googleapis.com/auth/devstorage.read_write',
    ],
    message=tools.message_if_missing(CLIENT_SECRETS))

r = redis.StrictRedis(host='localhost', port=6379, db=0)

def rp3_to_bq():
    """
    schema 
    timestamp:float, sound:integer, dist:integer, temp:float, light:integer, acc_x:float, acc_y:float, acc_z:float, humdiiy:float, slider:integer, touch:integer, pir:integer
    """
    items = r.lrange('rp3.solalla.ardyh', 0, -1)
    rows = ''
    for item in items:
        try:
            obj = json.loads(item)
            sensor_values = obj['message']['sensor_values']
        except:
            continue

        ts = obj['timestamp']
        acc_x, acc_y, acc_z = sensor_values.pop('acc_xyz')
        sensor_values.update({'acc_x':acc_x,
                              'acc_y':acc_y,
                              'acc_z':acc_z,
                              'timestamp':ts
                              })
        row = json.dumps({'json':sensor_values })
        rows += row+"\n"
        
    
    out = {'rows':rows}
    return out


def main(argv):

    # Parse the command-line flags.
    flags = parser.parse_args(argv[1:])

    # If the credentials don't exist or are invalid run through the native client
    # flow. The Storage object will ensure that if successful the good
    # credentials will get written back to the file.
    storage = file.Storage('sample.dat')
    credentials = storage.get()
    if credentials is None or credentials.invalid:
      credentials = tools.run_flow(FLOW, storage, flags)

    # Create an httplib2.Http object to handle our HTTP requests and authorize it
    # with our good Credentials.
    http = httplib2.Http()
    http = credentials.authorize(http)

    # Construct the service object for the interacting with the BigQuery API.
    service = discovery.build('bigquery', 'v2', http=http)

    try:

        bodyObj = rp3_to_bq()
        print bodyObj['rows'][0]
        print "Attempting to load %s rows" %( len(bodyObj['rows']) )
        body = bodyObj

        response = service.tabledata().insertAll(
            projectId='glossy-protocol-606',
            datasetId='rp3_grovebot',
            tableId='sensor_values2',
            body=body).execute()
        print response

    except client.AccessTokenRefreshError:
      print ("The credentials have been revoked or expired, please re-run"
        "the application to re-authorize")


# For more information on the BigQuery API you can visit:
#
#   https://developers.google.com/bigquery/docs/overview
#
# For more information on the BigQuery API Python library surface you
# can visit:
#
#   https://developers.google.com/resources/api-libraries/documentation/bigquery/v2/python/latest/
#
# For information on the Python Client Library visit:
#
#   https://developers.google.com/api-client-library/python/start/get_started
if __name__ == '__main__':
  main(sys.argv)
