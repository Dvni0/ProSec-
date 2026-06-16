# 🎨 Documentação de Design e UX — ProSec

Este documento detalha a arquitetura de informação, as decisões de experiência do usuário (UX) e a interface de usuário (UI) do projeto ProSec, estabelecendo a rastreabilidade direta entre a modelagem de requisitos da Sprint 1 e as telas funcionais desenvolvidas.

## 1. Mapa de Telas (Arquitetura de Informação)

O fluxo de navegação foi projetado para ser linear, intuitivo e de rápida alternância através de um menu lateral persistente, minimizando o tempo de resposta do supervisor em situações de emergência.

## 2. Decisões de UX/UI para o Contexto Industrial

A interface do ProSec foi projetada sob diretrizes rigorosas de usabilidade em ambientes de alta criticidade (chão de fábrica), atendendo a critérios ergonômicos e operacionais:

* **Legibilidade sob Estresse (Dark Mode Industrial):** Utilização de um fundo grafite escuro refinado para mitigar a fadiga ocular de supervisores durante turnos de 12 horas. Os elementos críticos utilizam contrastes agressivos baseados nas normas de segurança industrial (NR-26): *Safety Yellow* para riscos preventivos/preditivos e *Danger Red* para violações ativas e críticas.
* **Operação com Luvas de Proteção (Touch-Friendly):** Botões de ação rápida e mitigação de emergência (como o controle de disparo `TRIGGER ALARM` e o de descarte `DISMISS ALERT`) possuem dimensões ampliadas e áreas de clique expandidas. Isso viabiliza o uso preciso do sistema em tablets industriais de campo ou computadores de bordo por operadores utilizando luvas.
* **Densidade de Dados Eficiente:** Gráficos e indicadores circulares integrados de forma limpa ao layout para fornecer leitura instantânea do status da planta (Visão Computacional do YOLO e score preditivo do XGBoost) a metros de distância do monitor, eliminando ruídos visuais.

## 3. Mapeamento: Telas × Modelagem da Sprint 1

Para garantir a consistência do projeto, cada interface responde diretamente aos Casos de Uso (UC) e Requisitos Funcionais (RF) levantados na primeira fase:

| Tela do Protótipo | Nome da Interface | Caso de Uso Vinculado (Sprint 1) | Requisito Funcional Suportado | Elemento de Arquitetura / Classe |
| :--- | :--- | :--- | :--- | :--- |
| **Tela 1** | Dashboard Principal | UC01 - Monitorar Planta em Tempo Real | **RF01:** Exibição dos feeds de vídeo.<br>**RF04:** Visualização do Score de Risco Preditivo. | `Camera`, `SistemaInferenciaIA`, `XGBoostRegressor` |
| **Tela 2** | Alerta Crítico | UC02 - Emitir Alerta de Violação de Segurança | **RF02:** Notificação em tempo real.<br>**RF06:** Disparo de alarmes locais e mitigação. | `Alerta`, `Infracao`, `YOLOv8Detector` |
| **Tela 3** | Perfil do Operador | UC03 - Gerenciar Conformidade de EPI por Colaborador | **RF03:** Consulta de status de EPI por operador. | `Colaborador`, `ZonaDeRisco`, `ListaEPI` |
| **Tela 4** | Evolução de Risco | UC04 - Gerar Relatório Analítico e Estatístico | **RF05:** Geração de relatórios de conformidade.<br>**RF07:** Exportação de dados históricos. | `Supervisor`, `RelatorioConformidade`, `Database` |
