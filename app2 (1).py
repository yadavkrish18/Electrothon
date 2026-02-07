import cv2
import numpy as np
import math
import time
import datetime
import os
import threading
import csv
try:
    import requests
except Exception:
    requests = None
from flask import Flask, Response, jsonify, render_template_string, request

# ==========================================
# 1. PROFESSIONAL SURVEILLANCE DASHBOARD
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GuardianEye | Women Safety Analytics</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <!-- Leaflet Map CSS/JS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

    <style>
        body { 
            background-color: #09090b; 
            color: #e4e4e7; 
            font-family: 'Inter', sans-serif; 
            overflow: hidden; 
        }
        .sidebar-link { transition: all 0.2s; border-left: 3px solid transparent; cursor: pointer; }
        .sidebar-link:hover, .sidebar-link.active { background-color: #27272a; border-left-color: #3b82f6; color: white; }
        
        .panel { background-color: #18181b; border: 1px solid #27272a; }
        .hidden { display: none !important; }
        
        /* Map Container */
        #map { height: 100%; width: 100%; background: #e4e4e7; border-radius: 8px; }

        /* Video Feed Elements */
        .rec-dot { width: 10px; height: 10px; background-color: #ef4444; border-radius: 50%; animation: blink 1s infinite; }
        @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
        
        /* FIXED: Alert Animation uses box-shadow only (won't affect layout) */
        @keyframes flash-shadow {
            0% { box-shadow: 0 0 0 8px rgba(239,68,68,0.85); }
            50% { box-shadow: 0 0 0 0 rgba(239,68,68,0); }
            100% { box-shadow: 0 0 0 8px rgba(239,68,68,0.85); }
        }
        .alert-active {
            animation: flash-shadow 1s infinite;
            /* keep border untouched to prevent any layout change */
            border-color: inherit !important;
            box-sizing: border-box;
        }

        /* Prevent video container layout shifts when overlays update */
        #video-container {
            height: 420px; /* fixed height to lock position */
            box-sizing: border-box;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        #video-container img { position: relative; width: 100%; height: 100%; object-fit: contain; display: block; }

        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #18181b; }
        ::-webkit-scrollbar-thumb { background: #3f3f46; border-radius: 3px; }
    </style>
</head>
<body class="h-screen flex">

    <!-- 1. LEFT SIDEBAR NAVIGATION -->
    <aside class="w-64 bg-zinc-950 border-r border-zinc-800 flex flex-col justify-between z-20">
        <div>
            <div class="p-6 flex items-center gap-3">
                <div class="w-8 h-8 bg-blue-600 rounded flex items-center justify-center text-white font-bold">G</div>
                <h1 class="text-xl font-bold tracking-tight text-white">GuardianEye</h1>
            </div>
            
            <nav class="mt-4">
                <div class="px-4 text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">Monitor</div>
                <a onclick="switchView('live')" id="nav-live" class="sidebar-link active flex items-center gap-3 px-6 py-3 text-sm text-zinc-300">
                    <i class="fas fa-th-large w-5"></i> Live Operations
                </a>
                <a onclick="switchView('map')" id="nav-map" class="sidebar-link flex items-center gap-3 px-6 py-3 text-sm text-zinc-400">
                    <i class="fas fa-map-marker-alt w-5"></i> Map View
                </a>
                <a onclick="switchView('reports')" id="nav-reports" class="sidebar-link flex items-center gap-3 px-6 py-3 text-sm text-zinc-400">
                    <i class="fas fa-file-alt w-5"></i> Incident Reports
                </a>
            </nav>
        </div>

        <div class="p-4 border-t border-zinc-800">
            <div class="bg-zinc-900 rounded p-3 text-xs">
                <div class="text-zinc-500 mb-1">System Status</div>
                <div class="flex items-center gap-2 text-emerald-500 font-semibold">
                    <div class="w-2 h-2 bg-emerald-500 rounded-full"></div> Online
                </div>
                <div class="mt-2 text-zinc-500">AI Inference: Active</div>
            </div>
        </div>
    </aside>

    <!-- 2. MAIN CONTENT -->
    <main class="flex-1 flex flex-col relative">
        <!-- Top Toolbar -->
        <header class="h-16 bg-zinc-900 border-b border-zinc-800 flex items-center justify-between px-6">
            <div class="flex items-center gap-4">
                <h2 class="text-sm font-semibold text-white">CAM-01: Device Feed</h2>
                <span class="bg-zinc-800 text-zinc-400 text-xs px-2 py-1 rounded border border-zinc-700">1280x720 • 30FPS • HD+</span>
            </div>
            
            <div class="flex items-center gap-3">
                <div class="text-right mr-4">
                    <div class="text-sm font-mono text-white" id="clock">00:00:00</div>
                    <div class="text-xs text-zinc-500" id="date">...</div>
                </div>
                
                <!-- Manual Trigger -->
                <button onclick="triggerManualAlert()" class="px-3 py-1.5 bg-red-900/30 hover:bg-red-800/50 text-red-400 border border-red-500/50 text-xs font-bold rounded transition flex items-center gap-2 mr-2">
                    <i class="fas fa-bullhorn"></i> FORCE ALERT
                </button>

                <button onclick="toggleMode()" id="mode-btn" class="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-medium rounded border border-zinc-600 transition flex items-center gap-2">
                    <i class="fas fa-moon" id="mode-icon"></i> <span id="mode-text">Night Mode</span>
                </button>
                
                <button onclick="toggleAudio()" id="audio-btn" class="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-medium rounded border border-zinc-600 transition flex items-center gap-2">
                    <i class="fas fa-volume-mute" id="audio-icon"></i> <span id="audio-text">Audio Off</span>
                </button>
            </div>
        </header>

        <!-- VIEW 1: LIVE OPERATIONS -->
        <div id="view-live" class="flex-1 p-6 overflow-hidden">
            <div class="grid grid-cols-12 gap-6 h-full">
                <!-- Large Video Area -->
                <div class="col-span-8">
                    <div id="video-container" class="h-full bg-black rounded-lg border border-zinc-700 relative overflow-hidden shadow-xl">
                        <!-- Top overlays -->
                        <div class="absolute top-4 left-4 z-20 flex gap-2">
                            <span class="bg-red-600 text-white text-[11px] font-bold px-2 py-0.5 rounded flex items-center gap-2">
                                <div class="rec-dot"></div> REC
                            </span>
                            <span class="bg-black/50 backdrop-transparent text-white text-[11px] px-2 py-0.5 rounded border border-white/10 flex items-center gap-2">
                                <i class="fas fa-map-pin text-blue-400"></i> <span id="location-text">Locating Device...</span>
                            </span>
                        </div>

                        <!-- Video Stream -->
                        <img id="camera-img" src="/video_feed" alt="Camera Feed" class="w-full h-full object-contain block" style="image-rendering: crisp-edges; image-rendering: pixelated;">

                        <!-- Bottom info bar (locked, no resizing) -->
                        <div class="absolute bottom-0 left-0 right-0 z-10 p-4 bg-black/60 backdrop-blur flex items-center justify-between">
                            <div>
                                <div class="text-xs text-zinc-400 uppercase tracking-wider">Threat Level</div>
                                <div id="risk-display" class="text-3xl font-bold text-emerald-500 tracking-tight">SAFE</div>
                            </div>
                            <div class="text-right">
                                <div id="msg-display" class="text-sm font-medium text-white">Monitoring...</div>
                                <div class="text-xs text-zinc-400">AI Modules Active</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Right panel: controls, counts, logs -->
                <div class="col-span-4 flex flex-col gap-4">
                    <div class="panel rounded-lg p-4 flex flex-col gap-3">
                        <div class="flex items-center justify-between">
                            <h3 class="text-sm font-semibold text-zinc-300">Live Controls</h3>
                            <div class="text-xs text-zinc-500 font-mono">CAM-01</div>
                        </div>

                        <div class="flex gap-2">
                            <button onclick="triggerManualAlert()" class="flex-1 px-3 py-2 bg-red-700 text-white rounded">Force Alert</button>
                            <button id="mode-btn" onclick="toggleMode()" class="px-3 py-2 bg-zinc-800 text-zinc-300 rounded">Mode</button>
                        </div>

                        <div class="flex gap-2">
                            <button id="audio-btn" onclick="toggleAudio()" class="flex-1 px-3 py-2 bg-zinc-800 text-zinc-300 rounded">Toggle Audio</button>
                            <button id="snapshot-btn" onclick="fetch('/api/trigger_manual', {method:'POST'})" class="px-3 py-2 bg-zinc-700 text-white rounded">Snapshot</button>
                        </div>
                    </div>

                    <div class="panel rounded-lg p-4">
                        <h4 class="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">Census</h4>
                        <div class="grid grid-cols-2 gap-3">
                            <div class="bg-zinc-900 rounded p-3 border border-zinc-800 text-center">
                                <div class="text-3xl font-bold text-white" id="count-women">0</div>
                                <div class="text-[10px] text-zinc-500 uppercase mt-1">Women</div>
                            </div>
                            <div class="bg-zinc-900 rounded p-3 border border-zinc-800 text-center">
                                <div class="text-3xl font-bold text-white" id="count-men">0</div>
                                <div class="text-[10px] text-zinc-500 uppercase mt-1">Men</div>
                            </div>
                        </div>
                    </div>

                    <div class="panel rounded-lg flex-1 flex flex-col overflow-hidden">
                        <div class="p-3 border-b border-zinc-800 bg-zinc-900/50 flex justify-between items-center">
                            <span class="text-xs font-semibold text-zinc-400">Event Log</span>
                            <span class="text-[10px] bg-zinc-800 px-1.5 py-0.5 rounded text-zinc-500" id="log-count">0</span>
                        </div>
                        <div class="flex-1 overflow-y-auto p-3 space-y-2" id="log-container">
                            <div class="text-center text-zinc-600 text-xs mt-10">No events recorded.</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- VIEW 2: MAP VIEW -->
        <div id="view-map" class="hidden flex-1 p-6 relative">
            <div class="h-full w-full rounded-lg border border-zinc-700 overflow-hidden relative shadow-xl">
                <div id="map"></div>
                <div class="absolute top-4 right-4 bg-white/90 p-4 rounded border border-zinc-200 z-[1000] w-64 backdrop-blur shadow-lg text-black">
                    <h3 class="text-sm font-bold text-zinc-800 mb-2 flex items-center gap-2">
                        <i class="fas fa-satellite text-blue-600"></i> Device Location
                    </h3>
                    <div id="map-coords" class="text-xs text-zinc-600 font-mono mb-2">Waiting for GPS...</div>
                    <div class="flex items-center gap-2 text-xs text-emerald-600 border-t border-zinc-200 pt-2">
                        <span class="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span> Tracking Active
                    </div>
                </div>
            </div>
        </div>

        <!-- VIEW 3: INCIDENT REPORTS -->
        <div id="view-reports" class="hidden flex-1 p-6 overflow-hidden flex flex-col">
            <div class="bg-zinc-900 rounded-lg border border-zinc-700 flex-1 flex flex-col overflow-hidden shadow-xl">
                <div class="p-4 border-b border-zinc-800 flex justify-between items-center bg-zinc-950/50">
                    <h2 class="font-bold text-white flex items-center gap-3 text-lg">
                        <i class="fas fa-history text-blue-500"></i> Incident History
                    </h2>
                    <button onclick="refreshReports()" class="text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-4 py-2 rounded border border-zinc-600 transition flex items-center gap-2">
                        <i class="fas fa-sync-alt"></i> Refresh Data
                    </button>
                </div>
                <div class="flex-1 overflow-auto">
                    <table class="w-full text-left border-collapse">
                        <thead class="bg-zinc-950 text-zinc-500 text-xs uppercase sticky top-0 z-10">
                            <tr>
                                <th class="p-4 font-semibold border-b border-zinc-800">Timestamp</th>
                                <th class="p-4 font-semibold border-b border-zinc-800">Level</th>
                                <th class="p-4 font-semibold border-b border-zinc-800">Alert Message</th>
                                <th class="p-4 font-semibold border-b border-zinc-800">Location</th>
                            </tr>
                        </thead>
                        <tbody id="reports-body" class="text-sm text-zinc-300 divide-y divide-zinc-800">
                            <!-- Rows injected via JS -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

    </main>

    <script>
        // Update Time
        setInterval(() => {
            const now = new Date();
            document.getElementById('clock').innerText = now.toLocaleTimeString();
            document.getElementById('date').innerText = now.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
        }, 1000);

        // --- GLOBAL VARIABLES ---
        let mapInitialized = false;
        let mapObj = null;
        let userLat = 0, userLon = 0;

        // --- GEOLOCATION SETUP ---
        function initLocation() {
            const locText = document.getElementById("location-text");
            const mapLabel = document.getElementById("map-label");
            const mapCoords = document.getElementById("map-coords");
            
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        userLat = position.coords.latitude;
                        userLon = position.coords.longitude;
                        
                        const latStr = userLat.toFixed(4);
                        const lonStr = userLon.toFixed(4);
                        const locString = `LAT: ${latStr} N | LON: ${lonStr} E`;
                        
                        if(locText) locText.innerHTML = locString;
                        if(mapLabel) mapLabel.innerHTML = `Live: ${latStr}, ${lonStr}`;
                        if(mapCoords) mapCoords.innerHTML = `${latStr}, ${lonStr}`;
                    },
                    (error) => {
                        console.error("Geo Error:", error);
                        if(locText) locText.innerHTML = "GPS Signal Lost";
                    }
                );
            } else {
                if(locText) locText.innerHTML = "GPS Not Supported";
            }
        }
        initLocation();

        // --- VIEW SWITCHING LOGIC ---
        function switchView(viewName) {
            // Hide all
            document.getElementById('view-live').classList.add('hidden');
            document.getElementById('view-map').classList.add('hidden');
            document.getElementById('view-reports').classList.add('hidden');
            
            // Reset Sidebar Links
            document.querySelectorAll('.sidebar-link').forEach(el => {
                el.classList.remove('active');
                el.classList.add('text-zinc-400');
                el.classList.remove('text-zinc-300');
                el.style.backgroundColor = 'transparent';
                el.style.borderLeftColor = 'transparent';
            });

            // Activate Selected Link
            const activeNav = document.getElementById('nav-' + viewName);
            activeNav.classList.add('active');
            activeNav.classList.remove('text-zinc-400');
            activeNav.classList.add('text-zinc-300');
            activeNav.style.backgroundColor = '#27272a';
            activeNav.style.borderLeftColor = '#3b82f6';

            // Show Content
            document.getElementById('view-' + viewName).classList.remove('hidden');

            // View Specific Logic
            if (viewName === 'map') {
                setTimeout(() => {
                    if (!mapInitialized) initLeaflet();
                    else mapObj.invalidateSize();
                }, 100);
            }
            if (viewName === 'reports') {
                renderReportsTable();
            }
        }

        // --- MAP LOGIC (LEAFLET - LIGHT MODE) ---
        function initLeaflet() {
            if (!userLat || !userLon) return; // Wait for GPS
            
            // Initialize Map
            mapObj = L.map('map').setView([userLat, userLon], 15);
            
            // CartoDB Positron (Light Theme)
            L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
                subdomains: 'abcd',
                maxZoom: 20
            }).addTo(mapObj);

            // Add Marker
            L.marker([userLat, userLon]).addTo(mapObj)
                .bindPopup("<b>Live Camera Feed</b><br>Device Location")
                .openPopup();
                
            // Add Zone Circle
            L.circle([userLat, userLon], {
                color: '#3b82f6',
                fillColor: '#3b82f6',
                fillOpacity: 0.1,
                radius: 300
            }).addTo(mapObj);
            
            mapInitialized = true;
        }

        // --- REPORTS TABLE LOGIC ---
        function renderReportsTable() {
            const tbody = document.getElementById('reports-body');
            tbody.innerHTML = "";
            
            fetch('/api/stats')
                .then(r => r.json())
                .then(data => {
                    const logs = data.logs;
                    if(logs.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="4" class="p-8 text-center text-zinc-500">No security incidents recorded in current session.</td></tr>';
                        return;
                    }
                    
                    logs.forEach(log => {
                        let levelClass = "text-zinc-300";
                        let bgClass = "";
                        let icon = "";
                        
                        if(log.level === "WARNING") { 
                            levelClass = "text-amber-400 font-bold"; 
                            bgClass="bg-amber-900/10"; 
                            icon = "<i class='fas fa-exclamation-triangle mr-2'></i>";
                        }
                        if(log.level === "CRITICAL") { 
                            levelClass = "text-red-500 font-bold"; 
                            bgClass="bg-red-900/10"; 
                            icon = "<i class='fas fa-radiation mr-2'></i>";
                        }
                        
                        const row = `
                            <tr class="hover:bg-zinc-800/50 transition border-b border-zinc-800 last:border-0 ${bgClass}">
                                <td class="p-4 font-mono text-zinc-400 text-xs">${log.time}</td>
                                <td class="p-4 ${levelClass}">${icon}${log.level}</td>
                                <td class="p-4 text-zinc-200">${log.msg}</td>
                                <td class="p-4 text-zinc-500 text-xs">${log.location || 'Sector 4'}</td>
                            </tr>
                        `;
                        tbody.innerHTML += row;
                    });
                });
        }
        
        function refreshReports() {
            const btn = document.querySelector('button[onclick="refreshReports()"] i');
            btn.classList.add('fa-spin');
            renderReportsTable();
            setTimeout(() => btn.classList.remove('fa-spin'), 500);
        }

        // --- STATE MANAGEMENT ---
        let isNightMode = true;
        let audioEnabled = false;
        let audioCtx = null;
        let lastBeepTime = 0;

        // --- MANUAL TRIGGER ---
        async function triggerManualAlert() {
            try {
                await fetch('/api/trigger_manual', { method: 'POST' });
            } catch (e) { console.error(e); }
        }

        // --- MODE TOGGLE ---
        async function toggleMode() {
            try {
                const response = await fetch('/api/toggle_mode', { method: 'POST' });
                const data = await response.json();
                isNightMode = data.is_night;
                updateModeUI();
            } catch (e) { console.error(e); }
        }

        function updateModeUI() {
            const btn = document.getElementById('mode-btn');
            const icon = document.getElementById('mode-icon');
            const text = document.getElementById('mode-text');
            
            if (isNightMode) {
                btn.className = "px-3 py-1.5 bg-indigo-900/30 text-indigo-400 border border-indigo-500/50 text-xs font-medium rounded transition flex items-center gap-2";
                icon.className = "fas fa-moon";
                text.innerText = "Night Active";
            } else {
                btn.className = "px-3 py-1.5 bg-zinc-800 text-zinc-300 border border-zinc-600 text-xs font-medium rounded transition flex items-center gap-2 hover:bg-zinc-700";
                icon.className = "fas fa-sun";
                text.innerText = "Day Mode";
            }
        }
        updateModeUI();

        // --- AUDIO ---
        function toggleAudio() {
            const btn = document.getElementById('audio-btn');
            const icon = document.getElementById('audio-icon');
            const text = document.getElementById('audio-text');

            if (!audioEnabled) {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                audioEnabled = true;
                btn.className = "px-3 py-1.5 bg-emerald-900/30 text-emerald-400 border border-emerald-500/50 text-xs font-medium rounded transition flex items-center gap-2";
                icon.className = "fas fa-volume-up";
                text.innerText = "Audio On";
                playBeep(600, 0.1);
            } else {
                audioEnabled = false;
                if(audioCtx) audioCtx.close();
                btn.className = "px-3 py-1.5 bg-zinc-800 text-zinc-300 border border-zinc-600 text-xs font-medium rounded transition flex items-center gap-2 hover:bg-zinc-700";
                icon.className = "fas fa-volume-mute";
                text.innerText = "Audio Off";
            }
        }

        function playBeep(freq, duration) {
            if (!audioEnabled || !audioCtx) return;
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.type = 'square';
            osc.frequency.value = freq;
            gain.gain.setValueAtTime(0.05, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
            osc.start();
            osc.stop(audioCtx.currentTime + duration);
        }

        function playSiren() {
            if (!audioEnabled || !audioCtx) return;
            const now = Date.now();
            if (now - lastBeepTime < 500) return;
            playBeep(880, 0.4);
            setTimeout(() => playBeep(587, 0.4), 200);
            lastBeepTime = now;
        }

        // --- DATA FETCHING ---
        setInterval(async () => {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                updateDashboard(data);
            } catch (e) { console.error(e); }
        }, 500);

        function updateDashboard(data) {
            document.getElementById('count-men').innerText = data.men_count;
            document.getElementById('count-women').innerText = data.women_count;

            const riskDisplay = document.getElementById('risk-display');
            const msgDisplay = document.getElementById('msg-display');
            const vidContainer = document.getElementById('video-container');
            
            riskDisplay.innerText = data.status;
            msgDisplay.innerText = data.message;

            // Reset Styles
            riskDisplay.className = "text-4xl font-bold tracking-tight transition-colors duration-300";
            vidContainer.classList.remove('alert-active');

            if (data.status === "SAFE") {
                riskDisplay.classList.add("text-emerald-500");
                msgDisplay.className = "text-lg font-medium text-emerald-100";
            } else if (data.status === "WARNING") {
                riskDisplay.classList.add("text-amber-500");
                msgDisplay.className = "text-lg font-medium text-amber-100";
            } else if (data.status === "CRITICAL") {
                riskDisplay.classList.add("text-red-500");
                msgDisplay.className = "text-lg font-medium text-red-100";
                vidContainer.classList.add('alert-active');
                playSiren();
            }

            // Logs in Sidebar
            const logContainer = document.getElementById('log-container');
            const logCount = document.getElementById('log-count');
            
            if (data.logs.length > 0) {
                logContainer.innerHTML = "";
                logCount.innerText = data.logs.length;
                
                data.logs.forEach(log => {
                    let borderClass = "border-zinc-700";
                    let icon = "fa-info-circle text-blue-500";
                    
                    if(log.level === "WARNING") { borderClass = "border-amber-500"; icon = "fa-exclamation-triangle text-amber-500"; }
                    if(log.level === "CRITICAL") { borderClass = "border-red-500"; icon = "fa-bell text-red-500"; }

                    const logItem = `
                        <div class="bg-zinc-800/50 p-2.5 rounded border-l-2 ${borderClass} flex gap-2 items-start text-xs">
                            <div class="mt-0.5"><i class="fas ${icon}"></i></div>
                            <div class="flex-1">
                                <div class="flex justify-between">
                                    <span class="font-medium text-zinc-200">${log.msg}</span>
                                    <span class="text-zinc-500 font-mono">${log.time}</span>
                                </div>
                                <div class="text-[10px] text-zinc-500 mt-0.5">Loc: ${log.location || 'Unknown'}</div>
                            </div>
                        </div>
                    `;
                    logContainer.innerHTML += logItem;
                });
            }
        }
    </script>
</body>
</html>
"""

# ==========================================
# 2. FLASK BACKEND & LOGIC
# ==========================================
app = Flask(__name__)

# System Settings
CAMERA_LOCATION_NAME = "Sector 4 Entrance"
IS_NIGHT_SIMULATION = True 
MANUAL_ALERT_ACTIVE = False
CSV_LOG_FILE = "security_events.csv"

# Ensure CSV Log exists
if not os.path.exists(CSV_LOG_FILE):
    with open(CSV_LOG_FILE, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Level", "Message", "Location"])

dashboard_state = {
    "status": "SAFE",
    "message": "System Active",
    "men_count": 0,
    "women_count": 0,
    "logs": []
}

# --- Twilio SOS Configuration (use environment variables) ---
# Set these in your environment: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
# TWILIO_FROM_NUMBER, SOS_TO_NUMBER
TWILIO_ACCOUNT_SID = "AC4ef64d47ff7f1f2548908a47a738bec4"
TWILIO_AUTH_TOKEN = "0ff2281b01e0b99036a752da8a63517a"
TWILIO_FROM_NUMBER = "+12297017515"
SOS_TO_NUMBER = "+916200824071"
SOS_THROTTLE_SECONDS = int(os.getenv("SOS_THROTTLE_SECONDS", "60"))
last_sos_time = 0

# Config
faceModel = "opencv_face_detector_uint8.pb"
faceProto = "opencv_face_detector.pbtxt"
genderModel = "gender_net.caffemodel"
genderProto = "gender_deploy.prototxt"

MODEL_MEAN_VALUES = (78.4263377603, 87.7689143744, 114.895847746)
GENDER_LIST = ['Male', 'Female']
padding = 30  # Increased padding for better face extraction at higher resolution

PROXIMITY_THRESHOLD = 180
RISK_MALE_COUNT = 3
PANIC_SPEED_THRESHOLD = 50
SOS_MIN_AREA = 3000
SOS_FRAME_THRESHOLD = 10

# Create Evidence Directory
EVIDENCE_DIR = "evidence"
if not os.path.exists(EVIDENCE_DIR):
    os.makedirs(EVIDENCE_DIR)

# Load Models
try:
    faceNet = cv2.dnn.readNet(faceModel, faceProto)
    genderNet = cv2.dnn.readNet(genderModel, genderProto)
    print("[INFO] Models loaded successfully.")
except Exception as e:
    print(f"[CRITICAL] Models not found. Please download them.\nError: {e}")

# Helpers
def log_alert_to_state(level, message):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    full_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Update In-Memory State (Dashboard)
    if dashboard_state["logs"] and dashboard_state["logs"][0]["msg"] == message:
        # Prevent spamming the same message instantly in UI
        return

    dashboard_state["logs"].insert(0, {
        "time": timestamp, 
        "level": level, 
        "msg": message,
        "location": CAMERA_LOCATION_NAME
    })
    if len(dashboard_state["logs"]) > 20:
        dashboard_state["logs"] = dashboard_state["logs"][:20]

    # 2. Write to Permanent CSV Log (Audit Trail)
    try:
        with open(CSV_LOG_FILE, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([full_timestamp, level, message, CAMERA_LOCATION_NAME])
    except Exception as e:
        print(f"[ERROR] Logging to CSV failed: {e}")

def get_faces(net, frame, conf_threshold=0.7):
    frameOpencvDnn = frame.copy()
    frameHeight = frameOpencvDnn.shape[0]
    frameWidth = frameOpencvDnn.shape[1]
    
    # Optimized blob creation for better detection
    blob = cv2.dnn.blobFromImage(frameOpencvDnn, 1.0, (300, 300), [104, 117, 123], True, False)
    net.setInput(blob)
    detections = net.forward()
    bboxes = []
    
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > conf_threshold:
            x1 = int(detections[0, 0, i, 3] * frameWidth)
            y1 = int(detections[0, 0, i, 4] * frameHeight)
            x2 = int(detections[0, 0, i, 5] * frameWidth)
            y2 = int(detections[0, 0, i, 6] * frameHeight)
            
            # Ensure valid coordinates
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(frameWidth, x2)
            y2 = min(frameHeight, y2)
            
            bboxes.append([x1, y1, x2, y2])
    return frameOpencvDnn, bboxes

def detect_sos_gesture(frame, face_box):
    x1, y1, x2, y2 = face_box
    roi_top = max(0, y1 - 250)
    roi_bottom = min(frame.shape[0], y2 + 50)  # Bottom of face + margin
    roi_left = max(0, x1 - 30) 
    roi_right = min(frame.shape[1], x2 + 30)

    # Ensure valid ROI bounds
    if roi_top >= roi_bottom or roi_left >= roi_right:
        return False
    
    roi = frame[roi_top:roi_bottom, roi_left:roi_right]
    if roi.size == 0: return False

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    lower_skin = np.array([0, 40, 80], dtype=np.uint8)
    upper_skin = np.array([20, 255, 255], dtype=np.uint8)
    mask = cv2.inRange(hsv, lower_skin, upper_skin)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.erode(mask, kernel, iterations=2) 
    mask = cv2.dilate(mask, kernel, iterations=2) 
    
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 3000:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w) / h
            if aspect_ratio < 1.5: return True
    return False

def calculate_distance(pt1, pt2):
    return math.sqrt((pt1[0] - pt2[0])**2 + (pt1[1] - pt2[1])**2)


def send_sos_via_twilio(body):
    """Send an SMS via Twilio REST API. Returns True on success."""
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER and SOS_TO_NUMBER):
        print("[WARN] Twilio credentials not configured; skipping SOS send.")
        return False
    if requests is None:
        print("[WARN] 'requests' library not available; cannot send SOS.")
        return False

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    data = {
        'From': TWILIO_FROM_NUMBER,
        'To': SOS_TO_NUMBER,
        'Body': body
    }
    try:
        resp = requests.post(url, data=data, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), timeout=10)
        if 200 <= resp.status_code < 300:
            print(f"[INFO] SOS sent via Twilio to {SOS_TO_NUMBER}")
            return True
        else:
            print(f"[ERROR] Twilio send failed: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Exception while sending Twilio SMS: {e}")
        return False

# Video Gen
def generate_frames():
    cap = cv2.VideoCapture(0)
    camera_index = 0
    
    # Check if camera opened successfully
    if not cap.isOpened():
        print("[WARNING] Camera 0 not available, trying alternative indices...")
        for i in range(1, 10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                print(f"[SUCCESS] Camera opened at index {i}")
                camera_index = i
                break
        else:
            print("[CRITICAL] No camera found on system!")
            print("[INFO] Serving error frame to frontend...")
            # Generate static error frame instead of crashing
            while True:
                error_img = np.zeros((720, 1280, 3), dtype=np.uint8)
                cv2.putText(error_img, "NO CAMERA DETECTED", (380, 300), cv2.FONT_HERSHEY_DUPLEX, 2, (0, 0, 255), 3)
                ret, buffer = cv2.imencode('.jpg', error_img, [cv2.IMWRITE_JPEG_QUALITY, 90])
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                time.sleep(1)
            return
    
    # Optimize camera settings for best quality
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer for low latency
    
    time.sleep(1.0)
    previous_centroids = {}
    sos_persistence = 0
    last_evidence_time = 0
    frame_count = 0
    
    global MANUAL_ALERT_ACTIVE, last_sos_time
    
    print("[INFO] System Active. Layout: Professional.") 
    print(f"[INFO] Camera Resolution: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")

    try:
        while True:
            success, frame = cap.read()
            if not success: 
                print("[ERROR] Camera disconnected or frame read failed.")
                # Try to reconnect
                cap.release()
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    print("[CRITICAL] Cannot reconnect to camera")
                    break
                continue
            
            frame_count += 1
            
            # Adaptive resolution - maintain 16:9, optimize for display
            height, width = frame.shape[:2]
            target_width = 1280
            target_height = int(target_width * 9 / 16)
            
            # Only process if resolution changed significantly
            if (width != target_width or height != target_height):
                frame = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
            resultImg, bboxes = get_faces(faceNet, frame)
            
            women_centroids = []
            men_centroids = []
            current_centroids = {}
            sos_detected_in_frame = False
            
            frame_status = "SAFE"
            frame_msg = "All Systems Nominal"

            for i, box in enumerate(bboxes):
                x1, y1, x2, y2 = box
                face = frame[max(0,y1-padding):min(y2+padding,frame.shape[0]-1),
                             max(0,x1-padding):min(x2+padding, frame.shape[1]-1)]
                if face.size == 0: continue

                # Higher quality face preprocessing for gender detection
                blob = cv2.dnn.blobFromImage(face, 1.0, (227, 227), MODEL_MEAN_VALUES, swapRB=False)
                genderNet.setInput(blob)
                genderPreds = genderNet.forward()
                gender = GENDER_LIST[genderPreds[0].argmax()]
                gender_conf = genderPreds[0].max()
                
                centroid = ((x1 + x2) // 2, (y1 + y2) // 2)
                current_centroids[i] = centroid
                
                speed = 0
                if i in previous_centroids:
                    speed = calculate_distance(centroid, previous_centroids[i])

                color = (200, 200, 200) # Neutral Gray default
                if gender == 'Female':
                    color = (255, 105, 180) # Pink for visibility in UI
                    women_centroids.append(centroid)
                    
                    # SOS
                    if detect_sos_gesture(frame, box):
                        sos_detected_in_frame = True
                        cv2.rectangle(resultImg, (x1, y1-200), (x2, y1), (0, 255, 255), 1)

                    if sos_detected_in_frame and sos_persistence > SOS_FRAME_THRESHOLD:
                        frame_status = "CRITICAL"
                        frame_msg = "SOS GESTURE DETECTED"
                        cv2.putText(resultImg, "SOS!", (x1, y1 - 50), cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 0, 255), 3)
                        cv2.rectangle(resultImg, (x1, y1-200), (x2, y1), (0,0,255), 3)
                        log_alert_to_state("CRITICAL", "SOS Gesture Confirmed")

                    # Panic
                    if speed > PANIC_SPEED_THRESHOLD:
                        frame_status = "CRITICAL"
                        frame_msg = "Panic: Erratic Motion"
                        cv2.putText(resultImg, "PANIC!", (x1, y1 - 80), cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 0, 255), 3)
                        log_alert_to_state("CRITICAL", "Rapid/Panic Movement")
                else:
                    color = (235, 206, 135) # Light Blue
                    men_centroids.append(centroid)

                # Draw clean bounding boxes with better quality
                cv2.rectangle(resultImg, (x1, y1), (x2, y2), color, 3)
                cv2.putText(resultImg, gender, (x1, y1-10), cv2.FONT_HERSHEY_DUPLEX, 0.8, color, 2)

            if sos_detected_in_frame: sos_persistence += 1
            else: sos_persistence = 0
            previous_centroids = current_centroids

            # Scenarios
            num_men = len(men_centroids)
            num_women = len(women_centroids)

            # Contextual Logic (Day vs Night)
            if num_women == 1 and num_men == 0 and frame_status != "CRITICAL":
                if IS_NIGHT_SIMULATION:
                    frame_status = "WARNING"
                    frame_msg = "Lone Woman (Night)"
                    log_alert_to_state("WARNING", "Lone woman detected at night")
                else:
                    frame_msg = "Environment Safe (Day)"

            if num_women >= 1 and num_men >= RISK_MALE_COUNT:
                close_men = 0
                for w_cen in women_centroids:
                    for m_cen in men_centroids:
                        if calculate_distance(w_cen, m_cen) < PROXIMITY_THRESHOLD:
                            close_men += 1
                            cv2.line(resultImg, w_cen, m_cen, (0, 0, 255), 2)
                if close_men >= 2:
                    frame_status = "CRITICAL"
                    frame_msg = "Harassment Risk"
                    log_alert_to_state("CRITICAL", "Woman surrounded by group")

                    # Automatic SOS via Twilio when harassment pattern detected
                    try:
                        now = time.time()
                        if now - last_sos_time > SOS_THROTTLE_SECONDS:
                            sos_msg = (
                                f"SOS: Harassment risk detected at {CAMERA_LOCATION_NAME} on "
                                f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. "
                                f"Counts: {num_women} women, {num_men} men."
                            )

                            def _send_sos(msg):
                                ok = send_sos_via_twilio(msg)
                                if ok:
                                    log_alert_to_state("INFO", "SOS SMS sent via Twilio")
                                else:
                                    log_alert_to_state("WARNING", "SOS SMS failed")

                            threading.Thread(target=_send_sos, args=(sos_msg,), daemon=True).start()
                            last_sos_time = now
                    except Exception as e:
                        print(f"[ERROR] Failed to start SOS thread: {e}")

            # Manual Alert Override
            if MANUAL_ALERT_ACTIVE:
                frame_status = "CRITICAL"
                frame_msg = "MANUAL OVERRIDE: ALARM"
                cv2.putText(resultImg, "MANUAL ALARM", (400, 300), cv2.FONT_HERSHEY_DUPLEX, 2.0, (0, 0, 255), 4)
                
                # Auto-reset manual alert after 5 seconds to prevent stuck state
                if int(time.time()) % 10 == 0:
                    MANUAL_ALERT_ACTIVE = False

            # --- EVIDENCE CAPTURE (Auto-Save) ---
            if frame_status == "CRITICAL":
                current_time = time.time()
                if current_time - last_evidence_time > 3.0: 
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{EVIDENCE_DIR}/evidence_{timestamp}.jpg"
                    
                    # Threaded save to prevent "stutter"
                    threading.Thread(target=cv2.imwrite, args=(filename, frame)).start()
                    
                    log_alert_to_state("INFO", f"Evidence Saved: {filename}")
                    last_evidence_time = current_time
                    cv2.rectangle(resultImg, (0,0), (1280,720), (0,255,255), 10)
                    frame_msg = "DISPATCHING ALERT... EVID SAVED"

            # Update State
            dashboard_state["status"] = frame_status
            dashboard_state["message"] = frame_msg
            dashboard_state["men_count"] = num_men
            dashboard_state["women_count"] = num_women

            ret, buffer = cv2.imencode('.jpg', resultImg, [cv2.IMWRITE_JPEG_QUALITY, 90])
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    finally:
        cap.release()

# Routes
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/video_feed')
def video_feed():
    try:
        return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        print(f"[ERROR] Video feed error: {e}")
        # Return error frame
        return Response(generate_error_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_error_frame():
    """Generate a placeholder frame when camera unavailable"""
    # Create a simple error image
    error_img = np.zeros((720, 1280, 3), dtype=np.uint8)
    cv2.putText(error_img, "CAMERA NOT AVAILABLE", (350, 200), cv2.FONT_HERSHEY_DUPLEX, 2, (0, 0, 255), 3)
    cv2.putText(error_img, "Troubleshooting:", (100, 350), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(error_img, "1. Ensure camera is connected", (120, 400), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
    cv2.putText(error_img, "2. Check no other app is using camera", (120, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
    cv2.putText(error_img, "3. Run as Administrator if needed", (120, 500), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
    cv2.putText(error_img, "4. Restart the application", (120, 550), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
    
    while True:
        ret, buffer = cv2.imencode('.jpg', error_img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(1)  # Update once per second

@app.route('/api/stats')
def get_stats():
    return jsonify(dashboard_state)

@app.route('/api/toggle_mode', methods=['POST'])
def toggle_mode():
    global IS_NIGHT_SIMULATION
    IS_NIGHT_SIMULATION = not IS_NIGHT_SIMULATION
    return jsonify({"is_night": IS_NIGHT_SIMULATION})

@app.route('/api/trigger_manual', methods=['POST'])
def trigger_manual():
    global MANUAL_ALERT_ACTIVE, last_sos_time
    MANUAL_ALERT_ACTIVE = True

    def _send_manual_sos():
        global last_sos_time
        try:
            now = time.time()
            if now - last_sos_time > SOS_THROTTLE_SECONDS:
                sos_msg = (
                    f"SOS: Manual alert triggered at {CAMERA_LOCATION_NAME} on "
                    f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."
                )
                ok = send_sos_via_twilio(sos_msg)
                if ok:
                    log_alert_to_state("INFO", "Manual SOS SMS sent via Twilio")
                else:
                    log_alert_to_state("WARNING", "Manual SOS SMS failed")
                last_sos_time = now
            else:
                log_alert_to_state("INFO", "Manual SOS suppressed (throttle)")
        except Exception as e:
            print(f"[ERROR] Manual SOS thread exception: {e}")

    threading.Thread(target=_send_manual_sos, daemon=True).start()
    return jsonify({"status": "triggered"})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("GUARDIANEYE SYSTEM STARTING")
    print("="*60)
    print("[INFO] Models loaded successfully." if 'faceNet' in dir() else "[WARNING] Models not loaded yet")
    print("[INFO] Flask server starting on http://localhost:5000")
    print("[INFO] Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    try:
        app.run(debug=False, threaded=True, port=5000, use_reloader=False)
    except Exception as e:
        print(f"[ERROR] Failed to start Flask: {e}")
        import traceback
        traceback.print_exc()