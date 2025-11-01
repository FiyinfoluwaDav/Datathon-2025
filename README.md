# MediSense: AI-Powered Healthcare for Africa

MediSense is an AI-powered decision-support system designed to strengthen primary healthcare in Africa. It analyzes health facility data, predicts shortages and outbreaks, and supports smarter planning across Africa’s Primary Health Care systems.

## The Challenge

Africa's primary healthcare infrastructure faces critical gaps that impact millions of lives daily. 
- Less than 20% of PHCs in Nigeria are fully functional.
- 70% of health needs can be solved at the PHC level, yet most centers lack diagnostic capacity.
- Millions of people in underserved communities lack access to basic healthcare.

## Our Solution

MediSense is an AI-powered decision-support system that analyzes health facility data, predicts shortages and outbreaks, and supports smarter planning across Africa’s Primary Health Care systems.

### Features

- **AI-Driven Analytics:** Advanced machine learning models process healthcare data to identify patterns, predict challenges, and recommend evidence-based interventions in real-time.
- **Comprehensive Data Integration:** Seamlessly aggregates data from WHO, World Bank, health facilities, and local sources to create a unified view of healthcare infrastructure.
- **Predictive Modeling:** Forecast resource shortages, disease outbreaks, and capacity gaps before they become critical, enabling proactive interventions.
- **Community-Centered Design:** Built with input from healthcare workers and communities to ensure accessibility, usability, and real-world impact at the grassroots level.

### Automated Inventory Management

MediSense provides an automated inventory management system that helps PHCs to keep track of their stock levels. The system can predict when items will run out of stock based on their daily consumption rate. When an item is running low, the system automatically generates a restock request and assigns a priority level based on the number of days remaining. This feature helps to prevent stock-outs and ensures that PHCs have the necessary supplies to provide care to their patients.

### Authentication and Authorization

MediSense uses a token-based authentication system. Users can register and log in to the application using their email and password. Upon successful login, the application returns a JSON Web Token (JWT) that can be used to authenticate subsequent requests. The application also has a separate authentication system for PHC users.




### Backend

- **FastAPI:** A modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints.
- **SQLAlchemy:** The Python SQL toolkit and Object Relational Mapper that gives application developers the full power and flexibility of SQL.
- **Pandas:** A fast, powerful, flexible, and easy-to-use open-source data analysis and manipulation tool.
- **Scikit-learn:** A free software machine learning library for the Python programming language.
- **Google Generative AI:** A suite of generative AI models from Google.
- **PostgreSQL:** A powerful, open-source object-relational database system.

### Frontend

- **HTML5, CSS3, JavaScript:** The standard technologies for building web pages.
- **Tailwind CSS:** A utility-first CSS framework for rapidly building custom user interfaces.
- **Spline:** A 3D design tool that allows you to create and export 3D scenes for the web.

## Setup and Installation

### Backend

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/medisense.git
   cd medisense/Backend
   ```

2. **Create a virtual environment and activate it:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the database:**
   - Make sure you have PostgreSQL installed and running.
   - Create a new database.
   - Copy the `.env.example` file to `.env` and update the `DATABASE_URL` with your database credentials.

5. **Run the application:**
   ```bash
   uvicorn main:app --reload
   ```

### Frontend

1. **Navigate to the `Frontend` directory:**
   ```bash
   cd ../Frontend
   ```

2. **Open the `index.html` file in your browser.**

## API Endpoints

The backend API provides the following endpoints:

- `GET /`: Welcome message.
- `POST /patients`: Create a new patient.
- `GET /patients`: Get a list of patients.
- `GET /patients/{patient_id}`: Get a specific patient.
- `PUT /patients/{patient_id}`: Update a patient.
- `DELETE /patients/{patient_id}`: Delete a patient.
- `POST /inventory`: Add a new item to the inventory.
- `GET /inventory`: Get the inventory.
- `GET /inventory/{item_id}`: Get a specific item from the inventory.
- `PUT /inventory/{item_id}`: Update an item in the inventory.
- `DELETE /inventory/{item_id}`: Delete an item from the inventory.
- `POST /restock-requests`: Create a new restock request.
- `GET /restock-requests`: Get a list of restock requests.
- `GET /workload`: Get the workload of the PHC.
- `POST /feedback`: Submit feedback.
- `POST /token`: Get an access token.

## Team

- **Aderoju Abdulsallam** - AI Engineer
- **Osokoya Fiyinfoluwa** - Frontend Developer
- **David Prince** - AI Engineer

