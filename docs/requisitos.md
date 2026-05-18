# 📋 Documento de Requisitos e Escopo

## 1. Personas
1.  **João, Operador de Chão de Fábrica:** Trabalha diretamente nas linhas de montagem. O foco do sistema em relação a ele não é punir, mas alertá-lo (via painéis ou som) caso ele esqueça os óculos ou capacete.
2.  **Carlos, Supervisor de Segurança:** Monitorea múltiplos setores simultaneamente. Precisa de uma visão em tempo real de onde ocorrem os desvios de padrão para agir de forma educativa.
3.  **Mariana, Gestora Industrial:** Focada no longo prazo. Precisa de relatórios consolidados sobre a evolução da cultura de segurança da planta.

## 2. Requisitos Funcionais (RF)
*   **RF01:** O sistema deve analisar streams de vídeo em tempo real para detectar a presença ou ausência de EPIs obrigatórios (capacete, luvas, óculos).
*   **RF02:** O sistema deve emitir um alerta imediato (local/dashboard) quando a ausência de um EPI for detectada em uma zona demarcada.
*   **RF03:** O sistema deve registrar o incidente (timestamp, zona, EPI faltante) no banco de dados para consulta do supervisor.
*   **RF04:** O sistema deve permitir que o supervisor visualize um painel de monitoramento com o status "Conforme/Não Conforme" de cada câmera/setor.
*   **RF05:** O sistema deve gerar relatórios consolidados de conformidade ao final de cada turno.

## 3. Requisitos Não Funcionais (RNF)
*   **RNF01 (Performance):** A detecção da IA (YOLOv8) deve possuir latência inferior a 500ms para garantir ação em tempo real.
*   **RNF02 (Disponibilidade):** A operação do módulo de borda não pode depender totalmente de internet externa, devendo operar em rede local (offline-first para alertas locais).
*   **RNF03 (Usabilidade):** O dashboard web deve ser responsivo e carregar em menos de 2 segundos.
*   **RNF04 (Segurança):** Os dados de imagem processados não devem ser armazenados permanentemente a menos que ocorra um incidente grave, visando adequação à LGPD.

## 4. Restrições do Sistema
*   O hardware de processamento de imagem na ponta (Edge) possui recursos computacionais finitos (ex: limitados a GPUs de entrada), o que exige otimização do tamanho do batch (batch size) da IA.
*   Câmeras sujeitas a iluminação variável e oclusões no chão de fábrica.