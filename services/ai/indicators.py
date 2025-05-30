import logging
import os
from datetime import date, datetime
from time import time
from typing import Literal

import numpy as np
import pandas as pd
import pandas_ta
import requests
import talib
import yfinance as yf

from services.screening.indicators.fractals import FractalCandlestickPattern
from services.screening.indicators.vbp import get_vbp
from utils.helpers import get_db_connection

START_DATE = date(2015, 7, 21)


class Indicators:
    pair_df: pd.DataFrame
    key_level_table: str = "key_levels"
    raw_data: pd.DataFrame

    stop_loss: float = -0.02
    take_profit: float = 0.03

    def __init__(
        self,
        target_type: Literal["take_profit", "stop_loss"],
    ):
        self.target_type = target_type
        self.log = self.get_logger()
        self.db = get_db_connection()
        self.datasets = dict()

    @staticmethod
    def get_logger() -> logging.Logger:
        logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)
        return logging.getLogger("training-dataset")

    def update_table(self, table_name: str):
        pass

    def load_training_dataset(self, pairs: list[str] = None) -> pd.DataFrame:
        pass

    def compute_key_levels(self):
        self.get_fractal_key_levels()
        self.get_vbp_key_levels()
        self.pair_df.drop(
            columns=["open", "high", "low", "close", "volume", "pair_formatted"],
            inplace=True,
        )
        self.update_table(table_name=self.key_level_table)

    def get_fractal_key_levels(self):
        self.log.info("    Adding fractals key levels")
        all_dates = self.pair_df["calendar_dt"].unique().tolist()
        final_df = pd.DataFrame()
        for calendar_date in all_dates:
            date_df = self.pair_df[self.pair_df["calendar_dt"] <= calendar_date]
            fractals = FractalCandlestickPattern(date_df)
            ath = date_df["high"].max()
            atl = date_df["low"].min()
            date_df["fractal_support"] = fractals.get_level("support")
            date_df["fractal_resistance"] = fractals.get_level("resistance")
            date_df = date_df[date_df["calendar_dt"] == calendar_date]
            date_df["distance_to_ath"] = date_df["close"] / ath - 1
            date_df["distance_to_atl"] = date_df["close"] / atl - 1
            final_df = pd.concat([final_df, date_df])
        self.pair_df = final_df

    def get_vbp_key_levels(self):
        self.log.info("    Adding vbp key levels")
        all_dates = self.pair_df["calendar_dt"].unique().tolist()
        final_df = pd.DataFrame()
        for calendar_date in all_dates:
            date_df = self.pair_df[self.pair_df["calendar_dt"] <= calendar_date]
            vbp_df = get_vbp(date_df)
            vbp_df["price"] = vbp_df["price"].astype(float)
            date_df = date_df[date_df["calendar_dt"] == calendar_date]
            # date_df["poc"] = vbp_df.loc[vbp_df["volume"].idxmax()]["price"]

            support_vbp = vbp_df.loc[vbp_df["level_type"] == "support"]
            date_df["poc_support"] = (
                date_df["low"].min()
                if support_vbp.empty
                else support_vbp.loc[support_vbp["volume"].idxmax()]["price"]
            )

            resistance_vbp = vbp_df.loc[vbp_df["level_type"] == "resistance"]
            date_df["poc_resistance"] = (
                date_df["high"].max()
                if resistance_vbp.empty
                else resistance_vbp.loc[resistance_vbp["volume"].idxmax()]["price"]
            )

            final_df = pd.concat([final_df, date_df])
        self.pair_df = final_df

    def add_returns(self, periods: list[int]):
        for period in periods:
            self.pair_df.loc[:, f"{period}d_return"] = self.pair_df["close"].pct_change(
                periods=period
            )

    def add_patterns(self):
        # https://github.com/TA-Lib/ta-lib-python/blob/master/docs/func_groups/pattern_recognition.md
        self.log.info("Adding trading patterns")
        self.add_death_cross_pattern()
        pattern_list = [
            "CDL2CROWS",
            "CDL3BLACKCROWS",
            "CDL3INSIDE",
            "CDL3LINESTRIKE",
            "CDL3OUTSIDE",
            "CDL3STARSINSOUTH",
            "CDL3WHITESOLDIERS",
            "CDLABANDONEDBABY",
            "CDLADVANCEBLOCK",
            "CDLBELTHOLD",
            "CDLBREAKAWAY",
            "CDLCLOSINGMARUBOZU",
            "CDLCONCEALBABYSWALL",
            "CDLCOUNTERATTACK",
            "CDLDARKCLOUDCOVER",
            "CDLDOJI",
            "CDLDOJISTAR",
            "CDLDRAGONFLYDOJI",
            "CDLENGULFING",
            "CDLEVENINGDOJISTAR",
            "CDLEVENINGSTAR",
            "CDLGAPSIDESIDEWHITE",
            "CDLGRAVESTONEDOJI",
            "CDLHAMMER",
            "CDLHANGINGMAN",
            "CDLHARAMI",
            "CDLHARAMICROSS",
            "CDLHIGHWAVE",
            "CDLHIKKAKE",
            "CDLHIKKAKEMOD",
            "CDLHOMINGPIGEON",
            "CDLIDENTICAL3CROWS",
            "CDLINNECK",
            "CDLINVERTEDHAMMER",
            "CDLKICKING",
            "CDLKICKINGBYLENGTH",
            "CDLLADDERBOTTOM",
            "CDLLONGLEGGEDDOJI",
            "CDLLONGLINE",
            "CDLMARUBOZU",
            "CDLMATCHINGLOW",
            "CDLMATHOLD",
            "CDLMORNINGDOJISTAR",
            "CDLMORNINGSTAR",
            "CDLONNECK",
            "CDLPIERCING",
            "CDLRICKSHAWMAN",
            "CDLRISEFALL3METHODS",
            "CDLSEPARATINGLINES",
            "CDLSHOOTINGSTAR",
            "CDLSHORTLINE",
            "CDLSPINNINGTOP",
            "CDLSTALLEDPATTERN",
            "CDLSTICKSANDWICH",
            "CDLTAKURI",
            "CDLTASUKIGAP",
            "CDLTHRUSTING",
            "CDLTRISTAR",
            "CDLUNIQUE3RIVER",
            "CDLUPSIDEGAP2CROWS",
            "CDLXSIDEGAP3METHODS",
        ]
        for pattern in pattern_list:
            self.pair_df[pattern] = getattr(talib, pattern)(
                self.pair_df["open"],
                self.pair_df["high"],
                self.pair_df["low"],
                self.pair_df["close"],
            )

    def add_death_cross_pattern(self):
        self.pair_df["sma_50_below_sma_200"] = (
            self.pair_df["sma_50"] < self.pair_df["sma_200"]
        )
        self.pair_df["death_cross"] = self.pair_df["sma_50_below_sma_200"] & (
            ~self.pair_df["sma_50_below_sma_200"].shift(1, fill_value=False)
        )
        self.pair_df.drop(columns=["sma_50_below_sma_200"], inplace=True)

    def add_greed_and_fear(self):
        if self.datasets.get("greed_and_fear") is None:
            url = "https://api.alternative.me/fng/?limit=0"
            resp = requests.get(url)
            resp_json = resp.json()
            df = pd.DataFrame(
                resp_json["data"],
                columns=[
                    "value",
                    "value_classification",
                    "timestamp",
                    "time_until_update",
                ],
            )
            df = df[["value", "timestamp"]]
            df = df.rename(
                columns={"value": "greed_and_fear_index", "timestamp": "calendar_dt"}
            )
            df["calendar_dt"] = pd.to_datetime(
                df["calendar_dt"].astype(int), unit="s"
            ).dt.date
            self.datasets["greed_and_fear"] = df
        self.pair_df = self.pair_df.merge(
            self.datasets["greed_and_fear"], how="left", on="calendar_dt"
        )
        self.pair_df["greed_and_fear_index"] = self.pair_df[
            "greed_and_fear_index"
        ].astype(float)
        self.custom_ffill(self.datasets["greed_and_fear"], ["greed_and_fear_index"])
        self.pair_df["greed_and_fear_index_change"] = self.pair_df[
            "greed_and_fear_index"
        ].pct_change()

    def hit_target(
        self, next_day_open: float, next_day_low: float, next_day_high: float
    ) -> bool:
        next_day_drawdown = next_day_low / next_day_open - 1
        next_day_peak = next_day_high / next_day_open - 1
        if self.target_type == "take_profit":
            if next_day_peak >= self.take_profit:
                return True
            return False
        elif self.target_type == "stop_loss":
            if next_day_drawdown < self.stop_loss:
                return False
            return True
        raise ValueError("Invalid target type")

    def add_target(self):
        self.pair_df["next_open"] = self.pair_df["open"].shift(-1)
        self.pair_df["next_high"] = self.pair_df["high"].shift(-1)
        self.pair_df["next_low"] = self.pair_df["low"].shift(-1)
        self.pair_df["next_close"] = self.pair_df["close"].shift(-1)
        self.pair_df.insert(
            0,
            f"hit_{self.target_type}",
            self.pair_df.apply(
                lambda row: self.hit_target(
                    next_day_open=row["next_open"],
                    next_day_low=row["next_low"],
                    next_day_high=row["next_high"],
                ),
                axis=1,
            ),
        )
        self.pair_df = self.pair_df.iloc[:-1]
        self.pair_df.drop(
            columns=["next_open", "next_high", "next_low", "next_close"], inplace=True
        )

    @staticmethod
    def classify_trend(row):
        if row["SMA_short"] > row["SMA_mid"] > row["SMA_long"]:
            return 1
        elif row["SMA_short"] < row["SMA_mid"] < row["SMA_long"]:
            return -1
        else:
            return 0

    def add_current_trend(self):
        """
        Define short, mid, and long-term trends based on moving averages
        """
        # Calculate moving averages for short, mid, and long terms
        self.pair_df["SMA_short"] = (
            self.pair_df["close"].rolling(window=50).mean()
        )  # Short-term (50 periods)
        self.pair_df["SMA_mid"] = (
            self.pair_df["close"].rolling(window=100).mean()
        )  # Mid-term (100 periods)
        self.pair_df["SMA_long"] = (
            self.pair_df["close"].rolling(window=200).mean()
        )  # Long-term (200 periods)
        self.pair_df["short_term_trend"] = self.pair_df.apply(
            lambda row: self.classify_trend(row), axis=1
        )
        self.pair_df.drop(columns=["SMA_short", "SMA_mid", "SMA_long"], inplace=True)

    @staticmethod
    def call_coinalyze_api(
        endpoint: str,
        symbol: str,
        from_date_unix: int = None,
        to_date_unix: int = None,
    ) -> pd.DataFrame:
        """https://api.coinalyze.net/v1/doc/"""

        coinalyze_key = os.environ.get("COINALYZE_API_KEY")
        if not from_date_unix:
            from_date_unix = int(
                datetime(
                    START_DATE.year, START_DATE.month, START_DATE.day, 0, 0, 0
                ).timestamp()
            )
        if not to_date_unix:
            to_date_unix = int(time())

        binance_code = ".A"
        symbol += binance_code

        endpoint = (
            f"https://api.coinalyze.net/v1/{endpoint}?"
            f"symbols={symbol}&"
            f"interval=daily&"
            f"from={from_date_unix}&"
            f"to={to_date_unix}"
        )
        if endpoint in ("open-interest-history", "liquidation-history"):
            endpoint += "&convert_to_usd=true"
        resp = requests.get(url=endpoint, headers={"api_key": coinalyze_key})
        resp_json = resp.json()
        df = pd.DataFrame(resp_json[0]["history"])
        df = df.rename(columns={"t": "calendar_dt"})
        df["calendar_dt"] = pd.to_datetime(df["calendar_dt"], unit="s").dt.date
        return df

    def add_open_interest_history(self):
        if self.datasets.get("open_interest") is None:
            df = self.call_coinalyze_api(
                endpoint="open-interest-history", symbol="BTCUSDT_PERP"
            )
            df = df[["calendar_dt", "c"]]
            df = df.rename(columns={"c": "btc_usd_open_interest"})
            self.datasets["open_interest"] = df
        self.pair_df = self.pair_df.merge(
            self.datasets["open_interest"], how="left", on="calendar_dt"
        )

    def add_funding_rate_history(self):
        if self.datasets.get("funding_rates") is None:
            df = self.call_coinalyze_api(
                endpoint="funding-rate-history", symbol="BTCUSDT_PERP"
            )
            df = df[["calendar_dt", "c"]]
            df = df.rename(columns={"c": "btc_usd_funding_rate"})
            df = df[["calendar_dt", "btc_usd_funding_rate"]]
            self.datasets["funding_rates"] = df
        self.pair_df = self.pair_df.merge(
            self.datasets["funding_rates"], how="left", on="calendar_dt"
        )

    def add_liquidations_history(self):
        if self.datasets.get("liquidations") is None:
            liquidations = self.call_coinalyze_api(
                endpoint="liquidation-history", symbol="BTCUSDT_PERP"
            )
            self.datasets["liquidations"] = liquidations.rename(
                columns={"l": "longs_liquidations", "s": "shorts_liquidations"}
            )
        self.pair_df = self.pair_df.merge(
            self.datasets["liquidations"], how="left", on="calendar_dt"
        )

    def get_long_short_ratio_history(self):
        if self.datasets.get("long_short_ratio") is None:
            long_short_ratio = self.call_coinalyze_api(
                endpoint="long-short-ratio-history", symbol="BTCUSDT_PERP"
            )
            long_short_ratio = long_short_ratio[["calendar_dt", "r"]]
            self.datasets["long_short_ratio"] = long_short_ratio.rename(
                columns={"r": "ls_ratio"}
            )
        self.pair_df = self.pair_df.merge(
            self.datasets["long_short_ratio"], how="left", on="calendar_dt"
        )

    @staticmethod
    def days_to_next(df: pd.DataFrame, calendar_dt: date) -> int:
        future_dates = df[df["calendar_dt"] >= calendar_dt]
        future_dates.sort_values(by="calendar_dt", inplace=True)
        if not future_dates.empty:
            return (future_dates.iloc[0]["calendar_dt"] - calendar_dt).days

    def custom_ffill(self, df: pd.DataFrame, columns: list[str]):
        self.pair_df[columns] = self.pair_df[columns].ffill()
        oldest_ohlcv_value = self.pair_df["calendar_dt"].min()
        df = df[df["calendar_dt"] <= oldest_ohlcv_value]
        if not df.empty:
            for col in columns:
                oldest_metric_value = df.iloc[-1][col]
                self.pair_df[col] = self.pair_df[col].fillna(oldest_metric_value)

    def add_bitcoin_dominance(self):
        if self.datasets.get("bitcoin_dominance") is None:
            self.datasets["bitcoin_dominance"] = pd.read_csv(
                "services/ai/assets/bitcoin_dominance.csv"
            )
            self.datasets["bitcoin_dominance"]["calendar_dt"] = pd.to_datetime(
                self.datasets["bitcoin_dominance"]["calendar_dt"], utc=True
            ).dt.date
        self.pair_df = self.pair_df.merge(
            self.datasets["bitcoin_dominance"], how="left", on="calendar_dt"
        )
        self.custom_ffill(self.datasets["bitcoin_dominance"], ["bitcoin_dominance"])

    async def add_btc_returns(self):
        if self.datasets.get("btc_returns") is None:
            btc_returns = self.raw_data[self.raw_data["pair"] == "BTC/USD"]
            btc_returns["btc_return_1d"] = btc_returns["close"].pct_change(periods=1)
            btc_returns["btc_return_7d"] = btc_returns["close"].pct_change(periods=7)
            btc_returns["btc_return_30d"] = btc_returns["close"].pct_change(periods=30)
            self.datasets["btc_returns"] = btc_returns[
                ["calendar_dt", "btc_return_1d", "btc_return_7d", "btc_return_30d"]
            ]
        self.pair_df = self.pair_df.merge(
            self.datasets["btc_returns"], how="left", on="calendar_dt"
        )

    def add_ichimoku_indicators(self):
        ichimoku = pandas_ta.ichimoku(
            self.pair_df["high"],
            self.pair_df["low"],
            self.pair_df["close"],
            lookahead=False,
        )
        ichimoku_lines = ichimoku[0]
        self.pair_df = pd.concat([self.pair_df, ichimoku_lines], axis=1)
        self.pair_df["ichimoku_bullish_trend"] = (
            self.pair_df["close"] > self.pair_df[["ISA_9", "ISB_26"]].max(axis=1)
        ) & (self.pair_df["ISA_9"] > self.pair_df["ISB_26"])
        self.pair_df["ichimoku_bearish_trend"] = (
            self.pair_df["close"] < self.pair_df[["ISA_9", "ISB_26"]].min(axis=1)
        ) & (self.pair_df["ISA_9"] < self.pair_df["ISB_26"])
        self.pair_df["ichimoku_trend"] = self.pair_df.apply(
            lambda row: 1
            if row["ichimoku_bullish_trend"]
            else (-1 if row["ichimoku_bearish_trend"] else 0),
            axis=1,
        )
        self.pair_df.drop(
            columns=["ichimoku_bullish_trend", "ichimoku_bearish_trend"], inplace=True
        )

        self.pair_df["ichimoku_tenkan_kijun_bullish_cross"] = (
            self.pair_df["ITS_9"] > self.pair_df["IKS_26"]
        ) & (self.pair_df["ITS_9"].shift(1) <= self.pair_df["IKS_26"].shift(1))
        self.pair_df["ichimoku_tenkan_kijun_bearish_cross"] = (
            self.pair_df["ITS_9"] < self.pair_df["IKS_26"]
        ) & (self.pair_df["ITS_9"].shift(1) >= self.pair_df["IKS_26"].shift(1))
        self.pair_df["ichimoku_tenkan_signal"] = self.pair_df.apply(
            lambda row: 1
            if row["ichimoku_tenkan_kijun_bullish_cross"]
            else (-1 if row["ichimoku_tenkan_kijun_bearish_cross"] else 0),
            axis=1,
        )
        self.pair_df.drop(
            columns=[
                "ichimoku_tenkan_kijun_bullish_cross",
                "ichimoku_tenkan_kijun_bearish_cross",
            ],
            inplace=True,
        )

        self.pair_df["ichimoku_cloud_bullish_cross"] = (
            self.pair_df["close"] > self.pair_df[["ISA_9", "ISB_26"]].max(axis=1)
        ) & (
            self.pair_df["close"].shift(1)
            <= self.pair_df[["ISA_9", "ISB_26"]].max(axis=1).shift(1)
        )
        self.pair_df["ichimoku_cloud_bearish_cross"] = (
            self.pair_df["close"] < self.pair_df[["ISA_9", "ISB_26"]].min(axis=1)
        ) & (
            self.pair_df["close"].shift(1)
            >= self.pair_df[["ISA_9", "ISB_26"]].min(axis=1).shift(1)
        )
        self.pair_df["ichimoku_cloud_signal"] = self.pair_df.apply(
            lambda row: 1
            if row["ichimoku_cloud_bullish_cross"]
            else (-1 if row["ichimoku_cloud_bearish_cross"] else 0),
            axis=1,
        )
        self.pair_df["distance_to_ichimoku_cloud_bottom"] = (
            self.pair_df["close"] / self.pair_df["ISB_26"] - 1
        )
        self.pair_df["distance_to_ichimoku_cloud_top"] = (
            self.pair_df["close"] / self.pair_df["ISA_9"] - 1
        )
        self.pair_df.drop(
            columns=[
                "ITS_9",
                "IKS_26",
                "ISB_26",
                "ISA_9",
                "ichimoku_cloud_bullish_cross",
                "ichimoku_cloud_bearish_cross",
            ],
            inplace=True,
        )

    def add_adx_signals(self, adx_period: int = 14, adx_threshold: int = 25):
        """
        Implement ADX strategy with +DI/-DI crossovers
        Returns DataFrame with signals: 1 (buy), -1 (sell), 0 (neutral)
        """
        # Calculate ADX and DI values
        self.pair_df["adx"] = talib.ADX(
            self.pair_df["high"],
            self.pair_df["low"],
            self.pair_df["close"],
            timeperiod=adx_period,
        )
        self.pair_df["plus_di"] = talib.PLUS_DI(
            self.pair_df["high"],
            self.pair_df["low"],
            self.pair_df["close"],
            timeperiod=adx_period,
        )
        self.pair_df["minus_di"] = talib.MINUS_DI(
            self.pair_df["high"],
            self.pair_df["low"],
            self.pair_df["close"],
            timeperiod=adx_period,
        )
        # Generate signals (using vectorized operations for speed)
        conditions = [
            # Strong trend with bullish crossover
            (self.pair_df["adx"] > adx_threshold)
            & (self.pair_df["plus_di"] > self.pair_df["minus_di"]),
            # Strong trend with bearish crossover
            (self.pair_df["adx"] > adx_threshold)
            & (self.pair_df["minus_di"] > self.pair_df["plus_di"]),
            # Weak trend/no trend
            (self.pair_df["adx"] < 20),
        ]
        choices = [1, -1, 0]
        self.pair_df["adx_signal"] = np.select(conditions, choices, default=np.nan)
        # Forward fill to maintain position until reversal
        self.pair_df["adx_signal"].ffill(inplace=True)
        self.pair_df.drop(columns=["adx", "plus_di", "minus_di"], inplace=True)

    def add_sar_signal(self):
        self.pair_df["sar"] = talib.SAR(self.pair_df["high"], self.pair_df["low"])
        self.pair_df["sar_buy_signal"] = (
            self.pair_df["close"] > self.pair_df["sar"]
        ) & (self.pair_df["close"].shift(1) <= self.pair_df["sar"].shift(1))
        self.pair_df["sar_sell_signal"] = (
            self.pair_df["close"] < self.pair_df["sar"]
        ) & (self.pair_df["close"].shift(1) >= self.pair_df["sar"].shift(1))
        self.pair_df["sar_signal"] = self.pair_df.apply(
            lambda row: 1
            if row["sar_buy_signal"]
            else (-1 if row["sar_sell_signal"] else 0),
            axis=1,
        )
        self.pair_df.drop(
            columns=["sar_buy_signal", "sar_sell_signal", "sar"], inplace=True
        )

    def add_trend_indicators(self):
        """
        - SMA 50
        - SMA 200
        - EMA 100
        - Current Trend
        - Is Death Cross

        - SAR Signal: Buy when price crosses above SAR, Sell when price crosses below SAR
        - Ichimoku Trend: Bullish when close > max(ISA, ISB), Bearish when close < min(ISA, ISB)
        - Ichimoku Tenkan-Kijun Signal: Buy when Tenkan crosses above Kijun, Sell when Tenkan crosses below Kijun
        - Ichimoku Cloud Signal: Buy when close > max(ISA, ISB) and close > prev max(ISA, ISB), Sell when close < min(ISA, ISB) and close < prev min(ISA, ISB)
         - ADX Signal: Buy when +DI > -DI and ADX > 25, Sell when -DI > +DI and ADX > 25

        """
        self.log.info("Adding trend indicators")
        self.pair_df["sma_50"] = talib.SMA(self.pair_df["close"], timeperiod=50)
        self.pair_df["sma_200"] = talib.SMA(self.pair_df["close"], timeperiod=200)
        self.pair_df["ema_100"] = talib.EMA(self.pair_df["close"], timeperiod=100)
        self.add_current_trend()

        self.add_sar_signal()
        self.add_ichimoku_indicators()
        self.add_adx_signals()

    def add_price_indicators(self):
        """
        - Return 1d
        - Return 7d
        - Return 30d
        - Next fractal resistance
        - Has crossed previous day fractal resistance
        - Next fractal support
        - Has crossed previous day fractal support
        - Distance to ATL and ATH
        """
        self.log.info("Adding price indicators")
        self.add_returns(periods=[1, 7, 30])
        self.pair_df["has_crossed_fractal_resistance"] = (
            self.pair_df["high"]
            > self.pair_df["fractal_resistance"]  # .shift(1)  # prev day resistance
        )
        self.pair_df["has_crossed_fractal_support"] = (
            self.pair_df["low"] < self.pair_df["fractal_support"]
        )  # .shift(1)  # prev day support
        distance_to_close_metrics = [
            "fractal_resistance",
            "fractal_support",
        ]
        for metric in distance_to_close_metrics:
            self.pair_df[f"distance_to_{metric}"] = (
                self.pair_df["close"] / self.pair_df[metric] - 1
            )
        self.pair_df.drop(
            columns=["fractal_resistance", "fractal_support"], inplace=True
        )

    def add_derivatives_indicators(self):
        """
        - BTC/USD perp open interest
        - BTC/USD perp funding rate
        - BTC/USD liquidations
        - BTC/USD l/s ratio
        """
        self.log.info("Adding derivatives indicators")

        self.add_open_interest_history()
        self.add_funding_rate_history()
        self.add_liquidations_history()
        self.get_long_short_ratio_history()

    def add_macd_indicators(self):
        self.pair_df["macd"], self.pair_df["macd_signal"], self.pair_df["macd_hist"] = (
            talib.MACD(self.pair_df["close"])
        )
        self.pair_df["macd_bullish_signal"] = (
            self.pair_df["macd"] > self.pair_df["macd_signal"]
        ) & (self.pair_df["macd"].shift(1) < self.pair_df["macd_signal"].shift(1))
        self.pair_df["macd_bearish_signal"] = (
            self.pair_df["macd"] < self.pair_df["macd_signal"]
        ) & (self.pair_df["macd"].shift(1) > self.pair_df["macd_signal"].shift(1))
        self.pair_df["macd_signal"] = self.pair_df.apply(
            lambda row: 1
            if row["macd_bullish_signal"]
            else (-1 if row["macd_bearish_signal"] else 0),
            axis=1,
        )
        self.pair_df.drop(
            columns=["macd_bullish_signal", "macd_bearish_signal", "macd"], inplace=True
        )
        self.pair_df["macd_hist"] = self.pair_df["macd_hist"].pct_change()

    def add_stochastic_signal(self):
        self.pair_df["stoch_k"], self.pair_df["stoch_d"] = talib.STOCH(
            self.pair_df["high"], self.pair_df["low"], self.pair_df["close"]
        )
        self.pair_df["stochastic_overbought"] = self.pair_df["stoch_k"] > 80
        self.pair_df["stochastic_oversold"] = self.pair_df["stoch_k"] < 20
        self.pair_df["stochastic_signal"] = self.pair_df.apply(
            lambda row: 1
            if row["stochastic_overbought"]
            else (-1 if row["stochastic_oversold"] else 0),
            axis=1,
        )
        self.pair_df.drop(
            columns=[
                "stoch_k",
                "stoch_d",
                "stochastic_overbought",
                "stochastic_oversold",
            ],
            inplace=True,
        )

    def add_momentum_indicators(self):
        """
        - RSI
        - MACD Bullish Signal: MACD line crosses above the signal line.
        - MACD Bearish Signal: MACD line crosses below the signal line.
        - MACD Histogram expansion: Identifies trend acceleration via histogram expansion.
        - Stochastic Overbought: Stochastic K above 80.
        - Stochastic Oversold: Stochastic K below 20.
        """
        self.log.info("Adding momentum indicators")
        self.pair_df["rsi"] = talib.RSI(self.pair_df["close"])
        self.add_macd_indicators()
        self.add_stochastic_signal()

    def add_vix(self):
        vix = self.call_yahoo_finance_api(symbol="^VIX", return_only=False)
        self.pair_df = self.pair_df.merge(vix, how="left", on="calendar_dt")
        vix_cols = vix.columns.tolist()
        self.custom_ffill(vix, vix_cols)

    def add_bollinger_indicators(self):
        (
            self.pair_df["bollinger_upper"],
            self.pair_df["bollinger_middle"],
            self.pair_df["bollinger_lower"],
        ) = talib.BBANDS(self.pair_df["close"])
        self.pair_df["bollinger_spread"] = (
            self.pair_df["bollinger_upper"] / self.pair_df["bollinger_lower"] - 1
        )
        self.pair_df["distance_to_bollinger_upper"] = (
            self.pair_df["close"] / self.pair_df["bollinger_upper"] - 1
        )
        self.pair_df["distance_to_bollinger_lower"] = (
            self.pair_df["close"] / self.pair_df["bollinger_lower"] - 1
        )
        self.pair_df["distance_to_bollinger_middle"] = (
            self.pair_df["close"] / self.pair_df["bollinger_middle"] - 1
        )
        self.pair_df.drop(
            columns=["bollinger_upper", "bollinger_middle", "bollinger_lower"],
            inplace=True,
        )

    def add_volatility_indicators(self):
        """
        - Historical Volatility
        - High-Low Volatility (Parkinson's Volatility)
        - Fear & Greed Index
        - Fear & Greed Index 1d change
        - VIX
        - Bollinger Bands
        """
        self.log.info("Adding volatility indicators")
        self.pair_df["historical_volatility"] = self.pair_df["1d_return"].rolling(
            window=14
        ).std() * np.sqrt(252)  # Annualized
        self.pair_df["high_low_volatility"] = np.sqrt(
            (1 / (4 * np.log(2)))
            * self.pair_df[["high", "low"]]
            .apply(lambda x: np.log(x["high"] / x["low"]) ** 2, axis=1)
            .rolling(window=14)
            .mean()
        )
        self.add_greed_and_fear()
        self.add_vix()
        self.add_bollinger_indicators()

    def add_obv_indicators(self):
        self.pair_df["obv"] = talib.OBV(
            self.pair_df["close"], self.pair_df["usd_volume"]
        )
        """Volume-confirmed breakouts with ATR filtering"""
        volatility_window = 14
        # Calculate ATR for volatility adjustment
        self.pair_df["atr"] = talib.ATR(
            self.pair_df["high"],
            self.pair_df["low"],
            self.pair_df["close"],
            volatility_window,
        )

        # OBV momentum
        self.pair_df["obv_change"] = self.pair_df["obv"].pct_change(periods=3)

        # Breakout signals
        long_condition = (
            (self.pair_df["close"] > self.pair_df["high"].shift(1))
            & (self.pair_df["obv_change"] > 0.05)
            & (self.pair_df["atr"] > self.pair_df["atr"].rolling(50).mean())
        )
        short_condition = (
            (self.pair_df["close"] < self.pair_df["low"].shift(1))
            & (self.pair_df["obv_change"] < -0.05)
            & (self.pair_df["atr"] > self.pair_df["atr"].rolling(50).mean())
        )
        self.pair_df["obv_breakout_signal"] = np.select(
            [long_condition, short_condition], [1, -1], default=0
        )
        self.pair_df.drop(columns=["obv", "atr"], inplace=True)

    def add_volume_indicators(self):
        """
        - Volume SMA 50
        - Point of Control
        - Next PoC resistance
        - Has crossed previous day PoC resistance
        - Next PoC support
        - Has crossed previous day PoC support
        - On Balance Volume

        """
        self.log.info("Adding volume indicators")
        self.pair_df["volume_sma_50"] = talib.SMA(
            self.pair_df["usd_volume"], timeperiod=50
        )
        self.pair_df["has_crossed_poc_resistance"] = (
            self.pair_df["high"] > self.pair_df["poc_resistance"]  # .shift(1)
        )
        self.pair_df["has_crossed_poc_support"] = (
            self.pair_df["low"] < self.pair_df["poc_support"]  # .shift(1)
        )
        distance_to_close_metrics = [
            "poc_support",
            "poc_resistance",
        ]
        for metric in distance_to_close_metrics:
            self.pair_df[f"distance_to_{metric}"] = (
                self.pair_df["close"] / self.pair_df[metric] - 1
            )
        self.pair_df.drop(columns=["poc_support", "poc_resistance"], inplace=True)
        self.add_obv_indicators()

    async def add_btc_eth_correlation(self):
        if self.datasets.get("btc_eth_correlation") is None:
            eth_usd = self.raw_data[self.raw_data["pair"] == "ETH/USD"]
            eth_usd["eth_return_1d"] = eth_usd["close"].pct_change(periods=1)
            btc_usd = self.raw_data[self.raw_data["pair"] == "BTC/USD"]
            btc_usd["btc_return_1d"] = btc_usd["close"].pct_change(periods=1)
            df = pd.merge(
                btc_usd[["calendar_dt", "btc_return_1d"]],
                eth_usd[["calendar_dt", "eth_return_1d"]],
                on="calendar_dt",
            )
            df["btc_eth_correlation"] = (
                df["btc_return_1d"].rolling(window=14).corr(df["eth_return_1d"])
            )
            df = df[["calendar_dt", "btc_eth_correlation"]]
            eth_usd.drop(columns=["eth_return_1d"], inplace=True)
            self.datasets["btc_eth_correlation"] = df
        self.pair_df = self.pair_df.merge(
            self.datasets["btc_eth_correlation"], how="left", on="calendar_dt"
        )

    def call_yahoo_finance_api(
        self, symbol: str, return_only: bool = True
    ) -> pd.DataFrame:
        symbol_mapping = {
            "GC=F": "gold",
            "^IXIC": "nasdaq",
            "^VIX": "vix",
        }
        asset = symbol_mapping.get(symbol)
        if self.datasets.get(asset) is not None:
            return self.datasets[asset]
        df = yf.download(
            symbol, start=START_DATE.isoformat(), interval="1d", multi_level_index=False
        )
        df.insert(0, "calendar_dt", df.index)
        df["calendar_dt"] = df["calendar_dt"].dt.date
        df = df.reset_index(drop=True)
        asset_name = symbol_mapping.get(symbol, symbol)
        if not asset_name:
            raise ValueError("Symbol not recognized")
        df[f"{asset_name}_1d_return"] = df["Close"].pct_change(periods=1)
        df = df.rename(columns={"Close": asset_name})
        cols = ["calendar_dt", f"{asset_name}_1d_return", asset_name]
        if return_only:
            cols.remove(asset_name)
        df = df[cols]
        df["calendar_dt"] = pd.to_datetime(df["calendar_dt"], format="%d/%m/%Y").dt.date
        self.datasets[asset] = df
        return df

    async def add_market_beta_indicators(self):
        """
        - BTC dominance
        - BTC/USD return 1d
        - BTC/USD return 7d
        - BTC/USD return 30d
        - BTC/ETH correlation
        - Gold return 1d
        - NASDAQ return 1d
        """
        self.log.info("Adding market/beta indicators")
        self.add_bitcoin_dominance()
        await self.add_btc_returns()
        await self.add_btc_eth_correlation()
        for asset, symbol in dict(gold="GC=F", nasdaq="^IXIC").items():
            asset_df = self.call_yahoo_finance_api(symbol=symbol)
            self.pair_df = self.pair_df.merge(asset_df, how="left", on="calendar_dt")
            self.pair_df[f"{asset}_1d_return"].fillna(0, inplace=True)

    def add_macro_indicators(self):
        """
        - Current US non-form payroll
        - Days to next US non-form payroll
        - Current FOMC rate
        - Days to next FOMC decision
        """
        self.log.info("Adding macro indicators")
        for indicator in ("nfp", "fed_decisions"):
            if self.datasets.get(indicator) is None:
                self.datasets[indicator] = pd.read_csv(
                    f"services/ai/assets/{indicator}.csv"
                )
                self.datasets[indicator].iloc[:, 1:] = (
                    self.datasets[indicator].iloc[:, 1:].astype(float)
                )
            self.datasets[indicator]["calendar_dt"] = pd.to_datetime(
                self.datasets[indicator]["calendar_dt"]
            ).dt.date
            cols = self.datasets[indicator].columns.tolist()
            self.pair_df = self.pair_df.merge(
                self.datasets[indicator], how="left", on="calendar_dt"
            )
            self.custom_ffill(self.datasets[indicator], cols)
            self.pair_df[f"days_to_next_{indicator}"] = self.pair_df.apply(
                lambda row: self.days_to_next(
                    self.datasets[indicator], row["calendar_dt"]
                ),
                axis=1,
            )

    def add_seasonality(self):
        """
        - day of the week
        - month of the year
        - days to quarter end
        """
        self.log.info("Adding seasonality indicators")
        self.pair_df["calendar_dt"] = pd.to_datetime(
            self.pair_df["calendar_dt"], utc=True
        )
        self.pair_df["day_of_week"] = self.pair_df["calendar_dt"].dt.dayofweek
        self.pair_df["month_of_year"] = self.pair_df["calendar_dt"].dt.month
        self.pair_df["days_to_quarter_end"] = (
            pd.to_datetime(
                self.pair_df["calendar_dt"].dt.to_period("Q").dt.end_time, utc=True
            )
            - self.pair_df["calendar_dt"]
        ).dt.days

    async def add_indicators(self) -> pd.DataFrame:
        data_with_indicators = pd.DataFrame()
        for pair in self.raw_data["pair"].unique().tolist():
            self.log.info(f"    Adding indicators for {pair}")
            self.pair_df = self.raw_data[self.raw_data["pair"] == pair]

            self.add_target()

            self.add_trend_indicators()
            self.add_price_indicators()
            self.add_derivatives_indicators()
            self.add_momentum_indicators()
            self.add_volatility_indicators()
            self.add_volume_indicators()
            await self.add_market_beta_indicators()
            self.add_macro_indicators()
            self.add_seasonality()
            self.add_patterns()
            if self.pair_df["calendar_dt"].duplicated().any():
                raise Exception("Duplicates found!")
            data_with_indicators = pd.concat([data_with_indicators, self.pair_df])
        del self.pair_df
        return data_with_indicators
