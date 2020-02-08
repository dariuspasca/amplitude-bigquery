# Amplitude > Google Cloud Storage > Google BigQuery
Export your [Amplitude](https://amplitude.com/) data to [Google BigQuery](https://bigquery.cloud.google.com) for big data analysis using [Google Compute Engine](https://cloud.google.com/compute/) virtual machine.
This script will download all events & properties from Amplitude for a given day
Export API, parse the data and prepare a data job for Google BigQuery
by storing the data for backup purposes in [Google Cloud Storage](https://cloud.google.com/storage/).


## Features / Support
* Download data for a full day from Amplitude using the Export API
* Parse the data to match data types in Google BigQuery
* Export new parsed files for a load data job in Google BigQuery
* Store backup data in Google Cloud Storage
* Cleans up after use, all temporary files will be deleted.
