# github.com/kouchpouch 2024
import requests
from requests.exceptions import HTTPError, Timeout
import yaml
import time
import logging


log = logging.getLogger(__name__)
logging.basicConfig(
        format='%(asctime)s: %(message)s', 
        datefmt='%b %d, %Y %H:%M:%S', 
        filename='log.log', 
        encoding='utf-8', 
        level=logging.DEBUG
        )


try:
    with open('auth.yaml', 'r') as file:
        auth = yaml.safe_load(file)
        log.info("Loaded auth.yaml file")
except:
    log.critical("Failed to open auth.yaml, exiting")
    exit()


def find_server_ids():
    x = 10
    server_id_list = [f"server_id{i}" for i in range(1, x)]
    server_ids = []
    for server_id in server_id_list:
        if server_id in auth['pterodactyl']:
            value = auth['pterodactyl'][server_id]
            if value is not None:
                server_ids.append(value)
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
        response = requests.get(factorio_version_request_url, timeout=10)
        versions = response.json()
        status_code = response.status_code
        if status_code == 200:
            remote_version = (versions['stable']['headless'])
            log.info('Remote version: %s', remote_version)
        elif status_code == 404:
            print("Cannot find remote factorio version. Status code: 404. Check 'factorio_version_request_url' variable. Exiting")
            exit()
    except Timeout:
        log.error("Request to %s timed out. Trying again in 60 seconds", factorio_version_request_url)
        print("Request to %s timed out. Trying again in 60 seconds", factorio_version_request_url)
        time.sleep(60)
        get_remote_version()
    except KeyboardInterrupt:
        print("\nGoodbye!")
        exit()
    except Exception as e:
        log.exception(e)
        print("An exception occured while trying to get the remote version, check logs for details. Exiting")
        exit()


# Use Pterodactyl API to get the local version from the factorio server files.
def get_outdated_servers():
    servers_to_update = []
    valid_servers = []
    try:
        for server_id in find_server_ids():
            request_url = f"{server_url}/api/client/servers/{server_id}"
            url = f"{request_url}/files/contents?file=%2F/data/base/info.json"
            r = requests.request('GET', url, headers=headers, timeout=10)
            status = r.status_code
            response = r.json()
            if status == 200:
                valid_servers.append(server_id)
                if response['version'] != remote_version:
                    servers_to_update.append((response['version'], server_id))
            elif status == 401 and not servers_to_update:
                print("Unauthenticated to local servers. Is your API key correct?")
                log.error("Got 401 error from server. Your API key is not correct in auth.yaml.")
                continue
            elif status == 404 and not servers_to_update: 
                print("One or more servers not found. Check server IDs in auth.yaml")
                log.error("Got 404 error from server ID: %s", server_id)
                continue
        if not valid_servers:
            print("No response from any servers, check logs, exiting.")
            exit()
        if servers_to_update:
            log.info("Found servers to update: %s", servers_to_update)
    except Timeout:
        log.error("Request to pterodactyl servers timed out. Trying again in 60 seconds")
        print("Request to pterodactyl servers timed out. Trying again in 60 seconds")
        time.sleep(60)
        get_outdated_servers()
    except KeyboardInterrupt:
        print("\nGoodbye!")
        exit()
    except Exception as e:
        log.exception(e)
        print("An exception occured while trying to get local server information, check logs for details. Exiting")
        exit()
    return servers_to_update


def update_servers():
    servers_to_update = get_outdated_servers()
    for server_version, server_id in servers_to_update:
        request_url = f"{server_url}/api/client/servers/{server_id}"
        server_info = requests.request('GET', request_url, headers=headers).json()
        command_url = f"{request_url}/command"
        reinstall_url = f"{request_url}/settings/reinstall"
        power_url = f"{request_url}/power"
        backup_url = f"{request_url}/backups"
        backup_info = (requests.request('GET', backup_url, headers=headers)).json()
        backup_total = len(backup_info['data'])
        backup_limit = server_info['attributes']['feature_limits']['backups']
        log.info("Updating server: %s, from version %s to %s", server_id, server_version, remote_version)

    # Find and delete the oldest backup. This creates space for the new backup.
        if backup_total != 0 and (backup_limit - backup_total) == 0:
            backup_uuid = backup_info['data'][0]['attributes']['uuid']
            requests.request('DELETE', f"{backup_url}/{backup_uuid}", headers=headers)
            # Check that the backup is actually deleted
            i = 0
            while (i <= 5):
                time.sleep(5)
                check_backup_uuid = backup_info['data'][0]['attributes']['uuid']
                if backup_uuid == check_backup_uuid:
                    log.info("Backup deleted to make space from server: %s, backup UUID: %s", server_id, backup_uuid)
                    break
                else:
                    i = i + 1
                if i == 5:
                    print("Took too long to delete backup, exiting")
                    log.error("Could not delete backup from server: %s, backup UUID: %s", server_id, backup_uuid)
                    exit()

        # Save Game and create backup
        requests.request('POST', command_url, data={"command": "/save"}, headers=headers)
        log.info("Saving game on server: %s", server_id)
        requests.request('POST', backup_url, data={"name": f"{server_version} Backup"}, headers=headers)
        log.info("Creating backup on server: %s", server_id)
        check_backup_created = backup_info['data']
        specific_name = f"{server_version} Backup"
        backup_exists = any(element['attributes']['name'] == specific_name for element in check_backup_created)
        # Verify backup was created
        while backup_exists == "false":
            time.sleep(5)

        # Send server message to players
        requests.request('POST', 
                         command_url, 
                         data={"command": "[color=red]Server restarting for update[/color]"}, 
                         headers=headers
                         )
        time.sleep(10)

        # Reinstall server
        requests.request('POST', reinstall_url, headers=headers)
        log.info("Reinstall server: %s", server_id)
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
        logging.info("Staring server: %s", server_id)


while True:
    try:
        get_remote_version()
        servers_to_update = get_outdated_servers()
        if servers_to_update:
            update_servers()
            time.sleep(600)
        else:
            time.sleep(600)
    except KeyboardInterrupt:
        print("\nGoodbye!")
        exit()
    except Exception as e:
        print("An exception occured. Check logs. Exiting")
        log.exception(e)
        exit()
