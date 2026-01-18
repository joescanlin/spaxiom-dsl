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
        systemHealth: null,
        systemInfo: null,
        sensorHealth: {},
        
        // Modal states
        showAddSensorModal: false,
        showAddZoneModal: false,
        showAddPatternModal: false,
        
        // Form data
        newSensor: {
            name: '',
            sensor_type: 'random',
            location: null,
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
            pattern_type: 'occupancy_field',
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
        async addPattern() {
            try {
                const response = await fetch('/api/patterns', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.newPattern)
                });
                
                if (response.ok) {
                    this.showAddPatternModal = false;
                    this.newPattern = { name: '', pattern_type: 'occupancy_field', config: {}, zones: [], sensors: [], enabled: true };
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
