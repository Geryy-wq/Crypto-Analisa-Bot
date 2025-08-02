
import json
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
import ccxt
import logging

logger = logging.getLogger(__name__)

class AdvancedAlertSystem:
    def __init__(self, db_path="alerts.db"):
        self.db_path = db_path
        self.active_alerts = {}
        self.exchange = ccxt.binance()
        self.setup_database()
        
    def setup_database(self):
        """Initialize SQLite database for alerts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                condition_type TEXT NOT NULL,
                target_price REAL,
                current_price REAL,
                percentage_change REAL,
                volume_threshold REAL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                triggered_at TIMESTAMP,
                message TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER,
                triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                price_at_trigger REAL,
                message TEXT,
                FOREIGN KEY (alert_id) REFERENCES alerts (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_price_alert(self, user_id: str, symbol: str, condition_type: str, 
                          target_price: float, message: str = None) -> int:
        """Create price-based alert"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current price
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            current_price = ticker['last']
        except:
            current_price = 0
        
        cursor.execute('''
            INSERT INTO alerts (user_id, symbol, alert_type, condition_type, 
                               target_price, current_price, message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, symbol, 'PRICE', condition_type, target_price, 
              current_price, message or f"{symbol} price alert"))
        
        alert_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Price alert created: {alert_id} for {user_id}")
        return alert_id
    
    def create_volume_alert(self, user_id: str, symbol: str, volume_threshold: float,
                           message: str = None) -> int:
        """Create volume spike alert"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO alerts (user_id, symbol, alert_type, condition_type,
                               volume_threshold, message)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, symbol, 'VOLUME', 'SPIKE', volume_threshold,
              message or f"{symbol} volume spike alert"))
        
        alert_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return alert_id
    
    def create_percentage_alert(self, user_id: str, symbol: str, percentage_change: float,
                               condition_type: str, message: str = None) -> int:
        """Create percentage change alert"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            current_price = ticker['last']
        except:
            current_price = 0
        
        cursor.execute('''
            INSERT INTO alerts (user_id, symbol, alert_type, condition_type,
                               percentage_change, current_price, message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, symbol, 'PERCENTAGE', condition_type, percentage_change,
              current_price, message or f"{symbol} {percentage_change}% change alert"))
        
        alert_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return alert_id
    
    def check_alerts(self) -> List[Dict]:
        """Check all active alerts and trigger if conditions are met"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM alerts WHERE is_active = 1
        ''')
        
        active_alerts = cursor.fetchall()
        triggered_alerts = []
        
        for alert in active_alerts:
            alert_id, user_id, symbol, alert_type, condition_type, target_price, \
            current_price, percentage_change, volume_threshold, is_active, \
            created_at, triggered_at, message = alert
            
            try:
                # Get current market data
                ticker = self.exchange.fetch_ticker(symbol)
                live_price = ticker['last']
                live_volume = ticker['quoteVolume']
                
                triggered = False
                trigger_message = ""
                
                # Check price alerts
                if alert_type == 'PRICE':
                    if condition_type == 'ABOVE' and live_price >= target_price:
                        triggered = True
                        trigger_message = f"🚀 {symbol} hit target: ${live_price:,.4f} (Target: ${target_price:,.4f})"
                    elif condition_type == 'BELOW' and live_price <= target_price:
                        triggered = True
                        trigger_message = f"📉 {symbol} dropped to: ${live_price:,.4f} (Target: ${target_price:,.4f})"
                
                # Check percentage alerts
                elif alert_type == 'PERCENTAGE' and current_price > 0:
                    price_change_pct = ((live_price - current_price) / current_price) * 100
                    if condition_type == 'GAIN' and price_change_pct >= percentage_change:
                        triggered = True
                        trigger_message = f"📈 {symbol} gained {price_change_pct:+.2f}% (Target: +{percentage_change}%)"
                    elif condition_type == 'LOSS' and price_change_pct <= -percentage_change:
                        triggered = True
                        trigger_message = f"📉 {symbol} lost {abs(price_change_pct):.2f}% (Target: -{percentage_change}%)"
                
                # Check volume alerts
                elif alert_type == 'VOLUME':
                    # Get average volume (simplified - you could make this more sophisticated)
                    if live_volume >= volume_threshold:
                        triggered = True
                        trigger_message = f"📊 {symbol} volume spike: ${live_volume:,.0f} (Threshold: ${volume_threshold:,.0f})"
                
                if triggered:
                    # Mark alert as triggered
                    cursor.execute('''
                        UPDATE alerts SET is_active = 0, triggered_at = ?
                        WHERE id = ?
                    ''', (datetime.now().isoformat(), alert_id))
                    
                    # Add to history
                    cursor.execute('''
                        INSERT INTO alert_history (alert_id, price_at_trigger, message)
                        VALUES (?, ?, ?)
                    ''', (alert_id, live_price, trigger_message))
                    
                    triggered_alerts.append({
                        'alert_id': alert_id,
                        'user_id': user_id,
                        'symbol': symbol,
                        'message': trigger_message,
                        'price': live_price,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    logger.info(f"🔔 Alert triggered: {alert_id} - {trigger_message}")
                    
            except Exception as e:
                logger.error(f"Error checking alert {alert_id}: {e}")
        
        conn.commit()
        conn.close()
        
        return triggered_alerts
    
    def get_user_alerts(self, user_id: str) -> List[Dict]:
        """Get all alerts for a specific user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM alerts WHERE user_id = ? ORDER BY created_at DESC
        ''', (user_id,))
        
        alerts = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': alert[0],
                'symbol': alert[2],
                'alert_type': alert[3],
                'condition_type': alert[4],
                'target_price': alert[5],
                'is_active': bool(alert[9]),
                'created_at': alert[10],
                'message': alert[12]
            }
            for alert in alerts
        ]
    
    def delete_alert(self, alert_id: int, user_id: str) -> bool:
        """Delete an alert"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM alerts WHERE id = ? AND user_id = ?
        ''', (alert_id, user_id))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return deleted

# Global alert system instance
alert_system = AdvancedAlertSystem()
