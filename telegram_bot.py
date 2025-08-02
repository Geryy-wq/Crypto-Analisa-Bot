
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import requests
import asyncio
import os
import traceback

# Setup logging dengan level DEBUG untuk troubleshooting
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('telegram_bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Enable debug untuk semua komponen telegram
logging.getLogger('telegram').setLevel(logging.DEBUG)
logging.getLogger('telegram.ext').setLevel(logging.DEBUG)
logging.getLogger('httpx').setLevel(logging.DEBUG)

# Base URL untuk API crypto - use proper internal URL
API_BASE_URL = "http://0.0.0.0:5000/api"

class CryptoTelegramBot:
    def __init__(self, token):
        logger.info(f"🤖 Initializing CryptoTelegramBot...")
        logger.debug(f"Token length: {len(token) if token else 0}")
        
        self.token = token
        
        try:
            # Build application dengan timeout dan error handling
            self.application = Application.builder().token(token).build()
            logger.info("✅ Application builder berhasil")
            
            self.setup_handlers()
            logger.info("✅ Handlers berhasil di-setup")
            
        except Exception as e:
            logger.error(f"❌ Error dalam __init__: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def setup_handlers(self):
        """Setup command handlers"""
        logger.info("🔧 Setting up command handlers...")
        
        try:
            # Add handlers dengan debug
            handlers = [
                ("start", self.start_command),
                ("help", self.help_command),
                ("analyze", self.analyze_command),
                ("price", self.price_command),
                ("fibonacci", self.fibonacci_command),
                ("alerts", self.alerts_command),
                ("createalert", self.create_alert_command),
                ("myalerts", self.my_alerts_command),
                ("deletealert", self.delete_alert_command),
                ("volume", self.volume_command),
                ("onchain", self.onchain_command),
                ("feargreed", self.fear_greed_command)
            ]
            
            for command, handler in handlers:
                self.application.add_handler(CommandHandler(command, handler))
                logger.debug(f"✅ Handler '{command}' ditambahkan")
            
            # Callback query handler
            self.application.add_handler(CallbackQueryHandler(self.button_callback))
            logger.debug("✅ CallbackQueryHandler ditambahkan")
            
            # Message handler
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            logger.debug("✅ MessageHandler ditambahkan")
            
            logger.info("✅ Semua handlers berhasil di-setup")
            
        except Exception as e:
            logger.error(f"❌ Error setup handlers: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk command /start"""
        user_id = update.effective_user.id if update.effective_user else "Unknown"
        logger.info(f"📱 /start command received from user: {user_id}")
        
        try:
            if not update.message:
                logger.error("❌ No message object in update")
                return
                
            welcome_text = """🚀 *Selamat datang di Crypto Trading Bot!*

Bot ini dapat membantu Anda menganalisis cryptocurrency dengan fitur:
• 📊 Analisis teknikal lengkap
• 📈 Level Fibonacci & Pivot Points  
• 🔔 Alert MACD Crossover
• 💰 Data real-time harga & volume
• ⛓️ Data on-chain (BTC/ETH)

Gunakan /help untuk melihat semua perintah yang tersedia."""
            
            keyboard = [
                [InlineKeyboardButton("📊 Analisis BTC", callback_data="analyze_BTC/USDT")],
                [InlineKeyboardButton("📊 Analisis ETH", callback_data="analyze_ETH/USDT")],
                [InlineKeyboardButton("💰 Harga Real-time", callback_data="price_menu")],
                [InlineKeyboardButton("❓ Bantuan", callback_data="help")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            logger.debug("📤 Sending welcome message...")
            await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)
            logger.info("✅ Welcome message sent successfully")
            
        except Exception as e:
            logger.error(f"❌ Error in start_command: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Fallback response tanpa markdown
            try:
                simple_text = "🤖 Bot aktif! Ketik /help untuk bantuan."
                await update.message.reply_text(simple_text)
                logger.info("✅ Fallback message sent")
            except Exception as fallback_error:
                logger.error(f"❌ Fallback message juga gagal: {fallback_error}")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk command /help"""
        help_text = """
🤖 *Panduan Lengkap Bot Crypto*

*📊 Analisis & Data:*
• `/analyze <symbol>` - Analisis teknikal lengkap
• `/price <symbol>` - Harga real-time
• `/fibonacci <symbol>` - Level Fibonacci
• `/volume <symbol>` - Analisis volume
• `/onchain <symbol>` - Data on-chain
• `/feargreed` - Fear & Greed Index

*🔔 Alert Management:*
• `/createalert <symbol> <type> <condition> <value>` - Buat alert
• `/myalerts` - Lihat alert Anda
• `/deletealert <id>` - Hapus alert
• `/alerts <symbol>` - Alert terbaru symbol

*💡 Contoh Alert:*
• `/createalert BTC/USDT PRICE ABOVE 120000`
• `/createalert ETH/USDT PERCENTAGE GAIN 5`
• `/createalert BNB/USDT VOLUME SPIKE 1000000`

*📈 Contoh Analisis:*
• `/analyze BTC/USDT` - Analisis Bitcoin
• `/price ETH/USDT` - Harga Ethereum
• `/volume SOL/USDT` - Volume Solana

*📝 Format Symbol:*
BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT, ADA/USDT
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk command /analyze"""
        if not context.args:
            await update.message.reply_text("❌ Gunakan format: /analyze <symbol>\nContoh: /analyze BTC/USDT")
            return

        symbol = context.args[0].upper()
        timeframe = context.args[1] if len(context.args) > 1 else "1d"
        
        await update.message.reply_text(f"🔄 Menganalisis {symbol}...")
        
        try:
            response = requests.get(f"{API_BASE_URL}/analyze", params={
                "symbol": symbol,
                "timeframe": timeframe
            }, timeout=30)
            
            logger.debug(f"API Response status: {response.status_code}")
            logger.debug(f"API Response text: {response.text[:200]}...")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    analysis_text = self.format_analysis(data)
                    await update.message.reply_text(analysis_text, parse_mode='Markdown')
                except ValueError as json_error:
                    logger.error(f"JSON parsing error: {json_error}")
                    await update.message.reply_text(f"❌ Error parsing response: {str(json_error)}")
            else:
                try:
                    error_data = response.json()
                    await update.message.reply_text(f"❌ Error: {error_data.get('error', 'Unknown error')}")
                except:
                    await update.message.reply_text(f"❌ HTTP Error {response.status_code}: {response.text[:100]}")
                
        except requests.exceptions.RequestException as req_error:
            logger.error(f"Request error: {req_error}")
            await update.message.reply_text(f"❌ Connection error: {str(req_error)}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await update.message.reply_text(f"❌ Gagal mengambil data: {str(e)}")

    async def price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk command /price"""
        if not context.args:
            await update.message.reply_text("❌ Gunakan format: /price <symbol>\nContoh: /price BTC/USDT")
            return

        symbol = context.args[0].upper()
        
        try:
            response = requests.get(f"{API_BASE_URL}/realtime/{symbol}", timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    price_text = self.format_price_data(data)
                    await update.message.reply_text(price_text, parse_mode='Markdown')
                except ValueError as json_error:
                    await update.message.reply_text(f"❌ Error parsing price data: {str(json_error)}")
            else:
                try:
                    error_data = response.json()
                    await update.message.reply_text(f"❌ Error: {error_data.get('error', 'Unknown error')}")
                except:
                    await update.message.reply_text(f"❌ HTTP Error {response.status_code}")
                
        except requests.exceptions.RequestException as req_error:
            await update.message.reply_text(f"❌ Connection error: {str(req_error)}")
        except Exception as e:
            await update.message.reply_text(f"❌ Gagal mengambil data harga: {str(e)}")

    async def fibonacci_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk command /fibonacci"""
        if not context.args:
            await update.message.reply_text("❌ Gunakan format: /fibonacci <symbol>\nContoh: /fibonacci BTC/USDT")
            return

        symbol = context.args[0].upper()
        
        try:
            response = requests.get(f"{API_BASE_URL}/fibonacci/{symbol}", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                fib_text = self.format_fibonacci_data(data)
                await update.message.reply_text(fib_text, parse_mode='Markdown')
            else:
                error_data = response.json()
                await update.message.reply_text(f"❌ Error: {error_data.get('error', 'Unknown error')}")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Gagal mengambil data Fibonacci: {str(e)}")

    async def alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk command /alerts"""
        if not context.args:
            await update.message.reply_text("❌ Gunakan format: /alerts <symbol>\nContoh: /alerts BTC/USDT")
            return

        symbol = context.args[0].upper()
        
        try:
            response = requests.get(f"{API_BASE_URL}/alerts/{symbol}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                alerts_text = self.format_alerts_data(data)
                await update.message.reply_text(alerts_text, parse_mode='Markdown')
            else:
                error_data = response.json()
                await update.message.reply_text(f"❌ Error: {error_data.get('error', 'Unknown error')}")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Gagal mengambil alert: {str(e)}")

    async def create_alert_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk command /createalert"""
        if len(context.args) < 4:
            await update.message.reply_text(
                "❌ Format: /createalert <symbol> <type> <condition> <value>\n\n"
                "Contoh:\n"
                "• /createalert BTC/USDT PRICE ABOVE 120000\n"
                "• /createalert ETH/USDT PERCENTAGE GAIN 5\n"
                "• /createalert BNB/USDT VOLUME SPIKE 1000000"
            )
            return

        symbol = context.args[0].upper()
        alert_type = context.args[1].upper()
        condition = context.args[2].upper()
        value = float(context.args[3])
        user_id = str(update.effective_user.id)

        try:
            response = requests.post(f"{API_BASE_URL}/alerts/create", json={
                "symbol": symbol,
                "alert_type": alert_type,
                "condition": condition,
                "value": value,
                "user_id": user_id
            }, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                await update.message.reply_text(
                    f"✅ Alert berhasil dibuat!\n"
                    f"ID: {data['alert_id']}\n"
                    f"Symbol: {symbol}\n"
                    f"Type: {alert_type} {condition} {value}"
                )
            else:
                error_data = response.json()
                await update.message.reply_text(f"❌ Error: {error_data.get('error', 'Unknown error')}")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Gagal membuat alert: {str(e)}")

    async def my_alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk command /myalerts"""
        user_id = str(update.effective_user.id)
        
        try:
            response = requests.get(f"{API_BASE_URL}/alerts/user/{user_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                alerts = data.get('alerts', [])
                
                if not alerts:
                    await update.message.reply_text("📭 Anda belum memiliki alert aktif")
                    return
                    
                text = f"🔔 *Alert Anda ({len(alerts)} total):*\n\n"
                
                for alert in alerts[:10]:  # Show max 10 alerts
                    status = "🟢 Aktif" if alert['is_active'] else "🔴 Triggered"
                    text += f"*ID {alert['id']}:* {alert['symbol']}\n"
                    text += f"• Type: {alert['alert_type']} {alert.get('condition_type', '')}\n"
                    text += f"• Target: {alert.get('target_price', 'N/A')}\n"
                    text += f"• Status: {status}\n\n"
                
                await update.message.reply_text(text, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Gagal mengambil alert")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def delete_alert_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk command /deletealert"""
        if not context.args:
            await update.message.reply_text("❌ Format: /deletealert <alert_id>\nContoh: /deletealert 123")
            return

        alert_id = int(context.args[0])
        user_id = str(update.effective_user.id)

        try:
            response = requests.delete(f"{API_BASE_URL}/alerts/{alert_id}", json={
                "user_id": user_id
            }, timeout=10)
            
            if response.status_code == 200:
                await update.message.reply_text(f"✅ Alert {alert_id} berhasil dihapus!")
            else:
                await update.message.reply_text("❌ Gagal menghapus alert atau alert tidak ditemukan")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def volume_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk command /volume"""
        if not context.args:
            symbol = "BTC/USDT"
        else:
            symbol = context.args[0].upper()
        
        try:
            response = requests.get(f"{API_BASE_URL}/analyze?symbol={symbol}&timeframe=1d", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                volume_data = data.get('market_sentiment', {}).get('volume_analysis', {})
                
                text = f"📊 *Volume Analysis - {symbol}*\n\n"
                text += f"💰 Current 24h Volume: ${volume_data.get('current_24h_volume', 0):,.0f}\n"
                text += f"📈 Average 7d Volume: ${volume_data.get('average_7d_volume', 0):,.0f}\n"
                text += f"🔢 Volume Ratio: {volume_data.get('volume_ratio', 0):.2f}x\n"
                text += f"📊 Status: {volume_data.get('volume_status', 'N/A')}\n"
                
                await update.message.reply_text(text, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Gagal mengambil data volume")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def onchain_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk command /onchain"""
        if not context.args:
            symbol = "BTC/USDT"
        else:
            symbol = context.args[0].upper()
        
        try:
            response = requests.get(f"{API_BASE_URL}/analyze?symbol={symbol}&timeframe=1d", timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                onchain_data = data.get('onchain_data', {})
                
                if 'error' in onchain_data:
                    await update.message.reply_text(f"❌ {onchain_data['error']}")
                    return
                
                text = f"⛓️ *On-Chain Data - {symbol}*\n\n"
                
                # Format data berdasarkan cryptocurrency
                if 'BTC' in symbol:
                    text += f"🔨 Hash Rate: {onchain_data.get('network_hash_rate', 0):,.0f}\n"
                    text += f"📊 Difficulty: {onchain_data.get('difficulty', 0):,.0f}\n"
                    text += f"💰 Total Supply: {onchain_data.get('total_bitcoins', 0):,.2f} BTC\n"
                    text += f"🏊 Mempool Size: {onchain_data.get('mempool_transactions', 0):,} txs\n"
                elif 'ETH' in symbol:
                    text += f"💰 Total Supply: {onchain_data.get('total_supply', 0):,.0f} ETH\n"
                    text += f"⛽ Fast Gas: {onchain_data.get('fast_gas_price', 0)} gwei\n"
                    text += f"📊 Latest Block: {onchain_data.get('latest_block', 0):,}\n"
                    text += f"🌐 Total Nodes: {onchain_data.get('total_nodes', 0):,}\n"
                else:
                    text += f"💰 Market Cap: ${onchain_data.get('market_cap', 0):,.0f}\n"
                    text += f"📊 Volume: ${onchain_data.get('total_volume', 0):,.0f}\n"
                    text += f"🔄 Circulating: {onchain_data.get('circulating_supply', 0):,.0f}\n"
                
                await update.message.reply_text(text, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Gagal mengambil data on-chain")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def fear_greed_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk command /feargreed"""
        try:
            response = requests.get(f"{API_BASE_URL}/analyze?symbol=BTC/USDT&timeframe=1d", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                fg_data = data.get('market_sentiment', {}).get('fear_and_greed', {})
                
                value = fg_data.get('value', 'N/A')
                classification = fg_data.get('classification', 'N/A')
                
                # Determine emoji based on value
                if isinstance(value, (int, float)):
                    if value >= 75:
                        emoji = "🤑"
                    elif value >= 55:
                        emoji = "😊"
                    elif value >= 45:
                        emoji = "😐"
                    elif value >= 25:
                        emoji = "😰"
                    else:
                        emoji = "😱"
                else:
                    emoji = "❓"
                
                text = f"{emoji} *Fear & Greed Index*\n\n"
                text += f"📊 Value: {value}\n"
                text += f"📈 Classification: {classification}\n\n"
                text += "_Scale: 0 (Extreme Fear) - 100 (Extreme Greed)_"
                
                await update.message.reply_text(text, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Gagal mengambil Fear & Greed Index")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk inline keyboard buttons"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("analyze_"):
            symbol = data.replace("analyze_", "")
            await query.message.reply_text(f"🔄 Menganalisis {symbol}...")
            
            try:
                response = requests.get(f"{API_BASE_URL}/analyze", params={
                    "symbol": symbol,
                    "timeframe": "1d"
                }, timeout=30)
                
                if response.status_code == 200:
                    analysis_data = response.json()
                    analysis_text = self.format_analysis(analysis_data)
                    await query.message.reply_text(analysis_text, parse_mode='Markdown')
                else:
                    await query.message.reply_text("❌ Gagal mengambil data analisis")
                    
            except Exception as e:
                await query.message.reply_text(f"❌ Error: {str(e)}")
                
        elif data == "price_menu":
            keyboard = [
                [InlineKeyboardButton("💰 BTC Price", callback_data="price_BTC/USDT")],
                [InlineKeyboardButton("💰 ETH Price", callback_data="price_ETH/USDT")],
                [InlineKeyboardButton("💰 BNB Price", callback_data="price_BNB/USDT")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("Pilih cryptocurrency:", reply_markup=reply_markup)
            
        elif data.startswith("price_"):
            symbol = data.replace("price_", "")
            try:
                response = requests.get(f"{API_BASE_URL}/realtime/{symbol}", timeout=10)
                if response.status_code == 200:
                    price_data = response.json()
                    price_text = self.format_price_data(price_data)
                    await query.message.reply_text(price_text, parse_mode='Markdown')
                else:
                    await query.message.reply_text("❌ Gagal mengambil data harga")
            except Exception as e:
                await query.message.reply_text(f"❌ Error: {str(e)}")
                
        elif data == "help":
            await self.help_command(update, context)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk pesan text biasa"""
        text = update.message.text.upper()
        
        # Auto-detect symbol dan berikan analisis singkat
        crypto_symbols = ['BTC', 'ETH', 'BNB', 'ADA', 'DOT', 'LINK', 'UNI', 'DOGE']
        
        for symbol in crypto_symbols:
            if symbol in text:
                await update.message.reply_text(f"🔍 Terdeteksi {symbol}! Mengambil data harga...")
                try:
                    response = requests.get(f"{API_BASE_URL}/realtime/{symbol}/USDT", timeout=10)
                    if response.status_code == 200:
                        price_data = response.json()
                        price_text = self.format_price_data(price_data)
                        
                        keyboard = [
                            [InlineKeyboardButton(f"📊 Analisis {symbol}", callback_data=f"analyze_{symbol}/USDT")],
                            [InlineKeyboardButton(f"📈 Fibonacci {symbol}", callback_data=f"fib_{symbol}/USDT")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await update.message.reply_text(price_text, parse_mode='Markdown', reply_markup=reply_markup)
                        return
                except:
                    pass
        
        # Jika tidak ada symbol terdeteksi
        await update.message.reply_text(
            "🤖 Kirim nama cryptocurrency (contoh: BTC, ETH) atau gunakan perintah:\n"
            "• /analyze BTC/USDT\n"
            "• /price ETH/USDT\n"
            "• /help untuk panduan lengkap"
        )

    def format_analysis(self, data):
        """Format data analisis menjadi text yang mudah dibaca"""
        symbol = data.get('symbol', 'N/A')
        price = data.get('close_price', 0)
        indicators = data.get('technical_indicators', {})
        signals = data.get('signals', {})
        
        text = f"📊 *Analisis {symbol}*\n\n"
        text += f"💰 *Harga:* ${price:,.2f}\n\n"
        
        # Technical Indicators
        text += "*📈 Indikator Teknikal:*\n"
        if indicators.get('rsi'):
            text += f"• RSI: {indicators['rsi']:.1f}\n"
        if indicators.get('macd_line'):
            text += f"• MACD: {indicators['macd_line']:.4f}\n"
        if indicators.get('sma50') and indicators.get('sma200'):
            text += f"• SMA50: ${indicators['sma50']:,.2f}\n"
            text += f"• SMA200: ${indicators['sma200']:,.2f}\n"
        
        # Signals
        text += f"\n*🎯 Sinyal Trading:*\n"
        text += f"• Trend: {signals.get('trend_signal', 'N/A')}\n"
        text += f"• RSI: {signals.get('rsi_signal', 'N/A')}\n"
        
        # Patterns
        patterns = signals.get('candlestick_patterns', [])
        if patterns:
            text += f"\n*🕯️ Pola Candlestick:*\n"
            for pattern in patterns[:3]:  # Max 3 patterns
                text += f"• {pattern}\n"
        
        return text

    def format_price_data(self, data):
        """Format data harga real-time"""
        symbol = data.get('symbol', 'N/A')
        price = data.get('price', 0)
        change = data.get('change_24h', 0)
        volume = data.get('volume_24h', 0)
        
        change_emoji = "🟢" if change >= 0 else "🔴"
        change_sign = "+" if change >= 0 else ""
        
        text = f"💰 *{symbol} Real-time*\n\n"
        text += f"💵 *Harga:* ${price:,.4f}\n"
        text += f"{change_emoji} *24h Change:* {change_sign}{change:.2f}%\n"
        text += f"📊 *Volume 24h:* ${volume:,.0f}\n"
        
        if data.get('bid') and data.get('ask'):
            text += f"📈 *Bid:* ${data['bid']:,.4f}\n"
            text += f"📉 *Ask:* ${data['ask']:,.4f}\n"
        
        return text

    def format_fibonacci_data(self, data):
        """Format data Fibonacci levels"""
        symbol = data.get('symbol', 'N/A')
        current_price = data.get('current_price', 0)
        levels = data.get('fibonacci_levels', {})
        nearest_level = data.get('nearest_level', 'N/A')
        
        text = f"📈 *Fibonacci Levels - {symbol}*\n\n"
        text += f"💰 *Current Price:* ${current_price:,.2f}\n"
        text += f"🎯 *Nearest Level:* {nearest_level}\n\n"
        
        text += "*📊 Fibonacci Retracement:*\n"
        for level, price in levels.items():
            if level == nearest_level:
                text += f"🎯 {level}: ${price:,.2f} ← *NEAREST*\n"
            else:
                text += f"• {level}: ${price:,.2f}\n"
        
        return text

    def format_alerts_data(self, data):
        """Format data alerts"""
        symbol = data.get('symbol', 'N/A')
        alerts = data.get('alerts', [])
        total_alerts = data.get('total_alerts', 0)
        
        text = f"🔔 *Alerts - {symbol}*\n\n"
        text += f"📊 *Total Alerts:* {total_alerts}\n\n"
        
        if alerts:
            text += "*🚨 Recent Alerts:*\n"
            for alert in alerts[-5:]:  # Show last 5 alerts
                alert_type = alert.get('type', 'Unknown')
                message = alert.get('message', 'No message')
                timestamp = alert.get('timestamp', '')
                
                text += f"• {message}\n"
                if timestamp:
                    text += f"  ⏰ {timestamp[:16]}\n"
                text += "\n"
        else:
            text += "🔕 *Tidak ada alert terbaru*"
        
        return text

    def run(self):
        """Jalankan bot"""
        logger.info("🤖 Starting Telegram Bot...")
        
        try:
            # Test bot token terlebih dahulu
            logger.info("🔍 Testing bot token...")
            
            # Test koneksi ke Telegram API
            try:
                import requests
                test_url = f"https://api.telegram.org/bot{self.token}/getMe"
                response = requests.get(test_url, timeout=10)
                if response.status_code == 200:
                    bot_info = response.json()
                    logger.info(f"✅ Bot verified: {bot_info['result']['first_name']} (@{bot_info['result']['username']})")
                else:
                    logger.error(f"❌ Bot token test failed: {response.status_code} - {response.text}")
                    return
            except Exception as test_error:
                logger.error(f"❌ Bot token test error: {test_error}")
                return
            
            # Buat event loop baru untuk thread ini
            try:
                loop = asyncio.get_event_loop()
                logger.debug("📍 Using existing event loop")
            except RuntimeError:
                logger.info("🔄 Creating new event loop for thread")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run polling dengan error handling (tanpa signal handlers untuk thread)
            logger.info("🚀 Starting polling...")
            
            # Gunakan async approach untuk menghindari signal handler issue
            async def run_bot():
                async with self.application:
                    await self.application.start()
                    await self.application.updater.start_polling(
                        allowed_updates=Update.ALL_TYPES,
                        drop_pending_updates=True,
                        poll_interval=1.0,
                        timeout=20
                    )
                    # Keep running
                    await asyncio.sleep(float('inf'))
            
            # Jalankan dengan asyncio.run untuk thread safety
            asyncio.run(run_bot())
            
        except Exception as e:
            logger.error(f"❌ Error dalam run(): {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

# Bot instance
bot_instance = None

def start_telegram_bot():
    """Function untuk memulai bot"""
    global bot_instance
    
    logger.info("🔍 Mencari TELEGRAM_BOT_TOKEN...")
    
    # Ambil token dari environment variable
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Debug environment variables
    logger.debug(f"Environment variables yang tersedia: {list(os.environ.keys())}")
    
    if not bot_token:
        logger.error("❌ TELEGRAM_BOT_TOKEN tidak ditemukan di environment variables!")
        logger.error("💡 Silakan tambahkan token bot Telegram Anda ke Secrets")
        
        # Coba cari dengan nama lain
        alternative_names = ['BOT_TOKEN', 'TELEGRAM_TOKEN', 'TG_BOT_TOKEN']
        for alt_name in alternative_names:
            alt_token = os.getenv(alt_name)
            if alt_token:
                logger.info(f"🔍 Token ditemukan dengan nama: {alt_name}")
                bot_token = alt_token
                break
        
        if not bot_token:
            return None
    
    # Validasi format token
    if not bot_token.count(':') == 1:
        logger.error("❌ Format token tidak valid! Token harus format: 123456789:ABC...")
        return None
    
    logger.info(f"✅ Token ditemukan (length: {len(bot_token)})")
    logger.debug(f"Token preview: {bot_token[:10]}...{bot_token[-10:]}")
    
    try:
        logger.info("🚀 Membuat instance CryptoTelegramBot...")
        bot_instance = CryptoTelegramBot(bot_token)
        logger.info("✅ Telegram Bot berhasil diinisialisasi!")
        return bot_instance
        
    except Exception as e:
        logger.error(f"❌ Error membuat bot: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Detail error untuk debugging
        if "Unauthorized" in str(e):
            logger.error("🚨 Bot token tidak valid atau expired!")
        elif "Network" in str(e) or "timeout" in str(e).lower():
            logger.error("🚨 Masalah koneksi network!")
        
        return None

if __name__ == "__main__":
    bot = start_telegram_bot()
    if bot:
        bot.run()
