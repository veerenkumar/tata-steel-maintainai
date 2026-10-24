"""
TATA STEEL MAINTAINAI - Configuration and Industrial Settings
Independent Portfolio Project inspired by steel manufacturing operations.
Not an official Tata Steel deployment; does not access proprietary machinery data.
"""

from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SAMPLE_DATA_DIR = DATA_DIR / "sample"
MODELS_DIR = BASE_DIR / "models"
EXPORTS_DIR = BASE_DIR / "exports"
DB_PATH = BASE_DIR / "database" / "maintainai.db"

# Create directories if they do not exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "database").mkdir(parents=True, exist_ok=True)

# Disclaimers
APP_TITLE = "TATA STEEL MAINTAINAI"
APP_SUBTITLE = "Industrial Predictive Maintenance & Asset Intelligence Platform"
PORTFOLIO_DISCLAIMER = (
    "DISCLAIMER: This application is an independent portfolio demonstration project. "
    "It is NOT an official Tata Steel system, does not access proprietary machinery data or internal SCADA, "
    "and does not bypass physical safety interlocks. All model predictions are statistical risk estimates, "
    "not mechanical certainty. Safety alarms and qualified human inspections always take legal precedence."
)

# Equipment Categories
EQUIPMENT_CATEGORIES = [
    "Blast furnace auxiliary equipment",
    "Pumps and compressors",
    "Industrial motors",
    "Conveyor belt systems",
    "Rolling mill equipment",
    "Cooling systems",
    "Hydraulic systems",
    "Industrial fans and blowers",
    "Material-handling equipment",
    "Steel-processing machinery",
]

# Production Areas
PRODUCTION_AREAS = [
    "Blast Furnace (Ironmaking)",
    "Steel Melt Shop / BOF",
    "Continuous Casting Plant (CCP)",
    "Hot Strip Mill (HSM)",
    "Cold Rolling Mill (CRM)",
    "Sinter & Pellet Plant",
    "Raw Material Handling System (RMHS)",
]

# Sensor Reference Ranges by Equipment Type
# Units: Temp (°C), Vibration (RMS mm/s), Pressure (bar), Speed (RPM), Current (A), Load (%)
EQUIPMENT_REFERENCE_RANGES = {
    "Blast furnace auxiliary equipment": {
        "temperature": {"normal_min": 45.0, "normal_max": 75.0, "warn_max": 88.0, "crit_max": 105.0},
        "vibration": {"normal_min": 0.8, "normal_max": 3.8, "warn_max": 5.8, "crit_max": 8.5},
        "pressure": {"normal_min": 2.5, "normal_max": 5.0, "warn_max": 6.2, "crit_max": 7.5},
        "rotational_speed": {"normal_min": 1400, "normal_max": 1500, "warn_min": 1300, "warn_max": 1600},
        "electrical_current": {"normal_min": 80.0, "normal_max": 140.0, "warn_max": 170.0, "crit_max": 200.0},
        "operating_load": {"normal_min": 60.0, "normal_max": 85.0, "warn_max": 95.0, "crit_max": 100.0},
    },
    "Pumps and compressors": {
        "temperature": {"normal_min": 35.0, "normal_max": 68.0, "warn_max": 80.0, "crit_max": 95.0},
        "vibration": {"normal_min": 0.5, "normal_max": 3.2, "warn_max": 4.8, "crit_max": 7.2},
        "pressure": {"normal_min": 6.0, "normal_max": 12.0, "warn_min": 4.5, "warn_max": 14.0, "crit_max": 16.5},
        "rotational_speed": {"normal_min": 2800, "normal_max": 3000, "warn_min": 2600, "warn_max": 3150},
        "electrical_current": {"normal_min": 40.0, "normal_max": 90.0, "warn_max": 115.0, "crit_max": 135.0},
        "operating_load": {"normal_min": 50.0, "normal_max": 80.0, "warn_max": 92.0, "crit_max": 100.0},
    },
    "Industrial motors": {
        "temperature": {"normal_min": 40.0, "normal_max": 72.0, "warn_max": 85.0, "crit_max": 100.0},
        "vibration": {"normal_min": 0.6, "normal_max": 3.0, "warn_max": 4.5, "crit_max": 7.0},
        "pressure": {"normal_min": 1.0, "normal_max": 2.0, "warn_max": 2.5, "crit_max": 3.0},
        "rotational_speed": {"normal_min": 1420, "normal_max": 1490, "warn_min": 1350, "warn_max": 1550},
        "electrical_current": {"normal_min": 100.0, "normal_max": 220.0, "warn_max": 270.0, "crit_max": 320.0},
        "operating_load": {"normal_min": 65.0, "normal_max": 88.0, "warn_max": 95.0, "crit_max": 100.0},
    },
    "Conveyor belt systems": {
        "temperature": {"normal_min": 30.0, "normal_max": 60.0, "warn_max": 72.0, "crit_max": 85.0},
        "vibration": {"normal_min": 1.0, "normal_max": 4.0, "warn_max": 6.2, "crit_max": 9.0},
        "pressure": {"normal_min": 0.5, "normal_max": 1.5, "warn_max": 2.0, "crit_max": 2.5},
        "rotational_speed": {"normal_min": 700, "normal_max": 950, "warn_min": 600, "warn_max": 1050},
        "electrical_current": {"normal_min": 45.0, "normal_max": 95.0, "warn_max": 120.0, "crit_max": 145.0},
        "operating_load": {"normal_min": 50.0, "normal_max": 85.0, "warn_max": 95.0, "crit_max": 100.0},
    },
    "Rolling mill equipment": {
        "temperature": {"normal_min": 50.0, "normal_max": 85.0, "warn_max": 98.0, "crit_max": 115.0},
        "vibration": {"normal_min": 1.2, "normal_max": 4.5, "warn_max": 6.8, "crit_max": 10.0},
        "pressure": {"normal_min": 120.0, "normal_max": 210.0, "warn_min": 90.0, "warn_max": 240.0, "crit_max": 270.0},
        "rotational_speed": {"normal_min": 450, "normal_max": 850, "warn_min": 350, "warn_max": 950},
        "electrical_current": {"normal_min": 250.0, "normal_max": 650.0, "warn_max": 800.0, "crit_max": 950.0},
        "operating_load": {"normal_min": 70.0, "normal_max": 92.0, "warn_max": 98.0, "crit_max": 100.0},
    },
    "Cooling systems": {
        "temperature": {"normal_min": 25.0, "normal_max": 52.0, "warn_max": 64.0, "crit_max": 78.0},
        "vibration": {"normal_min": 0.5, "normal_max": 2.8, "warn_max": 4.2, "crit_max": 6.5},
        "pressure": {"normal_min": 3.0, "normal_max": 6.5, "warn_min": 2.2, "warn_max": 7.8, "crit_max": 9.0},
        "rotational_speed": {"normal_min": 950, "normal_max": 1200, "warn_min": 850, "warn_max": 1300},
        "electrical_current": {"normal_min": 30.0, "normal_max": 65.0, "warn_max": 80.0, "crit_max": 100.0},
        "operating_load": {"normal_min": 55.0, "normal_max": 80.0, "warn_max": 90.0, "crit_max": 100.0},
    },
    "Hydraulic systems": {
        "temperature": {"normal_min": 40.0, "normal_max": 65.0, "warn_max": 78.0, "crit_max": 92.0},
        "vibration": {"normal_min": 0.8, "normal_max": 3.2, "warn_max": 5.0, "crit_max": 7.5},
        "pressure": {"normal_min": 140.0, "normal_max": 220.0, "warn_min": 110.0, "warn_max": 250.0, "crit_max": 290.0},
        "rotational_speed": {"normal_min": 1400, "normal_max": 1500, "warn_min": 1300, "warn_max": 1600},
        "electrical_current": {"normal_min": 70.0, "normal_max": 150.0, "warn_max": 190.0, "crit_max": 230.0},
        "operating_load": {"normal_min": 60.0, "normal_max": 85.0, "warn_max": 95.0, "crit_max": 100.0},
    },
    "Industrial fans and blowers": {
        "temperature": {"normal_min": 38.0, "normal_max": 70.0, "warn_max": 82.0, "crit_max": 96.0},
        "vibration": {"normal_min": 1.0, "normal_max": 4.2, "warn_max": 6.5, "crit_max": 9.5},
        "pressure": {"normal_min": 0.8, "normal_max": 2.2, "warn_max": 2.8, "crit_max": 3.5},
        "rotational_speed": {"normal_min": 980, "normal_max": 1480, "warn_min": 900, "warn_max": 1600},
        "electrical_current": {"normal_min": 90.0, "normal_max": 210.0, "warn_max": 260.0, "crit_max": 310.0},
        "operating_load": {"normal_min": 60.0, "normal_max": 88.0, "warn_max": 95.0, "crit_max": 100.0},
    },
    "Material-handling equipment": {
        "temperature": {"normal_min": 30.0, "normal_max": 62.0, "warn_max": 75.0, "crit_max": 90.0},
        "vibration": {"normal_min": 0.9, "normal_max": 3.6, "warn_max": 5.4, "crit_max": 8.0},
        "pressure": {"normal_min": 50.0, "normal_max": 110.0, "warn_max": 135.0, "crit_max": 160.0},
        "rotational_speed": {"normal_min": 600, "normal_max": 1000, "warn_min": 500, "warn_max": 1150},
        "electrical_current": {"normal_min": 80.0, "normal_max": 180.0, "warn_max": 230.0, "crit_max": 280.0},
        "operating_load": {"normal_min": 40.0, "normal_max": 80.0, "warn_max": 95.0, "crit_max": 100.0},
    },
    "Steel-processing machinery": {
        "temperature": {"normal_min": 55.0, "normal_max": 90.0, "warn_max": 105.0, "crit_max": 125.0},
        "vibration": {"normal_min": 1.1, "normal_max": 4.4, "warn_max": 6.6, "crit_max": 9.8},
        "pressure": {"normal_min": 80.0, "normal_max": 160.0, "warn_min": 60.0, "warn_max": 185.0, "crit_max": 215.0},
        "rotational_speed": {"normal_min": 300, "normal_max": 750, "warn_min": 250, "warn_max": 850},
        "electrical_current": {"normal_min": 150.0, "normal_max": 380.0, "warn_max": 480.0, "crit_max": 580.0},
        "operating_load": {"normal_min": 65.0, "normal_max": 90.0, "warn_max": 98.0, "crit_max": 100.0},
    },
}

# Machine Fleet Registry (12 Representative Machinery Assets)
INITIAL_MACHINE_FLEET = [
    {
        "machine_id": "BF-PUMP-001",
        "equipment_type": "Blast furnace auxiliary equipment",
        "production_area": "Blast Furnace (Ironmaking)",
        "criticality": "Tier 1 - Critical",
        "commissioning_date": "2019-03-15",
        "operating_status": "Running",
        "operating_hours": 18450.0,
        "last_maintenance_date": "2026-08-10",
        "maintenance_interval_days": 90,
        "estimated_repair_cost": 28500.0,
        "downtime_cost_per_hour": 14500.0,
        "expected_maintenance_duration_hours": 6.5,
        "description": "High-Pressure Tuyere Cooling Water Pump A",
    },
    {
        "machine_id": "BF-BLWR-001",
        "equipment_type": "Blast furnace auxiliary equipment",
        "production_area": "Blast Furnace (Ironmaking)",
        "criticality": "Tier 1 - Critical",
        "commissioning_date": "2018-07-20",
        "operating_status": "Running",
        "operating_hours": 24100.0,
        "last_maintenance_date": "2026-07-22",
        "maintenance_interval_days": 120,
        "estimated_repair_cost": 45000.0,
        "downtime_cost_per_hour": 22000.0,
        "expected_maintenance_duration_hours": 8.0,
        "description": "Cold Blast Turbo Blower Auxiliary Impeller Unit",
    },
    {
        "machine_id": "RM-MOTOR-002",
        "equipment_type": "Industrial motors",
        "production_area": "Hot Strip Mill (HSM)",
        "criticality": "Tier 1 - Critical",
        "commissioning_date": "2020-01-10",
        "operating_status": "Degraded",
        "operating_hours": 16200.0,
        "last_maintenance_date": "2026-06-15",
        "maintenance_interval_days": 75,
        "estimated_repair_cost": 36000.0,
        "downtime_cost_per_hour": 18000.0,
        "expected_maintenance_duration_hours": 7.0,
        "description": "Roughing Mill Stand 2 Main Drive Synchronous Motor",
    },
    {
        "machine_id": "CONV-BELT-003",
        "equipment_type": "Conveyor belt systems",
        "production_area": "Raw Material Handling System (RMHS)",
        "criticality": "Tier 2 - High",
        "commissioning_date": "2021-05-18",
        "operating_status": "Running",
        "operating_hours": 12800.0,
        "last_maintenance_date": "2026-08-30",
        "maintenance_interval_days": 60,
        "estimated_repair_cost": 14000.0,
        "downtime_cost_per_hour": 6500.0,
        "expected_maintenance_duration_hours": 4.5,
        "description": "Sinter Ore Stacker Conveyor Main Drive & Tensioner",
    },
    {
        "machine_id": "RM-STAND-001",
        "equipment_type": "Rolling mill equipment",
        "production_area": "Hot Strip Mill (HSM)",
        "criticality": "Tier 1 - Critical",
        "commissioning_date": "2019-11-04",
        "operating_status": "Running",
        "operating_hours": 19500.0,
        "last_maintenance_date": "2026-09-02",
        "maintenance_interval_days": 60,
        "estimated_repair_cost": 52000.0,
        "downtime_cost_per_hour": 25000.0,
        "expected_maintenance_duration_hours": 8.5,
        "description": "Finishing Mill Stand F1 Work Roll Chock Assembly",
    },
    {
        "machine_id": "HYD-PRESS-001",
        "equipment_type": "Hydraulic systems",
        "production_area": "Cold Rolling Mill (CRM)",
        "criticality": "Tier 2 - High",
        "commissioning_date": "2020-08-14",
        "operating_status": "Running",
        "operating_hours": 14700.0,
        "last_maintenance_date": "2026-08-05",
        "maintenance_interval_days": 90,
        "estimated_repair_cost": 21000.0,
        "downtime_cost_per_hour": 9200.0,
        "expected_maintenance_duration_hours": 5.0,
        "description": "Skin Pass Mill Hydraulic Automatic Gauge Control (AGC)",
    },
    {
        "machine_id": "BOF-ID-FAN-001",
        "equipment_type": "Industrial fans and blowers",
        "production_area": "Steel Melt Shop / BOF",
        "criticality": "Tier 1 - Critical",
        "commissioning_date": "2018-12-01",
        "operating_status": "Degraded",
        "operating_hours": 23600.0,
        "last_maintenance_date": "2026-07-04",
        "maintenance_interval_days": 90,
        "estimated_repair_cost": 31000.0,
        "downtime_cost_per_hour": 19500.0,
        "expected_maintenance_duration_hours": 6.0,
        "description": "BOF Primary Off-Gas Induced Draft Scrubbing Fan",
    },
    {
        "machine_id": "COOL-TWR-001",
        "equipment_type": "Cooling systems",
        "production_area": "Continuous Casting Plant (CCP)",
        "criticality": "Tier 2 - High",
        "commissioning_date": "2021-02-28",
        "operating_status": "Running",
        "operating_hours": 13900.0,
        "last_maintenance_date": "2026-09-12",
        "maintenance_interval_days": 90,
        "estimated_repair_cost": 16500.0,
        "downtime_cost_per_hour": 8000.0,
        "expected_maintenance_duration_hours": 4.0,
        "description": "Caster Mold Secondary Water Cooling Circulation Unit",
    },
    {
        "machine_id": "COMP-GAS-001",
        "equipment_type": "Pumps and compressors",
        "production_area": "Steel Melt Shop / BOF",
        "criticality": "Tier 2 - High",
        "commissioning_date": "2020-04-12",
        "operating_status": "Running",
        "operating_hours": 15800.0,
        "last_maintenance_date": "2026-08-20",
        "maintenance_interval_days": 100,
        "estimated_repair_cost": 24000.0,
        "downtime_cost_per_hour": 11000.0,
        "expected_maintenance_duration_hours": 5.5,
        "description": "Argon Bottom-Stirring Screw Gas Compressor A",
    },
    {
        "machine_id": "LADLE-CRANE-001",
        "equipment_type": "Material-handling equipment",
        "production_area": "Steel Melt Shop / BOF",
        "criticality": "Tier 1 - Critical",
        "commissioning_date": "2019-09-15",
        "operating_status": "Running",
        "operating_hours": 17200.0,
        "last_maintenance_date": "2026-09-18",
        "maintenance_interval_days": 45,
        "estimated_repair_cost": 38000.0,
        "downtime_cost_per_hour": 24000.0,
        "expected_maintenance_duration_hours": 6.5,
        "description": "350-Tonne Liquid Steel Ladle Hoist Gearbox & Motor",
    },
    {
        "machine_id": "CONT-CAST-001",
        "equipment_type": "Steel-processing machinery",
        "production_area": "Continuous Casting Plant (CCP)",
        "criticality": "Tier 1 - Critical",
        "commissioning_date": "2019-06-30",
        "operating_status": "Running",
        "operating_hours": 21400.0,
        "last_maintenance_date": "2026-08-25",
        "maintenance_interval_days": 60,
        "estimated_repair_cost": 48000.0,
        "downtime_cost_per_hour": 26000.0,
        "expected_maintenance_duration_hours": 7.5,
        "description": "Caster Strand 1 Segment 3 Pinch Roll Withdrawal Drive",
    },
    {
        "machine_id": "SINT-MTR-004",
        "equipment_type": "Industrial motors",
        "production_area": "Sinter & Pellet Plant",
        "criticality": "Tier 3 - Medium",
        "commissioning_date": "2021-10-10",
        "operating_status": "Running",
        "operating_hours": 11300.0,
        "last_maintenance_date": "2026-09-05",
        "maintenance_interval_days": 90,
        "estimated_repair_cost": 12500.0,
        "downtime_cost_per_hour": 4500.0,
        "expected_maintenance_duration_hours": 3.5,
        "description": "Sinter Main Sizing Screen Excitator Motor B",
    },
]

# Technicians Roster
TECHNICIAN_ROSTER = [
    {"tech_id": "TECH-MECH-01", "name": "Rajesh Kumar", "specialization": "Mechanical", "skill_level": "Senior Specialist", "shift": "Day", "hourly_rate": 85.0},
    {"tech_id": "TECH-ELEC-02", "name": "Sunil Sharma", "specialization": "Electrical", "skill_level": "Senior Engineer", "shift": "Day", "hourly_rate": 90.0},
    {"tech_id": "TECH-HYD-03", "name": "Amit Patel", "specialization": "Hydraulic", "skill_level": "Lead Specialist", "shift": "Rotating", "hourly_rate": 88.0},
    {"tech_id": "TECH-INST-04", "name": "Priya Nair", "specialization": "Instrumentation", "skill_level": "Senior Analyst", "shift": "Day", "hourly_rate": 92.0},
    {"tech_id": "TECH-MECH-05", "name": "Vikram Das", "specialization": "Mechanical", "skill_level": "Field Technician", "shift": "Night", "hourly_rate": 75.0},
    {"tech_id": "TECH-ELEC-06", "name": "Ananya Mukherjee", "specialization": "Electrical", "skill_level": "Field Engineer", "shift": "Rotating", "hourly_rate": 80.0},
]

# Spare Parts Catalog
SPARE_PARTS_CATALOG = [
    {"part_id": "PART-BRG-22320", "name": "Spherical Roller Bearing 22320-E1", "equipment_type": "Industrial motors", "unit_cost": 1450.0, "stock_quantity": 8, "reorder_lead_days": 3},
    {"part_id": "PART-SEAL-HYD", "name": "High-Pressure Hydraulic Seal Kit 350-Bar", "equipment_type": "Hydraulic systems", "unit_cost": 680.0, "stock_quantity": 12, "reorder_lead_days": 2},
    {"part_id": "PART-IMP-BLWR", "name": "Inconel Dynamic Impeller Vane Set", "equipment_type": "Industrial fans and blowers", "unit_cost": 6200.0, "stock_quantity": 2, "reorder_lead_days": 14},
    {"part_id": "PART-PUMP-IMP", "name": "Cast Bronze Tuyere Pump Impeller", "equipment_type": "Blast furnace auxiliary equipment", "unit_cost": 3100.0, "stock_quantity": 3, "reorder_lead_days": 7},
    {"part_id": "PART-CHOCK-BRG", "name": "Four-Row Cylindrical Roll Chock Bearing", "equipment_type": "Rolling mill equipment", "unit_cost": 8900.0, "stock_quantity": 4, "reorder_lead_days": 10},
    {"part_id": "PART-BELT-EP800", "name": "Steel-Cord Conveyor Belt Splicing Kit EP800", "equipment_type": "Conveyor belt systems", "unit_cost": 1850.0, "stock_quantity": 6, "reorder_lead_days": 4},
    {"part_id": "PART-VALV-PROP", "name": "Rexroth Proportional Servo Valve 4WREE", "equipment_type": "Hydraulic systems", "unit_cost": 4200.0, "stock_quantity": 5, "reorder_lead_days": 5},
    {"part_id": "PART-COOL-NOZZ", "name": "Full-Cone Secondary Spray Nozzle Assembly (24pk)", "equipment_type": "Cooling systems", "unit_cost": 950.0, "stock_quantity": 15, "reorder_lead_days": 2},
]

# Risk Thresholds
RISK_THRESHOLDS = {
    "low": {"prob_max": 0.25, "score_max": 35.0, "color": "#10b981", "label": "Low Risk"},
    "medium": {"prob_max": 0.55, "score_max": 65.0, "color": "#f59e0b", "label": "Medium Risk"},
    "high": {"prob_max": 0.80, "score_max": 85.0, "color": "#f97316", "label": "High Risk"},
    "critical": {"prob_max": 1.00, "score_max": 100.0, "color": "#ef4444", "label": "Critical Risk"},
}

# Modeling Defaults
DEFAULT_PREDICTION_HORIZON_HOURS = 72
DEFAULT_ROLLING_WINDOW_HOURS = 24
ANOMALY_CONTAMINATION = 0.05
RANDOM_SEED = 42
