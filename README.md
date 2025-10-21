# Smart Map Routing System

A comprehensive smart routing system that provides intelligent pathfinding with flood prediction capabilities, geocoding services, and interactive map visualization. The system is designed for urban areas in Vietnam, specifically optimized for Hanoi districts.

## 🌟 Features

### Core Functionality
- **Smart Routing**: Advanced pathfinding algorithms with dynamic weight adjustments
- **Flood Prediction**: Integration with machine learning models for flood risk assessment
- **Geocoding Services**: Convert addresses to coordinates and vice versa using OpenStreetMap
- **Interactive Map**: Streamlit-based web interface with real-time route visualization
- **Dynamic Constraints**: Support for flood areas, restricted zones, and one-way roads
- **Database Integration**: PostGIS database for efficient spatial data storage

### Technical Features
- **FastAPI Backend**: High-performance REST API with automatic documentation
- **Docker Support**: Containerized deployment with Docker Compose
- **Caching System**: Intelligent caching for improved performance
- **Real-time Visualization**: Interactive maps with route overlays
- **Multi-language Support**: Vietnamese and English interface

## 🏗️ Architecture

```
Map-Routing/
├── src/
│   ├── app/                    # FastAPI application
│   │   ├── api/                # API endpoints
│   │   ├── core/               # Configuration
│   │   ├── models/             # ML models and graph data
│   │   └── schemas/            # Data validation schemas
│   ├── database/               # Database operations
│   ├── frontend/               # Streamlit web interface
│   └── services/               # Business logic services
├── cache/                      # Cached data files
├── test_files/                 # Test scripts and utilities
├── docker-compose.yml          # Docker orchestration
├── Dockerfile                  # Container configuration
└── requirements.txt            # Python dependencies
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- PostgreSQL with PostGIS extension

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Map-Routing
   ```

2. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   DATABASE_URL=postgresql://postgres:123456@localhost:5432/map_route_dtb
   WEATHER_API_KEY=your_weather_api_key
   LATITUDE=21.0245
   LONGITUDE=105.8412
   MODEL_PATH=src/app/models/flood_model.joblib
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

### Manual Setup (Alternative)

1. **Start PostgreSQL with PostGIS**
   ```bash
   # Using Docker
   docker run --name postgis_db -e POSTGRES_PASSWORD=123456 -p 5432:5432 -d postgis/postgis:15-3.3
   ```

2. **Initialize the database**
   ```bash
   python src/database/save_graph.py
   ```

3. **Start the FastAPI server**
   ```bash
   python main.py
   ```

4. **Start the Streamlit frontend**
   ```bash
   streamlit run src/frontend/app_streamlit.py
   ```

## 📡 API Documentation

### Base URL
- FastAPI: `http://localhost:8000`
- Streamlit: `http://localhost:8501`

### API Endpoints

#### Geocoding Services
- **POST** `/api/v1/geocoding/loc-to-coords`
  - Convert address to coordinates
  - Request: `{"address": "119 Lê Thanh Nghị, Hà Nội"}`
  - Response: `{"latitude": 21.0245, "longitude": 105.8412, "address": "..."}`

- **POST** `/api/v1/geocoding/coords-to-loc`
  - Convert coordinates to address
  - Query params: `latitude`, `longitude`

#### Routing Services
- **POST** `/api/v1/routing/find-standard-route`
  - Find optimal route between two addresses
  - Request body:
    ```json
    {
      "start_address": "119 Lê Thanh Nghị, Hà Nội",
      "end_address": "Cầu Vĩnh Tuy, Hà Nội",
      "blocking_geometries": [],
      "flood_areas": [],
      "ban_areas": []
    }
    ```

- **GET** `/health`
  - Health check endpoint

### Interactive API Documentation
Visit `http://localhost:8000/docs` for Swagger UI documentation.

## 🗺️ Web Interface

The Streamlit web interface provides:

### Map Features
- **Interactive Drawing**: Draw flood areas, restricted zones, and one-way roads
- **Route Visualization**: Real-time route display with distance and time estimates
- **Address Search**: Find routes by entering start and end addresses
- **Constraint Management**: Add/remove various types of road constraints

### Interface Tabs
1. **Flood Areas**: Mark areas with increased flood risk (blue overlay)
2. **Restricted Areas**: Mark completely blocked areas (red overlay)
3. **Address Routing**: Find routes between specific addresses

## 🔧 Configuration

### Database Configuration
The system uses PostGIS for spatial data storage:
- **Nodes Table**: Road intersections and points
- **Edges Table**: Road segments with geometry and attributes

### Model Configuration
- **Flood Model**: Machine learning model for flood prediction (Joblib format)
- **Graph Data**: OSMnx graph structure for routing algorithms

### Caching
- **Graph Cache**: Pre-computed graph structures for faster loading
- **API Cache**: Cached responses for geocoding and routing requests

## 🧪 Testing

### Run Tests
```bash
# Navigate to test directory
cd test_files

# Run pathfinding tests
python test_api_pf.py

# Run folium visualization tests
python test_folium.py
```

### Test Coverage
- API endpoint testing
- Pathfinding algorithm validation
- Geocoding service testing
- Map visualization testing

## 🐳 Docker Deployment

### Production Deployment
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Service Architecture
- **PostgreSQL**: Database with PostGIS extension
- **FastAPI**: REST API server
- **Streamlit**: Web interface
- **Database Initializer**: One-time setup service

## 📊 Performance

### Optimization Features
- **Graph Caching**: Pre-loaded graph structures
- **Database Indexing**: Optimized spatial queries
- **Request Caching**: Reduced API calls
- **Parallel Processing**: Concurrent route calculations

### Monitoring
- Health check endpoints
- Performance metrics
- Error logging and tracking

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Code Structure
- Follow PEP 8 style guidelines
- Add type hints for functions
- Include docstrings for classes and methods
- Write unit tests for new features

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Common Issues
1. **Database Connection**: Ensure PostgreSQL is running and accessible
2. **Missing Dependencies**: Run `pip install -r requirements.txt`
3. **Port Conflicts**: Check if ports 8000 and 8501 are available
4. **Memory Issues**: Increase Docker memory allocation for large graphs

### Getting Help
- Check the API documentation at `/docs`
- Review the test files for usage examples
- Open an issue for bug reports or feature requests

## 🔮 Future Enhancements

- Real-time traffic data integration
- Multi-modal transportation support
- Advanced flood prediction models
- Mobile application development
- Performance optimization for larger datasets

---

**Note**: This system is optimized for Vietnamese urban areas, particularly Hanoi. For other regions, you may need to adjust the geocoding parameters and coordinate systems.
