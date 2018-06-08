#!/usr/bin/env python
import json
import requests
import pprint
import time
import sys
import os

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


def requests_retry_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[ 502, 503, 504 ])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session


def get_api_status(endpoint):
    apiResponseValues = {}
    try:
        response = requests_retry_session().get(endpoint)
        if response.status_code == 200:
            responsePayload = json.loads(response.text)
            code = responsePayload['code']
            artifact = responsePayload['build']['artifact']
            buildNumber = responsePayload['build']['buildNumber']

            apiResponseValues["code"] = code
            apiResponseValues["artifact"] = artifact
            apiResponseValues["buildNumber"] = buildNumber

        else:
            print('Endpoint: {0} ==> Status: {1}'.format(endpoint, response.status_code))
    except Exception as x:
        print('Request failed! endpoint: {0}', format(endpoint))
    return apiResponseValues


def get_env_host_url(envTag):
    environments = {
        'plat'  : 'https://pivotus.plat.engage.pivotus.io',
        #'dev'   : 'https://pivotus.dev.engage.pivotus.io',
        #'qa'    : 'https://pivotus.dev.engage.pivotus.io'
    }

    if envTag.lower().startswith('env-'):
        env = envTag[len('env-'):]
        return environments[env.lower()] if env.lower() in environments else ''
    else:
        return ''


def start(hostUrl, expectedBuildNumber):
    time.sleep(60)

    apiPaths = {
        'users'         : '/api/users/status',
        'auth'          : '/api/auth/status',
        'conversations' : '/api/conversations/status',
        'notification'  : '/api/notification/status',
        'profiles'      : '/api/profiles/status'
    }

    for k, v in apiPaths.items():
        print("----------")
        apiResponseValues = get_api_status(hostUrl + v)

        if 'buildNumber' in apiResponseValues:
            print('Endpoint: {0} \nStatus: {1}'
                .format(hostUrl, apiResponseValues['code']))
            print('Artifact: {0} \nBuildNumber: {1}'
                .format(apiResponseValues['artifact'], apiResponseValues['buildNumber']))

            actualBuildNumber = apiResponseValues['buildNumber'][0:10]
            if actualBuildNumber == expectedBuildNumber:
                print('Expected build number [{0}] DID matched actual build number [{1}]'
                    .format(expectedBuildNumber, actualBuildNumber))
            else:
                sys.exit("Expected build number [{0}] DID NOT matched actual build number [{1}]"
                    .format(expectedBuildNumber, actualBuildNumber))


if __name__ == '__main__':
    acceptedEnvTags = {'ENV-PLAT'}

    if 'CIRCLE_TAG' in os.environ and os.environ['CIRCLE_TAG'] in acceptedEnvTags:
        hostUrl = get_env_host_url(os.environ['CIRCLE_TAG'])
        expectedBuildNumber = os.environ['CIRCLE_SHA1'][0:10]

        print('*** Start API status checks deployed at [ {0} ] ***'.format(hostUrl))
        start(hostUrl, expectedBuildNumber)
        print('*** End API status checks ***')
    else:
        print("No match for env tag!")
