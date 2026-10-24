"""
Custom CSS and Industrial Steel Design Styling for TATA STEEL MAINTAINAI.
Features deep industrial slate, steel blue, molten amber accents,
crisp KPI metric cards, and modern typography.
"""

CUSTOM_CSS = """
/* Import Modern Industrial Typography */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

:root {
    --primary-bg: #0f172a;
    --card-bg: #1e293b;
    --border-color: #334155;
    --accent-blue: #0284c7;
    --accent-light: #38bdf8;
    --molten-amber: #f59e0b;
    --molten-orange: #ea580c;
    --danger-red: #ef4444;
    --success-green: #10b981;
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
}

body, .gradio-container {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: #0b1120 !important;
    color: var(--text-main) !important;
}

/* Header Banner */
.steel-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0369a1 100%);
    border-bottom: 2px solid #0284c7;
    padding: 24px 32px;
    border-radius: 12px;
    margin-bottom: 20px;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
}

.steel-header h1 {
    font-size: 28px;
    font-weight: 700;
    color: #ffffff;
    margin: 0;
    letter-spacing: -0.5px;
    display: flex;
    align-items: center;
    gap: 12px;
}

.steel-header p.subtitle {
    font-size: 14px;
    color: #7dd3fc;
    margin: 6px 0 0 0;
    font-weight: 500;
}

.disclaimer-banner {
    background-color: rgba(234, 88, 12, 0.12);
    border: 1px solid rgba(234, 88, 12, 0.35);
    border-left: 4px solid #ea580c;
    padding: 10px 16px;
    border-radius: 6px;
    font-size: 11.5px;
    color: #fdba74;
    margin-top: 12px;
    line-height: 1.4;
}

/* KPI Card Styles */
.kpi-container {
    display: flex;
    gap: 16px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}

.kpi-card {
    background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 16px 20px;
    flex: 1;
    min-width: 160px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    transition: transform 0.2s ease, border-color 0.2s ease;
}

.kpi-card:hover {
    transform: translateY(-2px);
    border-color: #0284c7;
}

.kpi-title {
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #94a3b8;
    margin-bottom: 8px;
}

.kpi-value {
    font-size: 26px;
    font-weight: 700;
    color: #ffffff;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.1;
}

.kpi-subtext {
    font-size: 11px;
    color: #64748b;
    margin-top: 6px;
}

/* Priority & Risk Badges */
.badge-critical {
    background-color: rgba(239, 68, 68, 0.2);
    color: #fca5a5;
    border: 1px solid #ef4444;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
}

.badge-high {
    background-color: rgba(249, 115, 22, 0.2);
    color: #fdba74;
    border: 1px solid #f97316;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
}

.badge-medium {
    background-color: rgba(245, 158, 11, 0.2);
    color: #fde68a;
    border: 1px solid #f59e0b;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
}

.badge-low {
    background-color: rgba(16, 185, 129, 0.2);
    color: #6ee7b7;
    border: 1px solid #10b981;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
}

/* Tabs styling */
.tabs {
    border-bottom: 1px solid #334155 !important;
}

.tab-nav {
    background: #0f172a !important;
    border-radius: 8px !important;
    padding: 4px !important;
    gap: 4px !important;
}

.tab-nav button {
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #94a3b8 !important;
    padding: 8px 14px !important;
    border-radius: 6px !important;
    transition: all 0.2s ease !important;
}

.tab-nav button.selected {
    background: #0284c7 !important;
    color: #ffffff !important;
    box-shadow: 0 2px 8px rgba(2, 132, 199, 0.4) !important;
}

/* Section Card Container */
.steel-card {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.25);
}

.steel-card-title {
    font-size: 15px;
    font-weight: 600;
    color: #f8fafc;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
    border-bottom: 1px solid #334155;
    padding-bottom: 8px;
}

/* Action Buttons */
.btn-primary {
    background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
    color: white !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 6px !important;
    box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3) !important;
}

.btn-danger {
    background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%) !important;
    color: white !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 6px !important;
}

.btn-success {
    background: linear-gradient(135deg, #059669 0%, #065f46 100%) !important;
    color: white !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 6px !important;
}
"""
