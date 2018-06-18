import os
import sys
import json
import requests
import time

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


ENV_TAG_NAMES = {'ENV-PLAT', 'ENV-DEV'}

API_STATUS_PATH = {
    'users': '/api/users/status',
    'auth': '/api/auth/status',
    'conversations': '/api/conversations/status',
    'notification': '/api/notification/status',
    'profiles': '/api/profiles/status'
}


def requests_retry_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session


def get_api_status(endpoint):
    api_response_values = {}
    try:
        response = requests_retry_session().get(endpoint)
        if response.status_code == 200:
            response_payload = json.loads(response.text)
            api_response_values["code"] = response_payload['code']
            api_response_values["artifact"] = response_payload['build']['artifact']
            api_response_values["buildNumber"] = response_payload['build']['buildNumber']
        else:
            print('Endpoint: {0} ==> Status: {1}'.format(endpoint, response.status_code))
    except Exception as x:
        print('Request failed! endpoint: {0}', format(endpoint))
    return api_response_values


def get_env_host_url(env_tag):
    environments = {
        'plat': 'https://pivotus.plat.engage.pivotus.io',
        # 'dev': 'https://pivotus.dev.engage.pivotus.io',
        # 'qa': 'https://pivotus.dev.engage.pivotus.io'
    }

    if env_tag.lower().startswith('env-'):
        env = env_tag[len('env-'):]
        return environments[env.lower()] if env.lower() in environments else ''
    else:
        return ''


def start(host_url, expected_build_number):
    time.sleep(10)

    for k, v in API_STATUS_PATH.items():
        print("----------")
        api_response_values = get_api_status(host_url + v)

        if 'buildNumber' in api_response_values:
            print('Endpoint: {0} \nStatus: {1}'
                  .format(host_url, api_response_values['code']))
            print('Artifact: {0} \nBuildNumber: {1}'
                  .format(api_response_values['artifact'], api_response_values['buildNumber']))

            actual_build_number = api_response_values['buildNumber'][0:10]
            if actual_build_number == expected_build_number:
                print('Expected build number [{0}] DID matched actual build number [{1}]'
                      .format(expected_build_number, actual_build_number))
            else:
                sys.exit("Expected build number [{0}] DID NOT matched actual build number [{1}]"
                         .format(expected_build_number, actual_build_number))


def main():
    if 'CIRCLE_TAG' in os.environ and os.environ['CIRCLE_TAG'] in ENV_TAG_NAMES:
        in_host_url = get_env_host_url(os.environ['CIRCLE_TAG'])
        in_expected_build_number = os.environ['CIRCLE_SHA1'][0:10]

        print('*** Start API status checks deployed at [ {0} ] ***'.format(in_host_url))
        start(in_host_url, in_expected_build_number)
        print('*** End API status checks ***')
    else:
        print("No match for env tag!")


if __name__ == '__main__':
    main()
