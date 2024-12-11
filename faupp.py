# github.com/nakouchdoge 2024
import requests
import logging
import yaml
import json
import time

with open('auth.yaml', 'r') as file:
    auth = yaml.safe_load(file)

api_key = auth['pterodactyl']['api_key']
server_id = auth['pterodactyl']['server_id']
server_url = auth['pterodactyl']['server_url']
request_url = f"https://{server_url}/api/client/servers/{server_id}"
factorio_version_request_url = "https://factorio.com/api/latest-releases"


# Requests from Factorio's website and put into JSON format then extract the
# stable headless version.
def get_remote_version():
    global remote_version
    r = requests.get(factorio_version_request_url)
    response = r.json()
    status_code = r.status_code
    if status_code == 200:
        remote_version = (response['stable']['headless'])


# Use Pterodactyl API to get the local version from the factorio server files.
def get_local_version():
    global local_version
    url = f"{request_url}/files/contents?file=%2F/data/base/info.json"
    headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
    }

    r = requests.request('GET', url, headers=headers)
    response = r.json()
    status_code = (requests.get(url)).status_code
    if status_code == 200:
        local_version = (response['version'])


# Compare local to remote
def compare_versions():
    global version_mismatch
    get_remote_version()
    get_local_version()
    if remote_version == local_version:
        version_mismatch = 0
    else:
        version_mismatch = 1


def update_server():
    backup_url = f"{request_url}/backups"
    command_url = f"{request_url}/command"
    reinstall_url = f"{request_url}/settings/reinstall"
    power_url = f"{request_url}/power"
    headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
    }

    # Find and delete the oldest backup. This creates space for the new backup.
    backup_info = (requests.request('GET', backup_url, headers=headers)).json()
    number_of_backups = len(backup_info['data'])
    server_info = requests.request('GET', request_url, headers=headers).json()
    backup_limit = server_info['attributes']['feature_limits']['backups']
    backup_difference = (backup_limit - number_of_backups)

    if number_of_backups != 0 and backup_difference == 0:
        backup_uuid = backup_info['data'][0]['attributes']['uuid']
        requests.request('DELETE', f"{backup_url}/{backup_uuid}", headers=headers)
        # Check that the backup is actually deleted
        count = 0
        while (count <= 5):
            time.sleep(5)
            check_backup_uuid = backup_info['data'][0]['attributes']['uuid']
            if backup_uuid == check_backup_uuid:
                break
            else:
                count + 1
            if count == 5:
                print("Took too long to delete backup, quitting")
                quit()

    # Save Game and create backup
    requests.request('POST', command_url, data={"command": "/save"}, headers=headers)
    requests.request('POST', backup_url, data={"name": f"{local_version} Backup"}, headers=headers)
    check_backup_created = backup_info['data']
    specific_name = f"{local_version} Backup"
    backup_exists = any(element['attributes']['name'] == specific_name for element in check_backup_created)
    # Verify backup was created
    while backup_exists == "false":
        time.sleep(5)

    # Send server message to players
    requests.request('POST', command_url, data={"command": "[color=red]Server restarting for update[/color]"}, headers=headers)
    time.sleep(10)

    # Reinstall server
    requests.request('POST', reinstall_url, headers=headers)
    server_info = requests.request('GET', request_url, headers=headers).json()
    time.sleep(10)
    is_installing = server_info['attributes']['is_installing']
    # Check if server is installed
    print(is_installing, "is_installing")
    while 0 == 0:
        server_info = requests.request('GET', request_url, headers=headers).json()
        is_installing = server_info['attributes']['is_installing']
        time.sleep(1)
        print(is_installing, "is_installing")
        time.sleep(10)
        if (is_installing == False):
            break

    # Start server
    print("Starting server")
    time.sleep(10)
    requests.request('POST', power_url, data={"signal": "start"}, headers=headers)


while (0 == 0):
    print("main loop ran")
    compare_versions()
    if (version_mismatch == 0):
        time.sleep(600)
    else:
        if (version_mismatch == 1):
            update_server()
            time.sleep(600)
