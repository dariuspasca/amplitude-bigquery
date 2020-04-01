#!/usr/bin/python
import gzip
import json
import os
import shutil
import zipfile
import config

from datetime import date, datetime, timedelta
from google.cloud import bigquery, storage
from os import walk


# Add your private info here
ACCOUNT_ID = config.config_vars['account_id']
API_KEY = config.config_vars['api_key']
API_SECRET = config.config_vars['secret_key']
PROJECT_ID = config.config_vars['project_id']
CLOUD_STORAGE_BUCKET = config.config_vars['bucket_name']
PROPERTIES = ["event_properties", "data", "groups", "group_properties",
              "user_properties"]


storage_client = None
bigquery_client = None
dataset_ref = None

YESTERDAY = (datetime.utcnow().date() - timedelta(days=1)).strftime("%Y%m%d")

PATH = "amplitude/{id}/".format(id=ACCOUNT_ID)


def remove_file(file, folder=''):
    folder = folder if folder == '' else folder + '/'
    os.remove("{folder}{file}".format(folder=folder, file=file))


def remove_folder(folder):
    shutil.rmtree(folder)


def unzip_file(filename, extract_to):
    zip_ref = zipfile.ZipFile(filename, 'r')
    zip_ref.extractall(extract_to)
    zip_ref.close()


def file_list(extension):
    files = []
    for (dirpath, dirnames, filenames) in walk("amplitude/{id}".format(id=ACCOUNT_ID)):
        for filename in filenames:
            if filename.endswith(extension):
                files.append(filename)
    return files


def file_json(filename):
    return filename.replace('.gz', '')


def unzip_gzip(filename, remove_original=True):
    f = gzip.open(filename, 'rb')
    file_content = f.read()
    f.close()

    with open(file_json(filename), 'wb') as unzipped_file:
        unzipped_file.write(file_content)

    if remove_original:
        remove_file(filename)


def upload_file_to_gcs(filename, new_filename, folder=''):
    folder = folder if folder == '' else folder + '/'
    bucket = storage_client.get_bucket(CLOUD_STORAGE_BUCKET)
    blob = bucket.blob('{folder}{file}'.format(folder=folder,
                                               file=new_filename))
    blob.upload_from_filename(filename)


def import_json_url(filename):
    return "gs://" + CLOUD_STORAGE_BUCKET + "/import/" + filename


def value_def(value):
    value = None if value == 'null' else value
    return value


def value_paying(value):
    value = False if value is None else value
    return value


def load_into_bigquery(file, table):
    job_config = bigquery.LoadJobConfig()

    #You can also use Auto-detect schema detection
    #More info here: https://cloud.google.com/bigquery/docs/schema-detect
    #It my trigger an error if in the table of @events_properties sample data there are null/empty values
    #job_config.autodetect = True 
     
    if table == 'events_properties':
        job_config.schema = [
            bigquery.SchemaField("property_type", "STRING"),
            bigquery.SchemaField("insert_id", "STRING"),
            bigquery.SchemaField("key", "STRING"),
            bigquery.SchemaField("value", "STRING"),
        ]
    else:
        job_config.schema = [
            bigquery.SchemaField("client_event_time", "TIMESTAMP"),
            bigquery.SchemaField("ip_address", "STRING"),
            bigquery.SchemaField("library", "STRING"),
            bigquery.SchemaField("dma", "STRING"),
            bigquery.SchemaField("user_creation_time", "TIMESTAMP"),
            bigquery.SchemaField("insert_id", "STRING"),
            bigquery.SchemaField("schema", "INTEGER"),
            bigquery.SchemaField("processed_time", "TIMESTAMP"),
            bigquery.SchemaField("client_upload_time", "TIMESTAMP"),
            bigquery.SchemaField("app", "INTEGER"),
            bigquery.SchemaField("user_id", "STRING"),
            bigquery.SchemaField("city", "STRING"),
            bigquery.SchemaField("event_type", "STRING"),
            bigquery.SchemaField("device_carrier", "STRING"),
            bigquery.SchemaField("location_lat", "STRING"),
            bigquery.SchemaField("event_time", "TIMESTAMP"),
            bigquery.SchemaField("platform", "STRING"),
            bigquery.SchemaField("is_attribution_event", "BOOLEAN"),
            bigquery.SchemaField("os_version", "INTEGER"),
            bigquery.SchemaField("paying", "BOOLEAN"),
            bigquery.SchemaField("amplitude_id", "INTEGER"),
            bigquery.SchemaField("device_type", "STRING"),
            bigquery.SchemaField("sample_rate", "STRING"),
            bigquery.SchemaField("device_manufacturer", "STRING"),
            bigquery.SchemaField("start_version", "STRING"),
            bigquery.SchemaField("uuid", "STRING"),
            bigquery.SchemaField("version_name", "STRING"),
            bigquery.SchemaField("location_lng", "STRING"),
            bigquery.SchemaField("server_upload_time", "TIMESTAMP"),
            bigquery.SchemaField("event_id", "INTEGER"),
            bigquery.SchemaField("device_id", "STRING"),
            bigquery.SchemaField("device_family", "STRING"),
            bigquery.SchemaField("os_name", "STRING"),
            bigquery.SchemaField("adid", "STRING"),
            bigquery.SchemaField("amplitude_event_type", "STRING"),
            bigquery.SchemaField("device_brand", "STRING"),
            bigquery.SchemaField("country", "STRING"),
            bigquery.SchemaField("device_model", "STRING"),
            bigquery.SchemaField("language", "STRING"),
            bigquery.SchemaField("region", "STRING"),
            bigquery.SchemaField("session_id", "INTEGER"),
            bigquery.SchemaField("idfa", "STRING")
        ]
    job_config.max_bad_records = 25
    job_config.source_format = 'NEWLINE_DELIMITED_JSON'
    job = bigquery_client.load_table_from_uri(import_json_url(file_json(file)),
                                              dataset_ref.table(table),
                                              job_config=job_config)
    print(job.result())
    assert job.job_type == 'load'
    assert job.state == 'DONE'


def process_line_json(line):
    parsed = json.loads(line)
    if parsed:
        data = {}
        properties = []
        data['client_event_time'] = value_def(parsed['client_event_time'])
        data['ip_address'] = value_def(parsed['ip_address'])
        data['library'] = value_def(parsed['library'])
        data['dma'] = value_def(parsed['dma'])
        data['user_creation_time'] = value_def(parsed['user_creation_time'])
        data['insert_id'] = value_def(parsed['$insert_id'])
        data['schema'] = value_def(parsed['$schema'])
        data['processed_time'] = "{d}".format(d=datetime.utcnow())
        data['client_upload_time'] = value_def(parsed['client_upload_time'])
        data['app'] = value_def(parsed['app'])
        data['user_id'] = value_def(parsed['user_id'])
        data['city'] = value_def(parsed['city'])
        data['event_type'] = value_def(parsed['event_type'])
        data['device_carrier'] = value_def(parsed['device_carrier'])
        data['location_lat'] = value_def(parsed['location_lat'])
        data['event_time'] = value_def(parsed['event_time'])
        data['platform'] = value_def(parsed['platform'])
        data['is_attribution_event'] = value_def(
            parsed['is_attribution_event'])
        data['os_version'] = value_def(parsed['os_version'])
        data['paying'] = value_paying(parsed['paying'])
        data['amplitude_id'] = value_def(parsed['amplitude_id'])
        data['device_type'] = value_def(parsed['device_type'])
        data['sample_rate'] = value_def(parsed['sample_rate'])
        data['device_manufacturer'] = value_def(parsed['device_manufacturer'])
        data['start_version'] = value_def(parsed['start_version'])
        data['uuid'] = value_def(parsed['uuid'])
        data['version_name'] = value_def(parsed['version_name'])
        data['location_lng'] = value_def(parsed['location_lng'])
        data['server_upload_time'] = value_def(parsed['server_upload_time'])
        data['event_id'] = value_def(parsed['event_id'])
        data['device_id'] = value_def(parsed['device_id'])
        data['device_family'] = value_def(parsed['device_family'])
        data['os_name'] = value_def(parsed['os_name'])
        data['adid'] = value_def(parsed['adid'])
        data['amplitude_event_type'] = value_def(
            parsed['amplitude_event_type'])
        data['device_brand'] = value_def(parsed['device_brand'])
        data['country'] = value_def(parsed['country'])
        data['device_model'] = value_def(parsed['device_model'])
        data['language'] = value_def(parsed['language'])
        data['region'] = value_def(parsed['region'])
        data['session_id'] = value_def(parsed['session_id'])
        data['idfa'] = value_def(parsed['idfa'])
        
        for property_value in PROPERTIES:
            for key, value in parsed[property_value].items():
                value = 'True' if value is True else value
                value = 'False' if value is False else value
                properties.append({'property_type': property_value,
                                   'insert_id': value_def(parsed['$insert_id']),
                                   'key': value_def(key),
                                   'value': unicode(value)})

    return json.dumps(data), properties


###############################################################################

def start(YESTERDAY):
    # Perform a CURL request to download the export from Amplitude
    os.system("curl -u " + API_KEY + ":" + API_SECRET + " \
          'https://amplitude.com/api/2/export?start=" + YESTERDAY + "T01&end="
              + YESTERDAY + "T23'  >> amplitude.zip")

    # Unzip the file
    unzip_file('amplitude.zip', 'amplitude')

    # Initiate Google BigQuery
    global bigquery_client
    bigquery_client = bigquery.Client.from_service_account_json(
        'service_account.json')

    # Initiate Google Cloud Storage
    global storage_client
    storage_client = storage.Client.from_service_account_json(
        'service_account.json')
    upload_file_to_gcs('amplitude.zip', YESTERDAY + '.zip', 'export')

    # Loop through all new files, unzip them & remove the .gz
    for file in file_list('.gz'):
        print("Parsing file: {name}".format(name=file))
        unzip_gzip(PATH + file)

        with open(PATH + file_json(file)) as f:
            lines = f.readlines()
        lines = [x.strip() for x in lines if x]

        # Create a new JSON import file
        import_events_file = open(
            "amplitude/{id}/".format(id=ACCOUNT_ID) + file_json(file), "w+")
        import_properties_file = open("amplitude/{id}/".format(id=ACCOUNT_ID) + "properties_" +
                                      file_json(file), "w+")

        # Loop through the JSON lines
        for line in lines:
            events_line, properties_lines = process_line_json(line)
            import_events_file.write(events_line + "\r\n")
            for property_line in properties_lines:
                import_properties_file.write(
                    json.dumps(property_line) + "\r\n")

        # Close the file and upload it for import to Google Cloud Storage
        import_events_file.close()
        import_properties_file.close()
        upload_file_to_gcs("amplitude/{id}/".format(id=ACCOUNT_ID) + file_json(file), file_json(file),
                           'import')
        upload_file_to_gcs("amplitude/{id}/".format(id=ACCOUNT_ID) + "properties_" + file_json(file),
                           "properties_" + file_json(file), 'import')

        # Import data from Google Cloud Storage into Google BigQuery
        global dataset_ref
        dataset_ref = bigquery_client.dataset('amplitude')
        load_into_bigquery(file, 'events$' + YESTERDAY)
        load_into_bigquery("properties_" + file, 'events_properties')

        print("Imported: {file}".format(file=file_json(file)))

        # Remove JSON file
        remove_file(file_json(file), "amplitude/{id}".format(id=ACCOUNT_ID))
        remove_file("properties_" + file_json(file),
                    "amplitude/{id}".format(id=ACCOUNT_ID))

    # Remove the original zipfile
    remove_file("amplitude.zip")
    remove_folder("amplitude")


start(YESTERDAY)
