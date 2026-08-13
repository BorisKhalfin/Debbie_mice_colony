FROM python:3.11-slim

WORKDIR /app

# Connecting everything
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Taking the code
COPY Debbie_mice_colony.py .

# Opening port for Streamlit
EXPOSE 8501

# Running Streamlit
CMD ["python", "-m", "streamlit", "run", "Debbie_mice_colony.py", "--server.port=8501", "--server.address=0.0.0.0"]
