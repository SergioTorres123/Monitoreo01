
# Created by:  Maria Jose Lira ; 2024-11-13
# Modified by: Maria Jose Lira ; 2024-11-14

import os
import requests
import pandas as pd
from datetime import datetime


class ApiPowerAutomate:
    def __init__(self, 
                 tenant_id:str, 
                 client_id:str, 
                 client_secret:str, 
                 environment:str, 
                 username:str, 
                 password:str, 
                 token_filepath:str='token_pad.txt', 
                 tenant_name:str="Produccion"):
        self.tenant_id = tenant_id     
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_name = tenant_name
        self.token_filepath = token_filepath
        self.environment = environment
        self.username = username
        self.password = password
        self.token = None
        self.payload = None
        self.resource = 'https://service.flow.microsoft.com/'
        self.api_url = 'https://api.flow.microsoft.com/'



    def get_token(self):
        # Url get token
        url = f'https://login.microsoftonline.com/{self.tenant_id}/oauth2/token'
        # Build payload with token bearer
        self.payload = {
            'grant_type': 'password',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'username': self.username,
            'password': self.password,
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
            print('Leyendo token desde archivo')
            # print(self.token)
        else:
            # Request token
            response = requests.get(url, data=self.payload, headers=headers) 
            if response.status_code == 200:
                self.token = response.json()['access_token']
                with open(self.token_filepath, 'w') as file:
                    file.write(self.token)
                    # print(self.token)
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
        response = requests.get(self.api_url+request_url, headers=headers)
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
        
    def get_flows(self):
        print("---- starting get_flows ----")
        url = f"providers/Microsoft.Flow/environments/{self.environment}/flows?user={self.username}"
        data = self.get_response(request_url=url)
        dict = data["value"]
        # Add name and displayName
        list_flows = []
        append_data = [list_flows.append({"name": dict[inx]["name"], 
                                          "displayName": dict[inx]["properties"]["displayName"], 
                                          "triggers_type": dict[inx]["properties"]["definitionSummary"]["triggers"][0]["type"]}) for inx in range(len(dict))]
        # Create DataFrame
        df_flows = pd.DataFrame(list_flows)
        return (df_flows)
    
    def get_recurrence(self):
        def get_dict_recurrence(data):
            # Find the key that contains 'Recurrence'
            triggers = data.get('properties', {}).get('definition', {}).get('triggers', {})
            recurrence_key = next((key for key in triggers if 'Recurrence' in key), None)
            return(triggers[recurrence_key])
        def frequency_to_weekday_map(weekdays):
            weekday_map = {
            "Monday": 1,
            "Tuesday": 2,
            "Wednesday": 3,
            "Thursday": 4,
            "Friday": 5,
            "Saturday": 6,
            "Sunday": 0,
            }
            return ",".join(str(weekday_map[day]) for day in weekdays)
        def generate_crontab(schedule):
            # Create a crontab
            frequency = schedule.get("frequency", "Day")
            interval = schedule.get("interval", 1)
            start_time = schedule.get("startTime", "")
            time_zone = schedule.get("timeZone", "UTC")
            hours = schedule.get("schedule", {}).get("hours", ["*"])
            minutes = schedule.get("schedule", {}).get("minutes", ["*"])
            weekdays = schedule.get("schedule", {}).get("weekDays", ["*"]) 
            # Handle hours and minutes
            hour_field = ",".join(hours)
            minute_field = ",".join(map(str, minutes)) 
            # Handle weekday
            if frequency == "Week":
                weekday_field = frequency_to_weekday_map(weekdays)
            else:
                weekday_field = "*"
            # Build crontab
            crontab = f"{minute_field} {hour_field} * * {weekday_field}"
            return crontab
        print("---- starting get_recurrence ----")
        # Get all flows
        df_flows = self.get_flows()
        print(df_flows)
        # Add Id, name, displayName, triggers_type, recurrence
        list_schedule = []
        # Get data recurrence
        for i in range(len(df_flows)):
            flow_id = df_flows.iloc[i]['name']
            flow_name = df_flows.iloc[i]['displayName']
            triggers_type = df_flows.iloc[i]['triggers_type']
            # If trigger is type Recurrence
            if triggers_type == "Recurrence":
                url = f"providers/Microsoft.ProcessSimple/environments/{self.environment}/flows/{flow_id}?api-version=2016-11-01"
                dict = self.get_response(request_url=url)
                recurrence = get_dict_recurrence(dict)["recurrence"]
                # Create dict
                df_dict = {
                    "flow_id":flow_id,
                    "flow_name":flow_name,
                    "triggers_type":triggers_type,
                    "recurrence":generate_crontab(schedule=recurrence)
                }
                # Append dict to list
                list_schedule.append(df_dict)
                print(get_dict_recurrence(dict)["recurrence"])
                print(generate_crontab(schedule=recurrence))
        # Create DataFrame
        df_schedule = pd.DataFrame(list_schedule)
        print(df_schedule)
        return (df_schedule)
            
    

if __name__ == "__main__":
    # Get token
    filepath = "process_data/token_pad.txt"
    # Api creds 
    
    tenant_id = 'a5603b60-3a2f-4d5d-9f2d-1ec213aa643e'
    client_id = '92cd43dd-53a6-4c63-a4d5-c15880592a97'
    client_secret = 'AQb8Q~8cfMCcSaWsFuwvyqtfGU9dqcuTamX1zdrE'

    environment ="d84b2dcb-1d46-e024-b9a6-4f54de06ede3"
    username = "soporterpa@clarochile.cl"
    password = "k@E#8PjEI3I"
    
    # Initialize api class
    api_pad = ApiPowerAutomate(tenant_id=tenant_id, 
                               client_id=client_id, 
                               client_secret=client_secret, 
                               environment=environment, 
                               username=username, 
                               password=password, 
                               token_filepath=filepath)
    # Get folders
    api_pad.get_recurrence()
    
    
    
    
    
    # from datetime import datetime, timedelta

    # def crontab_to_datetime_range(crontab, start_of_week=None, end_of_week=None):
    #     # Obtenemos los valores del crontab
    #     minutes, hours, *_ = crontab.split(" ")
    #     minute_values = list(map(int, minutes.split(",")))  # Ej: [0, 30]
    #     hour_values = list(map(int, hours.split(",")))      # Ej: [10, 12]

    #     # Determinamos inicio y fin de la semana
    #     now = datetime.now()
    #     start_of_week = start_of_week or (now - timedelta(days=now.weekday()))
    #     end_of_week = end_of_week or (start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59))

    #     # Generar todos los datetime dentro del rango
    #     schedule = []
    #     current_date = start_of_week
    #     while current_date <= end_of_week:
    #         for hour in hour_values:
    #             for minute in minute_values:
    #                 scheduled_time = current_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    #                 if start_of_week <= scheduled_time <= end_of_week:
    #                     schedule.append(scheduled_time)
    #         current_date += timedelta(days=1)

    #     return start_of_week, end_of_week, schedule

    # # Ejemplo de uso
    # crontab = "0,30 10,12 * * *"
    # start, end, schedule = crontab_to_datetime_range(crontab)

    # print(f"Inicio de la semana: {start}")
    # print(f"Fin de la semana: {end}")
    # print("Fechas y horas programadas:")
    # for dt in schedule:
    #     print(dt)

