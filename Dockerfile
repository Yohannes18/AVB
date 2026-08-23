FROM python:3.9-slim

# VULNERABILITY: Running as root
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads backup config

# VULNERABILITY: Exposing debug + debugger ports
EXPOSE 5000 5678

# VULNERABILITY: debug=True baked in
CMD ["python", "app.py"]
