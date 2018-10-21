import pymc as pm
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.ticker as plticker
import pandas as pd

THRESHOLD = 0.05

def detect_markov(filename):
    historical_peaks = pd.read_csv(filename)
    historical_peaks[historical_peaks.columns[0]] = pd.to_datetime(historical_peaks[historical_peaks.columns[0]],
                                                                   format="%Y-%m-%dT%H:%M:%S.%f")

    # Count how many occurrences happened for each day
    daily_counts = historical_peaks[historical_peaks.columns[0]].dt.normalize().value_counts()

    count_data = daily_counts.values
    n_count_data = len(count_data)
    plt.bar(np.arange(n_count_data), count_data, color="#348ABD")
    plt.xlabel("Time (min)")
    plt.ylabel("Count of calls")
    plt.xlim(0, n_count_data);
    plt.savefig("bird_count.pdf", format="pdf", bbox_inches="tight")

    alpha = 1.0 / count_data.mean()
    # Recall count_data is the variable that holds our txt counts

    lambda_1 = pm.Exponential("lambda_1", alpha)
    lambda_2 = pm.Exponential("lambda_2", alpha)
    tau = pm.DiscreteUniform("tau", lower=0, upper=n_count_data)

    @pm.deterministic
    def lambda_(tau=tau, lambda_1=lambda_1, lambda_2=lambda_2):
        out = np.zeros(n_count_data)
        out[:tau] = lambda_1  # lambda before tau is lambda1
        out[tau:] = lambda_2  # lambda after (and including) tau is lambda2
        return out

    # observation = pm.Exponential("obs", lambda_, value=timestamps, observed=True)
    observation = pm.Poisson("obs", lambda_, value=count_data, observed=True)
    model = pm.Model([observation, lambda_1, lambda_2, tau])

    # Mysterious code to be explained in Chapter 3.
    mcmc = pm.MCMC(model)
    mcmc.sample(40000, 10000, 1)

    lambda_1_samples = mcmc.trace('lambda_1')[:]
    lambda_2_samples = mcmc.trace('lambda_2')[:]
    tau_samples = mcmc.trace('tau')[:]

    combined_samples = np.append(lambda_1_samples, lambda_2_samples)

    hist_lambda_1 = np.histogram(lambda_1_samples, bins=50, density=True, range=[combined_samples.min(), combined_samples.max()])
    hist_lambda_2 = np.histogram(lambda_2_samples, bins=50, density=True, range=[combined_samples.min(), combined_samples.max()])

    # Overlap ranges from 0% to 100%. If there was less than a 5% area overlap, we say a change occurred.
    result = []
    overlap = 0
    for x in range(0, 50, 1):
        mini = min(hist_lambda_1[0][x], hist_lambda_2[0][x])
        result.append(mini)
        overlap = overlap + mini

    if overlap <= THRESHOLD:
        return True, tau_samples.mean(), overlap
    else:
        return True, tau_samples.mean(), overlap


def plot_graphs(lambda_1_samples, lambda_2_samples, tau_samples, n_count_data):
    fig = plt.figure()
    fig.subplots_adjust(hspace=0.5)
    ax = fig.add_subplot(311)
    ax.set_autoscaley_on(True)
    loc = plticker.MultipleLocator(base=0.04)    # this locator puts ticks at regular intervals
    ax.yaxis.set_major_locator(loc)
    weights_1 = np.ones_like(lambda_1_samples)/float(len(lambda_1_samples))
    plt.hist(lambda_1_samples, histtype='stepfilled', bins=20, alpha=0.85,
             label="posterior of $\lambda_1$", color="#A60628", weights=weights_1)
    plt.legend(loc="upper left")
    plt.title(r"""Posterior distributions of the variables $\lambda_1,\;\lambda_2,\;\tau$
    """)
    plt.xlim([0, 8])
    plt.ylabel("Probability");
    plt.xlabel("$\lambda_1$ value")

    ax = fig.add_subplot(312)
    ax.set_autoscaley_on(True)
    loc = plticker.MultipleLocator(base=0.04)    # this locator puts ticks at regular intervals
    ax.yaxis.set_major_locator(loc)
    weights_2 = np.ones_like(lambda_2_samples)/float(len(lambda_2_samples))
    plt.hist(lambda_2_samples, histtype='stepfilled', bins=20, alpha=0.85,
             label="posterior of $\lambda_2$", color="#7A68A6", weights=weights_2)
    plt.legend(loc="upper right")
    plt.xlim([0, 8])
    plt.ylabel("Probability");
    plt.xlabel("$\lambda_2$ value")

    fig.add_subplot(313)
    w = 1.0 / tau_samples.shape[0] * np.ones_like(tau_samples)
    plt.hist(tau_samples, bins=n_count_data, alpha=1,
             label=r"posterior of $\tau$",
             color="#467821", weights=w, rwidth=2.)
    plt.xticks(np.arange(n_count_data))
    plt.legend(loc="upper left")
    # plt.ylim([0, .75])
    plt.xlim([40, 60])
    plt.xlabel(r"$\tau$ (min)")
    plt.ylabel("Probability");
    # plt.show()
    fig.savefig("Detect_change.pdf", format="pdf", bbox_inches="tight")


detect_markov("Detected Peaks/XXXXXX.csv")
