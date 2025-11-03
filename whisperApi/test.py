import requests

# URL вашого API
url = "http://localhost:5000/transcribe"

# Шлях до тестового аудіофайлу
audio_file_path = "2025-01-16_13.24.33.ogg"  # Змініть на шлях до вашого файлу

# Відправка POST-запиту
try:
    with open(audio_file_path, "rb") as file:
        files = {"file": file}
        response = requests.post(url, files=files)
    
    # Перевірка відповіді
    if response.status_code == 200:
        print("Розпізнаний текст:")
        print(response.json().get("text"))
    else:
        print(f"Помилка: {response.status_code}")
        print(response.json())
except Exception as e:
    print(f"Виникла помилка: {e}")