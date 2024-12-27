# github.com/nakouchdoge 2024
import requests
import yaml
import time

with open('auth.yaml', 'r') as file:
    auth = yaml.safe_load(file)


def find_server_ids():
    x = 10
    server_id_list = [f"server_id{i}" for i in range(1, x)]
    server_ids = []
    for server_id in server_id_list:
        if server_id in auth['pterodactyl']:
            server_ids.append(auth['pterodactyl'][server_id])
    return server_ids


server_ids = find_server_ids()
api_key = auth['pterodactyl']['api_key']
server_url = auth['pterodactyl']['server_url']
factorio_version_request_url = "https://factorio.com/api/latest-releases"

headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }


# Requests from Factorio's website and put into JSON format then extract the
# stable headless version.
def get_remote_version():
    global remote_version
    try:
        response = requests.get(factorio_version_request_url)
        versions = response.json()
        status_code = response.status_code
        if status_code == 200:
            remote_version = (versions['stable']['headless'])
    except Exception:
        time.sleep(60)
        get_remote_version()


# Use Pterodactyl API to get the local version from the factorio server files.
def get_outdated_servers():
    servers_to_update = []
    try:
        for server_id in find_server_ids():
            request_url = f"https://{server_url}/api/client/servers/{server_id}"
            url = f"{request_url}/files/contents?file=%2F/data/base/info.json"
            response = requests.request('GET', url, headers=headers).json()
            if response['version'] != remote_version:
                servers_to_update.append((response['version'], server_id))
    except Exception:
        time.sleep(60)
        get_outdated_servers()

    return servers_to_update


def update_servers():
    servers_to_update = get_outdated_servers()
    for server_version, server_id in servers_to_update:
        request_url = f"https://{server_url}/api/client/servers/{server_id}"
        server_info = requests.request('GET', request_url, headers=headers).json()
        command_url = f"{request_url}/command"
        reinstall_url = f"{request_url}/settings/reinstall"
        power_url = f"{request_url}/power"
        backup_url = f"{request_url}/backups"
        backup_info = (requests.request('GET', backup_url, headers=headers)).json()
        backup_total = len(backup_info['data'])
        backup_limit = server_info['attributes']['feature_limits']['backups']

    # Find and delete the oldest backup. This creates space for the new backup.
        if backup_total != 0 and (backup_limit - backup_total) == 0:
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
        requests.request('POST', backup_url, data={"name": f"{server_version} Backup"}, headers=headers)
        check_backup_created = backup_info['data']
        specific_name = f"{server_version} Backup"
        backup_exists = any(element['attributes']['name'] == specific_name for element in check_backup_created)
        # Verify backup was created
        while backup_exists == "false":
            time.sleep(5)

        # Send server message to players
        requests.request('POST', command_url, data={"command": "[color=red]Server restarting for update[/color]"}, headers=headers)
        time.sleep(10)

        # Reinstall server
        requests.request('POST', reinstall_url, headers=headers)
        time.sleep(10)
        is_installing = server_info['attributes']['is_installing']
        # Check if server is installed
        while True:
            is_installing = server_info['attributes']['is_installing']
            time.sleep(1)
            time.sleep(10)
            if (is_installing is False):
                break

        # Start server
        time.sleep(10)
        requests.request('POST', power_url, data={"signal": "start"}, headers=headers)


while True:
    get_remote_version()
    servers_to_update = get_outdated_servers()
    if servers_to_update:
        update_servers()
        time.sleep(600)
    else:
        time.sleep(600)
