
# Created by:  Maria Jose Lira ; 2024-08-28
# Modified by: Maria Jose Lira ; 2024-08-28

import os
import requests
import pandas as pd
from datetime import datetime



class ApiSecretKeyVault:
    def __init__(self, secret_name:str, tenant_id:str, client_id:str, client_secret:str, token_filepath:str='token_keyvault.txt', keyvault_name:str="KeyVault-Produccion-RPA"):
        self.secret_name    = secret_name
        self.tenant_id      = tenant_id
        self.client_id      = client_id
        self.client_secret  = client_secret
        self.keyvault_name  = keyvault_name
        self.token_filepath = token_filepath
        self.resource       = "https://vault.azure.net/"
        self.keyvault_url   = f"https://{self.keyvault_name}.vault.azure.net/"
        self.token          = None
        self.payload        = None
    
    def get_token(self):
        # Url get token
        url = f'https://login.microsoftonline.com/{self.tenant_id}/oauth2/token'
        # Build payload with token bearer
        self.payload = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'resource': self.resource
        }
        # Headers
        headers ={
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        # Verify if the token has to be reset
        if os.path.exists(self.token_filepath):
            # Get the time of last 30 minutes
            time_now = datetime.now().timestamp()
            last_30_min = time_now - (60*30)
            # Get the last time update of token file
            time_file = os.path.getmtime(filename=self.token_filepath)
            # Read token file if the time file is less than 30 minutes
            bool_read_file = True if (last_30_min) <= time_file else False
        else:
            bool_read_file = False
        # Verify if read file or request the token
        if bool_read_file:
            # Read file
            with open(self.token_filepath, 'r') as file:
                self.token = file.read().strip()
            print(f'Leyendo token desde archivo: {self.token_filepath}')
            # print(self.token)
        else:
            # Request token
            response = requests.post(url, data=self.payload, headers=headers) 
            if response.status_code == 200:
                self.token = response.json()['access_token']
                with open(self.token_filepath, 'w') as file:
                    file.write(self.token)
                print(self.token)
                print(f'Token guardado exitosamente en {self.token_filepath}')
            else:
                print('No se pudo obtener el token. Código de estado:', response.status_code)
                print(response.text)
        return (0)
        
    def get_response(self, request_url:str=""):
        """ Get the api response """
        # Get token
        self.get_token()
        # Token bearer
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }       
        # Get response
        response = requests.get(self.keyvault_url + request_url, headers=headers) #, data=self.payload
        # Validate result
        if response.status_code == 200:
            data = response.json()
            # print(data)
            return(data)
        else:
            error = f"Error: Unable to fetch data from the API. Status code: {response.status_code}"
            print(error)
            print(response.text)
            return(error)
        
    def get_secret(self):
        """Obtain the secret value of secret_name from keyvault_name"""
        response = self.get_response(request_url=f"secrets/{self.secret_name}?api-version=7.4")
        secret = response["value"]
        print("Secret: ", secret)
        return (secret)
        



if __name__ == "__main__":
    # Get token
    filepath = "process_data/token_keyvault.txt"
    # Api creds 
    tenant_id = 'a5603b60-3a2f-4d5d-9f2d-1ec213aa643e'
    client_id = 'c7182fca-44ef-4349-aca7-71e71a9566cd'
    client_secret = 'tK18Q~6KV97t1CNIgR0XYVp14OnzxWY-H762ja6v'
    secret_name = "KeyVault-TenantID"
    # Initialize api class
    api_pad = ApiSecretKeyVault(secret_name=secret_name, tenant_id=tenant_id, client_id=client_id, client_secret=client_secret, token_filepath=filepath)
    # Get folders
    api_pad.get_secret()
    
    # def codigo_azure():
        # Codigo no probado que podria ser mas optimo pero no me funciona descargar la libreria
        # from azure.identity import DefaultAzureCredential
        # from azure.keyvault.secrets import SecretClient

        # # URL del Key Vault
        # key_vault_name = "nombre-del-keyvault"
        # key_vault_url = f"https://{key_vault_name}.vault.azure.net/"

        # # Autenticarse utilizando DefaultAzureCredential
        # credential = DefaultAzureCredential()

        # # Crear el cliente de secretos
        # client = SecretClient(vault_url=key_vault_url, credential=credential)

        # # Obtener un secreto específico por su nombre
        # secret_name = "nombre-del-secreto"
        # retrieved_secret = client.get_secret(secret_name)

        # # Imprimir el valor del secreto
        # print(f"El valor del secreto '{secret_name}' es: {retrieved_secret.value}")
        # return (0)




