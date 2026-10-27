\# KisaanSaathi 🌾

\### AI-Powered Agricultural Scheme \& Farmer Support Assistant



KisaanSaathi is an AI-powered platform designed to help Indian farmers navigate agricultural schemes, understand required documents, and explore possible support options during financial distress. It combines a user-friendly web interface with a Python backend and retrieval-augmented generation (RAG) to make agricultural information easier to access.



\## 🎯 Problem Statement



Farmers often struggle to find reliable information about government schemes, eligibility requirements, documentation, crop-related risks, and financial support. Information can be scattered across multiple official documents and portals, making it difficult to identify the right next step.



\## 💡 Our Solution



KisaanSaathi aims to simplify this process through:



\- \*\*AI-powered assistance:\*\* Ask questions about agricultural schemes and farmer support.

\- \*\*Knowledge retrieval:\*\* Retrieve relevant information from a curated collection of agricultural resources.

\- \*\*Scheme discovery:\*\* Explore information about schemes such as PM-KISAN and the Pradhan Mantri Fasal Bima Yojana (PMFBY).

\- \*\*Document guidance:\*\* Understand common documentation requirements.

\- \*\*Farmer support resources:\*\* Explore crop-risk profiles, distress scenarios, and available support information.

\- \*\*Accessible interface:\*\* A React-based web experience designed around farmers' needs.



\*The information provided is intended for guidance. Users should verify eligibility, deadlines, and scheme details with the relevant official authorities.\*



\## 🛠️ Tech Stack



\*\*Frontend\*\*

\- React

\- Vite

\- JavaScript

\- CSS



\*\*Backend\*\*

\- Python

\- Flask

\- REST APIs



\*\*AI \& Knowledge Retrieval\*\*

\- Retrieval-Augmented Generation (RAG)

\- Document ingestion and text extraction

\- Text chunking and retrieval

\- Curated agricultural scheme resources



\*\*Testing \& Data\*\*

\- Python testing tools

\- SQLite for local knowledge storage, where configured



\## 🏗️ Project Structure



```text

KisanSathi/

├── backend/

│   ├── app.py

│   ├── rag.py

│   ├── retriever.py

│   ├── embed\_and\_upload.py

│   ├── requirements.txt

│   ├── knowledge/

│   │   ├── document\_ingestion.py

│   │   ├── document\_extraction.py

│   │   ├── chunking.py

│   │   └── authoritative\_documents/

│   ├── resources/

│   │   └── migrations/

│   └── schemes/

├── frontend/

│   ├── src/

│   │   ├── components/

│   │   ├── context/

│   │   ├── data/

│   │   ├── pages/

│   │   └── services/

│   ├── public/

│   ├── package.json

│   └── .env.example

├── tests/

├── .gitignore

└── README.md

```



\## ⚙️ Getting Started



\### Prerequisites



\- Python 3.10 or a compatible version supported by the backend dependencies

\- Node.js and npm

\- Git



\### 1. Clone the repository



```bash

git clone https://github.com/rutuja3305/KisaanSaathi.git

cd KisaanSaathi

```



\### 2. Set up the backend



Open a terminal in the project root:



```powershell

cd backend

python -m venv venv

.\\venv\\Scripts\\Activate.ps1

pip install -r requirements.txt

```



Configure the required environment variables using the backend's configuration and `.env` conventions. Never commit real API keys or credentials.



Start the Flask application:



```powershell

python app.py

```



Check the terminal output for the local server address and any required setup steps.



\### 3. Set up the frontend



Open a second terminal:



```powershell

cd frontend

npm install

npm run dev

```



Open the local URL displayed by Vite in your browser.



> Ensure the frontend API configuration points to the running backend. Refer to the frontend environment example and the API service configuration.



\## 🧪 Running Tests



From the project root, activate an environment with the required Python dependencies installed, then run:



```powershell

python -m pytest tests/

```



Some tests may require additional dependencies or configured test data. Review the test output for setup requirements.



\## 📚 Knowledge Resources



The backend includes a document-processing pipeline and a collection of agricultural knowledge resources. The repository contains documentation and source materials related to agricultural schemes, including PM-KISAN, PMFBY, and MahaDBT agriculture.



For scheme-related decisions, always consult the relevant official government portal because eligibility criteria and scheme rules may change.



\## 🔐 Security \& Configuration



\- Keep API keys, passwords, and private environment files out of version control.

\- Use `.env.example` only for placeholder configuration values.

\- Do not commit virtual environments, dependency folders, local databases, or generated files unless explicitly required.

\- Review official source documents and their redistribution permissions before publishing them.



\## 🚧 Future Enhancements



\- Multilingual assistance for Indian farmers

\- Improved retrieval relevance and answer grounding

\- Clear source citations for generated answers

\- More comprehensive scheme eligibility guidance

\- Better support for document uploads and farmer-specific information

\- Deployment and usability improvements for low-connectivity environments



\## 👩‍💻 Author



\*\*Rutuja Jabras\*\*



Developed as an AI-enabled agricultural support project focused on improving access to useful scheme information and farmer resources.



\## 📄 Disclaimer



KisaanSaathi is an informational project and is not an official government service, financial adviser, or substitute for professional agricultural or legal advice. Users should independently verify information with authorized sources.



