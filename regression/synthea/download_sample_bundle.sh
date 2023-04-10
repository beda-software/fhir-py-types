set -e

function download_r4() {
	curl --output r4.bundle.zip https://synthetichealth.github.io/synthea-sample-data/downloads/synthea_sample_data_fhir_r4_sep2019.zip
	shasum --algorithm 256 --check r4.bundle.checksumfile
	unzip r4.bundle.zip
}

case "$1" in
	*)
		download_r4
	;;
esac
