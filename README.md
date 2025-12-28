# WhatsApp AI Agent

A WhatsApp chatbot powered by Google Gemini AI, built with FastAPI. This bot can receive messages via WhatsApp Business API, process them through AI, and respond intelligently with security guardrails.

## Features

- 🤖 **AI-Powered Responses**: Uses Google Gemini 2.5 Flash for intelligent conversations
- 🔒 **Security Guardrails**: Implements Guardrails AI for prompt injection protection and content filtering
- 💬 **WhatsApp Integration**: Full integration with WhatsApp Business Cloud API
- 📊 **Database Storage**: Stores chat history in Appwrite database
- 🛡️ **Input Validation**: Comprehensive input sanitization and validation
- 📝 **Chat History**: Maintains conversation context for better responses

## Prerequisites

- Python 3.8 or higher
- Appwrite account and project
- Google AI API key (Gemini)
- WhatsApp Business Account (for WhatsApp integration)
- Meta Developer Account (for WhatsApp Cloud API)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/PavansaiVellanki/whatsapp_agent.git
cd whatsapp_agent/backend
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Guardrails AI Validators (Optional but Recommended)

```bash
guardrails hub install hub://guardrails/detect_jailbreak
guardrails hub install hub://guardrails/toxic_language
```

## Configuration

### 1. Create `.env` File

Create a `.env` file in the `backend/` directory with the following variables:

```env
# Appwrite Configuration
APPWRITE_ENDPOINT=https://cloud.appwrite.io/v1
APPWRITE_SECRET=your_appwrite_secret_key
APPWRITE_PROJECT_ID=your_appwrite_project_id
APPWRITE_DATABASE=your_database_id
APPWRITE_DATABASE_CHATS_TABLE=your_chats_table_id

# Google AI Configuration
GOOGLE_API_KEY=your_google_ai_api_key

# WhatsApp Cloud API Configuration (Optional - for WhatsApp integration)
WHATSAPP_PROJECT_ID=your_whatsapp_project_id
WHATSAPP_SECRET_KEY=your_whatsapp_app_secret
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id
WHATSAPP_BUSINESS_PHONE_ID=your_phone_number_id
WHATSAPP_BOT_PHONE_NUMBER=your_bot_phone_number
WHATSAPP_VERIFY_TOKEN=your_custom_verify_token
```

### 2. How to Get API Keys

#### Appwrite Setup

1. Go to [Appwrite Cloud](https://cloud.appwrite.io) or use self-hosted
2. Create a new project
3. Go to **Settings** → **API Keys**
4. Create a new API key with **Databases** permissions
5. Copy the **Secret Key** and **Project ID**
6. Create a database and table for chats
7. Copy the **Database ID** and **Table ID**

#### Google AI API Key

1. Go to [Google AI Studio]
2. Create a new API key
3. Copy the key to `GOOGLE_API_KEY` in `.env`

#### WhatsApp Business API Setup

1. Go to [Meta for Developers](https://developers.facebook.com)
2. Create a new app → Select **Business** type
3. Add **WhatsApp** product
4. Get your credentials:
   - **App ID** → `WHATSAPP_PROJECT_ID`
   - **App Secret** → `WHATSAPP_SECRET_KEY`
   - **Access Token** → `WHATSAPP_ACCESS_TOKEN` (generate from API Setup)
   - **Business Account ID** → `WHATSAPP_BUSINESS_ACCOUNT_ID`
   - **Phone Number ID** → `WHATSAPP_BUSINESS_PHONE_ID` (from API Setup)
   - **Bot Phone Number** → `WHATSAPP_BOT_PHONE_NUMBER`
   - **Verify Token** → `WHATSAPP_VERIFY_TOKEN` (create your own secure string)

## Database Initialization

Before running the application, you need to initialize the Appwrite database.

### Step 1: Run Database Initialization Script

```bash
python init_database.py
```

This script will:

- Connect to your Appwrite instance using credentials from `.env`
- Create the `chats` table if it doesn't exist
- Set up required columns:
  - `user_phone` (string, max 20 chars) - Stores the user's phone number
  - `role` (enum: "bot" or "user") - Identifies message sender
  - `message` (text, max 1MB) - Stores the message content

### Step 2: Verify Database Setup

After running the script, verify in Appwrite Console:

1. Go to your project → **Databases**
2. Check that the `chats` table exists
3. Verify the columns are created correctly:
   - `user_phone` (string)
   - `role` (enum with values: "bot", "user")
   - `message` (string)

**Note**: Column creation may take a few moments. Wait before using the table.

## Running the Application

### Development Mode

```bash
python main.py
```

The server will start on `http://localhost:8000`

### Production Mode

For production, use a proper ASGI server:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

## WhatsApp Webhook Setup

### 1. Subscribe Your App to WhatsApp Business Account

```bash
curl -X POST \
  "https://graph.facebook.com/v22.0/{WHATSAPP_BUSINESS_ACCOUNT_ID}/subscribed_apps" \
  -H "Authorization: Bearer {WHATSAPP_ACCESS_TOKEN}"
```

Replace `{WHATSAPP_BUSINESS_ACCOUNT_ID}` and `{WHATSAPP_ACCESS_TOKEN}` with your values.

### 2. Configure Webhook in Meta Console

1. Go to **Meta Developer Console** → Your App → **WhatsApp** → **Configuration**
2. Under **Webhooks**, click **Configure**
3. Set **Callback URL**: `https://your-domain.com/webhook`
4. Set **Verify Token**: Same as `WHATSAPP_VERIFY_TOKEN` in your `.env`
5. Subscribe to **messages** field (toggle ON)
6. Click **Verify and Save**

### 3. For Local Development (using ngrok)

```bash
# Install ngrok: https://ngrok.com/download
ngrok http 8000

# Use the ngrok HTTPS URL as your webhook URL
# Example: https://abc123.ngrok-free.dev/webhook
```

### 4. Add Test Phone Numbers

In **Test Mode**, you can only send messages to registered test recipients:

1. Go to **WhatsApp** → **API Setup**
2. Under **To** field, add your phone number
3. Verify with the code sent to your phone

**Note**: For production use, complete business verification to send messages to any phone number.

## API Endpoints

### Health Check

```
GET /health
```

### Root

```
GET /
```

### Chat API

```
POST /api/v1/chat
Body: {"message": "Hello"}
```

```
GET /api/v1/chat/history?limit=50&user_phone=1234567890
```

```
POST /api/v1/chat/message
Body: {"user_phone": "1234567890", "role": "user", "message": "Hello"}
```

### WhatsApp Webhook

```
GET /webhook (verification - used by Meta)
POST /webhook (incoming messages from WhatsApp)
```

### Test Endpoints

```
GET /test
POST /test/send?phone=1234567890&message=Hello
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py              # FastAPI app initialization
│   ├── database/
│   │   └── init_db.py           # Database initialization logic
│   ├── models/
│   │   └── chat.py              # Pydantic models for chat messages
│   ├── routes/
│   │   ├── chat.py              # Chat API routes
│   │   └── whatsapp.py          # WhatsApp webhook routes
│   ├── services/
│   │   ├── ai_service.py        # Google Gemini AI service
│   │   ├── appwrite_service.py  # Appwrite database service
│   │   ├── guardrails_service.py # Security guardrails
│   │   └── whatsapp_service.py   # WhatsApp API service
│   └── utils/
│       ├── config.py             # Configuration management
│       └── constants.py          # Constants
├── init_database.py              # Database setup script
├── main.py                       # Application entry point
├── requirements.txt              # Python dependencies
├── instructions.py               # AI system prompt
└── .env                          # Environment variables (not in git)
```

## Security Features

- **Prompt Injection Protection**: Detects and blocks jailbreak attempts
- **Content Filtering**: Filters toxic language and profanity
- **Input Sanitization**: Cleans and validates all user inputs
- **Response Validation**: Validates AI responses before sending
- **Webhook Signature Verification**: Verifies WhatsApp webhook authenticity

## Troubleshooting

### Database Connection Issues

- Verify Appwrite credentials in `.env`
- Check if database and table exist in Appwrite Console
- Ensure API key has proper permissions
- Run `python init_database.py` to create tables

### WhatsApp Webhook Not Receiving Messages

- Verify webhook URL is publicly accessible
- Check if app is subscribed to WhatsApp Business Account
- Ensure "messages" field is subscribed in Meta Console
- Verify webhook signature in logs
- Check Meta Console → Recent deliveries for errors

### Access Token Expired

- Generate new access token from Meta Console
- Update `WHATSAPP_ACCESS_TOKEN` in `.env`
- Restart the application

### Test Mode Limitations

- In test mode, only registered test recipients can send messages
- Add phone numbers in Meta Console → WhatsApp → API Setup
- For production, complete business verification

### Guardrails AI Not Working

- Install Guardrails AI: `pip install guardrails-ai`
- Install validators: `guardrails hub install hub://guardrails/detect_jailbreak hub://guardrails/toxic_language`
- The app will use fallback validation if Guardrails AI is not installed

## Development

### Running Tests

```bash
# Add test files and run
pytest
```

### Code Formatting

```bash
black .
isort .
```

## Environment Variables Summary

### Required Variables

- `APPWRITE_SECRET` - Appwrite API secret key
- `APPWRITE_PROJECT_ID` - Appwrite project ID
- `APPWRITE_DATABASE` - Appwrite database ID
- `APPWRITE_DATABASE_CHATS_TABLE` - Appwrite chats table ID
- `GOOGLE_API_KEY` - Google AI API key

### Optional Variables (for WhatsApp)

- `WHATSAPP_ACCESS_TOKEN` - WhatsApp access token
- `WHATSAPP_BUSINESS_PHONE_ID` - WhatsApp phone number ID
- `WHATSAPP_BOT_PHONE_NUMBER` - Bot phone number
- `WHATSAPP_SECRET_KEY` - WhatsApp app secret (for webhook verification)
- `WHATSAPP_VERIFY_TOKEN` - Webhook verify token
- `WHATSAPP_BUSINESS_ACCOUNT_ID` - Business account ID
- `WHATSAPP_PROJECT_ID` - WhatsApp project ID
