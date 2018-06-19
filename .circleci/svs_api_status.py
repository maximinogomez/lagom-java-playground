import os
import sys
import json
import requests
import time

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


API_STATUS_PATHS = {
    'auth': '/api/auth/status',
    'users': '/api/users/status',
    'profiles': '/api/profiles/status',
    'notification': '/api/notification/status',
    'conversations': '/api/conversations/status'
}

ENGAGE_ENVIRONMENTS = {
    'dev': 'https://pivotus.dev.engage.pivotus.io',
    'plat': 'https://pivotus.plat.engage.pivotus.io'
}

ENGAGE_DEPLOY_JOBS = {
    'dev': 'https://jenkins.pivotusventures.com/jenkins/job/Engage-Deploy-Dev/build',
    'plat': 'https://jenkins.pivotusventures.com/jenkins/job/Engage-Deploy-Plat/build'
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
            print('--- Endpoint: {0} ==> Status: {1}'.format(endpoint, response.status_code))
    except Exception as x:
        print('--- Request failed! endpoint: {0}'.format(endpoint))
    return api_response_values


def start_api_checks(host_url, expected_build_number):
    for k, v in API_STATUS_PATHS.items():
        api_response_values = get_api_status(host_url + v)

        if 'buildNumber' in api_response_values:
            print('----- Endpoint: {0} Status: {1}'
                  .format(host_url + v, api_response_values['code']))

            print('----- Artifact: {0} BuildNumber: {1}'
                  .format(api_response_values['artifact'], api_response_values['buildNumber']))

            actual_build_number = api_response_values['buildNumber'][0:10]
            if actual_build_number == expected_build_number:
                print('----- Expected build number [{0}] DID matched response build number [{1}]'
                      .format(expected_build_number, actual_build_number))
            else:
                sys.exit('----- Expected build number [{0}] DID NOT matched response build number [{1}]'
                         .format(expected_build_number, actual_build_number))
        else:
            sys.exit('----- Response from endpoint {0} did not return the build number!'.format(host_url + v))


def trigger_ci_deploy_job(env_name):
    # Change me! to dev jenkins values
    jenkins_username = 'maximinogomez'
    jenkins_password = 'c30e09bc41d4b026d4fee885f95d9a6b'

    # Initially only to plat environment
    if env_name in ENGAGE_DEPLOY_JOBS and env_name == 'plat':
        print('***** Initiate jenkins deploy job [ {0} ]'.format(ENGAGE_DEPLOY_JOBS[env_name]))

        response = requests_retry_session() \
            .post(ENGAGE_DEPLOY_JOBS[env_name], auth=(jenkins_username, jenkins_password))

        if response.status_code == 201:
            print('----- Remote jenkins job response status: {0}'.format(response.status_code))
            return True
        else:
            print('----- Remote jenkins job response status: {0}'.format(response.status_code))
            return False
    else:
        print('----- Remote jenkins deploy job not allow for env name: {0}'.format(env_name))
        return False


def get_env_host_url(env_name):
    return ENGAGE_ENVIRONMENTS[env_name] if env_name in ENGAGE_ENVIRONMENTS else ""


def main():
    # For now, PLAT only
    accepted_env_tags = {'ENV-PLAT'}

    if 'CIRCLE_TAG' in os.environ and os.environ['CIRCLE_TAG'] in accepted_env_tags:
        env_tag = os.environ['CIRCLE_TAG']
        expected_build_number = os.environ['CIRCLE_SHA1'][0:10]

        # Trim the env name from tag(env-plat) if it exists
        env_name = (env_tag[len('env-'):]).lower() if env_tag.lower().startswith('env-') else ""

        env_host_url = get_env_host_url(env_name)

        if env_host_url:
            print("--- Env name : {0}".format(env_name))
            print("--- Expected build number : {0}".format(expected_build_number))
            print("--- Env host URL : {0}".format(env_host_url))

            was_triggered_successful = trigger_ci_deploy_job(env_name)
            if was_triggered_successful:
                time.sleep(20)

                print('***** Start API status checks deployed at [ {0} ]'.format(env_host_url))

                start_api_checks(env_host_url, expected_build_number)

                print('***** End API status checks.')

            else:
                print('--- API status checks did not ran due to errors when triggering the remote jenkins job!')
        else:
            print('--- No host URL found for env name: {0}'.format(env_name))


if __name__ == '__main__':
    main()
