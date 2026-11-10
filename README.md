# 🎾 Tennis Court Availability Bot

A Python script that automates checking for open tennis court reservations at the City of Regina (via the ActiveCommunities platform). It generates a cleanly formatted report for the next 4 days and sends it directly to a Discord channel via a webhook.

## ✨ Features
*   **Dynamic Token Handling:** Uses Playwright (headless Chromium) to automatically fetch fresh CSRF tokens and session cookies, preventing expired session errors.
*   **4-Day Outlook:** Checks availability for today, tomorrow, and the next two days.
*   **Prime Time Highlighting:** Marks highly desirable weekday slots (after 5:00 PM) with a star (⭐) instead of a checkmark (✅).
*   **Smart Output:** If a court has no availability, it explicitly says so. If *no courts* are available at all for a given day, it economizes the output to a single line.
*   **Dockerized:** Fully containerized for easy deployment on any system (Windows, Linux, Mac) without dealing with local Python or Playwright dependencies.
*   **Logging:** Outputs detailed, timestamped logs to both the console and an `availability.log` file.
*   **Tested & Automated:** Includes a `pytest` suite and `pre-commit` hooks to ensure code quality before every commit.

## 🛠️ Prerequisites
*   Python 3.10+ (if running locally)
*   [Docker](https://docs.docker.com/get-docker/) (Recommended for easiest deployment)
*   A Discord Server and a [Webhook URL](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks)

## ⚙️ Configuration

This project uses environment variables for configuration and secrets. 

1. Duplicate the `.env.example` file and rename the copy to `.env`.
2. Open `.env` and fill in your specific details.

## 🚀 Usage

### Option 1: Using Docker (Recommended)
If you have Docker installed, you don't need Python or Playwright on your host machine. 

**Build the image:**
```bash
docker build -t tennis-alert-bot .
```

**Run the container (passing your `.env` file at runtime):**
```bash
docker run --rm --env-file .env tennis-alert-bot
```

### Option 2: Running Locally
If you prefer to run the script directly on your machine, install the production dependencies and the Playwright browser:

1. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
2. Install the Playwright Chromium browser:
   ```bash
   playwright install chromium
   ```
3. Run the script:
   ```bash
   python req_check.py
   ```

## 🧑‍💻 Development & Testing

If you want to modify the code or contribute, you should install the development dependencies.

1. **Install development dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Run the test suite:**
   ```bash
   pytest
   ```

3. **Enable pre-commit hooks (Optional but recommended):**
   Install the git hooks so that tests run automatically every time you commit:
   ```bash
   pre-commit install
   ```
   *(To bypass the hook in an emergency, use `git commit -m "message" --no-verify`)*

## 📅 Automation
This script is designed to be run once a day. 
*   **On Windows:** Use the **Task Scheduler** to run the script or the `docker run` command daily.
*   **On Linux:** Use **cron** to schedule the docker command (e.g., `0 12 * * * docker run --rm --env-file /path/to/.env tennis-alert-bot`). *Note: Ensure the `TZ` variable is set in your `.env` file so the container calculates "today" correctly.*