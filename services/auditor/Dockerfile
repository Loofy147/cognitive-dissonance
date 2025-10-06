# Use the official Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the service's source code
COPY ./services /app/services

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "services.auditor.main:app", "--host", "0.0.0.0", "--port", "8000"]