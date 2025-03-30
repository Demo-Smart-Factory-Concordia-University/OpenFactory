import requests
import json
import pandas as pd


def ksql_query_to_dataframe(ksqldb_url, query: str) -> pd.DataFrame:
    """
    Executes a ksqlDB query and returns the result as a Pandas DataFrame

    :param query: ksqlDB SQL query string
    :return: Pandas DataFrame containing the query results
    """
    payload = {
        "ksql": query,
        "streamsProperties": {}
    }

    headers = {"Content-Type": "application/json"}
    response = requests.post(f"{ksqldb_url}/query", headers=headers, data=json.dumps(payload), stream=True)

    if response.status_code != 200:
        raise Exception(f"Error in ksqlDB query: {response.text}")

    data = []
    columns = []

    # Process response line by line
    for line in response.iter_lines():
        if line:
            json_line = json.loads(line.decode("utf-8"))

            if "columnNames" in json_line:
                # Extract column names from metadata
                columns = json_line["columnNames"]

            elif isinstance(json_line, list):
                # Extract row data
                data.append(json_line)

    # Return results as a DataFrame
    return pd.DataFrame(data, columns=columns) if data else pd.DataFrame(columns=columns)
