const state = {
    adminPin: '1234',
    mode: 'monitor',
    eventSource: null,
    patternTypes: [],
    sensors: [],
    zones: [],
    patterns: [],
    agents: [],
};

const el = (id) => document.getElementById(id);

const formatUptime = (seconds) => {
    if (!seconds && seconds !== 0) return '--';
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
};

const formatTimestamp = (ts) => {
    if (!ts) return '';
    const date = new Date(ts);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const fetchJson = async (path, options = {}) => {
    const response = await fetch(path, options);
    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || response.statusText);
    }
    return response.json();
};

const setHealth = (status) => {
    const pill = el('healthStatus');
    pill.textContent = status || 'unknown';
    pill.classList.remove('healthy', 'degraded', 'unhealthy');
    if (status) {
        pill.classList.add(status);
    }
};

const renderAgents = () => {
    const grid = el('agentGrid');
    grid.innerHTML = '';
    if (!state.agents.length) {
        grid.innerHTML = '<div class="helper-text">No agents deployed.</div>';
        return;
    }
    state.agents.forEach((agent) => {
        const card = document.createElement('div');
        card.className = 'agent-card';
        card.innerHTML = `
            <div>
                <div>${agent.name}</div>
                <div class="helper-text">${agent.pattern_id?.slice(0, 8) || ''}</div>
            </div>
            <div class="agent-status ${agent.status}">${agent.status}</div>
        `;
        grid.appendChild(card);
    });
};

const renderEvents = (events) => {
    const feed = el('eventFeed');
    feed.innerHTML = '';
    events.slice(0, 20).forEach((event) => {
        const item = document.createElement('div');
        item.className = 'event-item';
        item.innerHTML = `
            <div class="event-title">${event.event_type || event.type || 'event'}</div>
            <div class="event-meta">${formatTimestamp(event.timestamp)} · ${event.source || 'system'}</div>
        `;
        feed.appendChild(item);
    });
};

const loadDashboard = async () => {
    const [health, info, sensors, patterns, agents] = await Promise.all([
        fetchJson('/api/system/health'),
        fetchJson('/api/system/info'),
        fetchJson('/api/sensors'),
        fetchJson('/api/patterns'),
        fetchJson('/api/agents'),
    ]);

    state.sensors = sensors;
    state.patterns = patterns;
    state.agents = agents;

    el('hostname').textContent = info.hostname || 'edge';
    el('version').textContent = info.version || '--';
    el('platform').textContent = info.platform || '--';
    el('sensorsCount').textContent = sensors.length;
    el('patternsCount').textContent = patterns.length;
    el('agentsCount').textContent = agents.length;
    el('uptime').textContent = formatUptime(health.uptime_seconds);
    el('cpu').textContent = `${(health.cpu_usage_percent || 0).toFixed(1)}%`;
    el('memory').textContent = `${(health.memory_usage_percent || 0).toFixed(1)}%`;
    el('disk').textContent = `${(health.disk_usage_percent || 0).toFixed(1)}%`;
    setHealth(health.status);
    renderAgents();
};

const loadEvents = async () => {
    try {
        const events = await fetchJson('/api/events?limit=20');
        renderEvents(events);
    } catch (error) {
        // Ignore
    }
};

const connectEventStream = () => {
    if (state.eventSource) {
        state.eventSource.close();
    }
    const feedStatus = el('feedStatus');
    state.eventSource = new EventSource('/api/events/stream');
    state.eventSource.onopen = () => {
        feedStatus.textContent = 'live';
    };
    state.eventSource.onerror = () => {
        feedStatus.textContent = 'offline';
    };
    state.eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            loadEvents();
            if (data.event_type) {
                feedStatus.textContent = 'live';
            }
        } catch (error) {
            // Ignore
        }
    };
};

const updateClock = () => {
    el('time').textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const openSetup = () => {
    el('pinInput').value = '';
    el('pinError').textContent = '';
    el('pinModal').classList.remove('hidden');
};

const unlockSetup = () => {
    const pin = el('pinInput').value.trim();
    if (pin === state.adminPin) {
        el('pinModal').classList.add('hidden');
        el('setupPane').classList.remove('hidden');
        state.mode = 'setup';
        loadSetupData();
    } else {
        el('pinError').textContent = 'Incorrect PIN';
    }
};

const closeSetup = () => {
    el('setupPane').classList.add('hidden');
    state.mode = 'monitor';
};

const updatePin = () => {
    const current = el('pinCurrent').value.trim();
    const next = el('pinNew').value.trim();
    const confirm = el('pinConfirm').value.trim();
    const message = el('pinMessage');
    if (current !== state.adminPin) {
        message.textContent = 'Current PIN is incorrect.';
        return;
    }
    if (next.length < 4) {
        message.textContent = 'New PIN must be at least 4 digits.';
        return;
    }
    if (next !== confirm) {
        message.textContent = 'PIN confirmation does not match.';
        return;
    }
    state.adminPin = next;
    localStorage.setItem('spaxiomAdminPin', next);
    message.textContent = 'PIN updated.';
    el('pinCurrent').value = '';
    el('pinNew').value = '';
    el('pinConfirm').value = '';
};

const loadSetupData = async () => {
    try {
        const [sensors, zones, patterns, patternTypes] = await Promise.all([
            fetchJson('/api/sensors'),
            fetchJson('/api/zones'),
            fetchJson('/api/patterns'),
            fetchJson('/api/patterns/types'),
        ]);
        state.sensors = sensors;
        state.zones = zones;
        state.patterns = patterns;
        state.patternTypes = patternTypes;
        populateSelect('patternZones', zones, 'name');
        populateSelect('patternSensors', sensors, 'name');
        populateSelect('agentPattern', patterns, 'name');
        populatePatternTypes();
    } catch (error) {
        // Ignore
    }
};

const populateSelect = (id, items, labelKey) => {
    const select = el(id);
    select.innerHTML = '';
    items.forEach((item) => {
        const option = document.createElement('option');
        option.value = item.id;
        option.textContent = item[labelKey] || item.id;
        select.appendChild(option);
    });
};

const populatePatternTypes = () => {
    const select = el('patternType');
    select.innerHTML = '';
    state.patternTypes.forEach((ptype) => {
        const option = document.createElement('option');
        option.value = ptype.type_id;
        option.textContent = ptype.name;
        select.appendChild(option);
    });
    renderPatternConfig();
};

const renderPatternConfig = () => {
    const container = el('patternConfig');
    container.innerHTML = '';
    const selected = state.patternTypes.find((p) => p.type_id === el('patternType').value);
    el('patternDescription').textContent = selected?.description || '';
    const properties = selected?.config_schema?.properties || {};
    Object.entries(properties).forEach(([key, def]) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'config-field';
        const label = document.createElement('label');
        label.textContent = key.replace(/_/g, ' ');
        const input = document.createElement('input');
        input.type = def.type === 'number' || def.type === 'integer' ? 'number' : 'text';
        input.step = def.type === 'integer' ? '1' : 'any';
        input.placeholder = def.default ?? '';
        input.dataset.key = key;
        wrapper.appendChild(label);
        wrapper.appendChild(input);
        container.appendChild(wrapper);
    });
};

const readConfigFields = () => {
    const config = {};
    document.querySelectorAll('#patternConfig input').forEach((input) => {
        if (input.value === '') return;
        if (input.type === 'number') {
            config[input.dataset.key] = Number(input.value);
        } else {
            config[input.dataset.key] = input.value;
        }
    });
    return config;
};

const addSensor = async () => {
    try {
        const payload = {
            name: el('sensorName').value.trim(),
            sensor_type: el('sensorType').value,
            location: [
                Number(el('sensorX').value || 0),
                Number(el('sensorY').value || 0),
                Number(el('sensorZ').value || 0),
            ],
            config: {},
            enabled: true,
        };
        await fetchJson('/api/sensors', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        el('sensorMessage').textContent = 'Sensor added.';
        await loadSetupData();
        await loadDashboard();
    } catch (error) {
        el('sensorMessage').textContent = 'Failed to add sensor.';
    }
};

const addZone = async () => {
    try {
        const payload = {
            name: el('zoneName').value.trim(),
            zone_type: el('zoneType').value,
            geometry: {
                x: Number(el('zoneX').value || 0),
                y: Number(el('zoneY').value || 0),
                width: Number(el('zoneW').value || 10),
                height: Number(el('zoneH').value || 10),
            },
        };
        await fetchJson('/api/zones', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        el('zoneMessage').textContent = 'Zone added.';
        await loadSetupData();
    } catch (error) {
        el('zoneMessage').textContent = 'Failed to add zone.';
    }
};

const addPattern = async () => {
    try {
        const selectedZones = Array.from(el('patternZones').selectedOptions).map((opt) => opt.value);
        const selectedSensors = Array.from(el('patternSensors').selectedOptions).map((opt) => opt.value);
        const payload = {
            name: el('patternName').value.trim(),
            pattern_type: el('patternType').value,
            config: readConfigFields(),
            zones: selectedZones,
            sensors: selectedSensors,
            enabled: true,
        };
        await fetchJson('/api/patterns', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        el('patternMessage').textContent = 'Pattern added.';
        await loadSetupData();
        await loadDashboard();
    } catch (error) {
        el('patternMessage').textContent = 'Failed to add pattern.';
    }
};

const deployAgent = async () => {
    try {
        const payload = {
            name: el('agentName').value.trim(),
            pattern_id: el('agentPattern').value,
            config: {},
        };
        await fetchJson('/api/agents', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        el('agentMessage').textContent = 'Agent deployed.';
        await loadDashboard();
    } catch (error) {
        el('agentMessage').textContent = 'Failed to deploy agent.';
    }
};

const init = async () => {
    const savedPin = localStorage.getItem('spaxiomAdminPin');
    if (savedPin) {
        state.adminPin = savedPin;
    } else {
        localStorage.setItem('spaxiomAdminPin', state.adminPin);
    }

    el('setupButton').addEventListener('click', openSetup);
    el('pinCancel').addEventListener('click', () => el('pinModal').classList.add('hidden'));
    el('pinConfirm').addEventListener('click', unlockSetup);
    el('setupClose').addEventListener('click', closeSetup);
    el('setupSavePin').addEventListener('click', updatePin);
    el('patternType').addEventListener('change', renderPatternConfig);
    el('addSensorBtn').addEventListener('click', addSensor);
    el('addZoneBtn').addEventListener('click', addZone);
    el('addPatternBtn').addEventListener('click', addPattern);
    el('deployAgentBtn').addEventListener('click', deployAgent);
    el('openFullUi').addEventListener('click', () => window.open('/', '_blank'));

    updateClock();
    setInterval(updateClock, 1000 * 30);

    await loadDashboard();
    await loadEvents();
    connectEventStream();
    setInterval(loadDashboard, 5000);
    setInterval(loadEvents, 15000);
};

init();
