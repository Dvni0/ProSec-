import os
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score
import joblib

# 1. Preparação do Diretório
pasta_destino = 'modelos'
os.makedirs(pasta_destino, exist_ok=True)

print("Iniciando pipeline de treinamento de Machine Learning...")
print("1. Gerando base de dados sintética de Postura e EPI...")

# 2. Geração de Dados Sintéticos (5.000 amostras)
np.random.seed(42)
num_amostras = 5000

# Features de Postura (Baseado na nossa extração de 4 variáveis)
# [angulo_graus, angulo_secundario, dx, dy]
angulo_principal = np.random.uniform(0, 50, num_amostras) # Varia de 0 a 50 graus
angulo_secundario = angulo_principal * 0.8 + np.random.normal(0, 2, num_amostras)
dx = np.sin(np.radians(angulo_principal)) * 100 + np.random.normal(0, 5, num_amostras)
dy = np.cos(np.radians(angulo_principal)) * 100 + np.random.normal(0, 5, num_amostras)

# Features de EPI (0 = Ausente, 1 = Presente)
capacete = np.random.choice([0, 1], size=num_amostras, p=[0.3, 0.7])
colete = np.random.choice([0, 1], size=num_amostras, p=[0.2, 0.8])

# Montando o DataFrame (Features)
X = pd.DataFrame({
    'angulo_principal': angulo_principal,
    'angulo_secundario': angulo_secundario,
    'dx': dx,
    'dy': dy,
    'capacete': capacete,
    'colete': colete
})

# 3. Definição da Classe de Risco (Target)
# Regras de Negócio para gerar o Y (0=BAIXO, 1=MÉDIO, 2=ALTO, 3=CRÍTICO)
y = []
for i in range(num_amostras):
    pontos = 0
    ang = X.loc[i, 'angulo_principal']
    cap = X.loc[i, 'capacete']
    col = X.loc[i, 'colete']
    
    # Risco Postural
    if ang > 30: pontos += 2
    elif ang > 15: pontos += 1
    
    # Risco de Segurança (Peso maior)
    if cap == 0: pontos += 2
    if col == 0: pontos += 1
    
    # Limita a classe máxima ao valor 3
    classe_risco = min(pontos, 3)
    y.append(classe_risco)

y = np.array(y)

print(f"Base gerada com {num_amostras} registros.")
print("Distribuição das classes de risco:", np.bincount(y))

# 4. Divisão em Treino e Teste
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# 5. Padronização dos Dados (Scikit-Learn)
print("\n2. Ajustando o Scaler (Scikit-Learn)...")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Salva o padronizador
caminho_scaler = os.path.join(pasta_destino, 'scaler_integrado.pkl')
joblib.dump(scaler, caminho_scaler)
print(f"✓ Scaler salvo em: {caminho_scaler}")

# 6. Treinamento do Modelo (XGBoost)
print("\n3. Treinando o classificador XGBoost...")
xgb_model = xgb.XGBClassifier(
    objective='multi:softprob',
    num_class=4,
    eval_metric='mlogloss',
    max_depth=4,
    learning_rate=0.1,
    n_estimators=100,
    random_state=42
)

xgb_model.fit(X_train_scaled, y_train)

# 7. Avaliação do Modelo
y_pred = xgb_model.predict(X_test_scaled)
print("\nDesempenho do Modelo (Acurácia):", accuracy_score(y_test, y_pred))
print("Relatório de Classificação:\n", classification_report(y_test, y_pred))

# 8. Exportação do Modelo
caminho_xgb = os.path.join(pasta_destino, 'xgboost_risco_operacional.json')
xgb_model.save_model(caminho_xgb)
print(f"✓ Modelo XGBoost salvo em: {caminho_xgb}")
print("\nO treinamento foi concluído com sucesso. Você já pode iniciar o Dashboard principal!")