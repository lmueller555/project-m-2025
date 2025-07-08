# Project M Trading Dashboard

This repository contains a Streamlit app for visualising a trading strategy using the data in `Updated_Dataset_with_Signals_Ranked_116.csv`.

## Running locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app shows key statistics for the backtest, a portfolio value chart and a table of open positions.

## Deployment on Streamlit Community Cloud

Simply deploy this repository and ensure the main file is set to `streamlit_app.py`. The configuration in `.streamlit/config.toml` applies a dark theme to match the dashboard styling.
