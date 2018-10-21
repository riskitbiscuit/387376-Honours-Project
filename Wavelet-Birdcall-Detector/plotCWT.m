plotMask = false;
debug = false;
testDirectory = 'Test Bird Calls';
inputDirectory = 'Inputs';

% Get the bird names
directories = dir(testDirectory);
birds = {directories.name};
birds = birds(~ismember(birds,{'.','..','.DS_Store'}));

for birdName = birds
    %% Load the sample and input signal
    [callToDetect,Fs] = audioread(strcat(testDirectory, '/' , char(birdName)));
    callToDetect = callToDetect(:, 1);

    titleBirdName = strsplit(char(birdName), '(');
    titleBirdName = titleBirdName(1);
    
    dt = 1/Fs;
    t = 0:dt:length(callToDetect)/Fs-dt;
     
    [wpt,F] = cwt(callToDetect, Fs);
    contour(t, F./1000, abs(wpt))
    grid on
    title(strcat('Wavelet Scalogra m of a', {' '}, titleBirdName, ' Call'))
    xlabel('Time (secs)')
    ylabel('Frequency (kHz)')
    ylim([0 8])

    pause
end



