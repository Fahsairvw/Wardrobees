# Wardrobees

Wardrobees is a wardrobe management application designed for people who frequently purchase new clothes and struggle with over-consumption. The application allows users to upload photos of their clothing to create a digital wardrobe. When users encounter new clothes in stores or online, they can take a photo and compare it with items they already own to determine whether a similar piece exists in their wardrobe. This feature helps users make more thoughtful and informed purchasing decisions.
Beyond duplicate prevention. The app then provides personalized care instructions (e.g., washing method, drying method, and storage tips).
The goal of Wardrobees is not to stop users from shopping, but to promote conscious consumption, extend garment lifespan, and reduce textile waste.

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Flutter (for mobile app development)
- PostgreSQL & pgvector (if running backend locally)

### Setup with Docker

1. **Start Server:**
   ```bash
   docker-compose up -d
   ```
2. **Access API:**
   - API Docs: `http://localhost:8000/docs`
   - Health Check: `http://localhost:8000/ml/health`
   
3. **Stop Server:**
   ```bash
   docker-compose down
   ```

### Setup with Local Development
1. Set up database
```bash
brew services start postgresql@17
```

1.2 Create user and database
```bash
psql -d postgres -c "CREATE USER wardrobe WITH PASSWORD 'your_password';"
psql -d postgres -c "CREATE DATABASE closet_db OWNER wardrobe;"
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE closet_db TO wardrobe;"
```

1.3 Create vector extension (as superuser)
```bash
psql -d closet_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

1.4 Verify setup
```bash
psql -d closet_db -c "\dx"
```

2. **Backend:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn app:app --reload
   ```
3. **Frontend:**
   ```bash
   cd frontend
   flutter run
   ```

### Google Colab
1. Data Exploration [EDA](https://colab.research.google.com/drive/1dqXWEzRaGQz-9ekagKLRD-8DFRo1pxwi?usp=sharing)
2. Model Training [train1](https://colab.research.google.com/drive/1zLyAMllBVnA7Ib7xe00YQDxtiG-JLBg9?usp=sharing)
3. Test model [test1](https://colab.research.google.com/drive/18HU_SsrOqhLxh3fUMctetj6M4ZFfL2Et?usp=sharing)
4. Model Fairness [fairness](https://colab.research.google.com/drive/1fV8MfqLm_h0Wvr-8KiV93EapQfPrJHg7?usp=sharing)
5. Model Versioning, Explainability, Prediction[versioning](https://colab.research.google.com/drive/1adetUTaBbpClGpDZiXfHIk4UDqKWx3hG?usp=sharing)

### Training & Model Management
- We trained a custom YOLOv26-seg model on Deepfashion2 Dataset with 500 samples per class. The trained model is saved as `yolo26.pt` and included in the `backend/models/` directory.
- The `model_loader.py` is designed to load `yolo26.pt` which is our trained model for clothing detection and segmentation. It checks multiple paths to ensure the model is found whether running locally or in a Docker container.
- The `inference.py` uses the loaded model to perform inference on input images, returning bounding boxes and segmentation masks for detected clothing items.
- `mlflow` is used for experiment tracking during model training, allowing us to log parameters, metrics, and artifacts for each training run. This helps us compare different model versions and select the best performing one for deployment.