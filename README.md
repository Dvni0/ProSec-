# 🛡️ ProSec - Proactive Security Metaindústria (Challenge 2026 FIAP × SPI)

![Status](https://img.shields.io/badge/Status-Sprint%201%20Concluída-success)
![Linguagem](https://img.shields.io/badge/Python-3.10+-blue)
![IA](https://img.shields.io/badge/YOLO-v8_Nano%20%7C%20Pose-orange)
![Interface](https://img.shields.io/badge/GUI-PyQt-lightgrey)

## 📖 Índice
* [Equipe - 1º Checkpoint](#-equipe---1º-checkpoint)
* [Contexto e Problema](#-contexto-e-problema)
* [A Solução ProSec](#-a-solução-prosec)
* [Arquitetura e Tecnologias](#-arquitetura-e-tecnologias)
* [Funcionalidades Principais](#-funcionalidades-principais)
* [Estrutura do Repositório](#-estrutura-do-repositório)
* [Guia de Instalação e Testes Locais](#-guia-de-instalação-e-testes-locais)
* [Documentação da Sprint 1](#-documentação-da-sprint-1)

---

## 👥 Equipe - 1º Sprint
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



## 📁 Documentação e Diagramas
*   [Documento de Requisitos](./docs/requisitos.md)
*   [Diagrama de Casos de Uso](./docs/diagramas/casos_de_uso.png)
*   [Diagrama de Atividades](./docs/diagramas/atividades.png)
*   [Diagrama de Classes](./docs/diagramas/classes.png)