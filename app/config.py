# config.py
import os

# ==============================================================================
# 👤 NOME DO OPERADOR / USUÁRIO (Sincronizado entre Ops e Menu Principal)
# ==============================================================================
NOME_DO_OPERADOR = "John Martinez"  

# --- CONSTANTES DE CORES (Paleta Dark & Safety Yellow) ---
COLOR_BG_MAIN = "#121318"
COLOR_BG_SIDEBAR = "#0F1015"
COLOR_BG_CARD = "#1A1C23"
COLOR_BORDER = "#2B2E3C"
COLOR_YELLOW = "#F4B400"
COLOR_RED = "#D9383A"
COLOR_GREEN = "#2D9C56"
COLOR_TEXT_MUTED = "#717686"

# ==============================================================================
# 🖼️ CAMINHO DA IMAGEM DE FUNDO DA TELA DE LOGIN
# ==============================================================================
LOGIN_BACKGROUND_IMAGE_PATH = "caminho_da_sua_foto_de_fabrica.png"

# --- DADOS GERAIS DO SISTEMA (Gerenciado pelo Back-end) ---
CONFIG = {
    # --- DASHBOARD ---
    "current_risk": 35,
    "active_operators": "24",
    "open_alerts": "3",
    "resolved_today": "12",
    "compliance": "98.5%",
    
    # Metadados das Câmeras (Para integração fácil com fontes de vídeo reais)
    "cameras": [
        {"title": "Camera 1", "location": "Assembly Line A"},
        {"title": "Camera 2", "location": "Warehouse Zone B"},
        {"title": "Camera 3", "location": "Loading Dock C"},
        {"title": "Camera 4", "location": "Quality Control"},
    ],
    
    # --- ALERTS ---
    # Alerta Crítico Ativo no topo
    "critical_alert": {
        "location": "Assembly Line A",
        "time": "14:23:17",
        "severity": "CRITICAL",
        "details": [
            "Operator detected without required hard hat in restricted zone",
            "Multiple safety violations detected in the past 15 minutes",
            "Immediate supervisor notification required"
        ]
    },
    
    # Histórico de Alertas Recentes
    "recent_alerts": [
        {"severity": "HIGH", "name": "Missing PPE Equipment - Zone B", "time_ago": "12 minutes ago", "status": "Active"},
        {"severity": "MEDIUM", "name": "Unauthorized Access Attempt", "time_ago": "45 minutes ago", "status": "Investigating"},
        {"severity": "MEDIUM", "name": "Equipment Malfunction - Press 3", "time_ago": "2 hours ago", "status": "In Progress"},
        {"severity": "LOW", "name": "Safety Check Overdue", "time_ago": "4 hours ago", "status": "Resolved"},
    ],
    
    # --- OPS ---
    "op_name": NOME_DO_OPERADOR,
    "op_role": "Senior Operator",
    "op_shift": "Morning (6AM - 2PM)",
    "op_experience_val": 8,
    "op_experience_unit": "Years",
    "op_compliance": "67%",
    
    # Estado dos Equipamentos de EPI (Ativo/Inativo lido pelo back-end)
    "ppe_items": [
        {"name": "Hard Hat", "description": "Head Protection", "active": False},
        {"name": "Safety Glasses", "description": "Eye Protection", "active": True},
        {"name": "Safety Vest", "description": "High Visibility", "active": False},
        {"name": "Safety Gloves", "description": "Hand Protection", "active": True},
        {"name": "Steel-Toe Boots", "description": "Foot Protection", "active": True},
        {"name": "Ear Protection", "description": "Hearing Protection", "active": False},
    ],
    
    # --- REPORTS ---
    "risk_trend_compliance_data": [95, 94, 92, 90, 93, 94, 95],
    "risk_trend_level_data": [25, 30, 45, 55, 40, 35, 35],
    "daily_incidents_data": [2, 3, 5, 7, 4, 3, 3],
    "rep_avg_risk_level": "38.4%",
    "rep_total_incidents": "27",
    "rep_avg_compliance": "93.7%",
    "rep_trend": "↓ 12%",
    
    # --- BARRA LATERAL (SIDEBAR) ---
    "sidebar_user_name": "Admin",
    "sidebar_user_role": "System Manager",
}