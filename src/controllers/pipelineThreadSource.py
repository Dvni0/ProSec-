import cv2
import time
import json
import serial
import math
import threading
from queue import Empty, Full, Queue
import numpy as np
import warnings
import joblib
import xgboost as xgb
from datetime import datetime
from pathlib import Path
from ultralytics import YOLO
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

# Constantes de Cores
COLOR_YELLOW = "#F4B400"
COLOR_RED = "#D9383A"
COLOR_GREEN = "#2D9C56"

class OperationalRiskPredictor:
    """Aplica o modelo histórico treinado com as features preservadas no scaler."""

    RISK_BY_CLASS = {0: 100, 1: 75, 2: 45, 3: 15}

    def __init__(self, model_path, scaler_path):
        self.model = None
        self.scaler = None
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.scaler = joblib.load(scaler_path)
            self.model = xgb.XGBClassifier()
            self.model.load_model(model_path)
            if self.scaler.n_features_in_ != 6 or self.model.n_features_in_ != 6:
                raise ValueError("O modelo de risco deve receber exatamente 6 features")
            print("✓ Modelo histórico de risco carregado")
        except Exception as error:
            print(f"⚠ Modelo histórico indisponível: {error}")

    def predict(self, features):
        if self.model is None or self.scaler is None:
            return None
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                scaled_features = self.scaler.transform(np.asarray([features], dtype=float))
                probabilities = self.model.predict_proba(scaled_features)[0]
            predicted_class = int(self.model.classes_[int(np.argmax(probabilities))])
            risk_score = round(sum(
                probability * self.RISK_BY_CLASS.get(int(class_id), 50)
                for probability, class_id in zip(probabilities, self.model.classes_)
            ))
            return min(max(risk_score, 0), 100), predicted_class
        except Exception as error:
            print(f"⚠ Falha na previsão histórica: {error}")
            return None


class SafetyPipelineThread(QThread):
    """
    Thread responsável exclusivamente pela lógica de IA, Visão Computacional,
    cálculo de risco (RULA) e comunicação de hardware (ESP32).
    """
    frame_updated = Signal(QImage)
    # status_postura, status_epi, risco_texto, cor_hex, risco_percentual
    metrics_updated = Signal(str, str, str, str, int) 
    # ativo, risco_percentual, nivel, detalhes, horario
    alert_updated = Signal(bool, int, str, str, str)

    def __init__(self, porta_serial='COM3', baudrate=115200, camera_index=0):
        super().__init__()
        self.stop_flag = False
        self.alert_active = False
        self.camera_index = camera_index
        source_root = Path(__file__).resolve().parents[1]
        
        # Carregamento dos modelos
        self.model_pose = YOLO(source_root / 'models' / 'yolo26n-pose.pt')
        self.model_epi = YOLO(source_root / 'models' / 'modelo_treino_mario.pt')
        project_root = Path(__file__).resolve().parents[2]
        self.risk_predictor = OperationalRiskPredictor(
            project_root / 'modelos' / 'xgboost_risco_operacional.json',
            project_root / 'modelos' / 'scaler_integrado.pkl'
        )
        self.active_tags = {
            "postura": True, "capacete": True, "colete": True,
            "oculos": True, "luvas": True, "botas": True
        }
        # Pontos normalizados (0.0 a 1.0), independentes da resolução da câmera.
        self.dead_zones = []
        # Configuração da comunicação USB com ESP32
        self.esp32_conn = None
        try:
            self.esp32_conn = serial.Serial(porta_serial, baudrate, timeout=1)
            print(f"✓ Conectado ao ESP32 na porta {porta_serial}")
        except Exception as e:
            print(f"⚠ Aviso: ESP32 não conectado em {porta_serial}. Erro: {e}")

    def set_tags(self, tags_dict):
        """Atualiza quais validações a IA deve processar no próximo frame"""
        self.active_tags.update(tags_dict)

    def set_dead_zones(self, zones):
        """Atualiza os polígonos nos quais a IA não deve procurar ocorrências."""
        self.dead_zones = [
            [(max(0.0, min(1.0, float(x))), max(0.0, min(1.0, float(y)))) for x, y in zone]
            for zone in zones
            if len(zone) >= 3
        ]

    def _apply_dead_zones(self, frame):
        if not self.dead_zones:
            return frame

        masked_frame = frame.copy()
        height, width = frame.shape[:2]
        for zone in self.dead_zones:
            polygon = np.array(
                [[round(x * width), round(y * height)] for x, y in zone],
                dtype=np.int32
            )
            cv2.fillPoly(masked_frame, [polygon], (0, 0, 0))
        return masked_frame

    def _draw_dead_zones(self, frame):
        if not self.dead_zones:
            return frame

        overlay = frame.copy()
        height, width = frame.shape[:2]
        for zone in self.dead_zones:
            polygon = np.array(
                [[round(x * width), round(y * height)] for x, y in zone],
                dtype=np.int32
            )
            cv2.fillPoly(overlay, [polygon], (80, 80, 80))
            cv2.polylines(frame, [polygon], True, (180, 180, 180), 2)
        return cv2.addWeighted(overlay, 0.28, frame, 0.72, 0)

    def _draw_detection_overlays(self, frame, results_pose, results_epi):
        output = frame.copy()
        pose_names = getattr(self.model_pose, 'names', {}) or {}
        epi_names = getattr(self.model_epi, 'names', {}) or {}

        def put_label(x1, y1, text, color):
            (text_w, text_h), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            x0 = max(0, x1)
            y0 = max(text_h + 10, y1)
            cv2.rectangle(output, (x0, y0 - text_h - 8), (x0 + text_w + 10, y0 + baseline), (0, 0, 0), -1)
            cv2.putText(output, text, (x0 + 5, y0), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        if results_pose and len(results_pose) > 0:
            try:
                pose = results_pose[0]
                if getattr(pose, 'boxes', None) is not None and len(pose.boxes) > 0:
                    for box in pose.boxes:
                        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].cpu().tolist()]
                        conf = float(box.conf[0].item())
                        cls_id = int(box.cls[0].item())
                        class_name = pose_names.get(cls_id, f'class_{cls_id}')
                        label = f"{class_name} {conf:.2f}"
                        color = (255, 255, 0)
                        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
                        put_label(x1, y1, label, color)

                if getattr(pose, 'keypoints', None) is not None:
                    keypoints = pose.keypoints.xy[0].cpu().numpy()
                    if keypoints is not None and len(keypoints) > 0:
                        pairs = [
                            (0, 1), (0, 2), (1, 3), (2, 4), (5, 6), (5, 7), (7, 9),
                            (6, 8), (8, 10), (5, 11), (6, 12), (11, 12), (11, 13),
                            (13, 15), (12, 14), (14, 16)
                        ]
                        for a, b in pairs:
                            if a < len(keypoints) and b < len(keypoints):
                                x1, y1 = map(int, keypoints[a])
                                x2, y2 = map(int, keypoints[b])
                                cv2.line(output, (x1, y1), (x2, y2), (0, 255, 255), 2)
                        for x, y in keypoints[:17]:
                            cv2.circle(output, (int(x), int(y)), 2, (255, 255, 0), -1)
            except Exception as exc:
                print(f"⚠ Falha ao desenhar overlay de pose: {exc}")

        if results_epi and len(results_epi) > 0:
            try:
                epi = results_epi[0]
                if getattr(epi, 'boxes', None) is not None and len(epi.boxes) > 0:
                    for box in epi.boxes:
                        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].cpu().tolist()]
                        cls_id = int(box.cls[0].item())
                        conf = float(box.conf[0].item())
                        class_name = epi_names.get(cls_id, f'class_{cls_id}')
                        label = f"{class_name} {conf:.2f}"
                        color = (0, 255, 0) if cls_id in (0, 1) else (255, 165, 0)
                        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
                        put_label(x1, y1, label, color)
            except Exception as exc:
                print(f"⚠ Falha ao desenhar overlay de EPI: {exc}")

        return output

    def _frame_to_qimage(self, frame):
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_image = np.ascontiguousarray(rgb_image)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        return QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()

    def _open_camera(self):
        candidates = []
        preferred = self.camera_index
        if preferred is not None:
            candidates.append(preferred)
        candidates.extend([0, 1, 2, 3, 4, 5])

        seen = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            try:
                cap = cv2.VideoCapture(candidate, cv2.CAP_DSHOW if hasattr(cv2, 'CAP_DSHOW') else cv2.CAP_ANY)
                if cap is not None and cap.isOpened():
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    print(f"✓ Câmera aberta no índice {candidate}")
                    return cap, candidate
            except Exception:
                pass

        for candidate in candidates:
            try:
                cap = cv2.VideoCapture(candidate)
                if cap is not None and cap.isOpened():
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    print(f"✓ Câmera aberta no índice {candidate} (fallback)")
                    return cap, candidate
            except Exception:
                pass

        return None, None

    def _capture_frames(self, cap, frame_queue, capture_stop):
        while not capture_stop.is_set() and not self.stop_flag:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue
            try:
                frame_queue.get_nowait()
            except Empty:
                pass
            try:
                frame_queue.put_nowait(frame)
            except Full:
                pass

    def run(self):
        cap, open_index = self._open_camera()
        if cap is None or not cap.isOpened():
            print("❌ Nenhuma câmera funcional encontrada.")
            return

        self.camera_index = open_index
        frame_queue = Queue(maxsize=1)
        capture_stop = threading.Event()
        capture_thread = threading.Thread(
            target=self._capture_frames,
            args=(cap, frame_queue, capture_stop),
            daemon=True,
        )
        capture_thread.start()

        while not self.stop_flag:
            try:
                frame = frame_queue.get(timeout=0.1)
            except Empty:
                continue

            status_postura = "Postura: OK"
            status_epi = "EPI: OK"
            risco_score = "BAIXO"
            cor_final = COLOR_GREEN
            risco_percentual = 0

            try:
                detection_frame = self._apply_dead_zones(frame)

                results_pose = self.model_pose(
                    detection_frame, verbose=False, conf=0.40, imgsz=640
                ) if self.active_tags["postura"] else None

                classes_permitidas = []
                if self.active_tags["botas"]: classes_permitidas.extend((0, 4))
                if self.active_tags["luvas"]: classes_permitidas.extend((1, 5))
                if self.active_tags["oculos"]: classes_permitidas.extend((2, 6))
                if self.active_tags["capacete"]: classes_permitidas.extend((3, 7))
                if self.active_tags["colete"]: classes_permitidas.extend((8, 9))

                if len(classes_permitidas) > 0:
                    results_epi = self.model_epi(
                        detection_frame, verbose=False, conf=0.25,
                        classes=classes_permitidas, imgsz=640
                    )
                else:
                    results_epi = None

                postura_score = 0
                angulo_tronco = 0.0
                angulo_secundario = 0.0
                dx = 0.0
                dy = 0.0

                epi_score = 0
                epi_ausentes = []
                person_present = bool(
                    results_pose
                    and len(results_pose) > 0
                    and getattr(results_pose[0], "boxes", None) is not None
                    and len(results_pose[0].boxes) > 0
                )

                if self.active_tags["postura"] and results_pose and results_pose[0].keypoints is not None and len(results_pose[0].keypoints.xy) > 0:
                    keypoints = results_pose[0].keypoints.xy[0].cpu().numpy()
                    if len(keypoints) > 12:
                        ombro_y = (keypoints[5][1] + keypoints[6][1]) / 2
                        ombro_x = (keypoints[5][0] + keypoints[6][0]) / 2
                        quadril_y = (keypoints[11][1] + keypoints[12][1]) / 2
                        quadril_x = (keypoints[11][0] + keypoints[12][0]) / 2

                        tronco_valido = quadril_y > 0 and ombro_y > 0
                        if tronco_valido:
                            dx = ombro_x - quadril_x
                            dy = quadril_y - ombro_y
                            angulo_tronco = math.degrees(math.atan2(abs(dx), dy))

                        nariz_x, nariz_y = keypoints[0]
                        if ombro_y > 0 and nariz_y > 0:
                            angulo_secundario = math.degrees(math.atan2(abs(nariz_x - ombro_x), abs(ombro_y - nariz_y)))

                        if tronco_valido:
                            if angulo_tronco < 10:
                                postura_score = 10
                                status_postura = f"Normal ({int(angulo_tronco)}°)"
                            elif 10 <= angulo_tronco <= 20:
                                postura_score = 30
                                status_postura = f"Atenção ({int(angulo_tronco)}°)"
                            elif 20 < angulo_tronco <= 60:
                                postura_score = 60
                                status_postura = f"Risco ({int(angulo_tronco)}°)"
                            else:
                                postura_score = 90
                                status_postura = f"Perigo ({int(angulo_tronco)}°)"

                    frame = results_pose[0].plot(img=frame)

                frame = self._draw_detection_overlays(frame, results_pose, results_epi)

                tem_capacete = not self.active_tags["capacete"]
                tem_colete = not self.active_tags["colete"]
                if person_present and results_epi and results_epi[0].boxes is not None:
                    for box in results_epi[0].boxes:
                        cls_id = int(box.cls[0].item())
                        if cls_id == 3 and self.active_tags["capacete"]: tem_capacete = True
                        elif cls_id == 9 and self.active_tags["colete"]: tem_colete = True
                    frame = results_epi[0].plot(img=frame)

                if person_present and not tem_capacete:
                    epi_score += 40
                    epi_ausentes.append("Capacete")
                if person_present and not tem_colete:
                    epi_score += 30
                    epi_ausentes.append("Colete")

                status_epi = "EPI: OK" if not person_present or epi_score == 0 else f"Falta: {', '.join(epi_ausentes)}"

                risco_imediato = min(postura_score + epi_score, 100)
                risco_predictivo = self.risk_predictor.predict([
                    angulo_tronco,
                    angulo_secundario,
                    dx,
                    dy,
                    float(tem_capacete),
                    float(tem_colete)
                ]) if person_present else None
                risco_modelo = risco_predictivo[0] if risco_predictivo else 0
                risco_percentual = max(risco_imediato, risco_modelo)

                if risco_percentual <= 30:
                    risco_score, cor_final = "BAIXO", COLOR_GREEN
                    violacao = False
                elif risco_percentual <= 60:
                    risco_score, cor_final = "MÉDIO", COLOR_YELLOW
                    violacao = False
                else:
                    risco_score, cor_final = "ALTO", COLOR_RED
                    violacao = True

                if violacao:
                    self.send_alert_to_esp32(risco_percentual, epi_ausentes, status_postura)

                if violacao != self.alert_active:
                    details = ", ".join(epi_ausentes) or status_postura
                    self.alert_updated.emit(
                        violacao,
                        risco_percentual,
                        risco_score,
                        details,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    )
                    self.alert_active = violacao

            except Exception as exc:
                print(f"⚠ Falha ao processar o frame da câmera: {exc}")
                risco_score, cor_final, risco_percentual = "BAIXO", COLOR_GREEN, 0
                status_postura = "Postura: OK"
                status_epi = "EPI: OK"

            try:
                if not isinstance(frame, np.ndarray) or frame is None or frame.size == 0:
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                frame = self._draw_dead_zones(frame)
                if frame is None or frame.size == 0:
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                qt_img = self._frame_to_qimage(frame)
                if qt_img.isNull():
                    raise ValueError("QImage inválida")
                self.frame_updated.emit(qt_img)
            except Exception as exc:
                print(f"⚠ Falha ao serializar o frame para a UI: {exc}")
                fallback = np.zeros((480, 640, 3), dtype=np.uint8)
                self.frame_updated.emit(self._frame_to_qimage(fallback))

            self.metrics_updated.emit(status_postura, status_epi, risco_score, cor_final, risco_percentual)

        capture_stop.set()
        capture_thread.join(timeout=2)
        cap.release()
        if self.esp32_conn and self.esp32_conn.is_open:
            self.esp32_conn.close()

    def send_alert_to_esp32(self, risco, epis_faltantes, postura):
        """Envia um payload JSON pela porta serial para o ESP32."""
        if self.esp32_conn and self.esp32_conn.is_open:
            payload = {
                "alarm_trigger": True,
                "risk_level": risco,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "details": {
                    "missing_ppe": epis_faltantes,
                    "posture_issue": postura
                }
            }
            try:
                json_data = json.dumps(payload) + "\n"
                self.esp32_conn.write(json_data.encode('utf-8'))
            except Exception as e:
                print(f"Erro ao enviar dados para ESP32: {e}")

    def stop(self):
        """Solicita a parada e só retorna quando a thread liberou a câmera."""
        self.stop_flag = True
        if self.isRunning():
            self.requestInterruption()
            self.wait()