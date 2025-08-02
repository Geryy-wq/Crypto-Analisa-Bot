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
    print("⚠️ Telegram bot tidak dapat diimport. Install python-telegram-bot terlebih dahulu.")
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
                        "network_hash_rate": data.get('hash_rate', 0),
                        "difficulty": data.get('difficulty', 0),
                        "total_bitcoins": data.get('totalbc', 0) / 100000000,
                        "unconfirmed_count": data.get('n_btc_mined', 0),
                        "mempool_size": data.get('mempool_size', 0)
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
                        "mempool_transactions": mempool_data.get('count', 0),
                        "mempool_size_bytes": mempool_data.get('vsize', 0),
                        "mempool_fees": mempool_data.get('total_fee', 0)
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
                        "difficulty_change": network_data.get('difficultyChange', 0),
                        "estimated_retarget_date": network_data.get('estimatedRetargetDate', 0),
                        "blocks_until_retarget": network_data.get('remainingBlocks', 0)
                    })
            except:
                pass
            
            return btc_data if btc_data else {"error": "Gagal mengambil data Bitcoin"}

        # Untuk Ethereum menggunakan Etherscan API
        elif 'ETH' in symbol:
            etherscan_api_key = os.getenv('ETHERSCAN_API_KEY')
            if not etherscan_api_key:
                return {"error": "ETHERSCAN_API_KEY tidak ditemukan di secrets"}
            
            eth_data = {}
            
            # 1. ETH Total Supply
            try:
                supply_url = f"https://api.etherscan.io/api?module=stats&action=ethsupply&apikey={etherscan_api_key}"
                supply_response = requests.get(supply_url, timeout=10)
                if supply_response.status_code == 200:
                    supply_data = supply_response.json()
                    if supply_data['status'] == '1':
                        eth_data['total_supply'] = int(supply_data['result']) / 10**18
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
                            'safe_gas_price': gas_data['result']['SafeGasPrice'],
                            'standard_gas_price': gas_data['result']['StandardGasPrice'],
                            'fast_gas_price': gas_data['result']['FastGasPrice']
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
                        eth_data['latest_block'] = int(block_data['result'], 16)
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
            
            return eth_data if eth_data else {"error": "Gagal mengambil data Ethereum"}

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
                        "market_cap": data.get('market_data', {}).get('market_cap', {}).get('usd', 0),
                        "total_volume": data.get('market_data', {}).get('total_volume', {}).get('usd', 0),
                        "circulating_supply": data.get('market_data', {}).get('circulating_supply', 0),
                        "max_supply": data.get('market_data', {}).get('max_supply', 0),
                        "developer_score": data.get('developer_data', {}).get('stars', 0),
                        "community_score": data.get('community_data', {}).get('twitter_followers', 0)
                    }
                else:
                    return {"error": f"Data tidak tersedia untuk {symbol}"}
                    
            except Exception as e:
                return {"error": f"Gagal mengambil data untuk {symbol}: {str(e)}"}

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
        lower_shadow = latest['open'] - latest['low'] if latest['open'] < latest['close'] else latest['close'] - latest['low']
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
            if (latest['close'] > latest['open'] and prev['close'] < prev['open'] and 
                curr_body_low < prev_body_low and curr_body_high > prev_body_high):
                patterns.append("Bullish Engulfing - Strong bullish signal")
            
            # Bearish engulfing
            elif (latest['close'] < latest['open'] and prev['close'] > prev['open'] and 
                  curr_body_low < prev_body_low and curr_body_high > prev_body_high):
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

        # Hitung semua indikator
        df.ta.rsi(append=True)
        df.ta.macd(append=True)
        df.ta.bbands(length=20, append=True)
        df.ta.stoch(append=True)
        df.ta.adx(append=True)
        df.ta.ichimoku(append=True)
        df.ta.sma(length=50, append=True)
        df.ta.sma(length=200, append=True)

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

        # --- 10. TECHNICAL ANALYSIS ---
        def get_indicator_value(indicator_name):
            if indicator_name in latest_data and pd.notna(
                    latest_data[indicator_name]):
                return round(latest_data[indicator_name], 2)
            return None

        price = latest_data['close']
        rsi_val = get_indicator_value('RSI_14')
        macd_line = get_indicator_value('MACD_12_26_9')
        signal_line = get_indicator_value('MACDs_12_26_9')
        sma50 = get_indicator_value('SMA_50')
        sma200 = get_indicator_value('SMA_200')

        # Sinyal trading
        rsi_signal = "Netral"
        if rsi_val:
            if rsi_val > 70: rsi_signal = "Overbought - Pertimbangkan Jual"
            elif rsi_val < 30: rsi_signal = "Oversold - Pertimbangkan Beli"

        trend_signal = "Netral / Sideways"
        if price and sma50 and sma200:
            if price > sma50 and sma50 > sma200: trend_signal = "Uptrend Kuat"
            elif price < sma50 and sma50 < sma200:
                trend_signal = "Downtrend Kuat"

        result = {
            "symbol":
            validated_symbol,
            "timeframe":
            timeframe,
            "close_price":
            price,
            "technical_indicators": {
                "rsi": rsi_val,
                "macd_line": macd_line,
                "macd_signal": signal_line,
                "sma50": sma50,
                "sma200": sma200,
                "bb_upper": get_indicator_value('BBU_20_2.0'),
                "bb_middle": get_indicator_value('BBM_20_2.0'),
                "bb_lower": get_indicator_value('BBL_20_2.0'),
            },
            "fibonacci_levels":
            fibonacci_levels,
            "pivot_points":
            pivot_points,
            "signals": {
                "trend_signal": trend_signal,
                "rsi_signal": rsi_signal,
                "macd_crossover": macd_alert,
                "candlestick_patterns": candlestick_patterns
            },
            "market_sentiment": {
                "order_book": order_book_data,
                "volume_analysis": volume_analysis,
                "fear_and_greed": fear_greed_data
            },
            "onchain_data":
            onchain_data,
            "alerts": {
                "latest_macd_alert": macd_alert,
                "recent_alerts": alert_history[-5:] if alert_history else []
            },
            "timestamp":
            pd.to_datetime(latest_data['timestamp'], unit='ms').isoformat(),
            "last_updated":
            datetime.now().isoformat()
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
            bid_price = order_book['bids'][0][0] if order_book.get('bids') else None
            ask_price = order_book['asks'][0][0] if order_book.get('asks') else None
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
        return jsonify({"error": f"Error getting realtime data: {str(e)}"}), 500


@app.route('/api/fibonacci/<path:symbol>')
def get_fibonacci_only(symbol):
    """Endpoint khusus untuk level Fibonacci"""
    try:
        validated_symbol = validate_symbol(symbol)
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(validated_symbol, '1d', limit=50)
        
        if not ohlcv or len(ohlcv) < 10:
            return jsonify({"error": "Insufficient data for Fibonacci calculation"}), 400
            
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
        return jsonify({"error": f"Error calculating Fibonacci: {str(e)}"}), 500


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
                poll_interval=2.0
            )
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
        logger.info(f"🔍 Bot token check: {'Found' if bot_token else 'Not found'}")
        
        if not bot_token:
            return jsonify({
                "error": "TELEGRAM_BOT_TOKEN tidak ditemukan. Silakan tambahkan ke Secrets!",
                "instructions": "1. Buat bot baru dengan @BotFather di Telegram\n2. Dapatkan token\n3. Tambahkan token ke Secrets dengan key 'TELEGRAM_BOT_TOKEN'",
                "debug": {
                    "env_vars": list(os.environ.keys()),
                    "checked_token": bool(bot_token)
                }
            }), 400
        
        # Start bot in background thread
        if not telegram_bot:
            logger.info("🚀 Creating new bot thread...")
            thread = threading.Thread(target=start_telegram_bot_thread, daemon=True)
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
        "token_valid_format": bot_token.count(':') == 1 if bot_token else False,
        "environment_variables": list(os.environ.keys()),
        "instructions": {
            "setup": "1. Chat dengan @BotFather di Telegram\n2. Gunakan /newbot untuk membuat bot baru\n3. Salin token yang diberikan\n4. Tambahkan token ke Secrets dengan key 'TELEGRAM_BOT_TOKEN'",
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
            "status": "success",
            "message": "Bot instance created successfully",
            "note": "Bot is ready to receive commands. Try sending /start to your bot on Telegram"
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
                "total_env_vars": len(os.environ),
                "telegram_related_vars": [k for k in os.environ.keys() if 'telegram' in k.lower() or 'bot' in k.lower()],
            }
        }
        
        if bot_token:
            debug_data["token_analysis"] = {
                "length": len(bot_token),
                "has_colon": ':' in bot_token,
                "colon_count": bot_token.count(':'),
                "starts_with_digit": bot_token[0].isdigit() if bot_token else False,
                "format_looks_valid": len(bot_token) > 20 and bot_token.count(':') == 1
            }
            
            # Test koneksi ke Telegram API
            try:
                import requests
                test_url = f"https://api.telegram.org/bot{bot_token}/getMe"
                response = requests.get(test_url, timeout=10)
                debug_data["api_test"] = {
                    "status_code": response.status_code,
                    "response": response.json() if response.status_code == 200 else response.text
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
            alert_id = alert_system.create_price_alert(user_id, symbol, condition, value)
        elif alert_type == 'PERCENTAGE':
            alert_id = alert_system.create_percentage_alert(user_id, symbol, value, condition)
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
        return jsonify({
            "alerts": alerts,
            "total": len(alerts)
        })
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
                                telegram_bot.application.updater._loop
                            )
                        
                        logger.info(f"🔔 Alert sent to user {user_id}: {message}")
                    except Exception as telegram_error:
                        logger.error(f"Failed to send Telegram alert: {telegram_error}")
                        
        except Exception as e:
            logger.error(f"Error in alert monitoring: {e}")
            
        # Check alerts every 60 seconds
        time.sleep(60)

async def send_telegram_alert(user_id, message):
    """Send alert notification to Telegram user"""
    try:
        if telegram_bot and telegram_bot.application:
            await telegram_bot.application.bot.send_message(
                chat_id=int(user_id),
                text=message,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error sending Telegram alert to {user_id}: {e}")

@app.route('/')
def home():
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    bot_status = "✅ Dikonfigurasi" if bot_token else "❌ Belum dikonfigurasi"
    
    return f"""
    <h1>🚀 Advanced Crypto Trading API</h1>
    <h2>🆕 New Features:</h2>
    <ul>
        <li>✅ Advanced Alert System with Custom Conditions</li>
        <li>✅ Interactive Web Dashboard</li>
        <li>✅ Real-time Volume & Order Book Analysis</li>
        <li>✅ Fibonacci Retracement Levels</li>
        <li>✅ Pivot Points & Support/Resistance</li>
        <li>✅ Auto-Update Technical Indicators</li>
        <li>✅ On-Chain Data Integration</li>
        <li>✅ MACD Crossover & Candlestick Pattern Alerts</li>
        <li>🤖 Telegram Bot Integration - {bot_status}</li>
    </ul>
    <div style="background-color: #e6f3ff; padding: 15px; border-radius: 5px; margin: 20px 0;">
        <h2>🌟 <a href="/dashboard" style="color: #0066cc; text-decoration: none;">Launch Web Dashboard</a></h2>
        <p>Interactive dashboard with real-time data, charts, and alert management!</p>
    </div>
    <h2>API Endpoints:</h2>
    <ul>
        <li><code>/api/analyze?symbol=BTC/USDT&timeframe=1d</code> - Analisis lengkap</li>
        <li><code>/api/alerts/BTC/USDT</code> - Alert terbaru</li>
        <li><code>/api/realtime/BTC/USDT</code> - Data real-time</li>
        <li><code>/api/fibonacci/BTC/USDT</code> - Level Fibonacci</li>
    </ul>
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
        thread = threading.Thread(target=start_telegram_bot_thread, daemon=True)
        thread.start()
        # Wait untuk bot initialization
        time.sleep(3)
    else:
        print("⚠️ TELEGRAM_BOT_TOKEN tidak ditemukan. Bot tidak akan dimulai.")
        print("💡 Tambahkan token ke Secrets untuk mengaktifkan bot Telegram.")
    
    print("🌐 Starting web server...")
    print("📊 Dashboard available at: http://0.0.0.0:8080/dashboard")
    print("🔗 Public URL akan tersedia setelah deploy")
    app.run(host='0.0.0.0', port=8080, debug=False)
