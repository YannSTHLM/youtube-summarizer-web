# YouTube Transcript Summarizer - Web App

A beautiful web application that monitors YouTube channels and generates AI-powered summaries from video transcripts. Designed for easy deployment on Vercel.

![Web App Screenshot](screenshot.png)

## Features

- 🎨 **Modern Web Interface** - Clean, responsive design
- 📺 **Multi-Channel Support** - Process up to 20+ channels at once
- 📝 **Real-Time Progress** - Live updates while processing
- 🤖 **AI Summaries** - Powered by OpenAI GPT-4
- 📥 **Download Summaries** - Save as text files
- ☁️ **Vercel Ready** - Free hosting on Vercel

## Quick Start

### 1. Clone or Download

Save this project to your computer:
```
youtube_summarizer_web/
├── api/
│   ├── index.py
│   ├── youtube_fetcher.py
│   ├── transcript_extractor.py
│   └── summarizer.py
├── public/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── vercel.json
├── requirements.txt
└── README.md
```

### 2. Deploy to Vercel (Recommended)

#### Option A: Deploy with Vercel CLI

```bash
# Install Vercel CLI
npm install -g vercel

# Login to Vercel
vercel login

# Deploy
vercel

# Follow the prompts
```

#### Option B: Deploy via GitHub

1. Push this project to a GitHub repository
2. Go to [vercel.com](https://vercel.com)
3. Click "New Project"
4. Import your GitHub repository
5. Click "Deploy"

### 3. Configure Environment Variables

After deploying, add your API keys:

1. Go to your project on Vercel Dashboard
2. Click "Settings" → "Environment Variables"
3. Add these variables:

| Variable | Description |
|----------|-------------|
| `YOUTUBE_API_KEY` | Your YouTube Data API v3 key |
| `OPENAI_API_KEY` | Your OpenAI API key |

### 4. Get API Keys

#### YouTube Data API v3 Key:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable "YouTube Data API v3"
4. Go to Credentials → Create API Key

#### OpenAI API Key:
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign in and go to API Keys
3. Create a new secret key

### 5. Access Your App

After deployment, Vercel will give you a URL like:
```
https://youtube-summarizer.vercel.app
```

Open this URL in your browser to use the app!

## Local Development

### Prerequisites
- Python 3.8+
- pip

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "YOUTUBE_API_KEY=your_key_here" > .env
echo "OPENAI_API_KEY=your_key_here" >> .env

# Run locally
cd api
uvicorn index:app --reload --port 8000
```

Then open `public/index.html` in your browser, or use a local server:

```bash
# In another terminal
cd public
python -m http.server 3000
```

Visit `http://localhost:3000`

## Usage

1. **Enter YouTube Channels** - Add channel IDs, URLs, or @handles (one per line)
2. **Click Process** - The app will fetch today's videos from each channel
3. **View Summaries** - AI-generated summaries appear in real-time
4. **Download** - Save summaries as text files

### Channel Input Formats

You can enter channels in any of these formats:
```
UC_x5XG1OV2P6uZZ5FSM9Ttw
https://www.youtube.com/@channelname
@channelhandle
```

### Example Channels to Try

```
UC_x5XG1OV2P6uZZ5FSM9Ttw
@3Blue1Brown
@mkbhd
@veritasium
```

## How It Works

1. **Fetch Videos** - Gets videos uploaded today from each channel
2. **Extract Transcripts** - Downloads video transcripts/captions
3. **Generate Summaries** - Uses OpenAI to create concise summaries
4. **Display Results** - Shows summaries with download options

## Configuration

### Vercel Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `YOUTUBE_API_KEY` | Yes | - | YouTube Data API v3 key |
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4` | OpenAI model to use |
| `MAX_SUMMARY_TOKENS` | No | `500` | Max tokens for summary |

## Limitations

- **Vercel Timeout**: Serverless functions have a 60-second timeout limit
- **YouTube Quotas**: YouTube API has daily usage quotas
- **Transcript Availability**: Not all videos have transcripts available
- **Processing Time**: Processing 20 channels may take several minutes

## Troubleshooting

### "API key not configured"
- Make sure you've added environment variables in Vercel Dashboard
- Redeploy after adding environment variables

### "No videos found"
- The app only processes videos uploaded **today**
- Try channels that upload frequently

### "Transcript not available"
- Not all videos have captions/transcripts enabled
- The app will note which videos don't have transcripts

### Timeout errors
- Process fewer channels at once
- Videos with long transcripts may take longer to summarize

## API Endpoints

The backend provides these endpoints:

- `GET /` - Health check
- `POST /api/process` - Process channels
- `GET /api/status` - Get processing status
- `GET /api/config/check` - Check API key configuration

## License

This project is provided as-is for personal use.

## Credits

- YouTube Data API for video metadata
- youtube-transcript-api for transcript extraction
- OpenAI for AI summarization
- FastAPI for the backend
- Vercel for hosting