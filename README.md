# Factorio Auto Update Python + Pterodactyl
## Install requirements
```
pip3 install -r requirements.txt
```
## Find your Pterodactyl server ID
Pterodactyl Admin Panel -> Servers -> (Select your server) -> About

The server ID is the first string as highlighted in the image below.

![trQYlQ](https://github.com/user-attachments/assets/949895a4-2e27-4796-aad1-1c9660ec5f67)

## Generate Pterodactyl User API key
Click on your account at the top right of the admin panel or navigate to <your pterodactyl panel url>/account/api

## Edit example.auth.yaml
Add your API key and server ID(s). To add more servers just continue adding lines: server_id3, server_id4, server_id5, etc.

The server_url is the URL of your Pterodactyl instance with NO trailing "/":

https://pterodactyl.example.com

Rename example.auth.yaml to auth.yaml
```
mv example.auth.yaml auth.yaml
```
Optional: Edit and move faupp.service to run on your machine if you wish to daemonize it with systemd.

Enjoy

December 11, 2024

- Initial Commit

December 27, 2024

- Allows multiple servers to be monitored and updated
