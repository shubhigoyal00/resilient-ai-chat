.PHONY: up down test build logs

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

test:
	cd backend && python -m pytest -q

build:
	cd frontend && npm run build
