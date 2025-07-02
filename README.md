# Project M Trading Dashboard

This repository contains a Streamlit app for visualising a trading strategy using the data in `Updated_Dataset_with_Signals_Ranked.csv`.

## Running locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app shows key statistics for the backtest, a portfolio value chart and a table of open positions.  All realised profits in the backtest are reduced by a 24% short‑term capital gains tax to provide a more realistic simulation.

## Deployment on Streamlit Community Cloud

Simply deploy this repository and ensure the main file is set to `streamlit_app.py`. The configuration in `.streamlit/config.toml` applies a dark theme to match the dashboard styling.
