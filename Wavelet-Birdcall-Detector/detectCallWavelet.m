plotMask = false;
debug = false;
testDirectory = 'Test Bird Calls';
inputDirectory = 'Inputs';


% Get the bird
directories = dir(testDirectory);
birds = {directories.name};
birds = birds(~ismember(birds,{'.','..','.DS_Store'}));

inputs = dir(inputDirectory);
inputSignalNames = {inputs.name};
inputSignalNames = inputSignalNames(~ismember(inputSignalNames,{'.','..','.DS_Store'}));
firstSignal = inputSignalNames(1);

% Save results to a new session folder
outputFileName = strsplit(char(firstSignal), '.wav');
SNR = outputFileName(1);
resultFileName = sprintf('Wavelet %0.2fdB %s', str2double(SNR{1}), datetime('now'));
resultSubFolder = sprintf('Detected Times/%s', resultFileName);

% Create this folder if it doesn't exist already.
if ~exist(resultSubFolder, 'dir')
  mkdir(resultSubFolder);
end

% Go through all the bird classes and put one of each in the result
for birdName = birds
    %% Load the sample and input signal
    [callToDetect,Fs] = audioread(strcat(testDirectory, '/' , char(birdName)));
    [input,FsInput] = audioread(strcat(inputDirectory, '/' , char(firstSignal)));

    if (Fs ~= FsInput)
        disp("Frequencies do not match");
        return;
    end
    
    % Strip to mono audio
    callToDetect = callToDetect(:, 1);
    input = input(:, 1);

    % Bird calls are contained within the 50Hz - 12kHz range. 
    % Compress inputs to frequencies of 0 - 11kHz
    compressFactor = 2;
    callToDetect = decimate(callToDetect,compressFactor);
    input = decimate(input,compressFactor);
    Fs = Fs/compressFactor;

%     %% Import when the calls were actually made
%     datetime = textread('Sulphur-crested Cockatoo (cacatua-galerita).csv', '%s');
%     timeOfCalls = cellfun(@(x) [0 0 0 3600 60 1] * sscanf(x,'%f-%f-%fT%f:%f:%f'), datetime);

    %% Perform the wavelet packet transform
    level = 4;
    callWT = wpdec(callToDetect,level,'sym6');
    inputWT = wpdec(input,level,'sym6');

    [callSpect,~,callF] = wpspectrum(callWT,Fs);
    [inputSpect,~,inputF] = wpspectrum(inputWT,Fs);
    % [callSpect,~,callF] = wpspectrum(callWT,Fs,'plot');
    % inputSpect = callSpect;
    % [inputSpect,~,inputF] = wpspectrum(inputWT,Fs,'plot');

    %% Create binary mask
    meanWS = mean2(callSpect);
    stdWS = std2(callSpect);
    threshold = meanWS + 5 * stdWS;
   
    % Apply the threshold to mask the inputs
    mask = callSpect > threshold;
    colSum = sum(mask, 1);
    fir = find(colSum, 1, 'first');
    las = find(colSum, 1, 'last');

    %% Plot the binary mask of the spectrum
    if (plotMask)
        % Create time axis
        dt = 1/Fs;
        t = 0:dt:length(callToDetect)/Fs-dt;
        
        % Plot
        y = fliplr(callF);
        contour(t, y, mask, 'LineColor', 'black')
        grid on
        xlabel('Time (s)')
        ylabel('Frequency (Hz)')
        ylim([0 8000])
        titleBirdName = strsplit(char(birdName), '(');
        titleBirdName = titleBirdName(1);
        title(strcat('Masked Wavelet Packet Transform of a', {' '}, titleBirdName))
        
        pause
        continue
    end

    %% Correlate mask with spectrum over time
    [~, callLength] = size(callSpect);

    resol = 0.05;                   % Seconds
    nResol = floor(resol * Fs);     % Samples
    [~, inputLength] = size(inputSpect);

    detectorOutput = zeros(floor(inputLength/nResol), 1);
    detectorOutputTimes = zeros(floor(inputLength/nResol), 1);
    i = 1;
    dt = nResol/Fs;
    % Apply mask to input over time, shifting by the resolution (saves computing power)
    % iTau is the time index of the input call. Starts at -callLength for patial comparison

    for iTau = -callLength : nResol : inputLength
        % Section of call over [iStart, iEnd] is compared to input. Allows for partial comparison
        iMaskStart = 1;
        iMaskEnd = callLength;

        iInputStart = iTau + 1;
        iInputEnd = iTau + callLength;

        if (iTau < 0)
            iMaskStart = -iTau + 1;
            iInputStart = 1;
        end
        if (iTau > inputLength - callLength)
            iMaskEnd = inputLength - iTau;
            iInputEnd = inputLength;
        end

        % Take out overlapping sections
        maskPart = mask(:, iMaskStart:iMaskEnd);
        inputPart = inputSpect(:, iInputStart:iInputEnd);

        % Point-multiply mask with input    
        masked = maskPart .* inputPart;

        % The mask result is stored in a resultant vector
        detectorOutput(i) = sum(sum(masked(:)));
        detectedTime = (iTau + callLength/2) * dt;
        
        if detectedTime < 0
            detectedTime = 0;
        end
        
        detectorOutputTimes(i) = detectedTime;
        i = i+1;

    end
    
    %% Find the peaks in the detector signal
    t = 0:dt:(length(detectorOutput)-1)*dt;
    
    %% Go through varying thresholds and generate ROC data
    for nStd = 0:0.5:20
        
        % Find the peaks in the detector signal that are above 2 std from 
        thresh = nStd * std(detectorOutput);
        [pks, pksLoc] = findpeaks(detectorOutput,'MinPeakDistance', 1/dt);
        overThresh = pks > thresh;
        detected = pks(overThresh);
        detectedTimes = detectorOutputTimes(overThresh);

%         %% Plot the correlation
%         figure
%         plot(t, detectorOutput)
%         hold on
%         % Plot the actual data on the same plot
%         scatter(detectedTimes, detected);
% 
%         xlabel('Time (s)') 
%         ylabel('Wavelet Correlation') 
        
        %% Convert seconds to timestamps
        detectedTimeStamps = datestr(datevec(detectedTimes/60/60/24) + [2000 1 1 0 0 0], 'yyyy-mm-ddTHH:MM:SS.FFF');
        
        %% Add t=0 timestamp for reference time
        t0 = datestr(datevec(0) + [2000 1 1 0 0 0], 'yyyy-mm-ddTHH:MM:SS.FFF');
        detectedTimeStamps = [t0; detectedTimeStamps];
        detectedTimeStamps = cellstr(detectedTimeStamps);

        %% Save timestamps to CSV file
        outputFileName = strsplit(char(birdName), '.');
        outputFileName = outputFileName(1);
        
        % Create this folder if it doesn't exist already.
        if ~exist(char(strcat(resultSubFolder, '/', outputFileName)), 'dir')
            mkdir(char(strcat(resultSubFolder, '/', outputFileName)));
        end
        
        filenameAndPath = char(strcat(resultSubFolder, '/', outputFileName, '/', num2str(nStd), '.csv'));
        cell2csv(filenameAndPath, detectedTimeStamps);
    end    
end

