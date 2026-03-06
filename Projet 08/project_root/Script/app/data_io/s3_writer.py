import json
import fsspec


def write_dataframe_to_s3(df, path):

	# Ecrit un dataframe pandas en JSONL dans S3
	df.to_json(
		path,
		orient="records",
		lines=True,
		date_format="iso"
	)



def write_report_to_s3(report, path):

    with fsspec.open(path, "w") as f:
        json.dump(report, f, indent=4)



def write_outputs(clean_df, rejected_df, report, bucket):

    clean_path = f"s3://{bucket}/clean/weather/weather_clean.jsonl"
    rejected_path = f"s3://{bucket}/rejected/weather/weather_rejected.jsonl"
    report_path = f"s3://{bucket}/reports/weather_report.json"

    write_dataframe_to_s3(clean_df, clean_path)
    write_dataframe_to_s3(rejected_df, rejected_path)
    write_report_to_s3(report, report_path)