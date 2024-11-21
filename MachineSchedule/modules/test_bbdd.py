import pyodbc
import urllib.parse

# Parámetros de conexión
server = 'org38a630b8.crm2.dynamics.com'
database = 'org38a630b8'
username = 'soporterpa@clarochile.cl'
password = 'k@E#8PjEI3I'
driver = '{ODBC Driver 17 for SQL Server}'

# Construcción de la cadena de conexión
params = urllib.parse.quote_plus(
    f'DRIVER={driver};SERVER={server};DATABASE={database};'
    f'UID={username};PWD={password}'
)

# Establecer conexión
connection_string = f'mssql+pyodbc:///?odbc_connect={params}'

try:
    # Usando SQLAlchemy
    from sqlalchemy import create_engine
    engine = create_engine(connection_string)
    
    # Conectar y ejecutar consulta
    with engine.connect() as connection:
        result = connection.execute('SELECT * FROM dbo.flowsession')
        for row in result:
            print(row)

except Exception as e:
    print(f"Error de conexión: {e}")