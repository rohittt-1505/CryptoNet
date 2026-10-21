
# import pyodbc


# def get_connection():
#     connection_string = (
#         "DRIVER={ODBC Driver 18 for SQL Server};"
#         "SERVER=localhost\\SQLEXPRESS;"
#         "DATABASE=CryptoNetDB;"
#         "Trusted_Connection=yes;"
#         "TrustServerCertificate=yes;"
#     )

#     return pyodbc.connect(connection_string)



import os
import pyodbc


def get_connection():
    server = os.getenv("DB_SERVER", "db75023.databaseasp.net,1433")
    database = os.getenv("DB_NAME", "db75023")
    username = os.getenv("DB_USER", "db75023")
    password = os.getenv("DB_PASSWORD", "qS!2C8t-7i_E")

    if not password:
        raise ValueError("DB_PASSWORD environment variable is not set.")

    connection_string = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=30;"
    )

    return pyodbc.connect(connection_string)
