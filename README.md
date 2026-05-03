**Hearthstone Deck Knowledge Base**

Backend-сервис на FastAPI для управления личными коллекциями карт, создания колод и алгоритмического подбора оптимальной колоды на основе имеющихся у игрока ресурсов. Реализует полный цикл REST API, аутентификацию, валидацию правил создания колод Hearthstone и бизнес-логику рекомендаций.

**Установка и запуск**

Установка зависимостей:

```bash
pip install -r requirements.txt
```

Запуск проекта:

```bash
uvicorn app.main:app --reload
```

Запуск тестов:
```bash
pytest tests/test_app.py -v
```

Запуск тестов со сбором покрытия:

```bash
pytest --cov=app --cov-report term-missing --cov-report html
```

**Автор**

Иванов Роман Александрович, студент 5 курса магситратуры ФРКТ