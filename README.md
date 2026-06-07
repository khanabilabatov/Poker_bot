# Poker_bot
The Quant Bot versions for FullHouse Hackaton
# The Quant Bot

A tournament poker bot developed for the **Full House 2026 Poker Bot Hackathon**.

## Overview

The Quant Bot is a multi-player tournament poker agent designed using quantitative research principles rather than purely rule-based heuristics. The project focuses on decision-making under uncertainty, combining probability, Monte Carlo simulation, expected value optimisation, risk management, and opponent pressure modelling.

The bot was developed through multiple iterations, with competing versions benchmarked against each other across hundreds of thousands of simulated hands. Every major modification was tested empirically before being incorporated into the final strategy.

## Competition Results

* **500+ registered bots**
* **Qualifier I:** Rank 147
* **Qualifier II:** Rank 21
* **Final Stage:** Top 64 Finalist

The bot successfully qualified for the final stage of the competition after progressing through two qualification rounds.

## Core Features

### Preflop Strategy

* Hand strength classification
* Position-aware hand selection
* Blind defence logic
* Multi-level raise and re-raise responses
* Tournament-oriented risk management

### Postflop Strategy

* Monte Carlo equity estimation
* Effective Hand Strength (EHS)
* Positive and negative hand potential
* Board texture analysis
* Draw evaluation
* Range and nut advantage estimation

### Risk Management

* Pot odds calculations
* Fold equity estimation
* Pressure-aware decision making
* Overbet defence
* Weak kicker protection
* Big-pot caution mechanisms

## Development Process

The project followed an iterative quantitative research workflow:

1. Formulate a hypothesis
2. Implement a modification
3. Benchmark against previous versions
4. Analyse results
5. Keep only improvements supported by data

Several versions of the bot were developed throughout the project, including:

* Early equity-based prototypes
* EHS-enhanced versions
* Aggression-focused variants
* Defensive variants
* Kicker-aware tournament versions
* Final competition submissions

Many seemingly reasonable improvements were ultimately discarded after testing revealed a negative impact on long-run profitability.

## Repository Structure

```text
bot.py                     # Main competition version
old.py                     # Previous tournament version
botclaudeimprovements.py   # Experimental branch
```

Additional versions may be included for research, benchmarking, and comparison purposes.

## Technical Components

* Python
* Monte Carlo Simulation
* Expected Value (EV) Optimisation
* Effective Hand Strength (EHS)
* Opponent Pressure Modelling
* Board Texture Analysis
* Tournament Strategy

## Lessons Learned

The most important lesson from this project is that performance improvements must be validated empirically.

Many modifications that appeared theoretically attractive reduced profitability in practice. The strongest versions emerged through systematic experimentation, statistical evaluation, and continuous refinement rather than intuition alone.

## Disclaimer

This project was created for educational and research purposes as part of the Full House 2026 Poker Bot Hackathon. It represents an exploration of quantitative decision-making under uncertainty and should not be interpreted as a production poker system.
