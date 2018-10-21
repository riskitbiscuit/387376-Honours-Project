
def detect_historical_cusum(detections, look_back, threshold, weights=None, look_back_mean=None):
    """
    @param detections: An array of the call occurrences at each day
    @param look_back: How many minutes the algorithm should look back
    @param look_back_mean: How many minutes the algorithm should look back when calculating previous average
    @param weights: An array the same size as look_back which determines how the cusum weights each sample
    @param threshold: The threshold value of
    @return: A declaration of whether change had been detected
    """

    # If we don't have enough historical data, we cannot make a judgement on whether change was detected
    if len(detections) < look_back:
        return False, "Not enough data to detect change "

    if look_back_mean is not None:
        previous_mean = detections[-look_back_mean:-look_back].mean()
    else:
        previous_mean = detections.mean()

    cusum_neg = cusum_pos = 0

    if weights is None:
        # By default, the weights array is zero.
        cusum_pos = sum(abs(detections[-i] - previous_mean) for i in range(1, look_back, 1) if detections[-i] > previous_mean)
        cusum_neg = sum(abs(detections[-i] - previous_mean) for i in range(1, look_back, 1) if detections[-i] < previous_mean)
    else:
        if len(weights) < look_back:
            raise ValueError("The weights array needs to be the same size as look_back. ")
        cusum_pos = sum(abs(detections[-i] - previous_mean) for i in range(1, look_back, 1) if detections[-i] > previous_mean + weights[i])
        cusum_neg = sum(abs(detections[-i] - previous_mean) for i in range(1, look_back, 1) if detections[-i] < previous_mean - weights[i])

    if cusum_pos > threshold:
        return True, "--- Change detected! Average calls went up "
    if cusum_neg > threshold:
        return True, "--- Change detected! Average calls went down "

    return False, "--- No change detected "




