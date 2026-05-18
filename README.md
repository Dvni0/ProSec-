# 🛡️ ProSec - Proactive Security Metaindústria (Challenge 2026)

## 👥 Integrantes - Grupo 1º Checkpoint
* Vinícius (RM: [Seu RM])
* Guilherme Torres da Silva (RM: [RM])
* Luis Fernando Picarelli Gonçalves Guariglia (RM: [RM])
* Alexandre Caus Haddade (RM: [RM])
* Mário Secundino Santana Lopes Portella (RM: [RM])

## 🎯 O Problema
No ambiente industrial tradicional, a segurança frequentemente atua de forma reativa e punitiva. Acidentes são investigados apenas após ocorrerem, e o não uso de Equipamentos de Proteção Individual (EPIs) ou a execução de movimentos ergonomicamente perigosos geram notificações retroativas. A falta de monitoramento contínuo em tempo real no chão de fábrica expõe os operadores a riscos invisíveis até que a infração se transforme em um acidente, gerando perdas humanas e operacionais.

## 💡 Proposta de Solução
O **ProSec** propõe uma transição definitiva para a **segurança proativa e preditiva** no ecossistema do Metaindústria. Através de um sistema desktop de alta performance, o projeto atua em três frentes:
1. **Monitoramento de EPIs:** Identifica a ausência de equipamentos obrigatórios em tempo real.
2. **Análise de Postura e Movimento:** Mapeia o esqueleto dos operadores para identificar quedas, posturas antiergonômicas ou entrada em áreas restritas de maquinário.
3. **Previsão de Risco:** Utiliza os dados históricos e em tempo real coletados pelas câmeras para alimentar um modelo preditivo, gerando um "Score de Risco" exibido no dashboard. Isso permite que o supervisor aja antes mesmo que uma situação perigosa se concretize (ex: prevendo que a fadiga de fim de turno aumentará o risco no setor B).

## 🛠️ Tecnologias Selecionadas e Justificativa
A arquitetura foi inteiramente desenhada visando máxima eficiência (Edge Computing), operando em um ecossistema unificado em Python para reduzir gargalos de integração.

*   **Visão Computacional: YOLOv8 Nano (yolov8n)**
    *   *Justificativa:* A versão "Nano" do YOLOv8 foi escolhida por ser extremamente leve e otimizada para inferência rápida. No contexto industrial (Edge Computing), onde o processamento ocorre em terminais próximos às câmeras, o modelo garante alta taxa de FPS (frames per second) com baixo consumo computacional.
*   **Análise Biomecânica: YOLO Pose Estimation**
    *   *Justificativa:* Além de detectar *o que* está na imagem, o YOLO Pose mapeia pontos-chave do corpo humano (keypoints). Isso permite identificar quedas, levantamento incorreto de peso ou se o braço de um operador está perigosamente próximo a uma prensa automatizada.
*   **Modelo Preditivo de Risco (Machine Learning)**
    *   *Justificativa:* Os dados gerados pelo YOLO (frequência de não conformidades, horários, anomalias posturais) alimentam um modelo de ML (como Random Forest ou XGBoost). O objetivo é identificar padrões invisíveis a olho nu e calcular a probabilidade de acidentes futuros, consolidando a inteligência no dashboard do supervisor.
*   **Front-end & Dashboard: PyQt (Python)**
    *   *Justificativa:* Em vez de uma aplicação web tradicional, o PyQt permite criar uma interface desktop nativa, rica e de altíssima performance. Como os pipelines de visão computacional (OpenCV/YOLO) e o modelo preditivo são em Python, o PyQt permite renderizar os streams de vídeo e os gráficos do dashboard diretamente na mesma aplicação, sem latência de rede ou necessidade de APIs REST complexas para streaming de vídeo.
*   **Banco de Dados: SQLite / PostgreSQL**
    *   *Justificativa:* Armazenamento leve e relacional para salvar o histórico de logs do YOLO e treinar os modelos preditivos periodicamente.

## 📁 Documentação e Diagramas
*   [Documento de Requisitos](./docs/requisitos.md)
*   [Diagrama de Casos de Uso](./docs/diagramas/casos_de_uso.png)
*   [Diagrama de Atividades](./docs/diagramas/atividades.png)
*   [Diagrama de Classes](./docs/diagramas/classes.png)