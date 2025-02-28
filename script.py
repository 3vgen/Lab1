import cv2
import asyncio
import logging
import psutil
from fastapi import FastAPI, Response, Request
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),  # Вывод в консоль
        logging.FileHandler("server.log", encoding="utf-8")  # Запись в файл
    ]
)
print("Hello World2!!!!")
app = FastAPI()
templates = Jinja2Templates(directory="templates")


class VideoStream:
    """Класс для работы с видеопотоком"""

    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(self.camera_index)

        if not self.cap.isOpened():
            logging.critical(f"[Камера {self.camera_index}] Ошибка: не удалось открыть камеру")
            raise RuntimeError(f"Ошибка: не удалось открыть камеру {self.camera_index}")

        logging.info(f"[Камера {self.camera_index}] Успешно открыта")

    def __del__(self):
        if self.cap.isOpened():
            self.cap.release()
            logging.info(f"[Камера {self.camera_index}] Закрыта")

    def get_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            logging.error("[Камера] Ошибка получения кадра")
            return None

        _, buffer = cv2.imencode(".jpg", frame)
        return buffer.tobytes()


# Создаём видеопоток
try:
    video_stream = VideoStream()
except Exception as e:
    logging.critical(f"[Ошибка] Критическая ошибка при запуске камеры: {e}")
    raise


async def video_generator():
    while True:
        frame = video_stream.get_frame()
        if frame is None:
            logging.error("[Видеопоток] Кадр не получен, прерываем поток")
            break

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        await asyncio.sleep(0.03)


@app.get("/video")
async def video_feed():
    logging.info("[API] Получен запрос на видеопоток")
    return StreamingResponse(video_generator(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/")
def home(request: Request):
    """Главная страница с видеопотоком"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/logs")
def get_logs(request: Request):
    """Отдаёт HTML страницу с логами"""
    return templates.TemplateResponse("logs.html", {"request": request})


@app.get("/test_rout")
def get_logs():
    """Отдаёт HTML страницу с логами"""
    return {"message": "success"}


@app.get("/logs/live")
def stream_logs():
    """Возвращает последние строки логов"""
    try:
        with open("server.log", "r", encoding="utf-8") as f:
            logs = f.readlines()[-10:]  # Берём последние 10 строк
    except FileNotFoundError:
        logs = ["Логи отсутствуют"]

    return Response("<br>".join(logs), media_type="text/html")


@app.get("/status")
def status():
    memory = psutil.virtual_memory()
    memory_usage = memory.used / (1024 ** 3)  # В гигабайтах
    logging.info(f"[API] Использование памяти: {memory_usage:.2f} GB")
    return {"status": "running", "memory_usage_gb": round(memory_usage, 2)}


logging.info("[Сервер] FastAPI сервер запущен 🚀")
