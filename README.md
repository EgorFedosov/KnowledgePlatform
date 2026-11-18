# Платформа знаний

Реализация объектной модели «Платформа для обмена знаниями и опытом между специалистами»
(ОМИС, лабораторная работа 2). Python 3.11+, Flask, SQLite.

## Запуск

```
pip install -r requirements.txt
python app.py
```

Откроется http://127.0.0.1:5000. При первом запуске создаётся `knowledge.db` с демо-данными.
Пароль у всех пользователей — `12345`.

| Пользователь | Роль |
|---|---|
| ivanov, sidorov, kozlov | Специалист |
| petrova | Эксперт |
| admin | Администратор |

## Тесты

```
python -m unittest
```

## Структура

| Пакет | Содержимое |
|---|---|
| `models/` | классы диаграммы: `User`, `Specialist`, `Expert`, `Administrator`, `Question`, `Comment`, `Tag`, `Rating`, `Notification` |
| `services/` | интерфейсы `*Service` (abc.ABC) и реализации `*ServiceImpl` |
| `controllers/` | `*Controller`, получают сервис в конструкторе; одно окно — один маршрут |
| `templates/` | 11 окон (Jinja2) |
| `storage.py` | хранилище SQLite (`Database`) |
| `app.py` | точка входа и сборка зависимостей (`Application`) |
