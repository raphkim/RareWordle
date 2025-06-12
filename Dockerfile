# Use the official Python image as a base
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY . .

# Expose the port that your Flask app runs on (Cloud Run will route traffic to this port)
EXPOSE 5000

# Define the command to run your Flask application
# Gunicorn is a production-ready WSGI HTTP Server.
# It's recommended over Flask's built-in development server for production.
# Install gunicorn: pip install gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]
