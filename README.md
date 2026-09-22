# 🛡️ ProSec - Proactive Security Metaindústria (Challenge 2026 FIAP × SPI)

![Status](https://img.shields.io/badge/Status-Sprint%203%20Em%20Andamento-yellow)
![Linguagem](https://img.shields.io/badge/Python-3.10+-blue)
![IA](https://img.shields.io/badge/YOLO-v8_Nano%20%7C%20Pose-orange)
![Interface](https://img.shields.io/badge/GUI-PyQt-lightgrey)

## 📖 Índice
* [Equipe](#-equipe)
* [Contexto e Problema](#-contexto-e-problema)
* [A Solução ProSec](#-a-solução-prosec)
* [Arquitetura e Tecnologias](#-arquitetura-e-tecnologias)
* [Funcionalidades Principais](#-funcionalidades-principais)
* [Sprint 2 — Prototipação Funcional e Navegável](#-sprint-2--prototipação-funcional-e-navegável)
* [Sprint 3 — Desenvolvimento e Estrutura Atual](#-sprint-3--desenvolvimento-e-estrutura-atual)
* [Documentação e Diagramas](#-documentação-e-diagramas)

---

## 👥 Equipe
* **Vinícius Barros Souza** 
* **Guilherme Torres da Silva** 
* **Luis Fernando Picarelli Gonçalves Guariglia** 
* **Alexandre Caus Haddade** 
* **Mário Secundino Santana Lopes Portella** 

---

## 🎯 Contexto e Problema
No ambiente do Metaindústria, a segurança do trabalho historicamente opera de forma reativa. O fluxo padrão consiste em investigar acidentes após a ocorrência ou aplicar notificações retroativas por infrações (como o não uso de EPIs). 

Essa abordagem apresenta falhas críticas:
* **Falta de visibilidade em tempo real:** Supervisores não conseguem monitorar todas as zonas de risco simultaneamente.
* **Riscos invisíveis e ergonômicos:** Posturas incorretas e fadiga muscular raramente são detectadas antes de causarem lesões.
* **Ausência de previsibilidade:** Dados de quase-acidentes (near-misses) são perdidos, impedindo a antecipação de falhas sistêmicas no chão de fábrica.

---

## 💡 A Solução ProSec
O **ProSec** é um sistema de monitoramento em tempo real operado na borda (Edge Computing) que consolida a **segurança proativa e preditiva**. Através de fluxos de vídeo das câmeras industriais, o sistema processa imagens localmente para fornecer intervenções imediatas.

A solução atua em três pilares fundamentais:
1. **Fiscalização Contínua de EPIs:** Validação da integridade dos equipamentos de proteção por zonas de obrigatoriedade.
2. **Análise Biomecânica:** Mapeamento esquelético dos operadores para detecção de anomalias ergonômicas e comportamentos inseguros.
3. **Previsão de Risco:** Consolidação dos dados de telemetria visual em um modelo de Machine Learning que calcula e exibe um "Score de Risco" futuro para cada setor.

---

## 🛠️ Arquitetura e Tecnologias
Para garantir latência mínima e processamento off-line na planta industrial, o projeto foi unificado em um ecossistema Python de alta performance.

* **Visão Computacional (Detecção de Objetos): YOLOv8 Nano**
  * O modelo `yolov8n.pt` foi escolhido por ser o estado da arte em velocidade, garantindo alto FPS em hardwares limitados (Edge) para identificar capacetes, óculos e luvas.
* **Visão Computacional (Comportamento): YOLO Pose Estimation**
  * Utilizado para extrair *keypoints* do corpo humano. Permite identificar operadores caídos (man-down), invasão de zonas de alcance de maquinário e levantamento de carga com postura crítica.
* **Motor Preditivo (Machine Learning): Scikit-Learn / XGBoost**
  * Modelo treinado com o histórico de anomalias, horários de turno e taxas de infração para projetar a probabilidade de incidentes nas próximas horas.
* **Front-end e Dashboard (Interface Operacional): PyQt**
  * Substitui arquiteturas web complexas por um executável desktop nativo. O PyQt consome os streams do OpenCV nativamente, desenha as *bounding boxes* sem *delay* de rede e exibe os gráficos preditivos com fluidez.
* **Persistência de Dados: SQLite3 / PostgreSQL**
  * O SQLite3 é utilizado para armazenamento ágil no terminal local (logs de incidentes e scores), permitindo replicação posterior para um banco centralizado no Metaindústria.

---

## 🚀 Funcionalidades Principais
* Renderização em tempo real das câmeras industriais na interface desktop PyQt.
* Emissão de alertas visuais (UI color-coded) e sonoros imediatos ao detectar a ausência de um EPI.
* Registro automático de logs (Timestamp, Setor, Tipo de Infração, Imagem do Incidente).
* Análise de queda ou postura perigosa via extração de esqueleto humano na imagem.
* Dashboard analítico exibindo o "Termômetro de Risco" preditivo atualizado dinamicamente por setor.

---

## 🖼️ Sprint 2 — Prototipação Funcional e Navegável

O protótipo de alta fidelidade do **ProSec** foi implementado para validar visualmente os fluxos operacionais e a inteligência preditiva modelada na Sprint 1. O design simula fielmente a experiência do usuário em um ambiente de supervisão industrial (SCADA).

* 🔗 **Link do Protótipo Interativo (Figma):** [Figma Workspace](https://www.figma.com/make/Kb3k6TgmOORUFSSxZSQodB/Industrial-Safety-System-Screens?fullscreen=1&t=GC23XgoxFXxl8aVL-1) ou [Figma Site](https://perch-deep-20808547.figma.site/)
* 🎬 **Vídeo de Walkthrough (YouTube):** [Apresentação ProSec](https://youtu.be/JV5UFHm-5uU)

### 🕹️ Instruções de Navegação
Para simular o fluxo completo da aplicação de segurança preditiva, siga os passos abaixo no modo de apresentação do Figma:

1.  **Monitoramento Geral:** O sistema é iniciado no **Dashboard Principal**. Observe a disposição dos feeds de vídeo das câmeras industriais e o painel à direita com o gráfico de nível de risco (*Risk Level* atual em 35%), alimentado pelas predições do nosso modelo XGBoost.
2.  **Disparo de Alerta Crítico:** No feed de vídeo que simula uma quebra de protocolo de segurança, clique na imagem da câmera. O protótipo navegará automaticamente para a tela de **Alerta Crítico (Critical Alert)**. Esta tela simula a reação do sistema quando o modelo YOLOv8 detecta um operador sem capacete. Avalie o design de alto contraste e teste a usabilidade dos botões ampliados de ação rápida (`TRIGGER ALARM` e `DISMISS ALERT`).
3.  **Consulta de Colaboradores:** No menu lateral esquerdo, clique no botão **Ops**. Você será direcionado para a tela de **Perfil do Operador (Operator Profile)**. Veja o gerenciamento granular do funcionário *John Martinez*, os *toggles* que indicam os status dos EPIs obrigatórios para o setor e o gráfico de histórico de conformidade dos últimos 30 dias.
4.  **Análise de Tendências:** No menu lateral, clique em **Reports**. A interface abrirá a tela de **Evolução de Risco (Risk Evolution)**, onde gráficos analíticos de linha detalham as tendências semanais (*Risk Level Trend*) e as métricas diárias consolidadas para suporte a decisões da diretoria.
5.  **Retorno:** Clique em **Dashboard** no menu lateral a qualquer momento para reiniciar o fluxo de navegação.

---

## 💻 Sprint 3 — Desenvolvimento e Estrutura Atual

A Sprint 3 tem como foco a integração das interfaces gráficas construídas (UI) com os modelos de Inteligência Artificial de visão computacional e machine learning, consolidando o código fonte da aplicação.

### 📂 Estrutura do Repositório (Current State)
O projeto atual reflete os artefatos de código base já criados para a integração:

*   **`main.py`** / **`app4.py`**: Orquestradores principais da aplicação desktop.
*   **Telas (Views):** Arquivos base da interface do usuário (`login_view.py`, `selection_view.py`, `dashboard_view.py`).
*   **Modelos e IA:**
    *   Arquivos de peso YOLO pré-treinados e customizados (`yolov8n.pt`, `yolov8n-pose.pt`, `yolo26n-pose.pt`).
    *   Estimativa de Pose: Script `YoloPoseEstimation.pt`.
    *   Scripts de Treino (XGBoost/ML): `treino.py`, `treinoBoost.py` e diretório `/modelos` contendo exportações como `modelo_treino_mario.pt`.
*   **Base de Dados & Config:** Arquivo `config.py` e dataset inicial `historico_risco.csv`.
*   **Dependências:** Listadas temporariamente em `libsProjeto.txt`.

### ⚙️ Próximos Passos (To-Do)
As próximas iterações do desenvolvimento focarão em Clean Code, integração fluida das partes e Deploy final:

1.  **Refatoração (Clean Architecture):** Padronizar as dependências gerando um `requirements.txt` oficial e estruturar as pastas isolando as Views (`/src`), Models (`/modelos`) e Assets (`/midias`).
2.  **Integração Backend x UI:** Conectar o stream de vídeo gerado pelas detecções do YOLO (`YoloPoseEstimation`) diretamente dentro da área de exibição do `dashboard_view.py`.
3.  **Dashboards Dinâmicos:** Integrar a leitura do `historico_risco.csv` com bibliotecas gráficas (como Matplotlib ou Plotly) para renderizar os alertas preditivos na tela em tempo real.
4.  **Sistema de Logs e Tratamento de Exceções:** Prevenir o fechamento abrupto da aplicação caso ocorra falha no stream de câmeras industriais.
5.  **Deploy (Executável):** Configurar bibliotecas de empacotamento (ex: PyInstaller) para gerar a build `.exe` do projeto, pronta para execução em terminais fabris Windows sem a necessidade de instalar o Python.

---

## 📁 Documentação e Diagramas
*   [Documento de Requisitos](./docs/requisitos.md)
*   [Documentação de Design](./docs/documentacao_design.md)
*   [Diagrama de Casos de Uso](./docs/diagramas/casos_de_uso.png)
*   [Diagrama de Atividades](./docs/diagramas/atividades.png)
*   [Diagrama de Classes](./docs/diagramas/classes.png)
