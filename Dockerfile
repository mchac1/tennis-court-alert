# Use an official Playwright image that includes Chromium and dependencies
FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install the Playwright browser (Chromium) inside the container
RUN playwright install chromium --with-deps

# Copy only the Python script (and any other necessary source files)
# This guarantees the .env is left behind
COPY req_check.py .

# Set environment variables to ensure Python output is unbuffered (for logs)
ENV PYTHONUNBUFFERED=1

# Command to run your script
CMD ["python", "req_check.py"]