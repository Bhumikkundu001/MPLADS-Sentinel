🚀 Key Features
📊 1. Intelligent Monitoring Dashboard

A centralized dashboard provides an overview of MPLADS data and analytical results.

It can provide:

Total works
High-risk works
Medium-risk works
Low-risk works
Risk distribution
Expenditure information
State-wise analysis
Constituency-wise analysis
Anomaly insights
Monitoring statistics
🚨 2. AI-Assisted Anomaly Detection

MPLADS Sentinel uses Isolation Forest to identify records exhibiting unusual patterns within the available data.

The anomaly detection layer can help identify unusual patterns related to available project and financial characteristics.

The output is treated as a risk indicator, not as proof of wrongdoing.

🧠 3. Explainable Risk Scoring

The platform combines available analytical indicators into a unified risk assessment.

Instead of only showing a numerical score, MPLADS Sentinel is designed to explain the factors contributing to the assessment.

Example:

Risk Score: 87 / 100
Risk Level: HIGH

Contributing Indicators:
• Expenditure Anomaly
• Pattern Deviation
• Similarity Concern

The user can then inspect the available evidence behind the assessment.

This makes the system more transparent and useful for human review.

🔗 4. Semantic Similarity Analysis

MPLADS Sentinel uses Sentence Transformers to analyze work descriptions and identify potentially similar recommendations.

The system can help surface:

Similar work descriptions
Semantically related recommendations
Potentially overlapping records requiring examination

Semantic similarity does not automatically mean that two works are duplicates.

The results are intended to support further review.

🗺️ 5. Geographic Risk Map

The Geographic Risk Map provides a visual representation of risk indicators across states and constituencies.

Users can explore:

India
  ↓
State
  ↓
Constituency
  ↓
Works
  ↓
Risk Analysis

The map can provide:

Total works by state
High-risk works
Medium-risk works
Low-risk works
State-level risk distribution
Navigation to relevant works

This provides a geographic perspective on monitoring priorities.

🔬 6. Investigation Workspace

The Investigation Workspace brings the information required to review an individual work into one place.

It can contain:

Work information
Financial information
Risk score
Risk level
Risk indicators
Anomaly analysis
Similar works
AI explanation
Supporting evidence
Reviewer notes
Review status

Example workflow:

Potentially High-Risk Work
          ↓
      Investigation
          ↓
     View Evidence
          ↓
     AI Explanation
          ↓
      Human Review
          ↓
   Action / Resolution
🤖 7. AI Copilot

MPLADS Sentinel includes an AI Copilot designed specifically for MPLADS monitoring.

Users can ask natural-language questions such as:

Why is this work classified as high risk?

Show me the highest-risk works.

Find potentially similar works.

Which works should be reviewed first?

What evidence supports this risk classification?

The Copilot retrieves relevant project and analytical information before generating an explanation.

It is designed as an evidence-grounded monitoring assistant, rather than a generic chatbot.

🔎 8. Advanced Work Search

Users can search and filter available works using relevant project attributes.

Possible filters include:

Work ID
State
Constituency
Lok Sabha / Rajya Sabha
Risk level
Risk score
Anomaly status
Available project status
Date range where supported
🔔 9. Monitoring Notifications

The platform can provide notifications for important monitoring events, such as:

Newly identified high-risk works
Significant anomaly indicators
Potentially similar recommendations
Works requiring review

The notification system is intended to help users focus attention on relevant cases.

👤 10. Authentication & Role-Based Access

The platform is designed with authenticated access and role-based permissions.

Possible roles include:

Administrator
Monitoring Officer
Reviewer
Viewer

Access to monitoring, investigation, administration, and other functionality can be controlled according to user roles.

📝 11. Human-in-the-Loop Review

A core principle of MPLADS Sentinel is:

AI assists the reviewer; AI does not replace the reviewer.

The system identifies potential risk indicators and provides supporting evidence.

The final assessment and action remain with the authorized human authority.

🏗️ System Architecture
                    MPLADS DATA
                         │
                         ▼
              ┌────────────────────┐
              │ Data Processing    │
              │ Cleaning           │
              │ Validation         │
              │ Integration        │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │ ML-Ready Dataset   │
              └─────────┬──────────┘
                        │
          ┌─────────────┼─────────────┐
          │             │             │
          ▼             ▼             ▼
   ┌────────────┐ ┌────────────┐ ┌───────────────┐
   │ Isolation  │ │ Risk       │ │ Sentence      │
   │ Forest     │ │ Scoring    │ │ Transformers  │
   │            │ │            │ │               │
   │ Anomalies  │ │ Risk Level │ │ Similar Works │
   └─────┬──────┘ └─────┬──────┘ └───────┬───────┘
         │              │                │
         └──────────────┼────────────────┘
                        ▼
               ┌───────────────────┐
               │    PostgreSQL     │
               │    SQLAlchemy     │
               └─────────┬─────────┘
                         │
                         ▼
               ┌───────────────────┐
               │   FastAPI Backend │
               └─────────┬─────────┘
                         │
        ┌────────────────┼─────────────────┐
        │                │                 │
        ▼                ▼                 ▼
   ┌─────────┐    ┌─────────────┐   ┌──────────────┐
   │ React   │    │ AI Copilot  │   │ Investigation│
   │Dashboard│    │             │   │ Workspace    │
   └────┬────┘    └──────┬──────┘   └──────┬───────┘
        │                │                 │
        └────────────────┼─────────────────┘
                         ▼
                ┌───────────────────┐
                │ Human Review &    │
                │ Decision Support  │
                └───────────────────┘
🛠️ Technology Stack
Frontend
React.js
Tailwind CSS
Recharts
React Router
Axios / Fetch API
Interactive Mapping
Backend
Python
FastAPI
SQLAlchemy
Database
PostgreSQL
Data Processing
Pandas
NumPy
Machine Learning
Scikit-learn
Isolation Forest
Natural Language Processing
Sentence Transformers
AI
Evidence-grounded AI Copilot
LLM integration through backend services
Deployment
Docker
Vercel
Render
📁 Project Structure
MPLADS-Sentinel/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── context/
│   │   └── App.jsx
│   │
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── database/
│   │   └── main.py
│   │
│   └── requirements.txt
│
├── ml/
│   ├── anomaly_detection.py
│   ├── risk_scoring.py
│   ├── similarity.py
│   └── feature_engineering.py
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── ml_ready/
│
├── tests/
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
⚙️ Getting Started
Prerequisites

Make sure the following are installed:

Python 3.x
Node.js
npm
PostgreSQL
Git

Optional:

Docker
Docker Compose
Clone the Repository
git clone <YOUR-GITHUB-REPOSITORY-URL>
cd MPLADS-Sentinel
🔧 Backend Setup

Create a Python virtual environment:

Windows
python -m venv venv
venv\Scripts\activate
Linux / macOS
python3 -m venv venv
source venv/bin/activate

Install dependencies:

pip install -r backend/requirements.txt

Create a .env file based on .env.example.

Example:

DATABASE_URL=postgresql://username:password@localhost:5432/mplads_sentinel
SECRET_KEY=your_secret_key
LLM_API_KEY=your_llm_api_key

Start the backend:

uvicorn backend.app.main:app --reload
🎨 Frontend Setup

Navigate to the frontend:

cd frontend

Install dependencies:

npm install

Start the development server:

npm run dev
🧪 Testing

Backend tests:

pytest

Frontend production build:

npm run build

The exact commands may vary according to the final project configuration.

🔐 Environment Variables

Sensitive credentials should never be committed to the repository.

Keep the following in environment variables:

DATABASE_URL
SECRET_KEY
LLM_API_KEY

A .env.example file should be used to document required variables without exposing real credentials.

📊 Data Processing Pipeline

The project follows a structured data-processing workflow:

Raw MPLADS Data
       ↓
Data Inspection
       ↓
Cleaning
       ↓
Validation
       ↓
Standardization
       ↓
Integration
       ↓
Feature Engineering
       ↓
ML-Ready Dataset

The pipeline focuses on:

Data validation
Missing-value analysis
Duplicate checking
Summary-row handling
Column standardization
Identifier consistency
Source/house preservation
ML-ready feature preparation

No unsupported external data should be introduced into the core MPLADS analysis.

🤖 Machine Learning
Isolation Forest

Isolation Forest is used for unsupervised anomaly detection.

It identifies records that exhibit patterns that are unusual relative to the available dataset.

The output is used to support:

Anomaly identification
Risk prioritization
Monitoring analysis

It is not treated as definitive evidence of misconduct.

Risk Scoring

MPLADS Sentinel combines available analytical indicators into a risk assessment.

The system can categorize works into:

LOW
MEDIUM
HIGH

Risk scores are intended to support prioritization and human review.

Semantic Similarity

Sentence Transformers are used to compare work descriptions semantically.

This helps identify potentially similar work recommendations.

Important:

Semantic similarity does not prove that two works are duplicates.

It is an indicator for further examination.

🤖 AI Copilot Architecture

The AI Copilot follows an evidence-first architecture:

User Question
      ↓
Intent Understanding
      ↓
Backend Data Retrieval
      ↓
ML Result Retrieval
      ↓
Evidence Assembly
      ↓
LLM Explanation
      ↓
Grounded Response
      ↓
Evidence Display

The LLM does not act as the source of MPLADS facts.

Relevant project and ML information is retrieved from the application's data layer before the response is generated.

This reduces the risk of unsupported responses and makes the Copilot easier to audit.

🎯 Example Copilot Questions

Users can ask:

Why is this work classified as high risk?

Show me the highest-risk works.

Find potentially similar works.

Which works should be reviewed first?

What evidence supports this risk classification?

Show unusual expenditure patterns.

Give me a summary of the current monitoring situation.

Compare these two constituencies.

The actual responses depend on the data and analytical results available in the system.

🔍 Investigation Workflow

MPLADS Sentinel connects AI-generated indicators with a human review process.

Risk Indicator
      ↓
Open Work
      ↓
Review Risk Score
      ↓
Analyze Anomalies
      ↓
Check Similar Works
      ↓
View AI Explanation
      ↓
Inspect Evidence
      ↓
Human Review
      ↓
Review Status / Action

Possible review statuses include:

NEW
UNDER REVIEW
REQUIRES ACTION
CLOSED

The exact workflow depends on the implemented backend authorization and review system.

🛡️ Responsible AI

MPLADS Sentinel is designed as an AI-assisted monitoring and decision-support system.

The system does not automatically conclude that a project is:

fraudulent
corrupt
fake
illegal
or otherwise misconduct

Instead, it identifies:

anomalies
unusual patterns
potential risk indicators
potentially similar work recommendations
cases that may warrant further review

The final decision remains with the authorized human authority.

🌐 Scalability & Future Scope

The architecture developed for MPLADS can potentially be adapted to other environments where large volumes of structured project or administrative data require monitoring and prioritization.

Potential future application areas include:

Public infrastructure monitoring
Municipal development
Government-funded programs
Procurement analytics
Enterprise project monitoring
NGO project monitoring

Such adaptations would require domain-specific datasets, features, validation, and risk definitions.

🚀 Startup Potential

The underlying technology can also evolve into a broader Project Risk Intelligence Platform.

A future product could help organizations:

Monitor large project portfolios
Detect unusual patterns
Prioritize projects for review
Investigate risk indicators
Identify potentially similar projects
Generate explainable analytical summaries
Interact with project data using natural language

MPLADS Sentinel represents a domain-specific implementation of this broader concept.

🏆 Smart India Hackathon 2026

MPLADS Sentinel was developed as part of our participation in the:

Smart India Hackathon 2026 – Internal Round

Problem Statement

PS ID: 26012

AI-Powered Monitoring and Analytics Platform for MPLADS

Theme

Smart Automation

Team

TECH SETU

👥 Team Contributions
Area	Responsibility
Dataset	Data cleaning, validation, integration and ML-ready dataset
Frontend	React dashboard, visualization, risk map and user interface
Backend	FastAPI, PostgreSQL, APIs and database integration
AI/ML	Anomaly detection, risk scoring and semantic similarity
Integration	System integration, authentication, AI Copilot, notifications, testing and deployment
📌 Project Status

The project is being developed around the following end-to-end pipeline:

Dataset
   ↓
Data Processing
   ↓
Machine Learning
   ↓
PostgreSQL
   ↓
FastAPI
   ↓
React Frontend
   ↓
AI Copilot
   ↓
Investigation Workspace
   ↓
Human Review
   ↓
Deployment
📈 Project Vision

The long-term vision of MPLADS Sentinel is to make large-scale monitoring more:

proactive
explainable
data-driven
efficient
scalable
human-centered

The core idea is simple:

Do not make the authority search through every record to find where attention may be needed. Use AI to help identify the records that deserve a closer look, explain the available evidence, and let the authority make the final decision.

⚠️ Disclaimer

MPLADS Sentinel is an AI-assisted monitoring and decision-support platform.

Model outputs represent analytical indicators derived from the available project data. They should not be interpreted as definitive evidence of fraud, corruption, misconduct, or illegality.

Final decisions and actions remain the responsibility of authorized human authorities.

📄 License

This project was developed as part of an academic and Smart India Hackathon initiative.

A suitable open-source license may be added if the repository is intended for public distribution.

Built by Team TECH SETU 🚀

Smart India Hackathon 2026

MPLADS Sentinel — From Data to Risk Intelligence.
