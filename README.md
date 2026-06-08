# 🐦 Sparrow Detector

A full-stack web application for detecting and analyzing sparrows in images using a trained YOLO11x deep learning model.

## Features

- **Image Upload** with drag-and-drop interface
- **Real-time Detection** with bounding box visualization
- **Statistics Dashboard** with KPI cards and timeline charts
- **Detection History** with filtering and deletion
- **Responsive Design** using Tailwind CSS
- **REST API** with FastAPI
- **Docker Compose** deployment

## Project Structure

```
sparrow-detector/
├── backend/              # FastAPI + YOLO
│   ├── app/
│   │   ├── main.py      # FastAPI app
│   │   ├── routers/     # API endpoints
│   │   ├── models/      # Database
│   │   ├── services/    # YOLO inference
│   │   └── config.py    # Configuration
│   ├── weights/         # Model weights (best.pt)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/            # React + Vite
│   ├── src/
│   │   ├── pages/       # Dashboard, Detect, History
│   │   ├── components/  # Reusable components
│   │   └── lib/         # API client
│   ├── Dockerfile
│   └── package.json
└── docker-compose.yml
```

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
docker compose build
docker compose up
```

Visit `http://localhost` in your browser.

### Option 2: Local Development

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` for the frontend and `http://localhost:8000/docs` for the API docs.

## API Endpoints

### Detection
- `POST /api/detect` — Upload image and run detection
- `GET /api/detections` — List all detections (paginated)
- `GET /api/detections/{id}` — Get detection details
- `DELETE /api/detections/{id}` — Delete detection

### Statistics
- `GET /api/stats` — Get aggregate statistics
- `GET /api/stats/timeseries` — Get timeline data

### Files
- `GET /uploads/{filename}` — Original images
- `GET /results/{filename}` — Annotated images

## Configuration

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

## Model Information

- **Architecture:** YOLOv11x (extra-large)
- **Input Size:** 640×640
- **Classes:** Sparrow
- **Framework:** Ultralytics

## Performance

- Average inference time: ~245ms per image
- GPU recommended for faster detection

## Development

### Backend Testing

```bash
# Run detection on a test image
curl -F "file=@test.jpg" http://localhost:8000/api/detect
```

### Frontend Development

```bash
npm run dev    # Start dev server
npm run build  # Build for production
npm run preview # Preview build
```

## Deployment

The app is Docker-ready. For production:

1. Build images: `docker compose build`
2. Run: `docker compose up -d`
3. Access frontend at `http://localhost`
4. API available at `http://localhost/api`

## License

MIT
