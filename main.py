from fastapi import FastAPI
import boto3
import psycopg2
import json
from datetime import datetime
import os

app = FastAPI()

# AWS Credentials & PostgreSQL Connection
session = boto3.Session()
client = boto3.client("stepfunctions",region_name="ap-south-1")

# client = boto3.client(
#     "stepfunctions")
conn = psycopg2.connect(
    host="database-1.cp60ewaeauvj.ap-south-1.rds.amazonaws.com",
    port=5432,
    user="postgres",
    password="chaithu06",
    database="postgres"
)
conn.autocommit = True
cursor = conn.cursor()

# Create Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS stepfunctions2 (
    id SERIAL PRIMARY KEY,
    name TEXT,
    arn TEXT UNIQUE,
    last_execution TEXT,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    status TEXT
);
""")
conn.commit()

@app.get("/")
async def root():
    return {"message": "Running successfully"}

@app.get("/stepfunctions")
def list_stepfunctions():
    response = client.list_state_machines()
    results = []

    for sm in response["stateMachines"]:
        name = sm["name"]
        arn = sm["stateMachineArn"]

        exec_response = client.list_executions(stateMachineArn=arn, maxResults=1)
        last_execution = exec_response["executions"][0] if exec_response["executions"] else None

        status = last_execution["status"] if last_execution else "N/A"
        start_date = last_execution["startDate"] if last_execution else None
        end_date = last_execution.get("stopDate") if last_execution else None  # Use `.get()` to avoid KeyError

        # ✅ Convert datetime objects to string safely
        if isinstance(start_date, datetime):
            start_date = start_date.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(end_date, datetime):
            end_date = end_date.strftime("%Y-%m-%d %H:%M:%S")

        # ✅ Convert last_execution dict to JSON-safe format
        if last_execution:
            last_execution = {
                key: (value.strftime("%Y-%m-%d %H:%M:%S") if isinstance(value, datetime) else value)
                for key, value in last_execution.items()
            }
            last_execution_str = json.dumps(last_execution)  # Convert to JSON string
        else:
            last_execution_str = None

        results.append({
            "name": name, "arn": arn, "last_execution": last_execution_str,
            "start_date": start_date, "end_date": end_date, "status": status
        })

        cursor.execute("""
        INSERT INTO stepfunctions (name, arn, last_execution, start_date, end_date, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (arn) DO UPDATE 
        SET last_execution = EXCLUDED.last_execution,
            start_date = EXCLUDED.start_date,
            end_date = EXCLUDED.end_date,
            status = EXCLUDED.status;
        """, (name, arn, last_execution_str, start_date, end_date, status))

        conn.commit()

    return results
