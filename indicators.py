import pandas as pd
import pandas_ta_classic as ta


def calculate_ema(df: pd.DataFrame, length: int) -> pd.Series:
    return ta.ema(df["close"], length=length)


def calculate_rsi(df: pd.DataFrame, length: int = 14) -> pd.Series:
    return ta.rsi(df["close"], length=length)


def calculate_macd(df: pd.DataFrame):
    macd = ta.macd(df["close"])
    return macd.iloc[:, 0], macd.iloc[:, 1], macd.iloc[:, 2]


def calculate_atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    return ta.atr(df["high"], df["low"], df["close"], length=length)


def calculate_adx(df: pd.DataFrame, length: int = 14) -> pd.Series:
    adx_df = ta.adx(df["high"], df["low"], df["close"], length=length)
    return adx_df.iloc[:, 0]
