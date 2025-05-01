# bwai2025-recipe-generator

This repository is used for the session conducted at the **Build with AI 2025 - Pre-Solution Challenge** event, hosted collaboratively by several **GDG on Campus groups.** The event is held on May 3, 2025, at Google Startup Campus in Seoul, South Korea.

You can find the detailed hands-on lab kit at: [http://bwai-kit-1.gdghufs.com](http://bwai-kit-1.gdghufs.com)

---
**Disclaimer:** The content and code within this project are solely for the purpose of the aforementioned session and are not officially affiliated with, endorsed by, or representative of Google or Google Startup Campus.
---

This document guides you through setting up and running the project.

## Prerequisites

* Python 3.x must be installed.

## 1. Virtual Environment Setup (venv)

It is recommended to use a virtual environment to manage project dependencies.

* In the project root directory, run the following command to create a virtual environment named `venv`:

    ```bash
    python -m venv venv
    ```

## 2. Entering the Virtual Environment

You need to activate the created virtual environment.

* **Windows:**

    ```bash
    .\venv\Scripts\activate
    ```

* **macOS / Linux:**

    ```bash
    source venv/bin/activate
    ```

    Once activated, you should see `(venv)` at the beginning of your terminal prompt.

## 3. Package Installation

Install the necessary libraries required to run the project. All required packages are listed in the `requirements.txt` file.

* With the virtual environment activated, run the following command:

    ```bash
    pip install -r requirements.txt
    ```

## 4. Environment Variable Setup (.env file)

You need to create and configure a `.env` file for API keys and model settings.

1.  Create a `.env` file in the project root directory.

    * **Linux / macOS:**

        ```bash
        touch .env
        ```

    * **Windows (Command Prompt):**

        ```bash
        type nul > .env
        ```

    * **Windows (PowerShell):**

        ```bash
        New-Item -ItemType File .env
        ```

    * Alternatively, you can create the `.env` file manually using a text editor.

2.  Open the created `.env` file and add the following content, **modifying it according to your own environment**:

    ```dotenv
    # IMPORTANT: The GOOGLE_API_KEY below is an example. You MUST replace it with your own valid Google API key obtained for the workshop or your personal key.
    GOOGLE_API_KEY=3e2e77d7-88f1-4880-a20b-8c8559fb930e

    # Specify the Gemini model names to use. You can change these if needed.
    INGREDIENTS_MODEL_NAME=gemini-2.5-flash-preview-04-17
    RECIPE_MODEL_NAME=gemini-2.5-flash-preview-04-17
    IMAGE_MODEL_NAME=gemini-2.0-flash-exp-image-generation
    ```

    **Note:**
    * You **must enter your own Google API key** for `GOOGLE_API_KEY`. The example key will not work. Use the key provided during the session or your personal API key.
    * The `MODEL_NAME` variables specify the Gemini models used by the project. You can use the default values or change them to other supported model names as needed.

## 5. Running the Application (Flask Server)

Once all setup is complete, you can run the Flask development server to test the application.

* With the virtual environment activated, run the following command:

    ```bash
    python app.py
    ```

* If the server starts successfully, you will see messages similar to this in your terminal:

    ```
     * Serving Flask app 'app'
     * Running on [http://127.0.0.1:5000](http://127.0.0.1:5000) (Press CTRL+C to quit)
    ```

* Open your web browser and navigate to the address shown (usually `http://127.0.0.1:5000/`) to test the application.
