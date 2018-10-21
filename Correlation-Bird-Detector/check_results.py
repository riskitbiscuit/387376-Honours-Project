import pandas as pd
from glob import glob
from pandas.io.common import EmptyDataError

all_tests = glob("Detected Peaks/*")

# DO NOT set tolerance to an integer! Use
TOLERANCE = 3.0
TOTAL_EVENTS = 600

columns = ["Bird", "Threshold (# std)", "True Positives", "False Positives", "True Negatives", "False Negatives",
           "False Alarm Rate", "True Positive Rate"]
results = pd.DataFrame(columns=columns)

for testName in all_tests:
    print("Testing " + testName + "...")
    snr_folder_name = testName.split("/")[-1]

    birds = glob(testName + "/*")

    # # Find every second which the detector has an occurance
    # combined_actual = pd.DataFrame()
    # for bird_directory in birds:
    #     csv_file_name = bird_directory.split("/")[-1]
    #     actual_calls_filename = csv_file_name.split("--")[-1] + ".csv"
    #     bird_name = actual_calls_filename.split(".csv")[0]
    #     actual_calls = pd.read_csv("Actual Results/" + actual_calls_filename, header=None)
    #
    #     # TOTAL_EVENTS = TOTAL_EVENTS + len(actual_calls)
    #     combined_actual = combined_actual.append(actual_calls, ignore_index=True)
    #     combined_actual = pd.to_datetime(combined_actual[combined_actual.columns[0]], format="%Y-%m-%dT%H:%M:%S.%f")
    #
    # combined_actual = combined_actual - combined_actual[0]
    # seconds_of_occurrences = combined_actual.dt.total_seconds()
    # seconds_of_occurrences = seconds_of_occurrences.sort_values()
    # seconds_of_occurrences = seconds_of_occurrences.round()
    # TOTAL_EVENTS = seconds_of_occurrences.nunique()

    for bird_directory in birds:
        results = pd.DataFrame(columns=columns)

        csv_file_name = bird_directory.split("/")[-1]
        actual_calls_filename = csv_file_name.split("--")[-1] + ".csv"
        bird_name = actual_calls_filename.split(".csv")[0]

        print("Checking " + bird_name + "...")

        actual_calls_df = pd.read_csv("Actual Results/" + actual_calls_filename, header=None)

        # The names of the files in the bird's directory will be their threshold
        threshold_tests = glob(bird_directory + "/*")

        # # The test with 0 stds will contain all the peaks present in the signal. We need that info
        # try:
        #     zero_test_filename = bird_directory + "/0.0.csv"
        #     all_peaks = pd.read_csv(zero_test_filename, header=None)
        # except IOError:
        #     zero_test_filename = bird_directory + "/0.01.csv"
        #     all_peaks = pd.read_csv(zero_test_filename, header=None)

        # TOTAL_EVENTS = len(all_peaks)

        for threshold_test in threshold_tests:

            true_positive = false_positive = true_negative = false_negative = 0

            # Get the threshold from the filename
            threshold = threshold_test.split("/")[-1]
            threshold = threshold.split(".csv")[0]

            # There is a chance that the csv will be empty (if no detections were made)
            try:
                detected_peaks = pd.read_csv(threshold_test, header=None)
                detected_peaks = detected_peaks.dropna(how="any")
                if len(detected_peaks) is 0:
                    raise EmptyDataError
            except EmptyDataError:
                false_negative = len(actual_calls_df)
                true_negative = TOTAL_EVENTS - false_negative - true_positive - false_positive

                # Calculate true positive rate and false alarm rate
                TPR = float(true_positive) / float(true_positive + false_negative)
                FAR = float(false_positive) / float(false_positive + true_negative)
                results.loc[len(results)] = [bird_name, threshold, true_positive, false_positive, true_negative, false_negative, TPR, FAR]
                continue

            detected_peaks[detected_peaks.columns[0]] = pd.to_datetime(detected_peaks[detected_peaks.columns[0]],
                                                                       format="%Y-%m-%dT%H:%M:%S.%f")
            actual_calls = pd.to_datetime(actual_calls_df[actual_calls_df.columns[0]], format="%Y-%m-%dT%H:%M:%S.%f")

            # The first timestamp is a reference for when the recording started (t=0).
            # Use this to line up the timestamps
            time_diff = detected_peaks[detected_peaks.columns[0]].iloc[0] - actual_calls[0]
            actual_calls = actual_calls + time_diff

            # Delete the reference times (first row)
            actual_calls = actual_calls[1:]
            detected_peaks = detected_peaks.iloc[1:]

            for timestamp in actual_calls:
                start_date = timestamp - pd.Timedelta(seconds=TOLERANCE/2)
                end_date = timestamp + pd.Timedelta(seconds=TOLERANCE/2)

                mask = (detected_peaks[detected_peaks.columns[0]] > start_date) & (detected_peaks[detected_peaks.columns[0]] < end_date)
                masked_times = detected_peaks.loc[mask]

                if len(masked_times) >= 1:
                    true_positive = true_positive + 1
                else:
                    false_negative = false_negative + 1

            false_positive = len(detected_peaks) - true_positive + 1
            true_negative = TOTAL_EVENTS - true_positive - false_positive - false_negative

            if true_negative < 0:
                print("Impossible results! True negative was " + str(true_negative))
                true_negative = 0
            if false_positive < 0:
                print("Impossible results! False positive was " + str(false_positive))
                false_positive = 0

            # if true_negative < 0:
            #     raise ValueError("Impossible results! True negative was " + str(true_negative))
            # if false_positive < 0:
            #     raise ValueError("Impossible results! False positive was " + str(false_positive))

            # Calculate true positive rate and false alarm rate
            TPR = float(true_positive) / float(true_positive + false_negative)
            FAR = float(false_positive) / float(false_positive + true_negative)
            results.loc[len(results)] = [bird_name, threshold, true_positive, false_positive, true_negative, false_negative, FAR, TPR]

        results.to_csv("ROC Data/" + bird_name + ".csv", index=False)


