# Facebook Screenshot PDF Generator

A Python tool that automatically organizes Facebook screenshots into professionally formatted PDF reports with AI-powered content analysis and context extraction.

## 🚀 Main Features

### **Intelligent Content Analysis**
- **OCR Text Extraction**: Automatically extracts text from screenshots using Tesseract OCR
- **AI-Powered Page Detection**: Uses local Mistral LLM to identify Facebook pages, groups, or individual posters
- **Smart Context Summarization**: Generates concise 3-sentence summaries including main content and commenter sentiment
- **Poster vs. Commenter Detection**: Distinguishes between original posters and commenters/reactions

### **Professional PDF Generation**
- **Date-Based Organization**: Automatically groups screenshots by date from filename timestamps
- **Dynamic Filename Generation**: Creates descriptive filenames like `LilibethLaygo - August 1 - August 26.pdf`
- **Responsive Layout**: Fits 3 images per page in landscape A4 format with proper aspect ratio preservation
- **Multi-Page Support**: Handles large collections with automatic pagination

### **Robust Text Processing**
- **Unicode Safety**: Handles special characters and emojis for PDF compatibility
- **Fallback Mechanisms**: Multiple layers of error handling for OCR and AI processing
- **Content Filtering**: Removes Facebook UI noise (timestamps, reactions, sponsored labels)

## 📋 Prerequisites

- Python 3.7+
- Tesseract OCR installed
- Ollama running with Mistral model
- Facebook screenshots with timestamp naming format: `Screenshot_YYYY-MM-DD-HH-MM-SS-xxx`

## 🛠️ Dependencies

```bash
pip install pillow pytesseract fpdf2 ollama
```

## ⚙️ Configuration

Edit the config section in the script:

```python
user_name = "NickoLaygo"  # user name for PDF filename
images_folder = "screenshots"        # Your screenshot folder
images_per_page = 3                 # Images per PDF page
ollama_model = "mistral:latest"     # AI model for analysis
```

## 🎯 Use Cases

- **Social Media Monitoring**: Track Facebook page activities and community responses
- **Content Documentation**: Archive important posts and discussions for reference
- **Research & Analysis**: Organize social media content for academic or business research
- **Digital Evidence**: Create organized reports of online interactions
- **Community Management**: Document group activities and member engagement

## 📁 Output Structure

Each PDF page contains:
- **Date Header**: Organized by screenshot date
- **Visual Content**: Up to 3 screenshots per page with preserved aspect ratios
- **Source Attribution**: Identified Facebook page/group/poster name
- **Context Summary**: AI-generated summary of post content and commenter reactions

## 🔧 How It Works

1. **Screenshot Collection**: Reads timestamped screenshots from specified folder
2. **Date Grouping**: Organizes images by extracted dates from filenames
3. **OCR Processing**: Extracts text content from each screenshot
4. **AI Analysis**: Uses Mistral LLM to identify posters and summarize content
5. **PDF Generation**: Creates formatted landscape PDF with images and context
6. **Smart Naming**: Generates descriptive filename based on date range

## 🎨 Sample Output

```
Page: One Batangas
Context: This post is an announcement about upcoming road maintenance in CALABARZON. 
Commenters are generally supportive but express concerns about traffic impact. 
Overall sentiment shows community cooperation despite inconvenience.
```

## 🔒 Privacy & Local Processing

- All AI processing happens locally using Ollama
- No data sent to external APIs
- Screenshots remain on your local machine
- Perfect for sensitive or private content documentation

## 📈 Technical Highlights

- **Modular Design**: Clean separation of OCR, AI analysis, and PDF generation
- **Error Resilience**: Multiple fallback strategies for robust processing
- **Memory Efficient**: Processes images in chunks to handle large collections
- **Format Flexibility**: Easily configurable layout and styling options

---

*Transform your scattered Facebook screenshots into organized, searchable documentation with intelligent context analysis.*"# Facebook-Screenshot-PDF-Automation" 
