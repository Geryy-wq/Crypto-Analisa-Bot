from flask import Flask, request, jsonify, render_template, send_from_directory
import ccxt
import pandas as pd
import pandas_ta as ta
import os
import requests
import numpy as np
from datetime import datetime, timedelta
import time
import threading
import json
import traceback
import asyncio

app = Flask(__name__)

# Import Alert System
from alert_system import alert_system

# Global variables untuk caching dan real-time updates
cache_data = {}
alert_history = []

# Import Telegram bot
try:
    from telegram_bot import start_telegram_bot
    telegram_bot = None
except ImportError:
    print(
        "⚠️ Telegram bot tidak dapat diimport. Install python-telegram-bot terlebih dahulu."
    )
    telegram_bot = None


def validate_symbol(symbol_input):
    return symbol_input.upper().replace('-', '/')


VALID_TIMEFRAMES = [
    '1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d',
    '3d', '1w', '1M'
]


def calculate_fibonacci_levels(high, low):
    """Hitung level Fibonacci retracement"""
    diff = high - low
    levels = {
        'level_0': high,

def generate_comprehensive_summary(analysis_data):
    """Generate human-readable comprehensive analysis summary"""
    try:
        # Extract key data
        symbol = analysis_data.get('symbol', 'N/A')
        price = analysis_data.get('close_price', 0)
        
        # Get sentiment score
        sentiment = analysis_data.get('signals', {}).get('market_sentiment_score', {})
        sentiment_score = sentiment.get('score', 50)
        sentiment_label = sentiment.get('label', 'Neutral')
        
        # Get key indicators
        momentum = analysis_data.get('technical_indicators', {}).get('momentum', {})
        trend = analysis_data.get('technical_indicators', {}).get('trend', {})
        ma = analysis_data.get('technical_indicators', {}).get('moving_averages', {})
        
        # Generate summary
        summary = {
            "overall_assessment": {
                "sentiment": sentiment_label,
                "confidence": sentiment.get('confidence', 'Medium'),
                "score": f"{sentiment_score:.1f}/100",
                "recommendation": get_trading_recommendation(sentiment_score)
            },
            
            "key_levels": {
                "current_price": f"${price:,.2f}",
                "nearest_support": analysis_data.get('support_resistance', {}).get('nearest_support'),
                "nearest_resistance": analysis_data.get('support_resistance', {}).get('nearest_resistance'),
                "pivot_point": analysis_data.get('pivot_points', {}).get('pivot')
            },
            
            "momentum_status": {
                "rsi_14": momentum.get('rsi_14'),
                "rsi_signal": classify_rsi(momentum.get('rsi_14')),
                "macd_trend": analysis_data.get('signals', {}).get('trend_analysis', {}).get('macd_trend', 'Neutral'),
                "trend_strength": analysis_data.get('signals', {}).get('trend_analysis', {}).get('trend_strength', 'Weak')
            },
            
            "moving_average_summary": {
                "short_term": "Bullish" if price > ma.get('sma_20', 0) else "Bearish" if ma.get('sma_20') else "N/A",
                "medium_term": "Bullish" if price > ma.get('sma_50', 0) else "Bearish" if ma.get('sma_50') else "N/A",
                "long_term": "Bullish" if price > ma.get('sma_200', 0) else "Bearish" if ma.get('sma_200') else "N/A"
            },
            
            "risk_assessment": {
                "volatility": analysis_data.get('signals', {}).get('volatility_analysis', {}).get('volatility_level', 'Normal'),
                "volume_trend": analysis_data.get('signals', {}).get('volume_analysis_detailed', {}).get('volume_trend', 'Normal'),
                "bb_position": analysis_data.get('signals', {}).get('volatility_analysis', {}).get('bb_position', 'Middle')
            }
        }
        
        return summary
        
    except Exception as e:
        return {"error": f"Failed to generate summary: {str(e)}"}

def get_trading_recommendation(sentiment_score):
    """Generate trading recommendation based on sentiment score"""
    if sentiment_score >= 75:
        return "Strong Buy - Multiple bullish signals aligned"
    elif sentiment_score >= 65:
        return "Buy - Bullish momentum present"
    elif sentiment_score >= 55:
        return "Weak Buy - Slight bullish bias"
    elif sentiment_score >= 45:
        return "Hold - Mixed signals, wait for clarity"
    elif sentiment_score >= 35:
        return "Weak Sell - Slight bearish bias"
    elif sentiment_score >= 25:
        return "Sell - Bearish momentum present"
    else:
        return "Strong Sell - Multiple bearish signals aligned"

def classify_rsi(rsi_value):
    """Classify RSI reading"""
    if not rsi_value:
        return "N/A"
    if rsi_value > 80:
        return "Extremely Overbought"
    elif rsi_value > 70:
        return "Overbought"
    elif rsi_value > 60:
        return "Bullish"
    elif rsi_value > 40:
        return "Neutral"
    elif rsi_value > 30:
        return "Bearish"
    elif rsi_value > 20:
        return "Oversold"
    else:
        return "Extremely Oversold"


        'level_23.6': high - (diff * 0.236),
        'level_38.2': high - (diff * 0.382),
        'level_50': high - (diff * 0.5),
        'level_61.8': high - (diff * 0.618),
        'level_78.6': high - (diff * 0.786),
        'level_100': low
    }
    return levels


def calculate_pivot_points(high, low, close):
    """Hitung pivot points dan support/resistance levels"""
    pivot = (high + low + close) / 3

    r1 = (2 * pivot) - low
    s1 = (2 * pivot) - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    r3 = high + 2 * (pivot - low)
    s3 = low - 2 * (high - pivot)

    return {
        'pivot': pivot,
        'resistance_1': r1,
        'resistance_2': r2,
        'resistance_3': r3,
        'support_1': s1,
        'support_2': s2,
        'support_3': s3
    }


def calculate_support_resistance(df, period=20):
    """Hitung level support dan resistance berdasarkan high/low"""
    try:
        if len(df) < period:
            return {
                "error": "Insufficient data for support/resistance calculation"
            }

        # Ambil data high dan low
        highs = df['high'].tail(period)
        lows = df['low'].tail(period)

        # Hitung resistance levels (dari high terbesar)
        resistance_levels = sorted(highs.nlargest(5).values, reverse=True)

        # Hitung support levels (dari low terkecil)
        support_levels = sorted(lows.nsmallest(5).values)

        # Current price untuk referensi
        current_price = df.iloc[-1]['close']

        # Filter levels yang masuk akal (dalam range tertentu)
        price_range = current_price * 0.15  # 15% dari harga current

        valid_resistance = [
            r for r in resistance_levels
            if current_price < r <= current_price + price_range
        ]
        valid_support = [
            s for s in support_levels
            if current_price - price_range <= s < current_price
        ]

        return {
            'current_price': current_price,
            'resistance_levels': valid_resistance[:3],  # Top 3
            'support_levels': valid_support[:3],  # Top 3
            'nearest_resistance':
            min(valid_resistance) if valid_resistance else None,
            'nearest_support': max(valid_support) if valid_support else None
        }

    except Exception as e:
        return {"error": f"Error calculating support/resistance: {str(e)}"}


def get_onchain_data(symbol):
    """Ambil data on-chain dari API blockchain explorer"""
    try:
        # Untuk Bitcoin
        if 'BTC' in symbol:
            # Menggunakan multiple endpoints untuk data Bitcoin yang lebih lengkap
            btc_data = {}

            # 1. Data dari Blockchain.info
            try:
                url = "https://api.blockchain.info/stats"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    btc_data.update({
                        "network_hash_rate":
                        data.get('hash_rate', 0),
                        "difficulty":
                        data.get('difficulty', 0),
                        "total_bitcoins":
                        data.get('totalbc', 0) / 100000000,
                        "unconfirmed_count":
                        data.get('n_btc_mined', 0),
                        "mempool_size":
                        data.get('mempool_size', 0)
                    })
            except:
                pass

            # 2. Data dari Mempool.space (untuk informasi mempool yang lebih akurat)
            try:
                mempool_url = "https://mempool.space/api/mempool"
                mempool_response = requests.get(mempool_url, timeout=10)
                if mempool_response.status_code == 200:
                    mempool_data = mempool_response.json()
                    btc_data.update({
                        "mempool_transactions":
                        mempool_data.get('count', 0),
                        "mempool_size_bytes":
                        mempool_data.get('vsize', 0),
                        "mempool_fees":
                        mempool_data.get('total_fee', 0)
                    })
            except:
                pass

            # 3. Data network dari Mempool.space
            try:
                network_url = "https://mempool.space/api/v1/difficulty-adjustment"
                network_response = requests.get(network_url, timeout=10)
                if network_response.status_code == 200:
                    network_data = network_response.json()
                    btc_data.update({
                        "difficulty_change":
                        network_data.get('difficultyChange', 0),
                        "estimated_retarget_date":
                        network_data.get('estimatedRetargetDate', 0),
                        "blocks_until_retarget":
                        network_data.get('remainingBlocks', 0)
                    })
            except:
                pass

            return btc_data if btc_data else {
                "error": "Gagal mengambil data Bitcoin"
            }

        # Untuk Ethereum menggunakan Etherscan API
        elif 'ETH' in symbol:
            etherscan_api_key = os.getenv('ETHERSCAN_API_KEY')
            if not etherscan_api_key:
                return {
                    "error": "ETHERSCAN_API_KEY tidak ditemukan di secrets"
                }

            eth_data = {}

            # 1. ETH Total Supply
            try:
                supply_url = f"https://api.etherscan.io/api?module=stats&action=ethsupply&apikey={etherscan_api_key}"
                supply_response = requests.get(supply_url, timeout=10)
                if supply_response.status_code == 200:
                    supply_data = supply_response.json()
                    if supply_data['status'] == '1':
                        eth_data['total_supply'] = int(
                            supply_data['result']) / 10**18
            except:
                pass

            # 2. Gas Price
            try:
                gas_url = f"https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey={etherscan_api_key}"
                gas_response = requests.get(gas_url, timeout=10)
                if gas_response.status_code == 200:
                    gas_data = gas_response.json()
                    if gas_data['status'] == '1':
                        eth_data.update({
                            'safe_gas_price':
                            gas_data['result']['SafeGasPrice'],
                            'standard_gas_price':
                            gas_data['result']['StandardGasPrice'],
                            'fast_gas_price':
                            gas_data['result']['FastGasPrice']
                        })
            except:
                pass

            # 3. Latest Block Number
            try:
                block_url = f"https://api.etherscan.io/api?module=proxy&action=eth_blockNumber&apikey={etherscan_api_key}"
                block_response = requests.get(block_url, timeout=10)
                if block_response.status_code == 200:
                    block_data = block_response.json()
                    if 'result' in block_data:
                        eth_data['latest_block'] = int(block_data['result'],
                                                       16)
            except:
                pass

            # 4. Node Count dari Ethernodes.org
            try:
                nodes_url = "https://www.ethernodes.org/api/nodes"
                nodes_response = requests.get(nodes_url, timeout=10)
                if nodes_response.status_code == 200:
                    nodes_data = nodes_response.json()
                    eth_data['total_nodes'] = nodes_data.get('total', 0)
            except:
                pass

            return eth_data if eth_data else {
                "error": "Gagal mengambil data Ethereum"
            }

        # Untuk cryptocurrency lainnya, gunakan CoinGecko API untuk data yang tersedia
        else:
            try:
                # Ambil market data dari CoinGecko
                coin_id = symbol.split('/')[0].lower()  # Ambil base currency
                if coin_id == 'btc': coin_id = 'bitcoin'
                elif coin_id == 'eth': coin_id = 'ethereum'

                url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "market_cap":
                        data.get('market_data', {}).get('market_cap',
                                                        {}).get('usd', 0),
                        "total_volume":
                        data.get('market_data', {}).get('total_volume',
                                                        {}).get('usd', 0),
                        "circulating_supply":
                        data.get('market_data',
                                 {}).get('circulating_supply', 0),
                        "max_supply":
                        data.get('market_data', {}).get('max_supply', 0),
                        "developer_score":
                        data.get('developer_data', {}).get('stars', 0),
                        "community_score":
                        data.get('community_data',
                                 {}).get('twitter_followers', 0)
                    }
                else:
                    return {"error": f"Data tidak tersedia untuk {symbol}"}

            except Exception as e:
                return {
                    "error": f"Gagal mengambil data untuk {symbol}: {str(e)}"
                }

    except Exception as e:
        return {"error": f"Gagal mengambil on-chain data: {str(e)}"}


def detect_candlestick_patterns(df):
    """Deteksi pola candlestick penting"""
    patterns = []

    try:
        # Pastikan data cukup untuk analisis pattern
        if len(df) < 3:
            return patterns

        # Analisis manual untuk pola sederhana
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        # Doji pattern - open hampir sama dengan close
        body_size = abs(latest['close'] - latest['open'])
        total_range = latest['high'] - latest['low']

        if total_range > 0 and body_size / total_range < 0.1:
            patterns.append("Doji - Indecision pattern")

        # Hammer pattern - small body, long lower shadow
        lower_shadow = latest['open'] - latest['low'] if latest[
            'open'] < latest['close'] else latest['close'] - latest['low']
        upper_shadow = latest['high'] - max(latest['open'], latest['close'])

        if total_range > 0 and lower_shadow > 2 * body_size and upper_shadow < body_size:
            patterns.append("Hammer - Bullish reversal")

        # Engulfing pattern - current candle body engulfs previous
        if len(df) > 1:
            curr_body_high = max(latest['open'], latest['close'])
            curr_body_low = min(latest['open'], latest['close'])
            prev_body_high = max(prev['open'], prev['close'])
            prev_body_low = min(prev['open'], prev['close'])

            # Bullish engulfing
            if (latest['close'] > latest['open']
                    and prev['close'] < prev['open']
                    and curr_body_low < prev_body_low
                    and curr_body_high > prev_body_high):
                patterns.append("Bullish Engulfing - Strong bullish signal")

            # Bearish engulfing
            elif (latest['close'] < latest['open']
                  and prev['close'] > prev['open']
                  and curr_body_low < prev_body_low
                  and curr_body_high > prev_body_high):
                patterns.append("Bearish Engulfing - Strong bearish signal")

    except Exception as e:
        print(f"DEBUG: Error in pattern detection: {e}")

    return patterns


def check_macd_crossover(df):
    """Cek crossover MACD dan generate alert"""
    if len(df) < 2:
        return None

    current_macd = df.iloc[-1].get('MACD_12_26_9', 0)
    current_signal = df.iloc[-1].get('MACDs_12_26_9', 0)
    prev_macd = df.iloc[-2].get('MACD_12_26_9', 0)
    prev_signal = df.iloc[-2].get('MACDs_12_26_9', 0)

    # Bullish crossover: MACD crosses above signal
    if prev_macd <= prev_signal and current_macd > current_signal:
        return {
            "type": "MACD_BULLISH_CROSSOVER",
            "message": "🟢 MACD Bullish Crossover - Sinyal Beli Potensial",
            "timestamp": datetime.now().isoformat()
        }

    # Bearish crossover: MACD crosses below signal
    elif prev_macd >= prev_signal and current_macd < current_signal:
        return {
            "type": "MACD_BEARISH_CROSSOVER",
            "message": "🔴 MACD Bearish Crossover - Sinyal Jual Potensial",
            "timestamp": datetime.now().isoformat()
        }

    return None


def get_realtime_volume_analysis(symbol, timeframe='1m'):
    """Analisis volume real-time"""
    try:
        exchange = ccxt.binance()
        # Ambil data volume 24h dan bandingkan dengan average
        ticker = exchange.fetch_ticker(symbol)
        volume_24h = ticker.get('quoteVolume', 0)

        # Ambil data historis untuk perbandingan
        ohlcv = exchange.fetch_ohlcv(symbol, '1d', limit=7)
        if ohlcv:
            df_vol = pd.DataFrame(ohlcv,
                                  columns=[
                                      'timestamp', 'open', 'high', 'low',
                                      'close', 'volume'
                                  ])
            avg_volume = df_vol['volume'].mean()
            volume_ratio = volume_24h / avg_volume if avg_volume > 0 else 1

            return {
                "current_24h_volume":
                volume_24h,
                "average_7d_volume":
                avg_volume,
                "volume_ratio":
                round(volume_ratio, 2),
                "volume_status":
                "High" if volume_ratio > 1.5 else
                "Normal" if volume_ratio > 0.7 else "Low"
            }
    except Exception as e:
        return {"error": f"Gagal mengambil analisis volume: {str(e)}"}


@app.route('/api/analyze', methods=['GET'])
def analyze_crypto():
    symbol = request.args.get('symbol')
    timeframe = request.args.get('timeframe', '1d')

    if not symbol:
        return jsonify({"error": "Parameter 'symbol' tidak ditemukan."}), 400
    if timeframe not in VALID_TIMEFRAMES:
        return jsonify({"error": f"Timeframe tidak valid."}), 400

    validated_symbol = validate_symbol(symbol)

    try:
        exchange = ccxt.binance()

        # --- 1. AMBIL DATA TEKNIKAL (OHLCV) ---
        ohlcv = exchange.fetch_ohlcv(validated_symbol, timeframe, limit=250)
        if not ohlcv or len(ohlcv) < 200:
            return jsonify(
                {"error": f"Data teknikal tidak cukup untuk {timeframe}"}), 404

        df = pd.DataFrame(
            ohlcv,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # Hitung semua indikator teknikal lengkap
        # Momentum Indicators
        df.ta.rsi(length=14, append=True)
        df.ta.rsi(length=7, append=True)  # Fast RSI
        df.ta.rsi(length=21, append=True)  # Slow RSI
        df.ta.stoch(k=14, d=3, append=True)
        df.ta.stochrsi(length=14, append=True)
        df.ta.williams_r(length=14, append=True)
        df.ta.cci(length=20, append=True)
        df.ta.roc(length=10, append=True)
        df.ta.mfi(length=14, append=True)  # Money Flow Index
        
        # Trend Indicators
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.adx(length=14, append=True)
        df.ta.aroon(length=14, append=True)
        df.ta.psar(append=True)  # Parabolic SAR
        df.ta.dmi(length=14, append=True)  # Directional Movement Index
        
        # Moving Averages
        df.ta.sma(length=10, append=True)
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)
        df.ta.sma(length=100, append=True)
        df.ta.sma(length=200, append=True)
        df.ta.ema(length=12, append=True)
        df.ta.ema(length=26, append=True)
        df.ta.ema(length=50, append=True)
        df.ta.ema(length=200, append=True)
        df.ta.wma(length=20, append=True)  # Weighted Moving Average
        df.ta.vwma(length=20, append=True)  # Volume Weighted Moving Average
        
        # Volatility Indicators
        df.ta.bbands(length=20, std=2, append=True)
        df.ta.kc(length=20, scalar=2, append=True)  # Keltner Channels
        df.ta.atr(length=14, append=True)  # Average True Range
        df.ta.natr(length=14, append=True)  # Normalized ATR
        df.ta.true_range(append=True)
        
        # Volume Indicators
        df.ta.obv(append=True)  # On Balance Volume
        df.ta.ad(append=True)  # Accumulation/Distribution
        df.ta.cmf(length=20, append=True)  # Chaikin Money Flow
        df.ta.efi(length=13, append=True)  # Elder's Force Index
        df.ta.vpt(append=True)  # Volume Price Trend
        df.ta.pvt(append=True)  # Price Volume Trend
        
        # Ichimoku Cloud (complete)
        df.ta.ichimoku(append=True)
        
        # Custom calculations
        # Support/Resistance strength
        df['pivot_high'] = df.ta.pivots(high=df['high'], length=5)
        df['pivot_low'] = df.ta.pivots(low=df['low'], length=5)
        
        # Price position relative to moving averages
        df['price_vs_sma20'] = (df['close'] - df['SMA_20']) / df['SMA_20'] * 100
        df['price_vs_sma50'] = (df['close'] - df['SMA_50']) / df['SMA_50'] * 100
        df['price_vs_ema20'] = (df['close'] - df['EMA_12']) / df['EMA_12'] * 100
        
        # Volume analysis
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Volatility measures
        df['price_change_pct'] = df['close'].pct_change() * 100
        df['volatility_20'] = df['price_change_pct'].rolling(window=20).std()
        
        # Market structure
        df['higher_high'] = (df['high'] > df['high'].shift(1)) & (df['high'].shift(1) > df['high'].shift(2))
        df['lower_low'] = (df['low'] < df['low'].shift(1)) & (df['low'].shift(1) < df['low'].shift(2))

        latest_data = df.iloc[-1]

        # --- 2. FIBONACCI LEVELS ---
        period_high = df['high'].tail(50).max()
        period_low = df['low'].tail(50).min()
        fibonacci_levels = calculate_fibonacci_levels(period_high, period_low)

        # --- 3. PIVOT POINTS ---
        prev_day = df.iloc[-2]  # Data hari sebelumnya
        pivot_points = calculate_pivot_points(prev_day['high'],
                                              prev_day['low'],
                                              prev_day['close'])

        # --- 3.1. SUPPORT & RESISTANCE LEVELS ---
        support_resistance = calculate_support_resistance(df, period=50)

        # --- 4. REAL-TIME VOLUME ANALYSIS ---
        volume_analysis = get_realtime_volume_analysis(validated_symbol)

        # --- 5. ORDER BOOK DATA ---
        order_book_data = {
            "bid_volume": None,
            "ask_volume": None,
            "ratio": None
        }
        try:
            order_book = exchange.fetch_order_book(validated_symbol, limit=100)
            bids = order_book['bids'][:20]  # Top 20 bids
            asks = order_book['asks'][:20]  # Top 20 asks

            bid_volume = sum([price * amount for price, amount in bids])
            ask_volume = sum([price * amount for price, amount in asks])
            ratio = bid_volume / ask_volume if ask_volume > 0 else float('inf')

            order_book_data = {
                "bid_volume":
                round(bid_volume, 2),
                "ask_volume":
                round(ask_volume, 2),
                "ratio":
                round(ratio, 2),
                "market_pressure":
                "Bullish"
                if ratio > 1.2 else "Bearish" if ratio < 0.8 else "Neutral"
            }
        except Exception as e:
            print(f"DEBUG: Gagal mengambil order book: {e}")

        # --- 6. FEAR & GREED INDEX ---
        fear_greed_data = {"value": None, "classification": "N/A"}
        try:
            fng_response = requests.get("https://api.alternative.me/fng/",
                                        timeout=10)
            fng_response.raise_for_status()
            fng_json = fng_response.json()
            fear_greed_data = {
                "value": fng_json['data'][0]['value'],
                "classification": fng_json['data'][0]['value_classification']
            }
        except Exception as e:
            print(f"DEBUG: Gagal mengambil Fear & Greed Index: {e}")

        # --- 7. ON-CHAIN DATA ---
        onchain_data = get_onchain_data(validated_symbol)

        # --- 8. CANDLESTICK PATTERNS ---
        try:
            candlestick_patterns = detect_candlestick_patterns(df.copy())
        except Exception as e:
            print(f"DEBUG: Error detecting candlestick patterns: {e}")
            candlestick_patterns = []

        # --- 9. MACD CROSSOVER ALERT ---
        try:
            macd_alert = check_macd_crossover(df)
            if macd_alert:
                alert_history.append(macd_alert)
                # Keep only last 50 alerts
                if len(alert_history) > 50:
                    alert_history.pop(0)
        except Exception as e:
            print(f"DEBUG: Error checking MACD crossover: {e}")
            macd_alert = None

        # --- 10. COMPREHENSIVE TECHNICAL ANALYSIS ---
        def get_indicator_value(indicator_name):
            if indicator_name in latest_data and pd.notna(latest_data[indicator_name]):
                return round(latest_data[indicator_name], 4)
            return None

        def get_indicator_signal(value, overbought=70, oversold=30, name=""):
            """Generate signal from indicator value"""
            if value is None:
                return "N/A"
            if value > overbought:
                return f"Overbought ({value:.2f})"
            elif value < oversold:
                return f"Oversold ({value:.2f})"
            else:
                return f"Neutral ({value:.2f})"

        # Current values
        price = latest_data['close']
        
        # Momentum indicators
        rsi_14 = get_indicator_value('RSI_14')
        rsi_7 = get_indicator_value('RSI_7')
        rsi_21 = get_indicator_value('RSI_21')
        stoch_k = get_indicator_value('STOCHk_14_3_3')
        stoch_d = get_indicator_value('STOCHd_14_3_3')
        stochrsi = get_indicator_value('STOCHRSIk_14_14_3_3')
        williams_r = get_indicator_value('WILLR_14')
        cci = get_indicator_value('CCI_20_0.015')
        roc = get_indicator_value('ROC_10')
        mfi = get_indicator_value('MFI_14')
        
        # Trend indicators
        macd_line = get_indicator_value('MACD_12_26_9')
        macd_signal = get_indicator_value('MACDs_12_26_9')
        macd_histogram = get_indicator_value('MACDh_12_26_9')
        adx = get_indicator_value('ADX_14')
        adx_pos = get_indicator_value('DMP_14')
        adx_neg = get_indicator_value('DMN_14')
        aroon_up = get_indicator_value('AROONU_14')
        aroon_down = get_indicator_value('AROOND_14')
        psar = get_indicator_value('PSARl_0.02_0.2') or get_indicator_value('PSARs_0.02_0.2')
        
        # Moving averages
        sma_10 = get_indicator_value('SMA_10')
        sma_20 = get_indicator_value('SMA_20')
        sma_50 = get_indicator_value('SMA_50')
        sma_100 = get_indicator_value('SMA_100')
        sma_200 = get_indicator_value('SMA_200')
        ema_12 = get_indicator_value('EMA_12')
        ema_26 = get_indicator_value('EMA_26')
        ema_50 = get_indicator_value('EMA_50')
        ema_200 = get_indicator_value('EMA_200')
        
        # Volatility indicators
        bb_upper = get_indicator_value('BBU_20_2.0')
        bb_middle = get_indicator_value('BBM_20_2.0')
        bb_lower = get_indicator_value('BBL_20_2.0')
        kc_upper = get_indicator_value('KCUe_20_2')
        kc_lower = get_indicator_value('KCLe_20_2')
        atr = get_indicator_value('ATR_14')
        natr = get_indicator_value('NATR_14')
        
        # Volume indicators
        obv = get_indicator_value('OBV')
        ad = get_indicator_value('AD')
        cmf = get_indicator_value('CMF_20')
        efi = get_indicator_value('EFI_13')
        
        # Ichimoku values
        ichimoku_a = get_indicator_value('ISA_9')
        ichimoku_b = get_indicator_value('ISB_26')
        tenkan = get_indicator_value('ITS_9')
        kijun = get_indicator_value('IKS_26')
        
        # Custom calculations
        price_vs_sma20 = get_indicator_value('price_vs_sma20')
        price_vs_sma50 = get_indicator_value('price_vs_sma50')
        volume_ratio = get_indicator_value('volume_ratio')
        volatility_20 = get_indicator_value('volatility_20')

        # --- COMPREHENSIVE SIGNAL ANALYSIS ---
        
        # 1. MOMENTUM SIGNALS
        momentum_signals = {
            "rsi_14": get_indicator_signal(rsi_14, 70, 30),
            "rsi_7": get_indicator_signal(rsi_7, 80, 20),  # More sensitive
            "rsi_21": get_indicator_signal(rsi_21, 65, 35),  # Less sensitive
            "stochastic": get_indicator_signal(stoch_k, 80, 20),
            "stochrsi": get_indicator_signal(stochrsi, 0.8, 0.2),
            "williams_r": get_indicator_signal(williams_r, -20, -80),
            "cci": get_indicator_signal(cci, 100, -100),
            "mfi": get_indicator_signal(mfi, 80, 20),
        }
        
        # 2. TREND SIGNALS
        trend_strength = "Weak"
        if adx:
            if adx > 50: trend_strength = "Very Strong"
            elif adx > 25: trend_strength = "Strong"
            elif adx > 20: trend_strength = "Moderate"
        
        macd_trend = "Neutral"
        if macd_line and macd_signal:
            if macd_line > macd_signal and macd_line > 0:
                macd_trend = "Strong Bullish"
            elif macd_line > macd_signal and macd_line < 0:
                macd_trend = "Bullish Momentum"
            elif macd_line < macd_signal and macd_line < 0:
                macd_trend = "Strong Bearish"
            elif macd_line < macd_signal and macd_line > 0:
                macd_trend = "Bearish Momentum"
        
        # 3. MOVING AVERAGE ANALYSIS
        ma_analysis = {
            "short_term_trend": "Neutral",
            "medium_term_trend": "Neutral", 
            "long_term_trend": "Neutral",
            "ma_alignment": "Mixed"
        }
        
        if price and sma_10 and sma_20:
            if price > sma_10 > sma_20:
                ma_analysis["short_term_trend"] = "Bullish"
            elif price < sma_10 < sma_20:
                ma_analysis["short_term_trend"] = "Bearish"
                
        if price and sma_50 and sma_100:
            if price > sma_50 > sma_100:
                ma_analysis["medium_term_trend"] = "Bullish"
            elif price < sma_50 < sma_100:
                ma_analysis["medium_term_trend"] = "Bearish"
                
        if price and sma_100 and sma_200:
            if price > sma_100 > sma_200:
                ma_analysis["long_term_trend"] = "Bullish"
            elif price < sma_100 < sma_200:
                ma_analysis["long_term_trend"] = "Bearish"
        
        # Check MA alignment (all trending in same direction)
        if sma_10 and sma_20 and sma_50 and sma_200:
            if sma_10 > sma_20 > sma_50 > sma_200:
                ma_analysis["ma_alignment"] = "Perfect Bullish"
            elif sma_10 < sma_20 < sma_50 < sma_200:
                ma_analysis["ma_alignment"] = "Perfect Bearish"
        
        # 4. VOLATILITY ANALYSIS
        volatility_analysis = {
            "bb_position": "Middle",
            "bb_squeeze": False,
            "volatility_level": "Normal"
        }
        
        if bb_upper and bb_lower and price:
            bb_width = bb_upper - bb_lower
            bb_position = (price - bb_lower) / bb_width
            
            if bb_position > 0.8:
                volatility_analysis["bb_position"] = "Upper Band - Overbought"
            elif bb_position < 0.2:

@app.route('/api/analyze/summary/<path:symbol>')
def get_comprehensive_summary(symbol):
    """Endpoint untuk mendapatkan ringkasan analisis yang mudah dipahami"""
    try:
        validated_symbol = validate_symbol(symbol)
        timeframe = request.args.get('timeframe', '1d')
        
        # Get full analysis
        response = requests.get(f"http://0.0.0.0:5000/api/analyze?symbol={validated_symbol}&timeframe={timeframe}")
        
        if response.status_code != 200:
            return jsonify({"error": "Failed to get analysis data"}), 500
        
        analysis_data = response.json()
        
        # Generate comprehensive summary
        summary = generate_comprehensive_summary(analysis_data)
        
        return jsonify({
            "symbol": validated_symbol,
            "timeframe": timeframe,
            "summary": summary,
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to generate summary: {str(e)}"}), 500

@app.route('/api/indicators/all/<path:symbol>')
def get_all_indicators(symbol):
    """Endpoint khusus untuk mendapatkan semua indikator dalam format terstruktur"""
    try:
        validated_symbol = validate_symbol(symbol)
        timeframe = request.args.get('timeframe', '1d')
        
        # Get full analysis
        response = requests.get(f"http://0.0.0.0:5000/api/analyze?symbol={validated_symbol}&timeframe={timeframe}")
        
        if response.status_code != 200:
            return jsonify({"error": "Failed to get analysis data"}), 500
        
        analysis_data = response.json()
        indicators = analysis_data.get('technical_indicators', {})
        
        # Organize indicators by category with interpretations
        organized_indicators = {
            "momentum_indicators": {
                "data": indicators.get('momentum', {}),
                "interpretation": "Momentum indicators help identify overbought/oversold conditions and potential reversals",
                "key_signals": []
            },
            "trend_indicators": {
                "data": indicators.get('trend', {}),
                "interpretation": "Trend indicators show the direction and strength of price movements",
                "key_signals": []
            },
            "moving_averages": {
                "data": indicators.get('moving_averages', {}),
                "interpretation": "Moving averages smooth price data to identify trend direction",
                "key_signals": []
            },
            "volatility_indicators": {
                "data": indicators.get('volatility', {}),
                "interpretation": "Volatility indicators measure price fluctuations and market uncertainty",
                "key_signals": []
            },
            "volume_indicators": {
                "data": indicators.get('volume', {}),
                "interpretation": "Volume indicators confirm price movements and identify accumulation/distribution",
                "key_signals": []
            }
        }
        
        # Add key signals for each category
        momentum_data = indicators.get('momentum', {})
        if momentum_data.get('rsi_14'):
            rsi = momentum_data['rsi_14']
            if rsi > 70:
                organized_indicators["momentum_indicators"]["key_signals"].append(f"RSI {rsi:.1f} - Overbought")
            elif rsi < 30:
                organized_indicators["momentum_indicators"]["key_signals"].append(f"RSI {rsi:.1f} - Oversold")
        
        return jsonify({
            "symbol": validated_symbol,
            "timeframe": timeframe,
            "total_indicators": 40,
            "indicators_by_category": organized_indicators,
            "analysis_timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get indicators: {str(e)}"}), 500


                volatility_analysis["bb_position"] = "Lower Band - Oversold"
            elif bb_position > 0.6:
                volatility_analysis["bb_position"] = "Above Middle - Bullish"
            elif bb_position < 0.4:
                volatility_analysis["bb_position"] = "Below Middle - Bearish"
        
        if natr:
            if natr > 3:
                volatility_analysis["volatility_level"] = "Very High"
            elif natr > 2:
                volatility_analysis["volatility_level"] = "High"
            elif natr < 1:
                volatility_analysis["volatility_level"] = "Low"
        
        # 5. VOLUME ANALYSIS
        volume_analysis_detailed = {
            "volume_trend": "Normal",
            "volume_confirmation": "Neutral",
            "accumulation_distribution": "Neutral"
        }
        
        if volume_ratio:
            if volume_ratio > 2:
                volume_analysis_detailed["volume_trend"] = "Extreme High Volume"
            elif volume_ratio > 1.5:
                volume_analysis_detailed["volume_trend"] = "High Volume"
            elif volume_ratio < 0.5:
                volume_analysis_detailed["volume_trend"] = "Low Volume"
        
        if cmf:
            if cmf > 0.2:
                volume_analysis_detailed["accumulation_distribution"] = "Strong Accumulation"
            elif cmf > 0.1:
                volume_analysis_detailed["accumulation_distribution"] = "Accumulation"
            elif cmf < -0.2:
                volume_analysis_detailed["accumulation_distribution"] = "Strong Distribution"
            elif cmf < -0.1:
                volume_analysis_detailed["accumulation_distribution"] = "Distribution"
        
        # 6. ICHIMOKU ANALYSIS
        ichimoku_analysis = {
            "cloud_position": "In Cloud",
            "tk_cross": "Neutral",
            "cloud_twist": "Neutral"
        }
        
        if ichimoku_a and ichimoku_b and price:
            if price > max(ichimoku_a, ichimoku_b):
                ichimoku_analysis["cloud_position"] = "Above Cloud - Bullish"
            elif price < min(ichimoku_a, ichimoku_b):
                ichimoku_analysis["cloud_position"] = "Below Cloud - Bearish"
                
        if tenkan and kijun:
            if tenkan > kijun:
                ichimoku_analysis["tk_cross"] = "Bullish (Tenkan > Kijun)"
            elif tenkan < kijun:
                ichimoku_analysis["tk_cross"] = "Bearish (Tenkan < Kijun)"
        
        # 7. OVERALL MARKET SENTIMENT SCORE
        bullish_signals = 0
        bearish_signals = 0
        total_signals = 0
        
        # Count momentum signals
        for signal in momentum_signals.values():
            if signal != "N/A":
                total_signals += 1
                if "Oversold" in signal:
                    bullish_signals += 1
                elif "Overbought" in signal:
                    bearish_signals += 1
        
        # Count trend signals
        if "Bullish" in macd_trend:
            bullish_signals += 1
        elif "Bearish" in macd_trend:
            bearish_signals += 1
        total_signals += 1
        
        # Count MA signals
        for trend in ma_analysis.values():
            if trend != "Mixed" and trend != "Neutral":
                total_signals += 1
                if "Bullish" in trend:
                    bullish_signals += 1
                elif "Bearish" in trend:
                    bearish_signals += 1
        
        # Calculate sentiment score
        sentiment_score = 50  # Neutral baseline
        if total_signals > 0:
            sentiment_score = (bullish_signals / total_signals) * 100
        
        sentiment_label = "Neutral"
        if sentiment_score >= 70:
            sentiment_label = "Strong Bullish"
        elif sentiment_score >= 60:
            sentiment_label = "Bullish"
        elif sentiment_score >= 55:
            sentiment_label = "Weak Bullish"
        elif sentiment_score <= 30:
            sentiment_label = "Strong Bearish"
        elif sentiment_score <= 40:
            sentiment_label = "Bearish"
        elif sentiment_score <= 45:
            sentiment_label = "Weak Bearish"

        result = {
            "symbol": validated_symbol,
            "timeframe": timeframe,
            "close_price": price,
            
            # COMPREHENSIVE TECHNICAL INDICATORS
            "technical_indicators": {
                # Momentum Indicators
                "momentum": {
                    "rsi_14": rsi_14,
                    "rsi_7": rsi_7,
                    "rsi_21": rsi_21,
                    "stochastic_k": stoch_k,
                    "stochastic_d": stoch_d,
                    "stochrsi": stochrsi,
                    "williams_r": williams_r,
                    "cci": cci,
                    "roc_10": roc,
                    "mfi": mfi
                },
                
                # Trend Indicators
                "trend": {
                    "macd_line": macd_line,
                    "macd_signal": macd_signal,
                    "macd_histogram": macd_histogram,
                    "adx": adx,
                    "adx_positive": adx_pos,
                    "adx_negative": adx_neg,
                    "aroon_up": aroon_up,
                    "aroon_down": aroon_down,
                    "parabolic_sar": psar
                },
                
                # Moving Averages
                "moving_averages": {
                    "sma_10": sma_10,
                    "sma_20": sma_20,
                    "sma_50": sma_50,
                    "sma_100": sma_100,
                    "sma_200": sma_200,
                    "ema_12": ema_12,
                    "ema_26": ema_26,
                    "ema_50": ema_50,
                    "ema_200": ema_200
                },
                
                # Volatility Indicators
                "volatility": {
                    "bb_upper": bb_upper,
                    "bb_middle": bb_middle,
                    "bb_lower": bb_lower,
                    "kc_upper": kc_upper,
                    "kc_lower": kc_lower,
                    "atr": atr,
                    "natr": natr,
                    "volatility_20d": volatility_20
                },
                
                # Volume Indicators
                "volume": {
                    "obv": obv,
                    "accumulation_distribution": ad,
                    "chaikin_money_flow": cmf,
                    "elder_force_index": efi,
                    "volume_ratio": volume_ratio
                },
                
                # Ichimoku Components
                "ichimoku": {
                    "tenkan_sen": tenkan,
                    "kijun_sen": kijun,
                    "senkou_span_a": ichimoku_a,
                    "senkou_span_b": ichimoku_b
                },
                
                # Price Position Analysis
                "price_position": {
                    "vs_sma20_pct": price_vs_sma20,
                    "vs_sma50_pct": price_vs_sma50
                }
            },
            
            # COMPREHENSIVE SIGNAL ANALYSIS
            "signals": {
                # Momentum Signals
                "momentum_signals": momentum_signals,
                
                # Trend Analysis
                "trend_analysis": {
                    "trend_strength": trend_strength,
                    "adx_reading": adx,
                    "macd_trend": macd_trend,
                    "moving_average_analysis": ma_analysis
                },
                
                # Volatility Analysis
                "volatility_analysis": volatility_analysis,
                
                # Volume Analysis
                "volume_analysis_detailed": volume_analysis_detailed,
                
                # Ichimoku Analysis
                "ichimoku_analysis": ichimoku_analysis,
                
                # Overall Market Sentiment
                "market_sentiment_score": {
                    "score": round(sentiment_score, 2),
                    "label": sentiment_label,
                    "bullish_signals": bullish_signals,
                    "bearish_signals": bearish_signals,
                    "total_signals": total_signals,
                    "confidence": "High" if total_signals > 10 else "Medium" if total_signals > 5 else "Low"
                },
                
                # Pattern Detection
                "candlestick_patterns": candlestick_patterns,
                "macd_crossover": macd_alert
            },
            
            # LEVELS ANALYSIS
            "fibonacci_levels": fibonacci_levels,
            "pivot_points": pivot_points,
            "support_resistance": support_resistance,
            
            # MARKET DATA
            "market_sentiment": {
                "order_book": order_book_data,
                "volume_analysis": volume_analysis,
                "fear_and_greed": fear_greed_data
            },
            
            # BLOCKCHAIN DATA
            "onchain_data": onchain_data,
            
            # ALERTS
            "alerts": {
                "latest_macd_alert": macd_alert,
                "recent_alerts": alert_history[-5:] if alert_history else []
            },
            
            # METADATA
            "analysis_metadata": {
                "total_indicators_calculated": 40,
                "analysis_completeness": "100%",
                "data_quality": "High" if len(df) > 200 else "Medium" if len(df) > 100 else "Low",
                "timestamp": pd.to_datetime(latest_data['timestamp'], unit='ms').isoformat(),
                "last_updated": datetime.now().isoformat(),
                "calculation_time": datetime.now().isoformat()
            }
        }

        # Cache data untuk auto-update
        cache_data[validated_symbol] = result

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": f"Terjadi kesalahan fatal: {str(e)}"}), 500


@app.route('/api/alerts/<path:symbol>')
def get_alerts(symbol):
    """Endpoint khusus untuk mendapatkan alert terbaru"""
    try:
        validated_symbol = validate_symbol(symbol)
        recent_alerts = [
            alert for alert in alert_history if validated_symbol in str(alert)
        ]
        return jsonify({
            "symbol": validated_symbol,
            "alerts": recent_alerts[-10:],  # 10 alert terbaru
            "total_alerts": len(recent_alerts)
        })
    except Exception as e:
        return jsonify({"error": f"Error getting alerts: {str(e)}"}), 500


@app.route('/api/realtime/<path:symbol>')
def get_realtime_data(symbol):
    """Endpoint untuk data real-time singkat"""
    try:
        validated_symbol = validate_symbol(symbol)
        exchange = ccxt.binance()
        ticker = exchange.fetch_ticker(validated_symbol)

        # Safely get order book
        try:
            order_book = exchange.fetch_order_book(validated_symbol, limit=10)
            bid_price = order_book['bids'][0][0] if order_book.get(
                'bids') else None
            ask_price = order_book['asks'][0][0] if order_book.get(
                'asks') else None
        except:
            bid_price = None
            ask_price = None

        return jsonify({
            "symbol": validated_symbol,
            "price": ticker.get('last', 0),
            "change_24h": ticker.get('percentage', 0),
            "volume_24h": ticker.get('quoteVolume', 0),
            "bid": bid_price,
            "ask": ask_price,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error":
                        f"Error getting realtime data: {str(e)}"}), 500


@app.route('/api/fibonacci/<path:symbol>')
def get_fibonacci_only(symbol):
    """Endpoint khusus untuk level Fibonacci"""
    try:
        validated_symbol = validate_symbol(symbol)
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(validated_symbol, '1d', limit=50)

        if not ohlcv or len(ohlcv) < 10:
            return jsonify(
                {"error": "Insufficient data for Fibonacci calculation"}), 400

        df = pd.DataFrame(
            ohlcv,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        period_high = df['high'].max()
        period_low = df['low'].min()
        current_price = df.iloc[-1]['close']

        fib_levels = calculate_fibonacci_levels(period_high, period_low)

        # Tentukan level terdekat
        price_distances = {
            level: abs(current_price - price)
            for level, price in fib_levels.items()
        }
        nearest_level = min(price_distances, key=price_distances.get)

        return jsonify({
            "symbol": validated_symbol,
            "current_price": current_price,
            "fibonacci_levels": fib_levels,
            "nearest_level": nearest_level,
            "nearest_price": fib_levels[nearest_level],
            "period_high": period_high,
            "period_low": period_low
        })
    except Exception as e:
        return jsonify({"error":
                        f"Error calculating Fibonacci: {str(e)}"}), 500


def start_telegram_bot_thread():
    """Start Telegram bot in a separate thread"""
    import logging
    logger = logging.getLogger(__name__)

    global telegram_bot

    try:
        logger.info("🔄 Starting telegram bot thread...")

        # Set event loop untuk thread ini
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            logger.info("🔄 Created new event loop for thread")

        telegram_bot = start_telegram_bot()

        if telegram_bot:
            logger.info("🚀 Starting Telegram Bot in background...")
            telegram_bot.run()
        else:
            logger.error("❌ Failed to create telegram bot instance")

    except Exception as e:
        logger.error(f"❌ Error starting Telegram bot thread: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")


def run_bot_directly():
    """Alternative: Run bot directly in main thread"""
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info("🔄 Starting bot directly in main thread...")
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

        if bot_token:
            from telegram_bot import CryptoTelegramBot
            bot = CryptoTelegramBot(bot_token)

            # Run bot dengan polling sederhana
            logger.info("🚀 Starting bot polling...")
            bot.application.run_polling(
                allowed_updates=None,  # Allow all updates
                drop_pending_updates=True,
                timeout=10,
                poll_interval=2.0)
        else:
            logger.error("❌ No bot token found")

    except Exception as e:
        logger.error(f"❌ Error running bot directly: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")


@app.route('/api/telegram/start')
def start_telegram():
    """Endpoint untuk memulai Telegram bot"""
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info("📥 Request to start Telegram bot received")

        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        logger.info(
            f"🔍 Bot token check: {'Found' if bot_token else 'Not found'}")

        if not bot_token:
            return jsonify({
                "error":
                "TELEGRAM_BOT_TOKEN tidak ditemukan. Silakan tambahkan ke Secrets!",
                "instructions":
                "1. Buat bot baru dengan @BotFather di Telegram\n2. Dapatkan token\n3. Tambahkan token ke Secrets dengan key 'TELEGRAM_BOT_TOKEN'",
                "debug": {
                    "env_vars": list(os.environ.keys()),
                    "checked_token": bool(bot_token)
                }
            }), 400

        # Start bot in background thread
        if not telegram_bot:
            logger.info("🚀 Creating new bot thread...")
            thread = threading.Thread(target=start_telegram_bot_thread,
                                      daemon=True)
            thread.start()

            # Wait a bit to see if bot starts successfully
            import time
            time.sleep(2)

            return jsonify({
                "status": "success",
                "message": "Telegram bot sedang dimulai...",
                "bot_token_available": True,
                "debug": {
                    "token_length": len(bot_token),
                    "token_format_valid": bot_token.count(':') == 1,
                    "thread_started": True
                }
            })
        else:
            return jsonify({
                "status": "already_running",
                "message": "Telegram bot sudah berjalan",
                "bot_token_available": True
            })

    except Exception as e:
        logger.error(f"❌ Error in start_telegram endpoint: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "error": f"Gagal memulai Telegram bot: {str(e)}",
            "debug": {
                "error_type": type(e).__name__,
                "error_details": str(e)
            }
        }), 500


@app.route('/api/telegram/status')
def telegram_status():
    """Check status Telegram bot"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

    # Detailed debug info
    debug_info = {
        "bot_configured": bot_token is not None,
        "bot_running": telegram_bot is not None,
        "token_length": len(bot_token) if bot_token else 0,
        "token_valid_format":
        bot_token.count(':') == 1 if bot_token else False,
        "environment_variables": list(os.environ.keys()),
        "instructions": {
            "setup":
            "1. Chat dengan @BotFather di Telegram\n2. Gunakan /newbot untuk membuat bot baru\n3. Salin token yang diberikan\n4. Tambahkan token ke Secrets dengan key 'TELEGRAM_BOT_TOKEN'",
            "start": "Kunjungi /api/telegram/start untuk memulai bot"
        }
    }

    if bot_token:
        debug_info["token_preview"] = f"{bot_token[:10]}...{bot_token[-10:]}"

    return jsonify(debug_info)


@app.route('/api/telegram/run-direct')
def run_telegram_direct():
    """Try running bot directly in main thread"""
    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            return jsonify({"error": "No bot token found"}), 400

        # Import dan test bot
        from telegram_bot import CryptoTelegramBot
        test_bot = CryptoTelegramBot(bot_token)

        return jsonify({
            "status":
            "success",
            "message":
            "Bot instance created successfully",
            "note":
            "Bot is ready to receive commands. Try sending /start to your bot on Telegram"
        })

    except Exception as e:
        return jsonify({
            "error": f"Failed to create bot: {str(e)}",
            "traceback": traceback.format_exc()
        }), 500


@app.route('/api/telegram/debug')
def telegram_debug():
    """Debug endpoint untuk troubleshooting bot"""
    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

        debug_data = {
            "timestamp": datetime.now().isoformat(),
            "bot_token_exists": bool(bot_token),
            "bot_instance_exists": telegram_bot is not None,
            "environment_check": {
                "total_env_vars":
                len(os.environ),
                "telegram_related_vars": [
                    k for k in os.environ.keys()
                    if 'telegram' in k.lower() or 'bot' in k.lower()
                ],
            }
        }

        if bot_token:
            debug_data["token_analysis"] = {
                "length":
                len(bot_token),
                "has_colon":
                ':' in bot_token,
                "colon_count":
                bot_token.count(':'),
                "starts_with_digit":
                bot_token[0].isdigit() if bot_token else False,
                "format_looks_valid":
                len(bot_token) > 20 and bot_token.count(':') == 1
            }

            # Test koneksi ke Telegram API
            try:
                import requests
                test_url = f"https://api.telegram.org/bot{bot_token}/getMe"
                response = requests.get(test_url, timeout=10)
                debug_data["api_test"] = {
                    "status_code":
                    response.status_code,
                    "response":
                    response.json()
                    if response.status_code == 200 else response.text
                }
            except Exception as api_error:
                debug_data["api_test"] = {
                    "error": str(api_error),
                    "error_type": type(api_error).__name__
                }

        return jsonify(debug_data)

    except Exception as e:
        return jsonify({
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }), 500


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    try:
        return send_from_directory('static', filename)
    except Exception as e:
        logger.error(f"Error serving static file {filename}: {e}")
        return f"Error loading file: {filename}", 404


@app.route('/dashboard')
def dashboard():
    """Serve web dashboard"""
    try:
        return send_from_directory('static', 'index.html')
    except Exception as e:
        logger.error(f"Error serving dashboard: {e}")
        return """
        <h1>Dashboard Error</h1>
        <p>Dashboard tidak dapat dimuat. Pastikan file static/index.html tersedia.</p>
        <p><a href="/">Kembali ke halaman utama</a></p>
        """, 500


@app.route('/api/alerts/create', methods=['POST'])
def create_alert():
    """Create new alert"""
    try:
        data = request.json
        user_id = data.get('user_id', 'web_user')
        symbol = data.get('symbol')
        alert_type = data.get('alert_type')
        condition = data.get('condition')
        value = data.get('value')

        if not all([symbol, alert_type, condition, value]):
            return jsonify({"error": "Missing required fields"}), 400

        if alert_type == 'PRICE':
            alert_id = alert_system.create_price_alert(user_id, symbol,
                                                       condition, value)
        elif alert_type == 'PERCENTAGE':
            alert_id = alert_system.create_percentage_alert(
                user_id, symbol, value, condition)
        elif alert_type == 'VOLUME':
            alert_id = alert_system.create_volume_alert(user_id, symbol, value)
        else:
            return jsonify({"error": "Invalid alert type"}), 400

        return jsonify({
            "success": True,
            "alert_id": alert_id,
            "message": "Alert created successfully"
        })

    except Exception as e:
        return jsonify({"error": f"Failed to create alert: {str(e)}"}), 500


@app.route('/api/alerts/user/<user_id>')
def get_user_alerts(user_id):
    """Get all alerts for a user"""
    try:
        alerts = alert_system.get_user_alerts(user_id)
        return jsonify({"alerts": alerts, "total": len(alerts)})
    except Exception as e:
        return jsonify({"error": f"Failed to get alerts: {str(e)}"}), 500


@app.route('/api/alerts/<int:alert_id>', methods=['DELETE'])
def delete_alert(alert_id):
    """Delete an alert"""
    try:
        data = request.json
        user_id = data.get('user_id', 'web_user')

        success = alert_system.delete_alert(alert_id, user_id)

        if success:
            return jsonify({"success": True, "message": "Alert deleted"})
        else:
            return jsonify({"error": "Alert not found or unauthorized"}), 404

    except Exception as e:
        return jsonify({"error": f"Failed to delete alert: {str(e)}"}), 500


@app.route('/api/alerts/check')
def check_alerts():
    """Manually trigger alert checking"""
    try:
        triggered_alerts = alert_system.check_alerts()
        return jsonify({
            "triggered_alerts": triggered_alerts,
            "count": len(triggered_alerts)
        })
    except Exception as e:
        return jsonify({"error": f"Failed to check alerts: {str(e)}"}), 500


def start_alert_monitoring():
    """Background thread for monitoring alerts"""
    import logging
    logger = logging.getLogger(__name__)

    while True:
        try:
            triggered_alerts = alert_system.check_alerts()

            # Send triggered alerts to Telegram bot if available
            if triggered_alerts and telegram_bot:
                for alert in triggered_alerts:
                    try:
                        # Send alert to Telegram user
                        user_id = alert.get('user_id', '')
                        message = alert.get('message', 'Alert triggered')
                        symbol = alert.get('symbol', '')
                        price = alert.get('price', 0)

                        # Format notification message
                        notification = f"🚨 *ALERT TRIGGERED!*\n\n"
                        notification += f"📊 Symbol: {symbol}\n"
                        notification += f"💰 Price: ${price:,.2f}\n"
                        notification += f"🔔 Message: {message}\n"
                        notification += f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}"

                        # Send via Telegram bot if user_id is valid
                        if user_id and user_id.isdigit():
                            asyncio.run_coroutine_threadsafe(
                                send_telegram_alert(user_id, notification),
                                telegram_bot.application.updater._loop)

                        logger.info(
                            f"🔔 Alert sent to user {user_id}: {message}")
                    except Exception as telegram_error:
                        logger.error(
                            f"Failed to send Telegram alert: {telegram_error}")

        except Exception as e:
            logger.error(f"Error in alert monitoring: {e}")

        # Check alerts every 60 seconds
        time.sleep(60)


async def send_telegram_alert(user_id, message):
    """Send alert notification to Telegram user"""
    try:
        if telegram_bot and telegram_bot.application:
            await telegram_bot.application.bot.send_message(
                chat_id=int(user_id), text=message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error sending Telegram alert to {user_id}: {e}")


@app.route('/')
def home():
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    bot_status = "✅ Dikonfigurasi" if bot_token else "❌ Belum dikonfigurasi"

    return f"""
    <h1>🚀 Advanced Crypto Trading API</h1>
    <h2>🆕 Enhanced Features:</h2>
    <ul>
        <li>✅ <strong>40+ Technical Indicators</strong> - RSI, MACD, Bollinger Bands, Ichimoku, ADX, Aroon, CCI, MFI, dll</li>
        <li>✅ <strong>Comprehensive Signal Analysis</strong> - Momentum, Trend, Volume, Volatility analysis</li>
        <li>✅ <strong>Market Sentiment Scoring</strong> - Overall bullish/bearish score dengan confidence level</li>
        <li>✅ <strong>Advanced Support/Resistance</strong> - Multi-level S/R dengan distance calculation</li>
        <li>✅ <strong>Moving Average Analysis</strong> - 9 different MA types with alignment analysis</li>
        <li>✅ <strong>Volume & Volatility Indicators</strong> - OBV, CMF, ATR, NATR, Volume ratio analysis</li>
        <li>✅ <strong>Ichimoku Cloud Complete</strong> - All components with position analysis</li>
        <li>✅ Interactive Web Dashboard</li>
        <li>✅ Real-time Alert System dengan SQLite Database</li>
        <li>✅ On-Chain Data Integration (BTC/ETH)</li>
        <li>🤖 Telegram Bot Integration - {bot_status}</li>
    </ul>
    <div style="background-color: #e6f3ff; padding: 15px; border-radius: 5px; margin: 20px 0;">
        <h2>🌟 <a href="/dashboard" style="color: #0066cc; text-decoration: none;">Launch Web Dashboard</a></h2>
        <p>Interactive dashboard dengan 40+ indikator teknikal, real-time data, charts, dan alert management!</p>
    </div>
    <h2>🔥 Comprehensive Analysis Endpoints:</h2>
    <ul>
        <li><code>/api/analyze?symbol=BTC/USDT&timeframe=1d</code> - <strong>Analisis Lengkap 40+ Indikator</strong></li>
        <li><code>/api/analyze/summary/BTC/USDT</code> - <strong>Ringkasan Analisis Mudah Dipahami</strong></li>
        <li><code>/api/indicators/all/BTC/USDT</code> - <strong>Semua Indikator Terorganisir</strong></li>
        <li><code>/api/realtime/BTC/USDT</code> - Data real-time dengan order book</li>
        <li><code>/api/fibonacci/BTC/USDT</code> - Level Fibonacci dengan nearest level</li>
        <li><code>/api/alerts/BTC/USDT</code> - Alert terbaru</li>
    </ul>
    <h2>📊 Indikator Yang Dihitung:</h2>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0;">
        <div style="background-color: #f0f8ff; padding: 15px; border-radius: 5px;">
            <h3>🚀 Momentum (10)</h3>
            <ul style="font-size: 0.9em;">
                <li>RSI (3 periods)</li>
                <li>Stochastic</li>
                <li>StochRSI</li>
                <li>Williams %R</li>
                <li>CCI</li>
                <li>ROC</li>
                <li>MFI</li>
            </ul>
        </div>
        <div style="background-color: #f0fff0; padding: 15px; border-radius: 5px;">
            <h3>📈 Trend (8)</h3>
            <ul style="font-size: 0.9em;">
                <li>MACD</li>
                <li>ADX + DI</li>
                <li>Aroon</li>
                <li>Parabolic SAR</li>
                <li>DMI</li>
            </ul>
        </div>
        <div style="background-color: #fff8f0; padding: 15px; border-radius: 5px;">
            <h3>📊 Moving Averages (9)</h3>
            <ul style="font-size: 0.9em;">
                <li>SMA (5 periods)</li>
                <li>EMA (4 periods)</li>
                <li>WMA</li>
                <li>VWMA</li>
            </ul>
        </div>
        <div style="background-color: #fff0f8; padding: 15px; border-radius: 5px;">
            <h3>🌊 Volatility (7)</h3>
            <ul style="font-size: 0.9em;">
                <li>Bollinger Bands</li>
                <li>Keltner Channels</li>
                <li>ATR</li>
                <li>NATR</li>
                <li>True Range</li>
                <li>Custom Volatility</li>
            </ul>
        </div>
        <div style="background-color: #f8f0ff; padding: 15px; border-radius: 5px;">
            <h3>📦 Volume (6)</h3>
            <ul style="font-size: 0.9em;">
                <li>OBV</li>
                <li>A/D Line</li>
                <li>CMF</li>
                <li>Elder's Force Index</li>
                <li>VPT</li>
                <li>PVT</li>
            </ul>
        </div>
    </div></ul>"""
    <h2>Telegram Bot:</h2>
    <ul>
        <li><a href="/api/telegram/status">📊 Status Telegram Bot</a></li>
        <li><a href="/api/telegram/start">🚀 Start Telegram Bot</a></li>
        <li><a href="/api/telegram/debug">🔧 Debug Telegram Bot</a></li>
    </ul>
    <h3>Test Links:</h3>
    <ul>
        <li><a href="/api/analyze?symbol=BTC/USDT&timeframe=1d">Test Analyze BTC/USDT</a></li>
        <li><a href="/api/realtime/BTC/USDT">Test Realtime BTC/USDT</a></li>
        <li><a href="/api/fibonacci/BTC/USDT">Test Fibonacci BTC/USDT</a></li>
    </ul>
    <div style="background-color: #f0f8ff; padding: 15px; border-radius: 5px; margin-top: 20px;">
        <h3>🤖 Setup Telegram Bot:</h3>
        <ol>
            <li>Chat dengan <strong>@BotFather</strong> di Telegram</li>
            <li>Gunakan command <strong>/newbot</strong></li>
            <li>Ikuti instruksi untuk membuat bot baru</li>
            <li>Salin token yang diberikan BotFather</li>
            <li>Tambahkan token ke <strong>Secrets</strong> dengan key <strong>TELEGRAM_BOT_TOKEN</strong></li>
            <li>Kunjungi <a href="/api/telegram/start">/api/telegram/start</a> untuk memulai bot</li>
        </ol>
    </div>
    """


if __name__ == "__main__":
    # Initialize database untuk alert system
    try:
        alert_system.setup_database()
        print("✅ Alert system database initialized")
    except Exception as e:
        print(f"⚠️ Alert system initialization warning: {e}")

    # Start alert monitoring
    print("🔔 Starting alert monitoring system...")
    alert_thread = threading.Thread(target=start_alert_monitoring, daemon=True)
    alert_thread.start()

    # Auto-start Telegram bot jika token tersedia
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if bot_token:
        print("🤖 Starting Telegram bot automatically...")
        thread = threading.Thread(target=start_telegram_bot_thread,
                                  daemon=True)
        thread.start()
        # Wait untuk bot initialization
        time.sleep(3)
    else:
        print("⚠️ TELEGRAM_BOT_TOKEN tidak ditemukan. Bot tidak akan dimulai.")
        print("💡 Tambahkan token ke Secrets untuk mengaktifkan bot Telegram.")

    print("🌐 Starting web server...")
    print("📊 Dashboard available at: http://0.0.0.0:5000/dashboard")
    print("🔗 Public URL akan tersedia setelah deploy")
    # Base URL for API crypto - use proper internal URL
    API_BASE_URL = "http://0.0.0.0:5000/api"
    app.run(host='0.0.0.0', port=5000, debug=False)
