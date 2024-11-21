# Created by:  Maria Jose Lira ; 2024-06-11
# Modified by: Maria Jose Lira ; 2024-06-18

import os
import sys
import logging
import pandas
from croniter import croniter
from datetime import datetime
from dateutil.relativedelta import relativedelta
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from clases.api_uipath import ApiUiPath
from utilities.utilities import *
from modules.update_ddbb_sql import UpdateDDBB


class GetScheduleMachineUipath:
    def __init__(self):
        configuration          = read_json()
        self.param             = configuration["PARAMETERS"]
        self.api_param         = self.param["API_UIPATH"]
        self.general_param     = self.param["GENERAL"]
        self.client_id         = self.api_param["CLIENT_ID"]
        self.client_secret     = self.api_param["CLIENT_SECRET"]
        self.filepath_token    = self.api_param["FILEPATH_TOKEN"]
        self.tenant_prd        = self.general_param["TENANT_PRODUCCION"]
        self.tenant_mb         = self.general_param["TENANT_MARCHA_BLANCA"]
        self.filepath_ddbb     = self.general_param["FILEPATH_DDBB_UIPATH"]
        self.filepath_schedule = self.general_param["FILEPATH_SCHEDULE_UIPATH"]
        self.df_schedule       = pandas.DataFrame()
        self.df_week_schedule  = pandas.DataFrame()
        self.start_datetime    = datetime.now()
        self.today             = datetime(self.start_datetime.year, self.start_datetime.month, self.start_datetime.day)
        self.start_time        = self.convert_to_monday(self.today)
        self.finish_date       = self.convert_to_sunday(self.today) + relativedelta(days=+1)
        
    def convert_to_monday(self, datetime):
        weekday = datetime.weekday()
        while weekday != 0:
            datetime = datetime + relativedelta(days=-1)
            weekday = datetime.weekday()
        return datetime
            
    def convert_to_sunday(self, datetime):
        weekday = datetime.weekday()
        while weekday != 6:
            datetime = datetime + relativedelta(days=+1)
            weekday = datetime.weekday()
        return datetime
        
    def convert_uipath_cron_expression(self, cron_expression): 
        """
        Convierte una expresión cron de UiPath (7 campos) en una expresión cron compatible
        con CronTrigger de apscheduler.
        """
        # Replace "?" for "*" and split fields
        parts = cron_expression.replace("?", "*").split(" ")
        # Drop seconds and year
        parts = parts[1:-1]
        join_parts = " ".join(parts)
        return (join_parts)
    
    def get_next_runs(self, cron_expression, start_time:datetime, finish_date:datetime=None, num_runs=None):
        """
        Get the next executions for a crontime expression.
        """
        # Convertir la expresión cron de UiPath
        converted_expression = self.convert_uipath_cron_expression(cron_expression)
        original_week = start_time.isocalendar().week
        # Obtener las próximas ejecuciones
        next_ejecutions = []
        if num_runs is not None:
            current_time = start_time
            for _ in range(num_runs):
                iter = croniter(converted_expression, current_time)
                next_run = iter.get_next(datetime)
                current_time = next_run
                if current_time.isocalendar().week == original_week:
                    # print(f"Próxima ejecución: {next_run}")
                    next_ejecutions.append(next_run)
        else:
            if finish_date is not None:
                current_time = start_time
                while current_time<finish_date:
                    iter = croniter(converted_expression, current_time)
                    next_run = iter.get_next(datetime)
                    current_time = next_run
                    if current_time.isocalendar().week == original_week:
                        # print(f"Próxima ejecución: {next_run}")
                        next_ejecutions.append(next_run)
        return (next_ejecutions)

    def get_schedule(self):
        # Initialize api class
        api_uipath_prd = ApiUiPath(client_id=self.client_id, 
                               client_secret=self.client_secret, 
                               token_filepath=self.filepath_token,
                               tenant_name=self.tenant_prd)
        api_uipath_mb = ApiUiPath(client_id=self.client_id, 
                               client_secret=self.client_secret, 
                               token_filepath=self.filepath_token,
                               tenant_name=self.tenant_mb)
        # Get folders
        self.df_schedule_prd = api_uipath_prd.get_schedule_subfolders()
        self.df_schedule_mb  = api_uipath_mb.get_schedule_subfolders()
        # Add tenat column
        self.df_schedule_prd["tenant"] = self.tenant_prd
        self.df_schedule_mb["tenant"] = self.tenant_mb
        # Concat tenants prd and mb
        self.df_schedule = pandas.concat([self.df_schedule_prd, self.df_schedule_mb], ignore_index=True)
        return (0)
    
    def format_cron_expressions(self):
        # Add data
        list_schedule = []
        # Get data schedules
        for i in range(len(self.df_schedule)):
            row = self.df_schedule.iloc[i]
            start_process_cron = row['start_process_cron']
            # Get the runs for week
            list_next_runs = self.get_next_runs(cron_expression=start_process_cron,
                                                start_time=self.start_time, 
                                                finish_date=self.finish_date)
            for run_date in list_next_runs:
                # Create dict
                df_dict = {
                    "run_id": int(f"{str(row['realease_id'])}{run_date.strftime('%Y%m%d%H%M')}"),
                    "folder_id":row['folder_id'],
                    "folder_path":row['folder_path'],
                    "package_name":row['package_name'],
                    "realease_name":row['realease_name'],
                    "trigger_name":row['trigger_name'],
                    "run_date":run_date,
                    "kill_process_expresion":int(row['kill_process_expresion']),
                    "stop_date":run_date + relativedelta(seconds=+int(row['kill_process_expresion'])),
                    "machine_name":row['machine_name'],
                    "machine_id":row['machine_id'],
                    "rpa": "UiPath",
                    "tenant": row['tenant']
                }
                # Append dict to list
                list_schedule.append(df_dict)
        # Create DataFrame
        self.df_week_schedule = pandas.DataFrame(list_schedule)
        print(self.df_week_schedule)
        # Save excel
        self.df_week_schedule['run_id'] = self.df_week_schedule['run_id'].astype(str)
        self.df_week_schedule.to_excel(self.filepath_schedule, index=False)
        return (0)
    
    def create_bbdd_power_bi(self):
        def busy_time(run_date, stop_date, current_date):
            is_busy_time = False
            if run_date <= current_date and current_date <= stop_date:
                is_busy_time = True
            return is_busy_time
        # Create date array for week
        date_range = pandas.date_range(start=self.start_time, end=self.finish_date, freq='min')
        # Get machines in use
        machines = self.df_week_schedule['machine_id'].unique()
        # machines = [172499] # Test by machine
        # Tenants
        tenants = [self.tenant_prd, self.tenant_mb]
        # Add busy time machine
        list_ddbb = []
        for tenant in tenants:
            df_tenant = self.df_week_schedule[self.df_week_schedule['tenant'] == tenant]
            for machine in machines:
                if not df_tenant.empty:
                    df_machine = df_tenant[df_tenant['machine_id'] == machine].copy()
                    if not df_machine.empty:
                        for date in date_range:
                            # Create column busy
                            df_machine.loc[:, 'busy'] = df_machine.apply(lambda row: busy_time(row['run_date'], row['stop_date'], date), axis=1)
                            # Filter by busy = True
                            df_busy = df_machine[df_machine['busy'] == True]
                            # Create dict
                            df_dict = {
                                "schedule_id":int(f"{str(machine)}{date.strftime('%Y%m%d%H%M')}"),
                                "machine_id": machine,
                                "date":date,
                                "week_day": datime_to_weeek_day(datetime=date),
                                "busy":1 if not df_busy.empty else 0,
                                "rpa": "UiPath",
                                "tenant": tenant    
                            }
                            # Append dict to list
                            list_ddbb.append(df_dict)
        # Create DataFrame
        self.df_graphs_ddbb = pandas.DataFrame(list_ddbb)
        print(self.df_graphs_ddbb)
        # Save excel
        self.df_graphs_ddbb['schedule_id'] = self.df_graphs_ddbb['schedule_id'].astype(str)
        self.df_graphs_ddbb.to_excel(self.filepath_ddbb, index=False)
        return (0)
    
    def create_grafic(self):
        """ Gráfico para utilizar en power BI con filtros de máquina y día """
        # Read excel
        dataset = pandas.read_excel(self.filepath_ddbb, index_col=0) 
        
        # Importar las librerías necesarias
        import matplotlib.pyplot as plt
        from matplotlib.patches import Patch
        import pandas as pd
        import numpy as np

        # Supongamos que 'dataset' es el DataFrame cargado en Power BI
        # Convertir la columna 'date' a formato datetime
        dataset['date'] = pd.to_datetime(dataset['date'])

        # Ordenar los datos por la columna 'date'
        dataset = dataset.sort_values(by='date')

        # Crear los colores para el gráfico
        red, green = '#ED1C1C', '#01b44c'
        colors = [green if b == 0 else red for b in dataset['busy']]

        # Crear el gráfico de torta
        fig, ax = plt.subplots(figsize=(5, 5))  # Ajustar el tamaño de la figura (ancho, alto)

        # Eliminar el autogenerado de etiquetas para asegurarse de que no haya confusión en el gráfico
        wedges, _ = ax.pie([1]*len(dataset), colors=colors, startangle=90, counterclock=False)

        # Añadir las etiquetas de las horas
        hours = [f'{i:02d}:00' for i in range(24)]
        hours.sort(reverse = True)
        angles = [i * 360 / 24 for i in range(24)]
        radius = 1.2  # Radio para colocar las etiquetas fuera del gráfico

        # Rotar 105 grados para que "00:00" quede en la parte superior
        rotation_angle = 105

        for angle, hour in zip(angles, hours):
            adjusted_angle = angle + rotation_angle
            x = radius * np.cos(np.radians(adjusted_angle))
            y = radius * np.sin(np.radians(adjusted_angle))
            plt.text(
                x, y, hour,
                horizontalalignment='center',
                verticalalignment='center',
                transform=ax.transData,
                fontsize=10
            )

        # Poner el fondo del gráfico transparente
        fig.patch.set_alpha(0.0)  # Fondo de la figura
        ax.patch.set_alpha(0.0)  # Fondo del eje

        # Añadir la leyenda
        legend_elements = [Patch(facecolor=green, edgecolor=green, label='Available'),
                        Patch(facecolor=red, edgecolor=red, label='Busy')]

        ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(-0.1, 1.05), frameon=False)

        plt.title('CLARORPA020', fontsize=18, pad=14)

        # Reducir márgenes
        plt.subplots_adjust(left=0, right=1, top=0.9, bottom=0.1)

        plt.show()
        return 0
    
    def update_database_schedule_machine(self):
        # Update database schedule_machines_uipath
        sql = UpdateDDBB(df_input=self.df_week_schedule)
        sql.merge_datarow_uipath_ddbb()
        return (0)        
    
    def update_database_machine_graphs(self):
        # Update database machine_graphs_uipath
        sql = UpdateDDBB(df_input=self.df_graphs_ddbb)
        sql.merge_datarow_uipath_graphs()
        return (0)   
                
    def run_workflow(self):
        self.get_schedule()
        self.format_cron_expressions()
        self.create_bbdd_power_bi()
        self.update_database_schedule_machine()
        self.update_database_machine_graphs()
        # self.create_grafic()
        return (0)
        
        
if __name__ == "__main__":
    state = GetScheduleMachineUipath()
    state.run_workflow()
