function createTestSoundData()

Fs = 44100;                                             % Sampling frequency (Hz)
outputDuration = 10*60;                                 % Test data duration (s)
gap = 5;                                               % Minimum gap between bursts of the same tone (s)
nUniqueIntervals = 500;                                 % Number of randomly generated gamma distributed time intervals

timestamps = [];                                        % Timestamps made of each call
result = zeros([Fs * outputDuration, 1]);               % Test sound output (audio file)


p = 1;

% Save results to a new session folder
resultFileName = sprintf('%s', datetime('now'));
newSubFolder = sprintf('Results/%s', resultFileName);

% Create this folder if it doesn't exist already.
if ~exist(newSubFolder, 'dir')
  mkdir(newSubFolder);
end

directories = dir('Test Bird Calls');
birdClasses = {directories([directories.isdir]).name};
birdClasses = birdClasses(~ismember(birdClasses,{'.','..'}));

% Choose a random bird class to change
classToChange = char(birdClasses(randi([1 length(birdClasses)])));
birdChanged = '';

% Go through all the bird classes and put one of each in the result
for birdClass = birdClasses   
    timestamps = [];                                        % Reset timestamps

    subdirectory = strcat('Test Bird Calls/', char(birdClass));
    
    directories = dir(subdirectory);
    birds = {directories([directories.isdir]).name};
    birds = birds(~ismember(birds,{'.','..'}));
    
    % Choose a random bird to add to result 
    bird = char(birds(randi([1 length(birds)])));
    
    if (strcmp(birdClass, classToChange)) 
        birdChanged = bird;
    end
        
%     for bird = birds
    % Go into the bird's directory and discover all the samples of that species
    subSubDirectory = strcat(strcat(subdirectory, '/', char(bird)));
    sampleFiles = dir(subSubDirectory);
    samples = {sampleFiles.name};
    samples = samples(~ismember(samples,{'.','..', '.DS_Store', strcat(char(bird), '.mp3')}));

    numberOfSamples = length(samples);

    % Find the duration of the longest sample and read audio into memory
    maxDuration = 0;
    callSamples = cell(1, numberOfSamples);
    i = 1;
    for sample = samples
        filename = char(strcat(subSubDirectory, '/', sample));
        info = audioinfo(filename);


        [toneAudio, toneFreq] = audioread(filename);

        % Check if the frequency of the result track does not match the tone playing
        if (toneFreq ~= Fs)
            frequencyException = MException("createTestSoundData:BadTone", "The tone at " + string(filename) + " had a frequency that did not match the rest of the sequence");
            throw(frequencyException)
        end

        % Only consider mono audio
        toneAudio = toneAudio(:, 1);
        callSamples{i} = toneAudio;

        if (maxDuration < info.Duration) 
            maxDuration = info.Duration;
        end
        i = i+1;
    end

    % Set what the time intervals between calls should be for each 
    averageInterval = maxDuration + gap + 10*rand;
    timeIntervals = randg(averageInterval, nUniqueIntervals, 1);

    t = 0;
    i = 1;
    speciesSound = [];
    
    % First timestamp will be t=0. Need this for reference
    timestamps{i, 1} = string(datestr(t/(24*60*60) + datenum(2000,1,1), 'YYYY-mm-ddTHH:MM:SS.FFF'));

    while (t < outputDuration + maxDuration)
        % Halfway through the output, double the average interval length of one of the tones.
%         if (t > 0.5*outputDuration && strcmp(birdClass, classToChange))
%             timeIntervals = randg(100*averageInterval, nUniqueIntervals, 1);
%         end
        
        % There's a chance that there are not enough intervals for the entire output file.
        % If this is the case, the modulo operator will wrap back to start.
        t_del = timeIntervals(mod(i, nUniqueIntervals)+1);
        n = floor(t_del * Fs);

        % Insert gap of silence between tones
        silence = zeros([n, 1]);

        % Insert tone
        callChosen = callSamples{randi([1 numberOfSamples])};
        toneWithGap = cat(1, silence, callChosen);
        chosenCallLength = length(callChosen)/Fs;

        % Insert tone and silence into species output
        speciesSound = cat(1, speciesSound, toneWithGap);
                
        % Record the timestamp of the tone burst
        if (t + t_del + chosenCallLength/2 <= outputDuration)
            timestamps{i, 1} = string(datestr((t + t_del + chosenCallLength/2)/(24*60*60) + datenum(2000,1,1), 'YYYY-mm-ddTHH:MM:SS.FFF'));
        end
        
        t = t + t_del + chosenCallLength;
        i = i + 1;
    end

    % Superimpose species onto output and write timestamps
    if (length(speciesSound) > Fs*outputDuration) 
        speciesSound = speciesSound(1:Fs*outputDuration);
    end
    result = result + speciesSound;
    cell2csv(char("Results/" + resultFileName + "/" + bird + ".csv"), timestamps);
    
    % Create a text file with the name of the bird that was changed
    if ~exist(char("Results/" + resultFileName + "/" + birdChanged + ".txt"), 'file' )
        fid = fopen(char("Results/" + resultFileName + "/" + birdChanged + ".txt"), 'w');
        fclose(fid);
    end

    p = p+1;
end

% Add noise to output 
for noiseFactor = [0, 10, 25, 50, 80]
    noise = (noiseFactor/1000) * randn(size(result));
    SNR = 10 * log10 (var(result)/var(noise));
    result = result + noise;
    
    % Keep result within output bounds
    result = result / max(abs(result(:)));
    
    outputFilename = sprintf('%.2f', SNR);
    audioOutputFilename = char("Results/" + resultFileName + "/" + outputFilename + ".wav");
    audiowrite(audioOutputFilename, result, Fs);
end 




