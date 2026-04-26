.PHONY: setup test dev-backend dev-frontend

setup:
	@echo "Setup is intentionally split by runtime on Windows."
	@echo "Backend: cd backend && python -m venv .venv && .\\.venv\\Scripts\\Activate.ps1 && python -m pip install -r requirements.txt"
	@echo "Frontend: cd frontend && npm install"

test:
	cd backend && python -m pytest

dev-backend:
	cd backend && python -m uvicorn proofflow.main:app --reload

dev-frontend:
	cd frontend && npm run dev
