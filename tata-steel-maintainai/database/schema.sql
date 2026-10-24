-- TATA STEEL MAINTAINAI SQLite Database Schema
-- Production maintenance records, sensor telemetry, failures, schedules, predictions, and audit trail

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS machines (
    machine_id TEXT PRIMARY KEY,
    equipment_type TEXT NOT NULL,
    production_area TEXT NOT NULL,
    criticality TEXT NOT NULL,
    commissioning_date TEXT NOT NULL,
    operating_status TEXT NOT NULL DEFAULT 'Running',
    operating_hours REAL NOT NULL DEFAULT 0.0,
    last_maintenance_date TEXT NOT NULL,
    maintenance_interval_days INTEGER NOT NULL,
    estimated_repair_cost REAL NOT NULL,
    downtime_cost_per_hour REAL NOT NULL,
    expected_maintenance_duration_hours REAL NOT NULL,
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sensor_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    machine_id TEXT NOT NULL,
    temperature REAL NOT NULL,
    vibration REAL NOT NULL,
    pressure REAL NOT NULL,
    rotational_speed REAL NOT NULL,
    electrical_current REAL NOT NULL,
    operating_load REAL NOT NULL,
    operating_hours REAL NOT NULL,
    is_anomaly INTEGER DEFAULT 0,
    anomaly_score REAL DEFAULT 0.0,
    FOREIGN KEY (machine_id) REFERENCES machines(machine_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sensor_machine_time ON sensor_readings(machine_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_sensor_time ON sensor_readings(timestamp);

CREATE TABLE IF NOT EXISTS failure_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id TEXT NOT NULL,
    failure_timestamp TEXT NOT NULL,
    failure_category TEXT NOT NULL,
    affected_component TEXT,
    downtime_duration REAL NOT NULL, -- hours
    repair_expense REAL NOT NULL,     -- currency
    root_cause TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (machine_id) REFERENCES machines(machine_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_failures_machine ON failure_events(machine_id, failure_timestamp);

CREATE TABLE IF NOT EXISTS maintenance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id TEXT NOT NULL,
    maintenance_date TEXT NOT NULL,
    maintenance_type TEXT NOT NULL, -- 'Preventive', 'Corrective', 'Emergency', 'Predictive Inspection'
    components_inspected_or_replaced TEXT,
    maintenance_duration REAL NOT NULL, -- hours
    maintenance_cost REAL NOT NULL,
    technician_or_team_assignment TEXT,
    work_order_status TEXT NOT NULL DEFAULT 'Completed',
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (machine_id) REFERENCES machines(machine_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_maint_machine ON maintenance_records(machine_id, maintenance_date);

CREATE TABLE IF NOT EXISTS production_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    production_area TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    planned_shift TEXT NOT NULL, -- 'Shift A (06:00-14:00)', 'Shift B (14:00-22:00)', 'Shift C (22:00-06:00)'
    planned_shutdown INTEGER DEFAULT 0, -- 1 if shutdown window
    shutdown_type TEXT, -- 'Major Campaign Shutdown', 'Weekly PM Stoppage', 'None'
    production_demand_pct REAL DEFAULT 100.0,
    machine_availability_required TEXT DEFAULT 'Full',
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_prod_area_time ON production_schedules(production_area, start_time, end_time);

CREATE TABLE IF NOT EXISTS technicians (
    tech_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    specialization TEXT NOT NULL, -- 'Mechanical', 'Electrical', 'Hydraulic', 'Instrumentation'
    skill_level TEXT NOT NULL,
    shift TEXT NOT NULL DEFAULT 'Day',
    hourly_rate REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'Available'
);

CREATE TABLE IF NOT EXISTS spare_parts (
    part_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    equipment_type TEXT NOT NULL,
    unit_cost REAL NOT NULL,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    reorder_lead_days INTEGER NOT NULL DEFAULT 7
);

CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_timestamp TEXT NOT NULL,
    machine_id TEXT NOT NULL,
    forecast_horizon_hours INTEGER NOT NULL,
    failure_probability REAL NOT NULL,
    risk_category TEXT NOT NULL,
    composite_risk_score REAL NOT NULL,
    expected_failure_loss REAL NOT NULL,
    is_anomaly INTEGER DEFAULT 0,
    anomaly_score REAL DEFAULT 0.0,
    top_contributing_features TEXT, -- JSON string of feature importances / SHAP
    model_version TEXT NOT NULL,
    limitations_disclaimer TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (machine_id) REFERENCES machines(machine_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pred_machine_time ON predictions(machine_id, prediction_timestamp);

CREATE TABLE IF NOT EXISTS maintenance_recommendations (
    recommendation_id TEXT PRIMARY KEY,
    machine_id TEXT NOT NULL,
    risk_category TEXT NOT NULL,
    predicted_failure_probability REAL NOT NULL,
    anomaly_evidence TEXT NOT NULL,
    reason_for_recommendation TEXT NOT NULL,
    suggested_action TEXT NOT NULL,
    priority TEXT NOT NULL, -- 'Critical', 'High', 'Medium', 'Routine'
    estimated_maintenance_duration REAL NOT NULL,
    estimated_maintenance_cost REAL NOT NULL,
    potential_downtime_exposure REAL NOT NULL,
    suggested_maintenance_window TEXT,
    required_parts TEXT,
    approval_status TEXT NOT NULL DEFAULT 'Pending', -- 'Pending', 'Approved', 'Rejected', 'Deferred'
    approval_notes TEXT,
    approved_by TEXT,
    decision_timestamp TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (machine_id) REFERENCES machines(machine_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS maintenance_work_orders (
    work_order_id TEXT PRIMARY KEY,
    recommendation_id TEXT,
    machine_id TEXT NOT NULL,
    task_priority TEXT NOT NULL,
    scheduled_start TEXT NOT NULL,
    scheduled_end TEXT NOT NULL,
    assigned_technician_id TEXT,
    allocated_parts TEXT,
    estimated_cost REAL NOT NULL,
    actual_cost REAL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'Scheduled', -- 'Scheduled', 'In-Progress', 'Completed', 'Cancelled'
    recorded_observations TEXT,
    actual_failure_occurred INTEGER DEFAULT 0, -- 0 = No failure / prevented, 1 = Actual failure occurred
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (machine_id) REFERENCES machines(machine_id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_technician_id) REFERENCES technicians(tech_id)
);

CREATE TABLE IF NOT EXISTS model_versions (
    version_id TEXT PRIMARY KEY,
    model_type TEXT NOT NULL,
    algorithm TEXT NOT NULL,
    trained_at TEXT NOT NULL,
    horizon_hours INTEGER NOT NULL,
    training_samples INTEGER NOT NULL,
    positive_samples INTEGER NOT NULL,
    precision_score REAL,
    recall_score REAL,
    f1_score REAL,
    pr_auc_score REAL,
    roc_auc_score REAL,
    brier_score REAL,
    hyperparameters TEXT,
    feature_columns TEXT,
    file_path TEXT NOT NULL,
    is_active INTEGER DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    action_type TEXT NOT NULL, -- 'DATA_INGESTION', 'MODEL_TRAIN', 'PREDICTION_RUN', 'APPROVAL_DECISION', 'WORK_ORDER_CREATE', 'SYSTEM_RESET'
    entity_type TEXT,
    entity_id TEXT,
    actor TEXT NOT NULL DEFAULT 'System Agent',
    details TEXT,
    previous_state TEXT,
    new_state TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_logs(event_timestamp);
