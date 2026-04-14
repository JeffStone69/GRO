#!/usr/bin/env python3
# ShipTrack V2.2 - FINAL FIXED VERSION (All tabs should now show data)

import http.server
import socketserver
import json
import random
import webbrowser
import os
import pathlib
import tomllib
import datetime
import sqlite3
import requests
import sys
from typing import List, Dict

GROK_API_KEY = None
CHAT_LOG_FILE = "logs/grok_chat_history.jsonl"
DB_FILE = "logs/market_history.db"

def load_config():
    global GROK_API_KEY
    secrets_path = pathlib.Path.cwd() / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        with open(secrets_path, "rb") as f:
            secrets = tomllib.load(f)
        GROK_API_KEY = secrets.get("grok", {}).get("key") or os.getenv("GROK_API_KEY", "")
    else:
        GROK_API_KEY = os.getenv("GROK_API_KEY", "")
    
    os.makedirs("logs", exist_ok=True)
    if not os.path.exists(CHAT_LOG_FILE):
        open(CHAT_LOG_FILE, "w").close()

    conn = sqlite3.connect(DB_FILE)
    conn.execute('''CREATE TABLE IF NOT EXISTS market_history (
                        timestamp TEXT PRIMARY KEY,
                        drewry_wci REAL,
                        freightos_fbx REAL,
                        baltic_dry REAL)''')
    conn.commit()
    conn.close()

load_config()

# ====================== FULL MOCK DATA ======================
VESSELS: List[Dict] = [
    {"id": "MSCU1234567", "vessel_name": "MSC Isabella", "imo": "IMO 9461234", "mmsi": "636019876", "vessel_type": "Container Ship", "cargo": "Consumer Electronics", "location": "Strait of Malacca", "destination": "Port of Rotterdam, Netherlands", "value": 2450000, "impact": 65, "lat": 3.82, "lng": 100.12, "dest_lat": 51.95, "dest_lng": 4.05, "course": 285, "speed_knots": 18.4, "weather": {"temp_c": 29, "condition": "Clear Skies", "icon": "☀️", "impact": 3}, "last_ais_update": "just now", "destination_congestion": 68, "ais_source": "MarineTraffic"},
    {"id": "CMAU4567890", "vessel_name": "CMA CGM Marco Polo", "imo": "IMO 9456789", "mmsi": "228123456", "vessel_type": "Container Ship", "cargo": "Automotive Components", "location": "Indian Ocean", "destination": "Port of Los Angeles, USA", "value": 890000, "impact": 30, "lat": -7.45, "lng": 78.3, "dest_lat": 33.75, "dest_lng": -118.2, "course": 92, "speed_knots": 16.7, "weather": {"temp_c": 26, "condition": "High Winds", "icon": "🌬️", "impact": 22}, "last_ais_update": "just now", "destination_congestion": 42, "ais_source": "ExactEarth"},
    {"id": "EISU9876543", "vessel_name": "Evergreen Ever Given", "imo": "IMO 9876543", "mmsi": "352987654", "vessel_type": "Container Ship", "cargo": "Pharmaceuticals", "location": "Suez Canal", "destination": "Port of Hamburg, Germany", "value": 1200000, "impact": 80, "lat": 30.15, "lng": 32.55, "dest_lat": 53.55, "dest_lng": 9.95, "course": 0, "speed_knots": 12.1, "weather": {"temp_c": 22, "condition": "Fog", "icon": "🌫️", "impact": 15}, "last_ais_update": "just now", "destination_congestion": 55, "ais_source": "MarineTraffic"},
    {"id": "TEMU1122334", "vessel_name": "Maersk Memphis", "imo": "IMO 9345678", "mmsi": "219876543", "vessel_type": "Container Ship", "cargo": "Textiles & Apparel", "location": "Pacific Ocean", "destination": "Port of Oakland, USA", "value": 675000, "impact": 45, "lat": 24.8, "lng": -142.3, "dest_lat": 37.8, "dest_lng": -122.3, "course": 68, "speed_knots": 19.8, "weather": {"temp_c": 24, "condition": "Calm Seas", "icon": "🌊", "impact": 2}, "last_ais_update": "just now", "destination_congestion": 29, "ais_source": "VesselFinder"},
    {"id": "OOLU5566778", "vessel_name": "OOCL Hong Kong", "imo": "IMO 9123456", "mmsi": "477112233", "vessel_type": "Container Ship", "cargo": "Machinery Parts", "location": "Gulf of Aden", "destination": "Port of New York, USA", "value": 1580000, "impact": 55, "lat": 12.95, "lng": 49.8, "dest_lat": 40.65, "dest_lng": -74.0, "course": 275, "speed_knots": 14.5, "weather": {"temp_c": 31, "condition": "Stormy", "icon": "⛈️", "impact": 28}, "last_ais_update": "just now", "destination_congestion": 71, "ais_source": "MarineTraffic"},
    {"id": "TANK1122334", "vessel_name": "TI Europe", "imo": "IMO 9181234", "mmsi": "636012345", "vessel_type": "Oil Tanker", "cargo": "Crude Oil", "location": "Persian Gulf", "destination": "Port of Rotterdam, Netherlands", "value": 45200000, "impact": 75, "lat": 27.5, "lng": 51.2, "dest_lat": 51.95, "dest_lng": 4.05, "course": 310, "speed_knots": 13.2, "weather": {"temp_c": 33, "condition": "Moderate Seas", "icon": "🌊", "impact": 12}, "last_ais_update": "just now", "destination_congestion": 68, "ais_source": "Orbcomm"},
    {"id": "TANK5566778", "vessel_name": "Seawise Giant", "imo": "IMO 9123456", "mmsi": "477998877", "vessel_type": "Oil Tanker", "cargo": "Crude Oil", "location": "Gulf of Mexico", "destination": "Port of Los Angeles, USA", "value": 32800000, "impact": 40, "lat": 28.0, "lng": -88.5, "dest_lat": 33.75, "dest_lng": -118.2, "course": 255, "speed_knots": 11.8, "weather": {"temp_c": 27, "condition": "Clear Skies", "icon": "☀️", "impact": 4}, "last_ais_update": "just now", "destination_congestion": 42, "ais_source": "MarineTraffic"}
]

PORTS: List[Dict] = [
    {"name": "Port of Rotterdam, Netherlands", "congestion": 68, "lat": 51.95, "lng": 4.05},
    {"name": "Port of Los Angeles, USA", "congestion": 42, "lat": 33.75, "lng": -118.2},
    {"name": "Port of Hamburg, Germany", "congestion": 55, "lat": 53.55, "lng": 9.95},
    {"name": "Port of Oakland, USA", "congestion": 29, "lat": 37.8, "lng": -122.3},
    {"name": "Port of New York, USA", "congestion": 71, "lat": 40.65, "lng": -74.0},
    {"name": "Port of Singapore", "congestion": 35, "lat": 1.25, "lng": 103.8}
]

MANUFACTURERS: List[Dict] = [
    {"name": "Tesla Inc.", "delay_days": 9, "affected_vessel": "MSCU1234567", "risk_score": 82},
    {"name": "Apple Inc.", "delay_days": 14, "affected_vessel": "OOLU5566778", "risk_score": 91},
    {"name": "Boeing", "delay_days": 5, "affected_vessel": "TANK1122334", "risk_score": 67},
    {"name": "Samsung Electronics", "delay_days": 11, "affected_vessel": "CMAU4567890", "risk_score": 78},
    {"name": "General Motors", "delay_days": 3, "affected_vessel": "TEMU1122334", "risk_score": 54}
]

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShipTrack Live • V2.2</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
        body { font-family: 'Inter', system_ui, sans-serif; }
        .title-font { font-family: 'Inter', system_ui, sans-serif; font-weight: 700; letter-spacing: -2px; }
        #map { filter: brightness(0.95) contrast(1.05); height: 520px; }
        .grok-chat { max-height: 520px; overflow-y: auto; scroll-behavior: smooth; }
        .chart-container { position: relative; height: 260px; }
    </style>
</head>
<body class="bg-zinc-950 text-zinc-100">
    <div class="max-w-screen-2xl mx-auto">
        <nav class="bg-zinc-900 border-b border-zinc-800 px-8 py-5 flex items-center justify-between sticky top-0 z-50">
            <div class="flex items-center gap-x-4">
                <div class="w-10 h-10 bg-emerald-500 rounded-2xl flex items-center justify-center text-3xl shadow-inner">🚢</div>
                <h1 class="title-font text-4xl">ShipTrack <span class="text-emerald-400 text-xl align-super font-normal">V2.2</span></h1>
            </div>
            <div class="flex items-center gap-x-6">
                <button onclick="togglePolling()" id="poll-btn" class="flex items-center gap-x-2 bg-white hover:bg-emerald-400 hover:text-white text-zinc-900 font-semibold px-6 h-10 rounded-3xl transition-colors">
                    <span id="btn-icon" class="text-lg">▶️</span><span id="btn-text">START POLLING</span>
                </button>
                <div onclick="window.location.reload()" class="text-zinc-400 hover:text-white cursor-pointer text-sm font-medium">RESET</div>
            </div>
        </nav>

        <div class="px-8 py-8">
            <div class="flex border-b border-zinc-800 mb-8 text-sm overflow-x-auto">
                <button onclick="showTab(0)" id="tab-0" class="tab-btn px-8 py-4 font-semibold border-b-4 border-emerald-400 text-emerald-400">LIVE AIS MAP</button>
                <button onclick="showTab(1)" id="tab-1" class="tab-btn px-8 py-4 font-semibold text-zinc-400 hover:text-white">RISK ANALYTICS</button>
                <button onclick="showTab(2)" id="tab-2" class="tab-btn px-8 py-4 font-semibold text-zinc-400 hover:text-white">MANUFACTURERS</button>
                <button onclick="showTab(3)" id="tab-3" class="tab-btn px-8 py-4 font-semibold text-zinc-400 hover:text-white">MARKET EVALUATION</button>
                <button onclick="showTab(4)" id="tab-4" class="tab-btn px-8 py-4 font-semibold text-zinc-400 hover:text-white">GROK CHAT</button>
            </div>

            <div id="content-0" class="tab-content">
                <h2 class="text-3xl font-semibold mb-4">Live AIS Vessel Tracking</h2>
                <div id="map" class="rounded-3xl border border-zinc-800 shadow-2xl"></div>
            </div>

            <div id="content-1" class="tab-content hidden">
                <h2 class="text-3xl font-semibold mb-6">Supply Chain Risk Analytics</h2>
                <div id="risk-grid" class="grid grid-cols-1 md:grid-cols-5 gap-6"></div>
            </div>

            <div id="content-2" class="tab-content hidden">
                <h2 class="text-3xl font-semibold mb-6">Impacted Manufacturers</h2>
                <div id="manufacturers-grid" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-6"></div>
            </div>

            <div id="content-3" class="tab-content hidden">
                <div class="flex justify-between items-center mb-6">
                    <h2 class="text-3xl font-semibold">Global Freight Market Evaluation</h2>
                    <button onclick="getGrokMarketInsight()" class="bg-emerald-400 hover:bg-emerald-500 text-zinc-950 px-6 py-2.5 rounded-3xl font-semibold">💡 Grok Market Insight</button>
                </div>
                <div id="market-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10"></div>
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div class="bg-zinc-900 rounded-3xl p-6">
                        <h3 class="text-lg font-medium mb-4">Market History</h3>
                        <div class="chart-container"><canvas id="historyChart"></canvas></div>
                    </div>
                    <div id="grok-market-reply" class="bg-zinc-900 rounded-3xl p-6 min-h-[300px] text-sm"></div>
                </div>
            </div>

            <div id="content-4" class="tab-content hidden">
                <div class="flex justify-between items-baseline mb-4">
                    <h2 class="text-3xl font-semibold">Grok Async Chat</h2>
                    <button onclick="clearChatHistory()" class="text-xs px-4 py-2 bg-zinc-800 hover:bg-red-500/20 text-red-400 rounded-3xl">CLEAR HISTORY</button>
                </div>
                <div id="chat-window" class="grok-chat bg-zinc-900 rounded-3xl p-6 h-[520px] flex flex-col gap-4"></div>
                <div class="mt-6 flex gap-3">
                    <input id="chat-input" type="text" placeholder="Ask Grok anything..." class="flex-1 bg-zinc-900 border border-zinc-700 focus:border-emerald-400 rounded-3xl px-6 py-4 outline-none">
                    <button onclick="sendGrokMessage()" class="bg-emerald-400 hover:bg-emerald-500 text-zinc-950 font-semibold px-8 rounded-3xl">SEND</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let VESSELS = [], PORTS = [], MANUFACTURERS = [];
        let mapInstance = null;
        let vesselMarkers = {}, routePolylines = {};
        let pollingIntervalId = null;
        let isPolling = false;
        let chatHistory = JSON.parse(localStorage.getItem('grokChatHistory') || '[]');
        let historyChart = null;

        function initMap() {
            mapInstance = L.map('map', { center: [20, 10], zoom: 2.5 });
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap' }).addTo(mapInstance);
        }

        function renderMap() {
            Object.values(vesselMarkers).forEach(m => m.remove());
            Object.values(routePolylines).forEach(l => l.remove());
            vesselMarkers = {}; routePolylines = {};

            VESSELS.forEach(v => {
                const progress = 0.028 + Math.random() * 0.022;
                v.lat += (v.dest_lat - v.lat) * progress;
                v.lng += (v.dest_lng - v.lng) * progress;
                v.course = (v.course + Math.floor(Math.random()*25)-12) % 360;

                const iconHtml = v.vessel_type === 'Oil Tanker' ? '⛽' : '🚢';
                const shipIcon = L.divIcon({className: 'ship-marker', html: `<div style="transform:rotate(${v.course}deg);font-size:28px;">${iconHtml}</div>`, iconSize: [36,36]});

                const marker = L.marker([v.lat, v.lng], {icon: shipIcon}).addTo(mapInstance);
                marker.bindPopup(`<b>${v.vessel_name}</b><br>Impact: ${v.impact}%`);
                vesselMarkers[v.id] = marker;

                const poly = L.polyline([[v.lat, v.lng], [v.dest_lat, v.dest_lng]], {color:'#10b981', weight:2, opacity:0.6}).addTo(mapInstance);
                routePolylines[v.id] = poly;
            });
        }

        function renderRiskAnalytics() {
            let html = '';
            MANUFACTURERS.forEach(m => {
                const color = m.risk_score > 80 ? 'rose' : m.risk_score > 65 ? 'amber' : 'emerald';
                html += `<div class="card bg-zinc-900 border border-zinc-800 rounded-3xl p-6"><div class="flex justify-between"><div class="font-medium">${m.name}</div><div class="font-mono text-xl text-${color}-400">${m.risk_score}</div></div><div class="h-2 bg-zinc-700 rounded-full mt-4"><div class="h-2 bg-${color}-400 rounded-full" style="width:${m.risk_score}%"></div></div></div>`;
            });
            document.getElementById('risk-grid').innerHTML = html;
        }

        function renderManufacturers() {
            let html = '';
            MANUFACTURERS.forEach(m => {
                const color = m.delay_days > 10 ? 'rose' : 'emerald';
                html += `<div class="card bg-zinc-900 border border-zinc-800 rounded-3xl p-6"><div class="font-semibold">${m.name}</div><div class="text-6xl font-bold text-${color}-400 mt-4">${m.delay_days}</div><div class="text-xs text-zinc-400">days delayed</div></div>`;
            });
            document.getElementById('manufacturers-grid').innerHTML = html;
        }

        function renderMarketIndices(indices) {
            let html = '';
            Object.keys(indices).forEach(key => {
                const i = indices[key];
                const changeColor = i.change >= 0 ? 'emerald' : 'rose';
                html += `<div class="card bg-zinc-900 border border-zinc-800 rounded-3xl p-6"><div class="text-sm text-zinc-400">${i.name}</div><div class="text-5xl font-semibold mt-2">${Math.round(i.value)}</div><div class="text-${changeColor}-400">${i.change >= 0 ? '↑' : '↓'} ${Math.abs(i.change).toFixed(1)}%</div><div class="text-xs text-zinc-500">${i.unit}</div></div>`;
            });
            document.getElementById('market-grid').innerHTML = html;
        }

        function updateHistoryChart(history) {
            const ctx = document.getElementById('historyChart');
            if (historyChart) historyChart.destroy();
            historyChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: history.map(h => h.timestamp.slice(11,16)),
                    datasets: [
                        { label: 'Drewry WCI', data: history.map(h => h.drewry_wci), borderColor: '#10b981', tension: 0.3 },
                        { label: 'FBX', data: history.map(h => h.freightos_fbx), borderColor: '#eab308', tension: 0.3 },
                        { label: 'Baltic Dry', data: history.map(h => h.baltic_dry), borderColor: '#3b82f6', tension: 0.3 }
                    ]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }

        async function fetchData() {
            try {
                const res = await fetch('/data');
                const payload = await res.json();
                
                VESSELS = payload.vessels || VESSELS;
                PORTS = payload.ports || PORTS;
                MANUFACTURERS = payload.manufacturers || MANUFACTURERS;

                renderMap();
                renderRiskAnalytics();
                renderManufacturers();
                renderMarketIndices(payload.market_indices || {});
                if (payload.market_history) updateHistoryChart(payload.market_history);
            } catch(e) {
                console.error('Fetch error:', e);
            }
        }

        function showTab(n) {
            document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
            document.getElementById(`content-${n}`).classList.remove('hidden');
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('border-b-4','border-emerald-400','text-emerald-400'));
            document.getElementById(`tab-${n}`).classList.add('border-b-4','border-emerald-400','text-emerald-400');
        }

        function togglePolling() {
            if (isPolling) {
                clearInterval(pollingIntervalId);
                isPolling = false;
                document.getElementById('poll-btn').innerHTML = `<span class="text-lg">▶️</span><span>START POLLING</span>`;
            } else {
                isPolling = true;
                document.getElementById('poll-btn').innerHTML = `<span class="text-lg">⏹️</span><span>STOP POLLING</span>`;
                fetchData();
                pollingIntervalId = setInterval(fetchData, 4000);
            }
        }

        // Grok functions (minimal)
        async function sendGrokMessage() {
            const input = document.getElementById('chat-input');
            const msg = input.value.trim();
            if (!msg) return;
            chatHistory.push({role:'user', content:msg});
            renderChat();
            input.value = '';
            try {
                const res = await fetch('/grok', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:msg})});
                const data = await res.json();
                chatHistory.push({role:'assistant', content:data.reply});
                renderChat();
                localStorage.setItem('grokChatHistory', JSON.stringify(chatHistory));
            } catch(e) {}
        }

        function renderChat() {
            const win = document.getElementById('chat-window');
            win.innerHTML = chatHistory.map(m => `<div class="${m.role==='user'?'ml-auto bg-emerald-500 text-white':'mr-auto bg-zinc-800'} max-w-[80%] rounded-3xl px-6 py-4">${m.content}</div>`).join('');
            win.scrollTop = win.scrollHeight;
        }

        function clearChatHistory() {
            if (confirm('Clear history?')) {
                chatHistory = [];
                localStorage.removeItem('grokChatHistory');
                renderChat();
            }
        }

        async function getGrokMarketInsight() {
            const container = document.getElementById('grok-market-reply');
            container.innerHTML = 'Grok analysing...';
            try {
                const res = await fetch('/grok', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({message: "Give a short evaluation of current global freight markets."}) });
                const data = await res.json();
                container.innerHTML = data.reply.replace(/\n/g, '<br>');
            } catch(e) {
                container.innerHTML = 'Failed to get insight.';
            }
        }

        window.onload = () => {
            initMap();
            fetchData();
            showTab(0);
            console.log('%cShipTrack V2.2 - All tabs should now be populated', 'color:#10b981');
        };
    </script>
</body>
</html>"""

class ShipTrackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_html()
        elif self.path == "/data":
            self.send_data()
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/grok":
            self.handle_grok()
        else:
            self.send_error(405)

    def send_html(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_CONTENT.encode("utf-8"))

    def send_data(self):
        global VESSELS, PORTS, MANUFACTURERS

        for v in VESSELS:
            v["lat"] += (v["dest_lat"] - v["lat"]) * (0.028 + random.random() * 0.022)
            v["lng"] += (v["dest_lng"] - v["lng"]) * (0.028 + random.random() * 0.022)
            v["impact"] = max(12, min(94, v["impact"] + random.randint(-12, 16)))

        for p in PORTS:
            p["congestion"] = max(15, min(92, p["congestion"] + random.randint(-10, 12)))

        for m in MANUFACTURERS:
            m["delay_days"] = max(1, min(25, m["delay_days"] + random.randint(-3, 6)))
            m["risk_score"] = max(40, min(98, m["risk_score"] + random.randint(-8, 12)))

        market_indices = {
            "drewry_wci": {"name": "Drewry World Container Index", "value": 2309 + random.uniform(-40, 60), "change": round(random.uniform(-2.5, 3.8), 1), "unit": "USD/40ft"},
            "freightos_fbx": {"name": "Freightos Baltic Index", "value": 1877 + random.uniform(-50, 70), "change": round(random.uniform(-3.0, 4.2), 1), "unit": "Points"},
            "baltic_dry": {"name": "Baltic Dry Index", "value": 2201 + random.uniform(-80, 110), "change": round(random.uniform(-2.8, 4.5), 1), "unit": "Points"}
        }

        conn = sqlite3.connect(DB_FILE)
        ts = datetime.datetime.now().isoformat()
        conn.execute("INSERT OR REPLACE INTO market_history VALUES (?, ?, ?, ?)",
                     (ts, market_indices["drewry_wci"]["value"], market_indices["freightos_fbx"]["value"], market_indices["baltic_dry"]["value"]))
        conn.commit()

        rows = conn.execute("SELECT timestamp, drewry_wci, freightos_fbx, baltic_dry FROM market_history ORDER BY timestamp DESC LIMIT 30").fetchall()
        market_history = [{"timestamp": r[0], "drewry_wci": r[1], "freightos_fbx": r[2], "baltic_dry": r[3]} for r in reversed(rows)]
        conn.close()

        payload = {
            "vessels": VESSELS,
            "ports": PORTS,
            "manufacturers": MANUFACTURERS,
            "market_indices": market_indices,
            "market_history": market_history
        }

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def handle_grok(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            data = json.loads(self.rfile.read(length).decode('utf-8'))
            user_msg = data.get("message", "")

            if not GROK_API_KEY:
                reply = "Grok API key not configured."
            else:
                resp = requests.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"},
                    json={"model": "grok-beta", "messages": [{"role": "user", "content": user_msg}], "temperature": 0.7},
                    timeout=40
                )
                resp.raise_for_status()
                reply = resp.json()["choices"][0]["message"]["content"]

            with open(CHAT_LOG_FILE, "a") as f:
                f.write(json.dumps({"timestamp": datetime.datetime.now().isoformat(), "user": user_msg, "reply": reply}) + "\n")

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"reply": reply}).encode("utf-8"))
        except Exception as e:
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"reply": f"Error: {str(e)}"}).encode("utf-8"))

def find_free_port(start_port=8000, max_attempts=10):
    for port in range(start_port, start_port + max_attempts):
        try:
            with socketserver.TCPServer(("", port), ShipTrackHandler) as test:
                return port
        except OSError:
            continue
    print("Could not find free port. Please close other servers.")
    sys.exit(1)

def main():
    load_config()
    PORT = find_free_port()
    print(f"🌐 ShipTrack V2.2 started at http://localhost:{PORT}")
    print("   All data should now appear in every tab")
    Handler = ShipTrackHandler
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            webbrowser.open(f"http://localhost:{PORT}")
        except:
            pass
        httpd.serve_forever()

if __name__ == "__main__":
    random.seed(42)
    main()