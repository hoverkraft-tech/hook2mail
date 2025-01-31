# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT="8000"
ENV SMTP_HOST="localhost"
ENV SMTP_PORT="25"
ENV USE_STARTTLS="true"
ENV USE_LOGIN="false"
ENV SMTP_USER=""
ENV SMTP_PASSWORD=""
ENV EMAIL_FROM="no-reply@example.com"
ENV EMAIL_TO="no-reply@example.com"

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Define the command to run the application
CMD ["python", "hook2mail.py"]
