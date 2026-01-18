/**
 * Spaxiom Edge - Frontend Application
 */

function app() {
    return {
        // Navigation
        currentPage: 'dashboard',
        
        // Data
        sensors: [],
        zones: [],
        patterns: [],
        agents: [],
        patternTypes: [],
        systemHealth: null,
        systemInfo: null,
        sensorHealth: {},
        
        // Modal states
        showAddSensorModal: false,
        showAddZoneModal: false,
        showAddPatternModal: false,
        showPatternTestModal: false,
        
        // Pattern configuration
        selectedPatternType: null,
        patternTestResult: null,
        
        // Form data
        newSensor: {
            name: '',
            sensor_type: 'random',
            location: [0, 0, 0],
            config: {},
            enabled: true
        },
        newZone: {
            name: '',
            zone_type: 'rectangle',
            geometry: { x: 0, y: 0, width: 10, height: 10 }
        },
        newPattern: {
            name: '',
            pattern_type: '',
            config: {},
            zones: [],
            sensors: [],
            enabled: true
        },
        
        // Lifecycle
        async init() {
            await this.loadAll();
            // Refresh data periodically
            setInterval(() => this.refreshHealth(), 5000);
        },
        
        // Data loading
        async loadAll() {
            await Promise.all([
                this.loadSensors(),
                this.loadZones(),
                this.loadPatterns(),
                this.loadAgents(),
                this.loadPatternTypes(),
                this.loadSystemHealth(),
                this.loadSystemInfo()
            ]);
        },
        
        async loadSensors() {
            try {
                const response = await fetch('/api/sensors');
                this.sensors = await response.json();
            } catch (error) {
                console.error('Failed to load sensors:', error);
            }
        },
        
        async loadZones() {
            try {
                const response = await fetch('/api/zones');
                this.zones = await response.json();
            } catch (error) {
                console.error('Failed to load zones:', error);
            }
        },
        
        async loadPatterns() {
            try {
                const response = await fetch('/api/patterns');
                this.patterns = await response.json();
            } catch (error) {
                console.error('Failed to load patterns:', error);
            }
        },
        
        async loadPatternTypes() {
            try {
                const response = await fetch('/api/patterns/types');
                this.patternTypes = await response.json();
            } catch (error) {
                console.error('Failed to load pattern types:', error);
            }
        },
        
        async loadAgents() {
            try {
                const response = await fetch('/api/agents');
                this.agents = await response.json();
            } catch (error) {
                console.error('Failed to load agents:', error);
            }
        },
        
        async loadSystemHealth() {
            try {
                const response = await fetch('/api/system/health');
                this.systemHealth = await response.json();
            } catch (error) {
                console.error('Failed to load system health:', error);
            }
        },
        
        async loadSystemInfo() {
            try {
                const response = await fetch('/api/system/info');
                this.systemInfo = await response.json();
            } catch (error) {
                console.error('Failed to load system info:', error);
            }
        },
        
        async refreshHealth() {
            await this.loadSystemHealth();
            // Update sensor health for displayed sensors
            for (const sensor of this.sensors) {
                try {
                    const response = await fetch(`/api/sensors/${sensor.id}/health`);
                    this.sensorHealth[sensor.id] = await response.json();
                } catch (error) {
                    // Ignore individual sensor health errors
                }
            }
        },
        
        // Sensor operations
        async addSensor() {
            try {
                const response = await fetch('/api/sensors', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.newSensor)
                });
                
                if (response.ok) {
                    this.showAddSensorModal = false;
                    this.newSensor = { name: '', sensor_type: 'random', location: null, config: {}, enabled: true };
                    await this.loadSensors();
                } else {
                    const error = await response.json();
                    alert('Failed to add sensor: ' + (error.detail || 'Unknown error'));
                }
            } catch (error) {
                console.error('Failed to add sensor:', error);
                alert('Failed to add sensor');
            }
        },
        
        async testSensor(sensorId) {
            try {
                const response = await fetch(`/api/sensors/${sensorId}/test`, { method: 'POST' });
                const result = await response.json();
                
                if (result.success) {
                    alert(`Sensor read successful!\nValue: ${result.value}\nTime: ${result.read_time_ms?.toFixed(2)}ms`);
                } else {
                    alert(`Sensor test failed: ${result.error}`);
                }
            } catch (error) {
                console.error('Failed to test sensor:', error);
                alert('Failed to test sensor');
            }
        },
        
        async deleteSensor(sensorId) {
            if (!confirm('Are you sure you want to delete this sensor?')) return;
            
            try {
                const response = await fetch(`/api/sensors/${sensorId}`, { method: 'DELETE' });
                if (response.ok) {
                    await this.loadSensors();
                } else {
                    alert('Failed to delete sensor');
                }
            } catch (error) {
                console.error('Failed to delete sensor:', error);
            }
        },
        
        // Zone operations
        async addZone() {
            try {
                const response = await fetch('/api/zones', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.newZone)
                });
                
                if (response.ok) {
                    this.showAddZoneModal = false;
                    this.newZone = { name: '', zone_type: 'rectangle', geometry: { x: 0, y: 0, width: 10, height: 10 } };
                    await this.loadZones();
                } else {
                    const error = await response.json();
                    alert('Failed to add zone: ' + (error.detail || 'Unknown error'));
                }
            } catch (error) {
                console.error('Failed to add zone:', error);
                alert('Failed to add zone');
            }
        },
        
        async deleteZone(zoneId) {
            if (!confirm('Are you sure you want to delete this zone?')) return;
            
            try {
                const response = await fetch(`/api/zones/${zoneId}`, { method: 'DELETE' });
                if (response.ok) {
                    await this.loadZones();
                } else {
                    alert('Failed to delete zone');
                }
            } catch (error) {
                console.error('Failed to delete zone:', error);
            }
        },
        
        // Pattern operations
        onPatternTypeChange() {
            const typeId = this.newPattern.pattern_type;
            this.selectedPatternType = this.patternTypes.find(t => t.type_id === typeId) || null;
            // Reset config when type changes
            this.newPattern.config = {};
        },
        
        selectPatternType(ptype) {
            this.newPattern.pattern_type = ptype.type_id;
            this.selectedPatternType = ptype;
            this.showAddPatternModal = true;
        },
        
        async addPattern() {
            try {
                const response = await fetch('/api/patterns', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.newPattern)
                });
                
                if (response.ok) {
                    this.showAddPatternModal = false;
                    this.newPattern = { name: '', pattern_type: '', config: {}, zones: [], sensors: [], enabled: true };
                    this.selectedPatternType = null;
                    await this.loadPatterns();
                } else {
                    const error = await response.json();
                    alert('Failed to add pattern: ' + (error.detail || 'Unknown error'));
                }
            } catch (error) {
                console.error('Failed to add pattern:', error);
                alert('Failed to add pattern');
            }
        },
        
        async testPattern(patternId) {
            try {
                const response = await fetch(`/api/patterns/${patternId}/test`, { method: 'POST' });
                this.patternTestResult = await response.json();
                this.showPatternTestModal = true;
            } catch (error) {
                console.error('Failed to test pattern:', error);
                alert('Failed to test pattern');
            }
        },
        
        configurePattern(pattern) {
            // Open modal with pattern configuration
            this.newPattern = { ...pattern };
            this.selectedPatternType = this.patternTypes.find(t => t.type_id === pattern.pattern_type);
            this.showAddPatternModal = true;
        },
        
        async deletePattern(patternId) {
            if (!confirm('Are you sure you want to delete this pattern?')) return;
            
            try {
                const response = await fetch(`/api/patterns/${patternId}`, { method: 'DELETE' });
                if (response.ok) {
                    await this.loadPatterns();
                } else {
                    alert('Failed to delete pattern');
                }
            } catch (error) {
                console.error('Failed to delete pattern:', error);
            }
        },
        
        async deployPattern(patternId) {
            try {
                const response = await fetch('/api/agents', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ pattern_id: patternId })
                });
                
                if (response.ok) {
                    await this.loadAgents();
                    alert('Agent deployed successfully');
                } else {
                    const error = await response.json();
                    alert('Failed to deploy pattern: ' + (error.detail || 'Unknown error'));
                }
            } catch (error) {
                console.error('Failed to deploy pattern:', error);
                alert('Failed to deploy pattern');
            }
        },
        
        // Agent operations
        async startAgent(agentId) {
            try {
                const response = await fetch(`/api/agents/${agentId}/start`, { method: 'POST' });
                if (response.ok) {
                    await this.loadAgents();
                } else {
                    const error = await response.json();
                    alert('Failed to start agent: ' + (error.detail || 'Unknown error'));
                }
            } catch (error) {
                console.error('Failed to start agent:', error);
            }
        },
        
        async stopAgent(agentId) {
            try {
                const response = await fetch(`/api/agents/${agentId}/stop`, { method: 'POST' });
                if (response.ok) {
                    await this.loadAgents();
                } else {
                    const error = await response.json();
                    alert('Failed to stop agent: ' + (error.detail || 'Unknown error'));
                }
            } catch (error) {
                console.error('Failed to stop agent:', error);
            }
        },
        
        async deleteAgent(agentId) {
            if (!confirm('Are you sure you want to delete this agent?')) return;
            
            try {
                const response = await fetch(`/api/agents/${agentId}`, { method: 'DELETE' });
                if (response.ok) {
                    await this.loadAgents();
                } else {
                    alert('Failed to delete agent');
                }
            } catch (error) {
                console.error('Failed to delete agent:', error);
            }
        },
        
        // Zone operations
        editZone(zone) {
            this.newZone = { ...zone };
            this.showAddZoneModal = true;
        },
        
        formatGeometry(geometry) {
            if (!geometry) return 'N/A';
            if (geometry.width && geometry.height) {
                return `${geometry.width}x${geometry.height} at (${geometry.x || 0}, ${geometry.y || 0})`;
            }
            if (geometry.radius) {
                return `r=${geometry.radius} at (${geometry.center_x || 0}, ${geometry.center_y || 0})`;
            }
            if (geometry.points) {
                return `${geometry.points.length} points`;
            }
            return JSON.stringify(geometry).slice(0, 30) + '...';
        },
        
        // Utilities
        formatUptime(seconds) {
            if (!seconds) return '0s';
            
            const days = Math.floor(seconds / 86400);
            const hours = Math.floor((seconds % 86400) / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            
            if (days > 0) return `${days}d ${hours}h`;
            if (hours > 0) return `${hours}h ${minutes}m`;
            if (minutes > 0) return `${minutes}m`;
            return `${Math.floor(seconds)}s`;
        }
    };
}

/**
 * Zone Editor Component
 */
function zoneEditor() {
    return {
        editorTool: 'select',
        showGrid: true,
        showSensors: true,
        selectedZone: null,
        zonePreview: null,
        drawing: false,
        startPoint: null,
        
        async init() {
            await this.loadPreview();
            this.render();
        },
        
        async loadPreview() {
            try {
                const response = await fetch('/api/zones/preview');
                this.zonePreview = await response.json();
            } catch (error) {
                console.error('Failed to load zone preview:', error);
            }
        },
        
        render() {
            const canvas = document.getElementById('zoneCanvas');
            if (!canvas) return;
            
            const ctx = canvas.getContext('2d');
            const width = canvas.width;
            const height = canvas.height;
            
            // Clear canvas
            ctx.fillStyle = '#f8f9fa';
            ctx.fillRect(0, 0, width, height);
            
            // Draw grid
            if (this.showGrid) {
                ctx.strokeStyle = '#e9ecef';
                ctx.lineWidth = 1;
                const gridSize = 20;
                
                for (let x = 0; x <= width; x += gridSize) {
                    ctx.beginPath();
                    ctx.moveTo(x, 0);
                    ctx.lineTo(x, height);
                    ctx.stroke();
                }
                for (let y = 0; y <= height; y += gridSize) {
                    ctx.beginPath();
                    ctx.moveTo(0, y);
                    ctx.lineTo(width, y);
                    ctx.stroke();
                }
            }
            
            // Draw zones
            if (this.zonePreview?.zones) {
                for (const zone of this.zonePreview.zones) {
                    this.drawZone(ctx, zone);
                }
            }
            
            // Draw sensors
            if (this.showSensors && this.zonePreview?.sensors) {
                for (const sensor of this.zonePreview.sensors) {
                    this.drawSensor(ctx, sensor);
                }
            }
        },
        
        drawZone(ctx, zone) {
            const scale = 5; // Scale factor for visualization
            const geom = zone.geometry || {};
            
            ctx.fillStyle = zone === this.selectedZone ? 'rgba(102, 126, 234, 0.3)' : 'rgba(102, 126, 234, 0.15)';
            ctx.strokeStyle = zone === this.selectedZone ? '#667eea' : '#9ca3af';
            ctx.lineWidth = zone === this.selectedZone ? 2 : 1;
            
            if (zone.type === 'rectangle') {
                const x = (geom.x || 0) * scale;
                const y = (geom.y || 0) * scale;
                const w = (geom.width || 10) * scale;
                const h = (geom.height || 10) * scale;
                
                ctx.fillRect(x, y, w, h);
                ctx.strokeRect(x, y, w, h);
                
                // Draw label
                ctx.fillStyle = '#333';
                ctx.font = '12px sans-serif';
                ctx.fillText(zone.name, x + 4, y + 14);
            } else if (zone.type === 'circle') {
                const cx = (geom.center_x || 50) * scale;
                const cy = (geom.center_y || 50) * scale;
                const r = (geom.radius || 10) * scale;
                
                ctx.beginPath();
                ctx.arc(cx, cy, r, 0, Math.PI * 2);
                ctx.fill();
                ctx.stroke();
                
                ctx.fillStyle = '#333';
                ctx.font = '12px sans-serif';
                ctx.fillText(zone.name, cx - 20, cy);
            }
        },
        
        drawSensor(ctx, sensor) {
            const scale = 5;
            const x = (sensor.x || 0) * scale;
            const y = (sensor.y || 0) * scale;
            
            ctx.fillStyle = '#28a745';
            ctx.beginPath();
            ctx.arc(x, y, 6, 0, Math.PI * 2);
            ctx.fill();
            
            ctx.fillStyle = '#fff';
            ctx.font = '8px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('S', x, y + 3);
            ctx.textAlign = 'left';
        },
        
        onCanvasMouseDown(event) {
            if (this.editorTool === 'select') {
                this.handleSelect(event);
            } else {
                this.drawing = true;
                const rect = event.target.getBoundingClientRect();
                this.startPoint = {
                    x: event.clientX - rect.left,
                    y: event.clientY - rect.top
                };
            }
        },
        
        onCanvasMouseMove(event) {
            if (!this.drawing) return;
            // Preview drawing could be added here
        },
        
        onCanvasMouseUp(event) {
            if (!this.drawing) return;
            this.drawing = false;
            
            const rect = event.target.getBoundingClientRect();
            const endPoint = {
                x: event.clientX - rect.left,
                y: event.clientY - rect.top
            };
            
            // Create zone from drawing
            if (this.editorTool === 'rectangle') {
                const scale = 5;
                const x = Math.min(this.startPoint.x, endPoint.x) / scale;
                const y = Math.min(this.startPoint.y, endPoint.y) / scale;
                const w = Math.abs(endPoint.x - this.startPoint.x) / scale;
                const h = Math.abs(endPoint.y - this.startPoint.y) / scale;
                
                if (w > 1 && h > 1) {
                    const name = prompt('Zone name:');
                    if (name) {
                        this.createZoneFromCanvas(name, 'rectangle', { x, y, width: w, height: h });
                    }
                }
            }
        },
        
        handleSelect(event) {
            // Simple hit testing for zones
            const rect = event.target.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;
            const scale = 5;
            
            this.selectedZone = null;
            
            if (this.zonePreview?.zones) {
                for (const zone of this.zonePreview.zones) {
                    const geom = zone.geometry || {};
                    if (zone.type === 'rectangle') {
                        const zx = (geom.x || 0) * scale;
                        const zy = (geom.y || 0) * scale;
                        const zw = (geom.width || 10) * scale;
                        const zh = (geom.height || 10) * scale;
                        
                        if (x >= zx && x <= zx + zw && y >= zy && y <= zy + zh) {
                            this.selectedZone = zone;
                            break;
                        }
                    }
                }
            }
            
            this.render();
        },
        
        async createZoneFromCanvas(name, type, geometry) {
            try {
                const response = await fetch('/api/zones', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, zone_type: type, geometry })
                });
                
                if (response.ok) {
                    await this.loadPreview();
                    this.render();
                    // Trigger parent refresh
                    window.dispatchEvent(new CustomEvent('zones-updated'));
                } else {
                    const error = await response.json();
                    alert('Failed to create zone: ' + (error.detail || 'Unknown error'));
                }
            } catch (error) {
                console.error('Failed to create zone:', error);
            }
        }
    };
}
