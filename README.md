# 🚗 HalfApp - Modern Ride Sharing Platform

A comprehensive ride-sharing platform built with FastAPI backend, React frontend, and a professional design system optimized for Figma integration.

## ✨ Features

### 🔐 Authentication & Security
- Secure user authentication with JWT tokens
- Role-based access control (Admin, Driver, Rider)
- Bcrypt password hashing
- Admin access code generation system

### 👥 User Management
- User registration and profile management
- Driver onboarding and verification
- Advanced admin dashboard with user analytics
- Role and status management

### 🚙 Ride Management
- Ride booking and matching system
- Real-time ride status tracking
- Driver availability management
- Ride history and analytics

### 🎨 Professional Design System
- **Figma-Ready Components**: Complete component library for easy design handoffs
- **Design Tokens**: Centralized theming system (colors, typography, spacing)
- **Responsive Design**: Mobile-first approach with breakpoint system
- **Component Library**: Button, Input, Card, Table, Badge, Layout utilities
- **Tree-Shaking Support**: Import only what you need for optimal performance

## 🛠️ Tech Stack

### Backend
- **FastAPI**: Modern Python web framework
- **PostgreSQL**: Robust relational database
- **SQLAlchemy**: Python SQL toolkit and ORM
- **Pydantic**: Data validation using Python type hints
- **JWT**: Secure token-based authentication

### Frontend
- **React 18**: Modern React with hooks
- **Vite**: Lightning-fast build tool
- **Custom Design System**: Professional UI components
- **Responsive Design**: Mobile-first CSS architecture

### DevOps & Infrastructure
- **Docker**: Containerized development and deployment
- **Docker Compose**: Multi-container orchestration
- **PostgreSQL 14**: Production-ready database

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Node.js 18+ (for local development)
- Python 3.9+ (for local development)

### 1. Clone and Setup
```bash
git clone https://github.com/yourusername/halfapp-driver.git
cd halfapp-driver
cp .env.example .env
```

### 2. Configure Environment
Edit `.env` file with your settings:
```env
DATABASE_URL=postgresql://halfapp:password123@db:5432/halfapp_db
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=http://localhost:3000
```

### 3. Launch with Docker
```bash
docker-compose up --build -d
```

### 4. Access the Application
- **Frontend**: http://localhost:3000
- **Admin Dashboard**: http://localhost:3000/admin-login
- **API Documentation**: http://localhost:8000/docs
- **Backend API**: http://localhost:8000

## 📱 Usage

### Admin Setup
1. Generate admin access code:
```bash
curl -X POST "http://localhost:8000/admin-access/generate-code" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@company.com", "password": "secure-password"}'
```

2. Use the generated code at `/admin-login` to create admin account

### Design System Integration
```jsx
// Import components from the design system
import { Button, Card, Table, Badge } from './design'

// Use pre-configured variants
import { QuickComponents } from './design'
const SaveButton = <QuickComponents.ActionButtons.Save onClick={handleSave} />
```

## 🏗️ Project Structure

```
halfapp-driver/
├── backend/                 # FastAPI backend application
│   ├── models/             # Database models (User, Driver, Ride)
│   ├── routes/             # API route handlers
│   ├── services/           # Business logic services
│   ├── main.py            # FastAPI application entry point
│   └── requirements.txt    # Python dependencies
├── frontend/               # React frontend application
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── design/        # Design system & UI components
│   │   └── main.jsx      # React application entry point
│   ├── package.json       # Node.js dependencies
│   └── vite.config.js     # Vite configuration
├── tests/                 # Test suites
├── docker-compose.yml     # Multi-container setup
└── README.md             # This file
```

## 🎨 Design System

Our design system is built for professional development and Figma integration:

### Components Available
- **Buttons**: Primary, Secondary, Success, Danger variants with loading states
- **Inputs**: Text, Email, Password with validation styling
- **Cards**: Flexible containers with headers, footers, and content areas
- **Tables**: Advanced data tables with sorting, filtering, and pagination
- **Badges**: Status indicators and role tags
- **Layout**: Grid, Flex, Stack, Container utilities

### Design Tokens
```javascript
// Centralized design system
import { designTokens } from './frontend/src/design/tokens'

// Example usage
const primaryColor = designTokens.colors.primary[600]
const largePadding = designTokens.spacing.lg
```

## 📊 API Endpoints

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `GET /auth/me` - Get current user info

### Admin Management
- `POST /admin-access/generate-code` - Generate admin access codes
- `POST /admin/register` - Register admin with access code
- `GET /admin/users` - Get all users (admin only)
- `GET /admin/drivers` - Get all drivers (admin only)

### User Management
- `GET /users/` - Get users list
- `PUT /users/{user_id}` - Update user profile
- `DELETE /users/{user_id}` - Delete user

### Driver Management  
- `POST /drivers/` - Register as driver
- `GET /drivers/` - Get drivers list
- `PUT /drivers/{driver_id}` - Update driver info

### Ride Management
- `POST /rides/` - Create new ride
- `GET /rides/` - Get rides list
- `PUT /rides/{ride_id}` - Update ride status

## 🔧 Development

### Local Development Setup
```bash
# Backend (Python virtual environment)
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend (Node.js)
cd frontend
npm install
npm run dev
```

### Database Setup
```bash
# Create database tables
docker-compose up -d db
# Tables are automatically created when backend starts
```

### Testing
```bash
# Run backend tests
cd backend
pytest

# Run frontend tests  
cd frontend
npm test

# Run end-to-end tests
cd tests
npx playwright test
```

## 🚀 Deployment

### Production Build
```bash
# Build all services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

### Environment Variables
Required environment variables for production:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT signing key (use secure random string)
- `CORS_ORIGINS`: Allowed frontend origins
- `ENVIRONMENT`: Set to "production"

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check `/docs` endpoint for API documentation
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Use GitHub Discussions for questions and ideas

## 🏆 Acknowledgments

- Built with FastAPI and React for modern web development
- Design system inspired by leading design systems (Material-UI, Chakra UI)
- Containerized for easy deployment and development