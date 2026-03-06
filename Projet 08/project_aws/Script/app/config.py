BUCKET_NAME = "s3-p8-construct-test-infra-demo"
S3_PREFIX = "raw/originaux/"

RAWS_PATH = {
	"ichtegem": "s3://s3-p8-construct-test-infra-demo/raw/weather_underground_ichtegem/",
	"lamadeleine": "s3://s3-p8-construct-test-infra-demo/raw/weather_underground_lamadeleine/",
	"infoclimat": "s3://s3-p8-construct-test-infra-demo/raw/infoclimat_json/"
}

CLEAN_PATH = "s3://s3-p8-construct-test-infra-demo/clean/weather/weather_clean.jsonl"

PUBLIC_EXCEL_FILES = {
    "ichtegem": {
        "filename": "Weather Underground - Ichtegem, BE.xlsx",
        "url": "https://s3.eu-west-1.amazonaws.com/course.oc-static.com/projects/922_Data+Engineer/922_P8/Weather+Underground+-+Ichtegem%2C+BE.xlsx",
        "s3_subfolder": "ichtegem"
    },
    "lamadeleine": {
        "filename": "Weather Underground - La Madeleine, FR.xlsx",
        "url": "https://s3.eu-west-1.amazonaws.com/course.oc-static.com/projects/922_Data+Engineer/922_P8/Weather+Underground+-+La+Madeleine%2C+FR.xlsx",
        "s3_subfolder": "lamadeleine"
    }
}